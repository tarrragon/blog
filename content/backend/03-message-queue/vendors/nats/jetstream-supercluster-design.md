---
title: "NATS JetStream 設計與 supercluster / leaf node：stream、consumer、跨區拓樸與多租戶"
date: 2026-06-16
description: "NATS JetStream 的 implementation-layer deep article：stream 設計（storage / retention / discard / 容量上限）、consumer 設計（pull/push、explicit ack、AckWait、MaxDeliver、replay）、Cluster Raft / Supercluster gateway / Leaf node edge 三層拓樸、subject-based ACL 多租戶；含 4 個 production 故障演練（AckWait 太短重投、discard policy 選錯丟訊息、leaf node 斷線重連、stream replica 失去 quorum）。"
weight: 12
tags: ["backend", "message-queue", "nats", "jetstream", "supercluster", "leaf-node", "deep-article"]
---

> 本文是 [NATS](/backend/03-message-queue/vendors/nats/) overview 的 implementation-layer deep article。Overview 回答「NATS 該不該選、Core NATS vs JetStream 怎麼分」；要不要從 core NATS 跨進 JetStream 的決策入口見 [core 到 JetStream 的邊界](/backend/03-message-queue/vendors/nats/jetstream-durability-consumer/)；本文回答「JetStream stream / consumer 的每個旋鈕怎麼設、設錯踩什麼坑、跨區拓樸怎麼鋪、多租戶怎麼隔離」。寫作結構依 [Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/) 的 6 段框架。

## JetStream 把 fire-and-forget 升級成 durable log

JetStream 是 NATS 內建的持久化層、責任是把 Core NATS 的 fire-and-forget subject 轉成 append-only 的 durable stream、並讓 consumer 能 ack、重投、replay。Core NATS 的訊息一旦沒有 active subscriber 就消失；JetStream 把符合特定 subject 的訊息攔截下來寫進 stream、即使沒有任何 consumer 在線也會留存到 retention 上限。

兩個概念要先分清楚、後面所有配置都掛在這個分界上。Stream 是 *儲存* 責任：定義「哪些 subject 的訊息要存、存多久、存多少、存哪裡」。Consumer 是 *投遞* 責任：定義「從 stream 的哪個位置開始讀、怎麼 ack、ack 不回來要不要重投、重投幾次」。同一個 stream 可以掛多個 consumer、各自有獨立的讀取游標跟重投狀態、互不影響。這個 stream / consumer 二分是 JetStream 跟 Kafka（topic / consumer group）對應、但跟 RabbitMQ（queue 本身就綁消費）不同的核心模型差異。

本文用一個訂單事件流當主線：subject 設計成 `orders.created.<region>`、stream 名 `orders`、subject filter `orders.>`。實機環境用單機 NATS server 加 `-js`、CLI 用 `natsio/nats-box` 容器；跨節點的 Cluster / quorum 段用 3 節點 docker compose 驗證、Supercluster / Leaf node 因拓樸複雜以 case 敘述加官方文件 caveat 標註。

## Stream 設計：storage、retention、discard、容量上限

Stream 的設計責任是回答四個彼此獨立的問題：訊息存在哪種介質、用什麼規則決定保留、超過上限時丟哪一端、上限本身設多大。這四個旋鈕組合錯了不會在建立時報錯、而是在 production 流量打進來才以丟訊息或塞爆 disk 的形式爆出來。

### Storage：file vs memory

Storage type 決定訊息寫在 disk 還是 RAM。`file` storage 把 stream 寫進 disk、server 重啟後資料還在、是需要 durability 的事件流預設選擇；`memory` storage 把 stream 放 RAM、吞吐跟延遲更好但 server 重啟即全失、適合短期 fan-out 或可重建的快取型資料。

實機建一個 file storage、limits retention、discard old 的 stream：

```bash
nats --server nats://localhost:4232 stream add orders \
  --subjects 'orders.>' \
  --storage file \
  --retention limits \
  --discard old \
  --max-msgs 1000 \
  --max-bytes 10MB \
  --max-age 1h \
  --replicas 1 \
  --defaults
```

