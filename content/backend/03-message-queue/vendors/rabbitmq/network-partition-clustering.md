---
title: "RabbitMQ Network Partition 與 Cluster 一致性：腦裂下要保誰"
date: 2026-06-16
description: "RabbitMQ Erlang cluster 在 network partition 下的行為與處置 — disc/ram node 拓樸、cluster_partition_handling 三策略（ignore / pause_minority / autoheal）的可用性與一致性取捨、腦裂偵測機制、quorum queue 在失去 quorum 時的 Raft 行為。含 3-node OrbStack 實機演練（pause_minority 暫停少數派、quorum queue 失去 quorum 後寫入阻塞、classic queue 同情境續寫對照）。"
weight: 14
tags: ["backend", "message-queue", "rabbitmq", "cluster", "network-partition", "split-brain", "deep-article"]
---

> 本文是 [RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/) overview「Erlang clustering 與 network partition」段的 implementation-layer deep article。Overview 回答「RabbitMQ cluster 是什麼、跟同類 broker 差在哪」；本文回答「partition 發生時 broker 怎麼決策、各策略保住什麼、丟掉什麼」。

Network partition 是 cluster 節點之間的網路連線中斷、雙方各自仍存活但互相不可達的狀態。RabbitMQ cluster 建立在 Erlang distribution 之上、節點靠固定心跳（net_tick）互相確認存活；心跳連續數次收不到、Erlang 就判定對方失聯、把單一 cluster 切成兩個互不知道對方狀態的子群。此時的核心問題不是「怎麼避免 partition」——跨機房、跨 AZ、雲端 VPC 路由抖動都會造成短暫不可達、partition 在分散式系統是必然會遇到的物理事件——而是「分裂的瞬間、broker 要犧牲可用性保一致性、還是犧牲一致性保可用性」。`cluster_partition_handling` 設定就是這個取捨的開關。

## 問題情境：兩邊都覺得自己是對的

腦裂（split-brain）的破壞性在於分裂的兩個子群各自繼續服務、各自接受寫入、各自認為對方已死。等到網路恢復、兩邊的狀態已經分歧：同一個 queue 在 A 子群被消費掉的訊息、在 B 子群還在；同一個 exchange 的 binding 在兩邊被改成不同樣子；同一筆業務在兩邊各被處理一次。

RabbitMQ 的 classic queue 沒有內建的衝突解決機制。當兩個子群在 partition 期間各自修改了 cluster metadata（queue / exchange / binding 的定義）、恢復連線後 RabbitMQ 無法自動合併這些分歧、預設行為是 *拒絕自動重新加入*、把節點停在 partition 狀態等人工處置。這就是為什麼 partition handling 策略的選擇、本質是「願意在分裂瞬間付出什麼代價、來換取恢復時的可預測性」。

這個取捨跟 [3.6 processing semantics 與 recovery semantics](/backend/03-message-queue/processing-recovery-semantics/) 的判斷同源：投遞成功、處理成功、恢復成功是三件事。Partition 期間「broker 還在收訊息」（投遞層可用）不代表「訊息會被正確處理一次」（處理層一致）、更不代表「partition 結束後狀態能無損合併」（恢復層一致）。

## 核心概念一：disc node 與 ram node

RabbitMQ cluster 的每個節點承擔一種角色、決定它存哪些資料。Cluster metadata（vhost、user、exchange、queue 定義、binding）在所有節點間複製、但 *持久化到磁碟* 與否分兩種：

| 節點類型  | metadata 存放 | 適用場景                                    |
| --------- | ------------- | ------------------------------------------- |
| Disc node | 記憶體 + 磁碟 | 預設、cluster 必須至少有一個                |
| Ram node  | 僅記憶體      | metadata 變更極頻繁的特殊場景、現代極少使用 |

Disc node 把 cluster metadata 寫到磁碟、整個 cluster 重啟後能從磁碟恢復拓樸定義。Ram node 只把 metadata 放記憶體、metadata 操作（宣告大量 queue / binding）較快、但 cluster 若全部節點同時掛掉就會遺失定義。

Ram node 是早期為了加速高頻 metadata 變更而設計的角色。實務上現代 RabbitMQ 部署幾乎都用全 disc node：metadata 操作的效能瓶頸在現代硬體上不再顯著、而全 disc 換來的「任意節點重啟都能恢復拓樸」的可預測性、價值遠高於那點 metadata 寫入速度。官方文件也建議 cluster 內 disc node 至少兩個、避免唯一的 disc node 掛掉時整個 cluster 的 metadata 無法持久化。

