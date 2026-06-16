---
title: "RabbitMQ Queue Type 選型：Classic、Quorum、Stream 的責任邊界與容量取捨"
date: 2026-06-16
description: "RabbitMQ 3.x 三種 queue type 的選型 deep article — classic queue（mirrored 已 deprecated）、quorum queue（Raft 一致性、取代 mirrored）、stream（3.9+ append-only log、可重複消費）。涵蓋三種模型在 throughput / retention / replay / 記憶體成本的判讀、宣告語意差異（實機驗證）、4 個 production 故障演練（mirrored 網路放大 / quorum loss / stream retention 超量 / classic→quorum in-flight message），與容量規劃。"
weight: 13
tags: ["backend", "message-queue", "rabbitmq", "quorum-queue", "stream", "deep-article"]
---

> 本文是 [RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/) overview 的 implementation-layer deep article、對應 overview「Classic queue vs Quorum queue vs Stream」段。Overview 回答「RabbitMQ 該不該選、跟 Kafka / SQS 差在哪」、本文回答「選了 RabbitMQ 之後、同一個 broker 內三種 queue type 怎麼挑、各自的容量與故障形狀」。

## 同一個 broker、三套儲存引擎

RabbitMQ 的 queue 由三種 *儲存引擎* 構成、共用同一套 AMQP 協議與 management 介面。Queue type 決定訊息怎麼持久化、怎麼跨節點複製、消費後是否保留 — 這些差異在宣告 queue 的那一刻就鎖定、之後無法原地切換。選錯 queue type 的代價不是參數調整、是 *重建 queue + 遷移 in-flight 訊息*。

三種 type 各自承擔不同責任：

- **Classic queue**：單節點的 durable / transient queue、訊息消費即刪除、是 RabbitMQ 最原始的工作隊列模型。跨節點高可用曾靠 *mirrored queue*（鏡像複製）達成、但該機制在 3.x 已標記 deprecated、4.0 移除。
- **Quorum queue**：Raft 共識協議實作的 replicated queue、跨節點維持強一致的訊息狀態、設計目標是 *取代 mirrored queue* 提供可靠的工作隊列高可用。訊息仍是消費即刪除的隊列語意。
- **Stream**：3.9 引入的 append-only log、訊息寫入後 *不因消費而刪除*、多個 consumer 可從各自的 offset 重複讀取、retention 由時間 / 大小上限控制。語意接近 Kafka 的 partition log、但跑在 RabbitMQ 體系內、共用 AMQP 與專屬 stream protocol。

判讀起點是一個問題：訊息被消費後該不該保留。需要 replay、多 consumer 各自進度、長期事件流 → stream；訊息是一次性任務、處理完即丟、要跨節點不丟 → quorum；單節點夠用、可接受節點故障時該 queue 暫時不可用 → classic。

本文用 RabbitMQ 3.13.7（OrbStack 單節點）實機驗證宣告語意差異。生產的跨節點行為（Raft 選舉、replica lag）單節點環境無法重現、相關段落標注來源。

## 三種 queue type 的宣告語意差異（實機驗證）

Queue type 由宣告時的 `x-queue-type` argument 決定。三種 type 在同一 broker 宣告後、`type` 欄位區分清楚：

```bash
rabbitmqadmin declare queue name=q-classic durable=true
rabbitmqadmin declare queue name=q-quorum  durable=true arguments='{"x-queue-type":"quorum"}'
rabbitmqadmin declare queue name=q-stream  durable=true arguments='{"x-queue-type":"stream"}'

rabbitmqctl list_queues name type durable leader members
```

實機輸出（節錄、單節點所以 leader / members 都是同一節點）：

```text
name       type     durable  leader              members
q-classic  classic  true
q-quorum   quorum   true     rabbit@<node>       [rabbit@<node>]
q-stream   stream   true     rabbit@<node>       [rabbit@<node>]
```

兩個關鍵差異在這裡浮現。

第一、**quorum 與 stream 強制 durable**。Classic queue 可宣告為 transient（`durable=false`、broker 重啟後消失、適合臨時 RPC reply queue）；quorum 與 stream 不允許 transient — 嘗試宣告會直接被拒：

```text
*** invalid property 'non-durable' for queue 'q-quorum-nondur' in vhost '/'
*** invalid property 'non-durable' for queue 'q-stream-nondur' in vhost '/'
```