`nats stream info orders` 回報的配置確認旋鈕都生效：

```text
                     Subjects: orders.>
                      Storage: File
                    Retention: Limits
               Discard Policy: Old
             Maximum Messages: 1,000
                Maximum Bytes: 10 MiB
                  Maximum Age: 1h0m0s
```

選 memory 的判讀訊號：訊息可從上游重建（例如 metrics 採樣、可重抓的 snapshot）、或 consumer 一定在線且消費速度跟得上、且單 stream 資料量遠小於可用 RAM。一旦這三條有一條不成立、預設回到 file storage。

### Retention：limits vs interest vs workqueue

Retention policy 決定「訊息什麼時候從 stream 移除」、是 stream 三種使用形態的分水嶺。

`limits` retention 是時間 / 容量驅動：訊息留到撞上 MaxMsgs / MaxBytes / MaxAge 任一上限才移除、跟有沒有人消費無關。這是「事件 log」形態、適合需要 replay、多個獨立 consumer 各讀各的場景。訂單事件流用 limits、因為審計、[對帳](/backend/knowledge-cards/data-reconciliation/)、即時處理可能是三個獨立 consumer、訊息不能因為某個 consumer ack 了就消失。

`interest` retention 是訂閱驅動：當 stream 上 *所有* 已註冊的 consumer 都 ack 了某筆訊息、該訊息立刻移除。它介於 limits 跟 workqueue 之間、適合「只要所有關心的 consumer 都收到就不必再留」的扇出場景。

`workqueue` retention 是任務佇列形態：每筆訊息只會被 *一個* consumer 成功 ack、ack 後立刻刪除。它把 stream 當成工作分派佇列、語意接近 RabbitMQ 的 work queue。實機驗證 workqueue 的 retention 在 info 反映：

```bash
nats --server nats://localhost:4232 stream add wq \
  --subjects 'wq.>' --storage memory --retention work \
  --max-msgs 100 --replicas 1 --defaults
# nats stream info wq → Retention: WorkQueue
```

判讀路由：需要多 consumer 各自 replay → limits；需要扇出且所有訂閱者收齊就清 → interest；需要競爭式單次消費的任務派工 → workqueue。選 workqueue 卻又掛兩個 filter 重疊的 consumer 會在建 consumer 時被拒、因為 workqueue 不允許同一筆訊息被兩個 consumer 認領。

### Discard：old vs new

Discard policy 決定 stream *撞上 MaxMsgs / MaxBytes 上限後* 丟哪一端。這個旋鈕的選擇直接對應業務對「舊資料」跟「新資料」誰更重要的判斷、選錯會靜默丟訊息。

`discard old` 在達上限時丟掉最舊的訊息、騰空間給新訊息。實機驗證：max-msgs 設 3、連發 5 筆、stream 留下最後 3 筆：

```text
discard old, max-msgs 3, published 5:
                     Messages: 3
               First Sequence: 3
                Last Sequence: 5
```

最舊的 seq 1、2 被丟、保留 seq 3-5。這對應「新資料比舊資料重要」的場景：即時儀表板、最新狀態快照、寧可丟歷史也要保住最新。

`discard new` 在達上限時拒絕新訊息、保住已存的舊訊息。同樣 max-msgs 3、連發 5 筆：

```text
discard new, max-msgs 3, published 5:
                     Messages: 3
               First Sequence: 1
                Last Sequence: 3
```

保留 seq 1-3、後到的 seq 4、5 進不來。這對應「舊資料是已承諾的工作、不能丟」的場景：任務佇列在塞滿時應拒收新任務（並對上游施加 backpressure）、而不是把排隊中的任務擠掉。

discard new 有個容易踩的投遞行為差異、見故障演練 Case 2。

### 容量上限：MaxMsgs / MaxBytes / MaxAge