本文實機演練的 3-node cluster 全部是 disc node、這也是 `rabbitmqctl cluster_status` 在 OrbStack 上的實際輸出：

```text
Disk Nodes
rabbit@rmq1
rabbit@rmq2
rabbit@rmq3
```

要特別區分的是：disc / ram 講的是 *cluster metadata* 的持久化、跟 *訊息本身* 是否持久化（durable queue + persistent message）是兩個獨立軸。Disc node 不會讓 transient queue 的訊息變持久、ram node 也不會讓 durable queue 的訊息變揮發。訊息持久化的判讀見 [3.2 durable queue](/backend/03-message-queue/durable-queue/)。

## 核心概念二：partition 偵測機制

RabbitMQ 不自己實作節點存活偵測、而是直接用 Erlang distribution 的 net_tick 機制。每個節點對 cluster 內其他節點定期送 tick、`net_ticktime` 預設 60 秒；連續數個 tick interval（預設約 4 個、即 net_ticktime 區間內）收不到對方回應、Erlang 就判定該節點 `nodedown`、向上層的 RabbitMQ partition handler 報告。

這個機制有兩個實務後果。第一、partition 偵測有 *延遲*：短於 net_ticktime 的網路抖動（幾秒的 GC pause、瞬間封包遺失）不會觸發 partition、避免把暫時性抖動誤判成永久分裂。第二、偵測延遲是雙刃：net_ticktime 設太長、真的 partition 了也要等很久才反應、期間腦裂持續擴大；設太短、雲端環境正常的網路抖動會頻繁誤觸發 partition handler、造成不必要的節點暫停。

本文實機演練用 `docker network disconnect` 切斷一個節點的網路、實測偵測延遲：disconnect 後約 60 秒（吻合 net_ticktime 預設值）、多數派側的 `cluster_status` 的 Running Nodes 才從三個掉到兩個：

```text
disconnect 後立即查 → Running Nodes 仍顯示 3 個（尚未偵測）
等待約 60 秒 → Running Nodes 掉到 2 個（partition 已偵測）
```

偵測到 partition 之後、broker 怎麼處置、完全取決於 `cluster_partition_handling` 設定。

## 核心概念三：cluster_partition_handling 三策略

這個設定決定 broker 在偵測到 partition 後的行為、是整個 cluster 一致性與可用性取捨的單一開關。三種策略對應三種不同的 CAP 立場。

| 策略             | partition 時行為                           | 保住     | 犧牲             | 適用                      |
| ---------------- | ------------------------------------------ | -------- | ---------------- | ------------------------- |
| `ignore`         | 兩邊都繼續服務、不做任何處置               | 可用性   | 一致性（會腦裂） | 單機 / 不在乎一致性的場景 |
| `pause_minority` | 少數派節點暫停 broker、多數派繼續          | 一致性   | 少數派可用性     | 奇數節點 cluster（推薦）  |
| `autoheal`       | partition 結束後自動選贏家、輸家重啟丟狀態 | 自動恢復 | 輸家側的訊息     | 可容忍少量訊息遺失的場景  |

設定方式在 `rabbitmq.conf`：

```ini
cluster_partition_handling = pause_minority
```

或在舊版 advanced config（Erlang term 格式）：

```erlang
[
  {rabbit, [
    {cluster_partition_handling, pause_minority}
  ]}
].
```

三個策略的差異不在「哪個比較好」、而在「分裂瞬間願意讓誰停下來」。下面三段把每個策略在真實服務裡長什麼樣展開。

### ignore：兩邊都活、恢復時等人來

`ignore` 是預設值（OrbStack 起的 cluster `rabbitmqctl environment` 實測輸出 `{cluster_partition_handling, ignore}`）。它的行為是 partition 偵測到了、但 broker 什麼都不做、兩個子群繼續各自服務。

這在單節點部署完全沒問題——沒有 cluster 就沒有 partition。問題出在多節點 cluster：兩個子群會各自接受 publish、各自讓 consumer 消費、各自修改 metadata。網路恢復後、RabbitMQ 偵測到兩邊狀態分歧、會把節點停在 partition 狀態、不自動重新加入、在 log 留下 partition 警告等人工介入。此時 metadata 已經分歧、需要人工決定保留哪一邊、reset 另一邊重新 join。