這個限制反映設計意圖：quorum 與 stream 存在的理由是 *資料安全*、transient 模式與該目標矛盾、所以從宣告層就封死。Classic queue 保留 transient 選項、是因為它要同時服務「臨時隊列」與「持久隊列」兩種場景。

第二、**quorum 與 stream 有 leader / members、classic 沒有**。Classic queue 的訊息只存在宣告它的節點上（mirrored policy 另算）；quorum 與 stream 在設計上就是 *cluster-aware* 的 replicated 結構、leader 處理讀寫、members 列出 replica 所在節點。單節點環境下 members 只有一個、但欄位本身揭露了複製拓樸的存在。

Stream 的 retention 與 segment 參數在宣告時設定、宣告後可查：

```bash
rabbitmqadmin declare queue name=q-stream-ret durable=true \
  arguments='{"x-queue-type":"stream","x-max-length-bytes":20000000000,"x-max-age":"7D","x-stream-max-segment-size-bytes":100000000}'

rabbitmqctl list_queues name type arguments
```

```text
q-stream-ret  stream  [{"x-max-age","7D"},{"x-max-length-bytes",20000000000},
                       {"x-queue-type","stream"},{"x-stream-max-segment-size-bytes",100000000}]
```

`x-max-age`（保留 7 天）與 `x-max-length-bytes`（保留 20GB）是 stream 獨有的 retention 控制 — classic 與 quorum 沒有這個概念、因為它們消費即刪除、不存在「保留多久」的問題。Quorum queue 對應的是 `x-delivery-limit`（投遞次數上限、超過進 dead-letter）這類 *重試治理* 參數、而非 retention：

```text
q-quorum-dl  quorum  [{"x-delivery-limit",5},{"x-queue-type","quorum"}]
```

宣告參數的差異就是責任邊界的縮影：stream 的參數圍繞「保留多少歷史」、quorum 的參數圍繞「重試到第幾次放棄」、classic 兩者都精簡。

## 三軸選型判讀

Queue type 的選擇由三個軸決定：消費後是否保留（retention / replay）、跨節點一致性需求、記憶體與 throughput 成本。

| 判讀軸        | Classic                         | Quorum                              | Stream                                  |
| ------------- | ------------------------------- | ----------------------------------- | --------------------------------------- |
| 消費語意      | 消費即刪除                      | 消費即刪除                          | 消費不刪除、offset 各自獨立             |
| Replay        | 不支援                          | 不支援                              | 支援、consumer 可重設 offset 重讀       |
| 跨節點一致性  | 無（mirrored deprecated）       | Raft 強一致、majority 寫入才 ack    | Leader-follower 複製、append-only       |
| 高 throughput | 中（單節點 fsync 上限）         | 中（Raft majority round-trip 成本） | 高（順序寫 log、批次讀）                |
| 記憶體成本    | 高（訊息常駐記憶體、lazy 例外） | 中（on-disk 為主、index 在記憶體）  | 低（log 在磁碟、讀靠 page cache）       |
| 典型場景      | 單節點任務隊列、臨時 RPC reply  | 跨節點不可丟的工作隊列              | 事件流、多 consumer、需要 replay 的審計 |

### 消費後是否保留：retention 與 replay

Stream 與 classic / quorum 的根本分界是訊息生命週期。Classic 與 quorum 是 *隊列*：訊息被 ack 後從 queue 移除、後到的 consumer 看不到歷史。Stream 是 *log*：訊息寫入後常駐到 retention 上限為止、consumer 各自維護 offset、可以從 offset 0 重讀整段歷史、也可以從 timestamp 起讀。

實機可觀察到 stream 的訊息在 publish 後保留在 queue 內：

```bash
rabbitmqadmin publish exchange=amq.default routing_key=q-stream payload="msg1"
rabbitmqadmin publish exchange=amq.default routing_key=q-stream payload="msg2"
rabbitmqadmin publish exchange=amq.default routing_key=q-stream payload="msg3"
rabbitmqctl list_queues name type messages messages_ready
```

```text
q-stream   stream  3  3
```