三個上限是 OR 關係：任一撞到就觸發 discard / 移除。MaxMsgs 限筆數、MaxBytes 限總位元組、MaxAge 限訊息存活時間。實務上三者搭配使用：MaxAge 防止無限累積（例如事件流只保留 7 天）、MaxBytes 是 disk 的硬護欄（防單 stream 撐爆 volume）、MaxMsgs 在訊息大小均勻時當作粗略筆數控制。

容量規劃的判讀順序是先定 MaxAge（業務需要 replay 多久）、再用「平均訊息大小 × 預估 throughput × MaxAge」反推 MaxBytes 是否在 disk 預算內、超出就縮短 MaxAge 或拆 stream。把 MaxBytes 設成 unlimited 而只靠 MaxMsgs 是常見的容量事故來源：訊息大小一旦變大（例如 payload 夾帶了 base64 附件）、筆數沒到上限但 disk 已滿。

## Consumer 設計：pull/push、ack、AckWait、MaxDeliver、replay

Consumer 的設計責任是控制「訊息怎麼從 stream 送到處理端、處理端怎麼確認、確認不回來怎麼辦」。它的每個旋鈕都圍繞同一個核心張力：在 at-least-once 投遞下、如何在「不漏處理」跟「不過度重投」之間取得平衡。對應的概念基礎見 [Delivery Semantics](/backend/knowledge-cards/delivery-semantics/) 與 [Processing Semantics](/backend/knowledge-cards/processing-semantics/) 知識卡。

### Pull vs push

Pull consumer 由處理端主動拉：consumer 發 pull request 帶 batch size、server 才送對應數量的訊息。流量控制天然落在消費端、消費端有多少處理能力就拉多少、是現代 JetStream 應用的預設模式。Push consumer 由 server 主動推到一個 delivery subject、處理端訂閱那個 subject、適合需要 server 端 flow control 或既有 Core NATS 訂閱模型遷移的場景。

實機建一個 pull consumer、explicit ack、AckWait 30s、MaxDeliver 5、replay instant：

```bash
nats --server nats://localhost:4232 consumer add orders worker \
  --pull \
  --deliver all \
  --ack explicit \
  --wait 30s \
  --max-deliver 5 \
  --replay instant \
  --filter 'orders.>' \
  --defaults
```

`nats consumer info orders worker` 確認配置：

```text
                    Name: worker
               Pull Mode: true
          Deliver Policy: All
              Ack Policy: Explicit
                Ack Wait: 30.00s
           Replay Policy: Instant
      Maximum Deliveries: 5
```

push consumer 改用 `--target <subject>` 取代 `--pull`、info 會回報 `Delivery Subject:` 而非 Pull Mode。

### AckPolicy：explicit 是預設選擇

Ack policy 決定 consumer 怎麼確認訊息已處理。`explicit` 要求對每一筆訊息單獨 ack、是 at-least-once 處理的基礎、production 預設選擇。`all` 用累積 ack：ack 第 N 筆等於 ack 了第 N 筆以前全部、吞吐高但一筆處理失敗會讓整段重投。`none` 完全不 ack、投遞即視為完成、語意退化成接近 fire-and-forget、只適合可容忍丟失的場景。

explicit ack 之所以是預設、是因為它讓每筆訊息的處理結果獨立可追蹤：哪筆 ack 了、哪筆還 outstanding、哪筆重投超限、都能在 consumer info 看到。實機發 3 筆訊息後、consumer info 的 `Unprocessed Messages` 反映 stream 中尚未投遞的 backlog：

```bash
nats --server nats://localhost:4232 pub orders.created.us-1 "order-1"
# 發 3 筆後：
# nats consumer info orders worker →
#     Unprocessed Messages: 3
```

拉出訊息但不 ack、consumer info 的 `Outstanding Acks` 反映已投遞但未確認的數量：

```text
        Outstanding Acks: 3 out of maximum 1,000
```