`ignore` 適合的場景很窄：單機部署、或刻意接受腦裂並在應用層做衝突解決的特殊架構。多數需要 cluster 的場景不該用 `ignore`——它把一致性的責任完全推給人工處置、而人工處置在凌晨三點的 incident 現場是最不可靠的環節。

### pause_minority：少數派主動停下

`pause_minority` 是奇數節點 cluster 的推薦策略、它的設計直接對應 quorum 的數學：partition 把 cluster 切成兩半時、節點數較少的那一側（少數派）主動 *暫停自己的 broker*、停止接受任何 client 連線；節點數較多的那一側（多數派）繼續服務。

這保證了任何時刻最多只有一個子群在服務、從根本上杜絕腦裂。代價是少數派側的所有 client 在 partition 期間完全失去服務。

3-node cluster 是這個策略的最小有效配置。實機演練：把 rmq3 從 network disconnect、製造「rmq1 + rmq2 多數派 vs rmq3 少數派」的分裂、約 60 秒後查少數派 rmq3 的狀態：

```text
$ rabbitmqctl cluster_status   # 在被孤立的 rmq3 上執行
Error: this command requires the 'rabbit' app to be running on the target node.
       Start it with 'rabbitmqctl start_app'.
```

少數派 rmq3 的 rabbit 應用被 partition handler 主動停止——這正是 pause_minority 的預期行為。同時多數派側 rmq1 的 cluster_status 顯示 Running Nodes 只剩 rmq1 + rmq2、繼續正常服務。

恢復也是自動的。把 rmq3 重新 network connect、約 15 秒後它自動重啟 rabbit 應用、重新加入 cluster、Running Nodes 回到三個、Network Partitions 顯示 `(none)`、無殘留 partition 需要人工處置。這是 pause_minority 相對 ignore 的關鍵優勢：恢復路徑自動化、不依賴凌晨的人工判斷。

pause_minority 有一個硬性前提：cluster 必須是奇數節點、且要能形成明確的多數。2-node cluster 用 pause_minority 是反模式——partition 時兩邊各 1 個、都不是多數、結果兩邊都暫停、整個 cluster 完全不可用。4-node cluster 切成 2:2 也同樣兩邊都停。要用 pause_minority、節點數必須是 3、5、7 這種能在最常見的 1-node 失聯情境下仍形成多數的奇數。

### autoheal：分裂時都活、恢復時選贏家丟輸家

`autoheal` 走另一條路：partition 期間 *兩個子群都繼續服務*（跟 ignore 一樣）、但在 partition *結束* 的瞬間、broker 自動裁決——選出一個「贏家」子群、強制「輸家」子群的節點重啟、丟棄輸家在 partition 期間累積的狀態、然後重新加入贏家。

贏家的選擇規則是：先比 client 連線數（連線多的贏）、連線數相同比節點數、再相同比節點名稱。

autoheal 的取捨點跟 pause_minority 相反。pause_minority 在分裂瞬間就讓少數派停止、犧牲的是少數派 partition 期間的 *可用性*；autoheal 讓兩邊都活、犧牲的是輸家 partition 期間累積的 *訊息與狀態*。輸家側在 partition 期間被消費掉的訊息、被接受的新 publish、被修改的 binding、在 autoheal 重啟輸家後全部丟失。

這讓 autoheal 適合一種特定場景：可用性比訊息完整性重要、且訊息本身是冪等或可重送的。例如純粹的快取失效通知、可重算的衍生事件——丟幾條重新觸發即可。對「丟一條訊息等於丟一筆訂單」的場景、autoheal 的自動丟棄是不可接受的。

## quorum queue 在 partition 下的行為

前面三個 `cluster_partition_handling` 策略管的是 *classic queue 與 cluster metadata* 的 partition 行為。Quorum queue 是另一套機制——它不依賴 `cluster_partition_handling`、而是用 Raft 共識協議自己決定 partition 下的行為。這是 RabbitMQ 對腦裂問題的根本性改寫。

Quorum queue 把每個 queue 實作成一個獨立的 Raft 複製群組：一個 leader 加數個 follower、預設複製到奇數個節點（3-node cluster 通常 3 副本）。每筆 publish 必須被 *多數副本* 確認寫入、leader 才回 publisher confirm。實機驗證 3-node cluster 上 quorum queue 的 Raft 拓樸：