對 classic queue、同樣 publish 後 consumer ack 一次、訊息歸零；對 stream、即使一個 consumer 讀完、`messages` 仍維持 3、因為訊息保留供其他 consumer 與未來 replay。這個差異決定了選型：需要「新上線的 consumer 補讀歷史事件」「同一份事件流餵給多個下游」「審計與重算」→ stream 是唯一選項；只要「一個任務交給一個 worker 處理一次」→ classic 或 quorum、不要用 stream（log 保留會吃磁碟、且隊列語意更貼合任務分派）。

需要在 RabbitMQ 體系外做大規模事件流（跨團隊 schema 治理、tiered storage、生態工具）時、stream 不是終點、改評估 [Kafka](/backend/03-message-queue/vendors/kafka/)。Stream 的定位是「已經在用 RabbitMQ、需要 replay 但不想引入第二套 broker」。

### 跨節點一致性：mirrored 的退場與 quorum 的接手

Classic queue 在單節點上沒有複製。早期要跨節點高可用、靠 *mirrored queue* — 一個 master、多個 mirror、master 寫入同步到所有 mirror。這個機制的問題在 [3.C30 Runtastic](/backend/03-message-queue/cases/rabbitmq-runtastic-mirrored-queue-bottleneck/) 揭露：mirror 數越多、每筆訊息的網路放大越大、規模化時網路元件先被壓垮。RabbitMQ 3.x 已將 mirrored queue 標記 deprecated、4.0 移除。

Quorum queue 用 Raft 共識取代 mirroring。差異在「同步多少 replica 才算寫成功」：mirrored queue 要求 *所有* mirror 同步（全量放大）；Raft 只要求 *majority*（多數派）寫入即 ack，少數派慢或暫時離線不阻塞寫入。majority 機制讓 quorum queue 在「容忍少數節點故障」與「寫入延遲」之間取得 mirrored 做不到的平衡。

代價是 Raft 的 round-trip 成本：每筆訊息要等多數派落盤、單筆延遲高於 classic 單節點 fsync。所以 quorum queue 適合「不可丟、可接受中等延遲」的工作隊列、不適合追求極致低延遲的場景。

### 記憶體與 throughput 成本

Classic queue 的歷史包袱是訊息傾向常駐記憶體、queue 堆積時記憶體壓力大（lazy queue 模式可緩解、但仍是 classic 的調校負擔）。Quorum queue 預設 on-disk 為主、記憶體只放 index 與近期訊息、堆積時記憶體曲線比 classic 平緩。Stream 是 append-only log、寫入是順序磁碟 I/O、讀取靠 OS page cache、是三者中記憶體效率最高、throughput 最高的 — 順序寫與批次讀讓它在高吞吐事件流場景接近 Kafka 的量級。

throughput 排序大致是 stream > classic ≈ quorum（quorum 因 Raft round-trip 略低於單節點 classic、但換得一致性）。選型時 throughput 不該是唯一軸：stream throughput 高但語意是 log、用它跑任務隊列會錯配；quorum throughput 中但提供 classic 給不了的高可用。

## 故障演練

三種 queue type 的故障形狀完全不同。以下四個場景對應實際遷移與運維會踩的坑。

### Mirrored queue 的網路放大成本

**徵兆**：流量暴增期間、RabbitMQ cluster 出現高延遲與間歇中斷、但 CPU 與磁碟未飽和；performance test 指向網路元件被壓垮。這正是 [3.C30 Runtastic](/backend/03-message-queue/cases/rabbitmq-runtastic-mirrored-queue-bottleneck/) 2020 lockdown 期間的情況。

**根因**：mirrored queue 把每筆訊息同步到 *所有* mirror。一個 master + 2 mirror 的 queue、每筆 publish 產生 2 份額外的跨節點複製流量；mirror 數與訊息量相乘、網路頻寬隨規模線性放大。可靠性看似免費（多一個 mirror 就多一份備援）、實際成本藏在網路層、平時不顯、流量尖峰才爆。

**修法**：

1. **量化 mirror 的網路成本**：mirror 數不是越多越安全、每個 mirror 都是固定的複製流量稅。生產上 mirror 數很少需要超過總節點的 majority。
2. **遷移到 quorum queue**：Raft 的 majority 寫入取代全量同步、把網路放大從「mirror 數」降到「majority round-trip」。Runtastic case 是「為何該遷 quorum」的典型動機。
3. **監控網路而非只看 CPU / 磁碟**：mirrored queue 的瓶頸常在網路、用 Prometheus integration 把跨節點複製流量納入告警基線。