這兩個數字是診斷 consumer 健康的第一手訊號：`Unprocessed` 高代表 consumer 拉得太慢或停了（stream backlog）；`Outstanding Acks` 持續高代表訊息拉出去了但處理端沒 ack（處理慢或卡住）。這個區分對應 overview 排錯段的「pending 是 ack-pending 還是 stream backlog」判讀。

### AckWait + MaxDeliver：重投的兩個邊界

AckWait 是 server 等待 ack 的時間窗：訊息投遞後、若 AckWait 內沒收到 ack、server 視為投遞失敗、重新投遞。MaxDeliver 是同一筆訊息的投遞次數上限：達到後不再重投、訊息進入 terminal 狀態（可導向 advisory / DLQ 機制）。

這兩個旋鈕共同定義重投行為。AckWait 要設成 *略大於 consumer 處理一筆訊息的 p99 時間*：太短會在 consumer 還在正常處理時就誤判失敗重投、造成重複處理（見故障演練 Case 1）；太長會讓真正卡死的訊息遲遲不重投、拖慢 recovery。MaxDeliver 是 poison message 的護欄：一筆訊息若處理永遠失敗（例如 payload 格式壞）、沒有 MaxDeliver 它會無限重投佔住 consumer。對應 [Redelivery Loop](/backend/knowledge-cards/redelivery-loop/) 知識卡描述的失控重投。

### Replay：instant vs original

Replay policy 只在 consumer 從歷史位置讀（例如 `--deliver all` 重讀整個 stream）時生效、決定投遞節奏。`instant` 以 server 最快速度投遞、是處理 backlog 或重建狀態的預設。`original` 按訊息 *原始寫入的時間間隔* 重放：若原始訊息間隔 1 秒寫入、replay 也間隔 1 秒投遞、用於需要重現時序的測試或模擬。實機兩種都可建：

```bash
nats consumer add orders replayorig ... --replay original  # Replay Policy: Original
```

## Cluster / Supercluster / Leaf node：三層拓樸

NATS 的拓樸分三層、各解一個不同尺度的問題：Cluster 解單區內的高可用、Supercluster 解跨區的延展、Leaf node 解邊緣到中心的連接。三者可組合、但職責不重疊。

### Cluster：單區 Raft 高可用

Cluster 是同一 region 內多個 NATS server 用 full mesh route 互連、JetStream 的 stream 透過 Raft 在多個 replica 間複製。Replica 數（R1 / R3 / R5）決定容錯：R3 容忍 1 節點失效、R5 容忍 2 節點。Raft 要求多數派（quorum）才能寫入、所以 R3 需要至少 2 節點健康。

實機用 3 節點 docker compose 起 cluster、建 R3 stream、stream info 顯示 Raft group 與 replica 狀態：

```bash
nats --server nats://n1:4222 stream add rep3 \
  --subjects 'rep3.>' --storage file --retention limits \
  --discard old --max-msgs 1000 --replicas 3 --defaults
```

```text
                     Replicas: 3
Cluster Information:
                Cluster Group: S-R3F-unEqlH8C
                       Leader: n2 (222ms)
                      Replica: n1, current, seen 217ms ago
                      Replica: n3, current, seen 219ms ago
```

Leader 是 Raft 選出的寫入協調者、其餘 replica 跟隨。`current` 代表該 replica 與 leader 同步；落後會顯示 `outdated` 加落後的 operation 數。失去 quorum 的行為見故障演練 Case 4。

### Supercluster：跨區 gateway 延展

Supercluster 用 gateway 連接多個 Cluster、形成跨 region / 跨雲的單一 NATS 邏輯網路。Gateway 之間是按需轉發、不是 full mesh：訊息只在有訂閱者的 region 之間流動、避免跨區頻寬被無謂的全量複製吃掉。Supercluster 讓 publisher 在任一 region 發訊息、訂閱者在另一 region 收到、同時讓每個 Cluster 維持自己的 JetStream Raft 群組與本地高可用。