```text
$ rabbitmq-queues quorum_status qq.test
Node Name      Raft State   Membership
rabbit@rmq1    leader       voter
rabbit@rmq2    follower     voter
rabbit@rmq3    follower     voter
```

Partition 切斷 Raft 群組時、行為完全由 Raft 的 majority 規則決定、不需要 `cluster_partition_handling` 介入：

含 majority 副本的那一側選出（或維持）leader、繼續接受讀寫；不含 majority 的那一側無法 commit 任何寫入、自動進入唯讀或拒絕狀態。因為 commit 需要 majority 確認、少數派永遠湊不到 majority、所以少數派 *物理上不可能* 接受新寫入並確認——腦裂在協議層被排除、不靠運維設定。

實機演練最關鍵的一段：把 rmq2 與 rmq3 *同時* disconnect、讓 quorum queue 的 leader（在 rmq1）只剩自己一個副本、3 副本只剩 1 副本、失去 majority（1/3 < 2/3）。此時 `quorum_status` 顯示其他兩個節點變 `timeout` 狀態：

```text
Node Name      Raft State   Membership
rabbit@rmq1    leader       voter
rabbit@rmq2    timeout
rabbit@rmq3    timeout
```

然後對這個失去 quorum 的 queue 嘗試 publish：

```text
$ rabbitmqadmin publish routing_key=qq.test payload="during-quorum-loss"
[實測：publish 阻塞、12 秒後仍未返回——Raft 無 majority 可 commit]
```

Publish 被阻塞、不返回 publisher confirm。因為 leader 拿不到任何 follower 的確認、無法達成 majority、寫入永遠 commit 不了。這是 quorum queue 用 *阻塞* 換 *一致性*：寧可不接受寫入、也不接受一筆無法被多數副本保證的寫入。

同一個 partition 情境下、對 classic queue 做同樣的 publish 作為對照：

```text
$ rabbitmqadmin publish routing_key=cq.test payload="classic-during-partition"
Message published   # 立即成功
```

Classic queue 立即接受寫入。它沒有 Raft、leader 節點獨自決定、可用性優先——但這也正是它在腦裂下會分歧的根源：rmq1 接受的這筆、partition 結束後可能跟另一側的狀態衝突。

把兩邊 disconnect 的節點重新 connect、quorum 恢復、`quorum_status` 三個節點回到 leader + 2 follower、原本被阻塞的 publish 路徑恢復、新 publish 立即成功。Quorum queue 的恢復是協議自動完成的、不需要人工 reset 任何節點。

這就是 classic queue 加 `cluster_partition_handling` 與 quorum queue 的根本差異：前者是 *用運維策略事後補救* 一個本身會腦裂的資料結構、後者是 *用共識協議從設計上排除* 腦裂。現代 RabbitMQ 對需要跨節點一致性的 queue、官方建議直接用 quorum queue、把 partition 一致性交給 Raft、而不是依賴 `cluster_partition_handling` 的 classic queue 補救。Classic / quorum / stream 的完整選型判讀見 [Queue Type 選型](/backend/03-message-queue/vendors/rabbitmq/queue-types-classic-quorum-stream/)。

## 真實 cluster 治理：以 Zalando 為例

[3.C27 Zalando RabbitMQ on AWS](/backend/03-message-queue/cases/rabbitmq-zalando-aws-master-selection/) 案例揭露了 K8s 普及之前、雲端 RabbitMQ cluster 治理的工程模式、跟 partition 處理直接相關。

Zalando 的 communication platform 把 RabbitMQ cluster 跑在 EC2 上、自建 sidekick 服務查 AWS API 動態識別 cluster 成員、指定「最老的 instance」當 master、master 死後晉升下一個最老的節點。這套機制本質是在 RabbitMQ 內建的 partition handling 之外、額外加一層 *外部協調者* 來決定 cluster 拓樸——因為當時 mirrored queue（quorum queue 的前身）的 partition 行為不夠可預測、需要外部邏輯補強節點角色的確定性。

這個案例對映到本文的判讀是：早期 RabbitMQ cluster 的 partition 一致性需要大量外部工程（sidekick + AWS API + 自訂 master selection）來補足。Quorum queue 用 Raft 把這套外部協調內化進 broker——Raft 的 leader election 與 majority commit 取代了 Zalando 手寫的「最老 instance 當 master」邏輯。現代部署若用 quorum queue + pause_minority、不再需要外部 sidekick 來決定誰是 master。