### Quorum queue 的 quorum loss

**徵兆**：cluster 有節點故障後、某些 quorum queue 變成不可寫、publisher confirm 卡住超時、`rabbitmq-diagnostics check_if_node_is_quorum_critical` 報警。

> 以下跨節點行為依官方文件、單節點環境未實機驗證。

**根因**：quorum queue 靠 Raft majority 運作。一個 3-replica 的 queue 容忍 1 個節點故障（剩 2 個構成 majority）；故障 2 個節點時、剩 1 個無法構成多數派、queue 進入 *無 leader* 狀態、拒絕寫入以保證一致性。這是 Raft 的設計選擇：寧可不可用、不可不一致。replica 數設成偶數（如 2 或 4）更糟 — 偶數的 majority 門檻不會提升容錯、反而浪費資源。

**修法**：

1. **replica 數設奇數**：3 replica 容忍 1 故障、5 replica 容忍 2 故障。奇數讓 majority 計算最有效率。
2. **監控 quorum critical 狀態**：`rabbitmq-diagnostics check_if_node_is_quorum_critical` 在「再掛一個節點就會失去 quorum」時提前告警、在維護重啟前先確認不會打破 majority。
3. **跨故障域分佈 replica**：把 3 個 replica 放在不同 AZ / 機架、避免單一故障域同時帶走多數派。
4. **理解不可用是預期行為**：quorum loss 時 queue 拒寫是 *正確* 的、不是 bug。恢復路徑是把故障節點拉回 cluster 重組 majority、不是強制覆寫。

### Stream retention 超量

**徵兆**：stream queue 所在節點磁碟使用率持續上升、最終觸發 disk alarm、broker 暫停所有 publisher；或 consumer 嘗試讀取較舊的 offset 時拿到「offset 不存在」、發現歷史訊息已被截斷。

**根因**：stream 是 append-only log、訊息 *不因消費而刪除*、只靠 retention 上限（`x-max-age` 時間 / `x-max-length-bytes` 大小）回收。retention 設太寬、或寫入速率超過預估、log 持續長大直到塞滿磁碟。反過來 retention 設太緊、consumer 還沒讀到的舊訊息就被截斷、replay 場景拿不到完整歷史。Stream 的容量管理是「設定 retention」、不是「靠消費清空」 — 這跟隊列直覺相反。

**修法**：

1. **retention 雙保險**：同時設 `x-max-age`（時間上限、對齊業務 replay 窗口、如 7 天）與 `x-max-length-bytes`（大小上限、對齊磁碟容量）。先到的條件先觸發截斷、避免單一維度失控。
2. **segment 大小對齊回收粒度**：`x-stream-max-segment-size-bytes` 決定 log 分段大小、retention 以 segment 為單位回收。segment 太大、retention 觸發後一次釋放大量空間、磁碟曲線鋸齒；太小、segment 檔案數量爆炸。
3. **容量公式先算再設**：預估 `寫入速率 × 訊息平均大小 × retention 時間`、確認低於節點磁碟可用空間的安全水位（如 70%）、再上線。
4. **monitor disk_free_limit**：stream 節點的磁碟告警閾值要比一般節點更早、因為 stream 是磁碟密集型、disk alarm 觸發會凍結整個 broker 的 publisher。

### Classic → Quorum 遷移的 in-flight message

**徵兆**：把工作隊列從 classic（或 deprecated mirrored）遷到 quorum 時、切換瞬間有訊息遺失、或重複處理 — queue 重建期間 publisher 已經在發、consumer 還沒接上新 queue。

**根因**：queue type 無法原地變更、遷移本質是 *建新 queue + 切流量 + 排空舊 queue*。最大的坑是 in-flight 訊息：舊 classic queue 裡還有未消費的訊息、若直接刪除舊 queue、這些訊息就丟了；若 publisher 提前切到新 queue、舊 queue 的 consumer 還在處理、就出現新舊兩條路徑並存的一致性窗口。[3.C27 Zalando](/backend/03-message-queue/cases/rabbitmq-zalando-aws-master-selection/) 跨版本升級用 federation 過渡、正是為了平滑搬移而非硬切。

**修法**：