> 以下 Supercluster 行為依 [NATS 官方文件](https://docs.nats.io/running-a-nats-service/configuration/gateways) 描述、未在本文實機環境驗證（gateway 多區拓樸需要跨 region 部署）。

[3.C35 Form3](/backend/03-message-queue/cases/nats-form3-multi-cloud-payments/) 是 Leaf node 跨雲橋接的代表案例（Supercluster 為相應的一般拓樸選項、case 本身明確點到的是 Leaf node）：服務 Tier-1 銀行、要求 500ms 端到端 SLA、AWS SNS/SQS 約 300ms 延遲吃掉預算。Form3 用 JetStream 跨雲橋接、達到約 6× 延遲改善、並做到「AWS 整個 region 掛掉時不喪失處理能力」。這個案例揭露的判讀是：金融支付的硬 latency 預算逼出特定拓樸選型、不是把 Kafka / SQS 通用化套上去。

### Leaf node：邊緣連中心

Leaf node 是輕量 NATS server、跑在邊緣（工廠、店面、IoT gateway）、透過單一 leaf connection 連回中心 hub。它在邊緣本地提供完整的 NATS / JetStream 能力（本地 publish / subscribe / 本地持久化）、同時把需要的 subject 透過 leaf connection 雙向橋接到 hub。Leaf node 的價值在於：邊緣到中心的網路斷線時、邊緣端的本地 JetStream 持續收訊息、連線恢復後再同步、不丟資料。

> 以下 Leaf node 行為依 [NATS 官方文件](https://docs.nats.io/running-a-nats-service/configuration/leafnodes) 與下列 case 描述、未在本文實機環境驗證（leaf 拓樸需要 hub + edge 雙端部署）。

[3.C37 MachineMetrics](/backend/03-message-queue/cases/nats-machinemetrics-edge-to-cloud/) 是 Leaf node 邊緣到雲端的完整案例：跨數百客戶廠區、數千機台、單機最高 1000Hz 採樣、工廠網路斷斷續續、Kinesis 等 cloud-only 工具無法跑在資源受限 edge。MachineMetrics 用 Leaf node 做 hub-and-spoke、edge 端用 JetStream 做本地持久化抵抗斷線。這個案例揭露的判讀是：broker 的功能集合（messaging + 本地持久化 + KV + Object Store + auth）決定它能不能取代邊緣的多套工具。

[3.C41 i-flow](/backend/03-message-queue/cases/nats-iflow-ot-it-integration/) 是多工廠 leaf node 拓樸的另一證據：每日 4 億筆 data operation、200+ OT/IT connector、用 leaf node hub-and-spoke 把多工廠接到 central、而不是每工廠自管一套 cluster。判讀：多工廠場景的運維成本由「每個邊緣點是不是要獨立維運一套 cluster」決定、leaf node 把邊緣端壓到單一 server。

## Subject-based ACL 與多租戶

NATS 多租戶的主機制是 account：account 是完全隔離的 subject 命名空間、不同 account 之間預設互不可見、即使 subject 名稱相同也不會互通。Account 之內再用 subject-level permission 控制每個 user 能 publish / subscribe 哪些 subject。這兩層組合起來：account 給租戶硬隔離、subject permission 給租戶內的角色細分權限。

跨 account 的受控互通用 import / export：一個 account 把特定 subject export 出來、另一個 account 顯式 import、才會打通那條 subject。預設不通、互通是顯式授權的結果、這讓多租戶的資料流動可審計。對應 MachineMetrics 案例用 decentralized auth 隔離不同客戶廠區的設計：每個客戶是一個 account、廠區設備在 account 內用 subject permission 限定只能發自己廠區的 subject。

多租戶設計的判讀訊號：租戶之間要完全隔離、用 account；同租戶內的不同服務 / 角色要限權、用 subject permission；少數需要跨租戶共享的 subject（例如全域控制信號）、用 import / export 顯式打通、不要為了方便把不同租戶塞進同 account。

## Production 故障演練

deep article 的差異化價值在故障演練。以下四個都是 JetStream stream / consumer / 拓樸層的典型事故、前兩個有本文實機驗證、後兩個結合實機（quorum）與 case 敘述。

### Case 1：AckWait 太短造成重複處理

**徵兆**：consumer 正常運行、處理邏輯沒報錯、但下游出現大量重複副作用（重複扣款、重複寄信、重複寫入）。consumer info 的 `Redelivered Messages` 持續上升、即使處理端沒有任何 exception。

**根因**：AckWait 設得比 consumer 處理一筆訊息的實際耗時短。訊息投遞後 consumer 還在處理、AckWait 就到期、server 判定投遞失敗、把同一筆訊息重投給（可能是另一個）consumer 實例、於是同一筆訊息被處理兩次。實機重現：建一個 AckWait 1s 的 consumer、拉出訊息不 ack、過 1s 後再拉、`tries` 從 1 變 2：

```text
第一次拉：subj: orders.created.us-1 / tries: 1 / str seq: 1
過 1s 後：subj: orders.created.us-1 / tries: 2 / str seq: 1
consumer info → Redelivered Messages: 3
```

**修法**：

1. **量測再設值**：AckWait 設成 consumer 處理 p99 時間的 2-3 倍、而不是拍腦袋設 30s。處理一筆要 5s 的 worker 配 AckWait 30s、處理一筆要 45s 的 worker 配 AckWait 30s 就會持續誤判重投。
2. **長任務用 in-progress ack**：處理時間本就偏長且方差大的任務、處理端在處理中定期送 `AckProgress`（working ack）延長 AckWait、而不是把 AckWait 設成一個無法涵蓋最壞情況的固定大值。
3. **處理端做冪等**：at-least-once 投遞下重複是常態而非異常、副作用以業務 key 去重（對應 [Processing Semantics](/backend/knowledge-cards/processing-semantics/) 的冪等要求）。AckWait 只能降低重複頻率、不能消除重複。

### Case 2：discard policy 選錯靜默丟訊息

**徵兆**：上游 publisher 一切正常、沒收到任何 error、但下游 consumer 發現訊息有缺口（seq 跳號）、或最舊的歷史訊息神祕消失。對帳時帳目對不上、但日誌裡找不到任何失敗紀錄。

**根因**：兩種情況。其一、stream 用 `discard old`、流量超過 MaxMsgs / MaxBytes、最舊的訊息被靜默丟棄騰空間——這在「事件 log 需要完整 replay」的場景是資料遺失。其二、stream 用 `discard new`、滿了之後新訊息被拒、但 publisher 用的是 *Core NATS publish*（不等 stream ack）、所以 publisher 端看到「發送成功」、訊息其實沒進 stream。實機重現後者的危險：對一個 discard new 已滿的 stream 用 Core pub 與 JetStream-aware pub、結果完全不同：

```text
Core pub（不等 ack）：    Published 8 bytes to "dnew.x"        ← 看似成功、實際丟失
JetStream pub（等 ack）： nats: error: maximum messages exceeded (10077)  ← 正確報錯
```

**修法**：

1. **publisher 一律用 JetStream-aware publish**：等 stream 的 PubAck 回來才算發送成功、才能在 stream 滿、quorum 失效、subject 不匹配時收到明確 error。用 Core pub 發進 JetStream subject 等於放棄所有投遞保證。
2. **discard policy 對齊業務語意**：事件 log（需要完整歷史）配 limits + 充足 MaxAge、絕不靠 discard old 當容量控制；任務佇列配 discard new + 上游 backpressure、滿了就讓 producer 慢下來而不是擠掉排隊任務。
3. **監控 discard 計數**：stream 的 discard 不是錯誤狀態、不會觸發 alert。要主動監控訊息 seq 連續性與 stream 的訊息移除速率、把「非預期的 discard」變成可觀測訊號。

### Case 3：Leaf node 斷線重連

**徵兆**：邊緣端（工廠 / 店面）到中心 hub 的網路抖動、leaf connection 反覆斷開重連、hub 端看到某些 subject 的訊息延遲尖刺、邊緣端 reconnect 計數持續累加。網路恢復後、邊緣累積的訊息一次湧入 hub、造成 hub 端短暫的處理尖峰。

**根因**：邊緣到中心是廣域網、品質不如資料中心內網。Leaf connection 斷線期間、邊緣端的本地 JetStream 持續收訊息並本地持久化（這正是 leaf node 的設計目的）；連線恢復後、累積的 backlog 一次同步到 hub、形成尖峰。若邊緣端沒有本地 JetStream、斷線期間的訊息直接丟失。

> 以下根因與修法依 NATS 官方 leaf node 文件與 [MachineMetrics](/backend/03-message-queue/cases/nats-machinemetrics-edge-to-cloud/) / [i-flow](/backend/03-message-queue/cases/nats-iflow-ot-it-integration/) case 描述、未在本文實機環境驗證。

**修法**：

1. **邊緣端必開本地 JetStream**：把斷線容忍從「依賴網路不斷」改成「斷線期間本地持久化、恢復後同步」。這是 MachineMetrics 用 edge JetStream 取代 SQLite 的核心理由——工廠網路斷斷續續是常態、不是異常。
2. **hub 端對同步尖峰做 flow control**：恢復連線後的 backlog 同步用 consumer 端的 pull batch 限速、避免邊緣 backlog 一次打爆 hub 的處理能力。
3. **監控 reconnect 與 latency**：leaf 連線的 reconnect 次數與 subject mapping latency 是邊緣網路品質的直接訊號（對應 overview 排錯段「leaf node 連線不穩」）。reconnect 頻繁代表網路或 hub 容量要處理、不是調 leaf 參數能解。

### Case 4：Stream replica 失去 quorum

**徵兆**：R3 stream 突然無法寫入、publisher 的 JetStream publish 卡住後回 `no responders available`；stream info 顯示 `Leader:` 欄位空白、多數 replica 標 OFFLINE。讀取可能還能從存活節點拿到舊資料、但寫入完全停擺。

**根因**：JetStream 的 stream 用 Raft 複製、寫入需要多數派確認。R3 stream 需要至少 2 節點健康才有 quorum；同時失去 2 節點就只剩 1 節點、達不到多數、Raft 無法選出 leader、stream 變成無法寫入。實機重現：3 節點 cluster 的 R3 stream、停掉 2 個節點、stream info 顯示無 leader、JetStream publish 報錯：

```text
停 2 節點後 stream info：
                       Leader:
                      Replica: n1, current, seen 3.35s ago
                      Replica: n2, outdated, OFFLINE, not seen
                      Replica: n3, outdated, OFFLINE, not seen

此時 JetStream publish：
                      nats: error: nats: no responders available for request
```

恢復 1 個節點（回到 2/3 多數）後、Raft 立即重選 leader、stream 恢復可寫：

```text
啟動 n2 後：
                       Leader: n1 (506ms)
                      Replica: n2, current, seen 499ms ago
                      Replica: n3, outdated, OFFLINE, not seen, 4 operations behind
```

**修法**：

1. **replica 數對齊容錯目標**：要容忍 1 節點失效用 R3、容忍 2 節點用 R5；不要為了省資源把關鍵 stream 設 R1（單點、節點掛了 stream 直接不可用）。
2. **replica 跨 failure domain 散開**：R3 的 3 個 replica 要落在不同 availability zone / rack、避免單一 AZ 故障同時帶走 2 個 replica 直接失去 quorum。
3. **監控 replica 健康而非只看 leader**：stream info 的每個 replica 的 `current` / `outdated` / `OFFLINE` 狀態是 quorum 餘裕的直接訊號。R3 已經有 1 個 replica OFFLINE 時 quorum 餘裕只剩 0、要當成 P1 處理、不能等到第 2 個也掛才反應（對應 overview 排錯段「JetStream raft 不一致」）。

## 容量與規模判讀

JetStream 的配置在不同規模下適用性不同、超出範圍要換拓樸而非調參數。

| 規模訊號                             | 適用拓樸                             | 換檔訊號                                                |
| ------------------------------------ | ------------------------------------ | ------------------------------------------------------- |
| 單區、中等吞吐、需要 HA              | 單 Cluster R3                        | 單區頻寬 / 節點數撐不住 → 加節點 reshard 或拆 stream    |
| 跨 region / 跨雲、訂閱者分散各區     | Supercluster（多 Cluster + gateway） | 需要邊緣本地持久化 → 疊加 Leaf node                     |
| 大量邊緣點、網路不穩、邊緣要本地能力 | Leaf node hub-and-spoke              | 邊緣點 > 數百、每點要獨立運維 → 評估 managed（Synadia） |

**單 Cluster R3** 是多數中等規模服務的起點：單區內高可用、JetStream Raft 處理節點故障、運維只有一套 cluster。撞到天花板的訊號是單區頻寬或單節點 disk / CPU 到上限、此時先評估加節點重分配或把熱 stream 拆出去、而不是急著上 supercluster。

**Supercluster** 在訂閱者地理分散、或要求單區整個掛掉仍能服務時才值得引入。它的成本是跨區 gateway 的運維複雜度與跨區頻寬、不該為了「以後可能要跨區」提前鋪。Form3 的判讀是硬 SLA（500ms、region 全掛仍可用）逼出來的、不是預設架構。

**Leaf node hub-and-spoke** 在邊緣點多、邊緣網路不穩、邊緣要本地持久化 / KV / 計算能力時適用。當邊緣點數量大到每點獨立運維成本不可接受、評估走 managed NATS（Synadia Cloud）把運維外包、而不是自建更大的 hub。

## 整合與下一步

本文聚焦 JetStream stream / consumer / 拓樸的 implementation；以下是往上下游的銜接。

### 回 vendor overview 與相鄰章節

- 上游 vendor 頁：[NATS overview](/backend/03-message-queue/vendors/nats/)——Core NATS vs JetStream 的選型判讀、排錯快速判讀、何時改走其他 broker
- 跨 vendor consumer 設計：[3.4 consumer 設計](/backend/03-message-queue/consumer-design/)——本文的 pull/push、ack、重投放回語言無關的 consumer 設計框架
- 投遞與處理語意基礎：[Delivery Semantics](/backend/knowledge-cards/delivery-semantics/) / [Processing Semantics](/backend/knowledge-cards/processing-semantics/) / [Redelivery Loop](/backend/knowledge-cards/redelivery-loop/) 知識卡

### 對應 case

- [3.C35 Form3](/backend/03-message-queue/cases/nats-form3-multi-cloud-payments/)——Supercluster + Leaf node 跨雲低延遲支付、硬 SLA 驅動拓樸
- [3.C37 MachineMetrics](/backend/03-message-queue/cases/nats-machinemetrics-edge-to-cloud/)——Leaf node + edge JetStream + KV + Object Store + 多租戶 auth 的完整邊緣案例
- [3.C41 i-flow](/backend/03-message-queue/cases/nats-iflow-ot-it-integration/)——多工廠 leaf node hub-and-spoke、運維成本驅動拓樸選型

### 後續可深入的議題

- **JetStream KV / Object Store**：基於 stream 的 key-value 與 blob 儲存、何時用 NATS KV vs 真的 KV 服務（Redis / etcd）、見 overview 進階主題段
- **Leaf node 多節點實機驗證**：本文 Supercluster / Leaf node 段以 case + 官方文件敘述；補一篇 hub + edge 雙端 compose 的實機演練（含斷線注入、backlog 同步觀測）是自然延伸
- **Subject mapping 與 transform**：leaf node 跨層的 subject 重映射、跨 account import / export 的細部配置