語義誤配的風險在 partition 場景同樣存在。[3.C9 Queue 語義切換誤配](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/) 指出 broker 行為改變時、「表面上訊息仍被送達、但業務資料開始出現重複或遺漏」。Partition 恢復正是這種高風險時刻：autoheal 丟棄輸家狀態、或人工從 ignore 的腦裂中合併、都可能讓同一批事件被處理零次或兩次。Partition 恢復後的 reconciliation、要對照 [3.6 recovery semantics](/backend/03-message-queue/processing-recovery-semantics/) 確認哪一段資料已被哪一側處理過、而不是假設「broker 恢復了 = 狀態正確了」。

## 容量與規模判讀

Partition 處理策略的選擇隨 cluster 規模與一致性需求變化、不存在單一最佳解。

| 規模 / 場景                  | 建議策略                              | 判讀                                               |
| ---------------------------- | ------------------------------------- | -------------------------------------------------- |
| 單節點                       | `ignore`（無 partition 可言）         | 沒有 cluster、不需要 partition 處理                |
| 3 / 5 / 7 奇數節點、需一致性 | `pause_minority` + quorum queue       | 少數派暫停、quorum queue 用 Raft 保一致            |
| 偶數節點                     | 加一個節點變奇數、再用 pause_minority | 偶數節點對 pause_minority 是反模式                 |
| 可容忍訊息遺失、可用性優先   | `autoheal` + classic queue            | 接受輸家丟狀態、換 partition 期間雙邊可用          |
| 跨 AZ / 跨 region            | 重新評估是否該用單一 cluster          | partition 機率高、考慮 federation 拆成獨立 cluster |

幾個容量相關的硬性邊界：

跨 region 拉一個 RabbitMQ cluster 是高風險配置。跨 region 網路延遲與抖動讓 partition 從「偶發事件」變成「常態」——net_tick 頻繁逾時、pause_minority 頻繁暫停節點、cluster 實質不穩定。跨 region 的正確做法是每個 region 一個獨立 cluster、用 federation 或 shovel 做 region 間的訊息搬運、partition 限制在單一 region 內。

quorum queue 的副本數要對齊 cluster 規模。3-node cluster 配 3 副本能容忍 1 節點失聯（仍有 2/3 majority）；5-node 配 5 副本能容忍 2 節點失聯。副本數越多、容錯越高、但每筆寫入要等的確認也越多、寫入延遲上升。多數場景 3 副本是延遲與容錯的平衡點。

net_ticktime 的調整要保守。把它調短以加速 partition 偵測、會讓雲端正常抖動頻繁誤觸發 partition handler——pause_minority 下就是節點被頻繁暫停、可用性反而下降。除非有明確證據顯示偵測延遲是問題、否則保留 60 秒預設值。

## 整合與下一步

Partition 處理是 RabbitMQ cluster 可靠性的一環、跟以下能力環環相扣：

queue 類型的選擇直接決定 partition 行為。Classic queue 靠 `cluster_partition_handling` 事後補救、quorum queue 靠 Raft 從設計排除腦裂、stream 又是另一套複製模型。三者在 partition、throughput、retention 上的完整取捨、見 [Queue Type 選型](/backend/03-message-queue/vendors/rabbitmq/queue-types-classic-quorum-stream/)。

partition 恢復的核心是恢復語義、不是連線恢復。Broker 重新連上不等於狀態一致——這正是 [3.6 processing semantics 與 recovery semantics](/backend/03-message-queue/processing-recovery-semantics/) 區分投遞、處理、恢復三層的價值。Partition 後的 reconciliation 要對照這三層判斷。

雲端 cluster 治理的歷史脈絡見 [3.C27 Zalando AWS master selection](/backend/03-message-queue/cases/rabbitmq-zalando-aws-master-selection/)——理解外部協調者怎麼被 Raft 內化、有助於判斷現代部署該把多少責任交給 broker、多少留給運維。

語義誤配在 partition 恢復時的具體告警條件見 [3.C9 Queue 語義切換誤配](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/)——下游同時出現重複與遺漏、是 partition 恢復處置出錯的典型訊號。

回到上游：[RabbitMQ overview](/backend/03-message-queue/vendors/rabbitmq/) 的進階主題段列了 Erlang clustering 之外的 federation / shovel / Cluster Operator 議題；[3.1 broker basics](/backend/03-message-queue/broker-basics/) 是 broker 通用概念的起點。