1. **新 queue 先建、binding 並存**：用新 routing key 或新 queue 名建立 quorum queue、舊 classic queue 暫不刪。
2. **consumer 先切、publisher 後切**：先讓 consumer 同時消費新舊兩個 queue、確認新 queue 路徑正常、再把 publisher 切到只發新 queue。順序顛倒（publisher 先切）會讓舊 queue 的 in-flight 訊息沒人消費。
3. **排空舊 queue 再刪**：publisher 切換後、等舊 classic queue `messages` 歸零（用 `list_queues name messages` 確認）、才刪除舊 queue。
4. **依賴 idempotency 兜底**：遷移窗口內訊息可能重複投遞、consumer 端的 [idempotency](/backend/knowledge-cards/idempotency/) 是最後一道防線（語義誤配的後果見 [3.C9](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/)）、不要假設遷移零重複。
5. **用 federation / shovel 做大規模搬移**：跨 cluster 或跨版本場景、用 federation upstream 把舊 cluster 訊息引流到新 cluster、避免一次性硬切（Zalando case 的做法）。

## 容量與成本規劃

| 維度             | Classic                              | Quorum                               | Stream                                                              |
| ---------------- | ------------------------------------ | ------------------------------------ | ------------------------------------------------------------------- |
| 單筆寫入延遲     | 低（單節點 fsync）                   | 中（Raft majority round-trip）       | 低（順序 append、批次 ack）                                         |
| 記憶體 / 訊息    | 高（常駐、lazy 緩解）                | 中（on-disk 為主 + index）           | 低（log 在磁碟、靠 page cache）                                     |
| 磁碟成長         | 隨未消費堆積                         | 隨未消費堆積                         | 隨 retention 上限、消費不回收                                       |
| 節點故障容忍     | 無（該 queue 不可用）                | 容忍少數派故障（3 replica 容 1）     | Leader 故障可切 follower                                            |
| 適用規模上限訊號 | 堆積導致記憶體壓力 / 需要跨節點 HA   | Raft 延遲成為瓶頸 / 超高吞吐         | 事件流規模需要跨團隊 schema 治理                                    |
| 超出後改走       | Quorum（要 HA）/ Stream（要 replay） | Stream（要 replay）/ Kafka（要生態） | [Kafka](/backend/03-message-queue/vendors/kafka/)（跨團隊事件平台） |

實務 default：

- **單節點開發 / 臨時隊列**：classic、最簡單、transient 模式適合 RPC reply。
- **生產工作隊列、不可丟訊息**：quorum、3 replica 跨 AZ、replica 數設奇數。
- **事件流 / 多 consumer / 需要 replay**：stream、retention 雙保險、磁碟容量先算。
- **判斷該不該升級到 Kafka**：當 stream 場景開始需要跨團隊 schema registry、tiered storage、或成熟的 streaming 生態工具時、stream 是過渡、Kafka 是終點。

## 整合與下一步

Queue type 的選擇與 RabbitMQ 其他能力交織：

- **回 vendor overview**：三種 queue type 的取捨在 [RabbitMQ overview](/backend/03-message-queue/vendors/rabbitmq/)「Classic queue vs Quorum queue vs Stream」段有 vendor-level 定位；本文是其 implementation 展開。
- **durable queue 能力層**：queue type 的持久化語意建立在 [3.2 durable queue](/backend/03-message-queue/durable-queue/) 的概念上 — quorum 與 stream 強制 durable、正是把「處理即承諾」的可靠性從單節點延伸到跨節點。
- **durable queue 知識卡**：訊息持久化的概念基礎見 [durable queue 知識卡](/backend/knowledge-cards/durable-queue/)。
- **mirrored → quorum 的遷移動機**：[3.C30 Runtastic](/backend/03-message-queue/cases/rabbitmq-runtastic-mirrored-queue-bottleneck/) 量化 mirrored 網路成本、是遷 quorum 的證據。
- **跨版本 / 跨 cluster 平滑遷移**：[3.C27 Zalando](/backend/03-message-queue/cases/rabbitmq-zalando-aws-master-selection/) 用 federation 過渡、是 in-flight message 安全搬移的範本。

何時 revisit queue type 選擇：classic queue 開始出現記憶體壓力或需要跨節點 HA 時、評估 quorum；任何 queue 場景開始需要「補讀歷史」「多 consumer 各自進度」「replay 重算」時、評估 stream；stream 場景開始需要跨團隊事件治理時、評估遷 [Kafka](/backend/03-message-queue/vendors/kafka/)。
