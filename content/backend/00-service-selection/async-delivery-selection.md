---
title: "0.3 非同步與事件傳遞選型"
date: 2026-04-23
description: "區分背景工作、durable queue、stream、pub/sub 與 outbox 的選型邊界"
weight: 3
tags: ["backend", "service-selection"]
---

非同步與事件傳遞選型的核心原則是先判斷工作離開 request 後需要什麼保證。背景工作、[durable queue](/backend/knowledge-cards/durable-queue/)、stream、[pub/sub](/backend/knowledge-cards/pub-sub/) 與 outbox 都能讓流程非同步化，但它們對持久化、重試、順序、[fan-out](/backend/knowledge-cards/fan-out/) 與一致性的承諾不同。

## 本章目標

學完本章後，你將能夠：

1. 區分本地背景工作、[broker](/backend/knowledge-cards/broker/) [queue](/backend/knowledge-cards/queue/)、stream、[pub/sub](/backend/knowledge-cards/pub-sub/) 與 outbox
2. 用投遞保證、重試需求與 [fan-out](/backend/knowledge-cards/fan-out/) 需求判斷服務類型
3. 看懂 RabbitMQ、Kafka、NATS、Redis Streams 這類工具的選型入口
4. 把非同步設計轉成可檢查的工程判斷

---

## 【觀察】非同步需求來自 request 邊界外的工作

非同步處理通常從一個現象開始：某件事適合在 request 結束後繼續做。這可能是因為工作太慢、需要重試、需要多個 [consumer](/backend/knowledge-cards/consumer/)、需要跨服務傳遞，或需要在資料庫交易後補送事件。

| 需求訊號                                   | 代表的工程問題                                                                                                 | 常見服務方向                                             |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| 工作只需要離開 request，但留在同一 process | 背景處理與生命週期                                                                                             | [local worker](/backend/knowledge-cards/local-worker/)   |
| 工作需要 process 重啟後仍存在              | 持久化與重試                                                                                                   | [durable queue](/backend/knowledge-cards/durable-queue/) |
| 多個 consumer 要各自追進度                 | replay、[offset](/backend/knowledge-cards/offset/)、[consumer group](/backend/knowledge-cards/consumer-group/) | stream / [log](/backend/knowledge-cards/log/)            |
| 多個訂閱者即時收到訊息                     | [fan-out](/backend/knowledge-cards/fan-out/) 與即時通知                                                        | [pub/sub](/backend/knowledge-cards/pub-sub/)             |
| 資料寫入和事件發布要一起可靠               | 交易一致性與補送                                                                                               | outbox                                                   |

這張表是索引。選型時要看事件是否能遺失、是否會重複、是否要重播、是否要多個服務各自消費。

## 【判讀】local worker 承擔 process 內背景工作

[Local worker](/backend/knowledge-cards/local-worker/) 的核心責任是把工作從 request 等待時間中拆出來，但仍留在同一個 process 裡。當工作可以接受 process 重啟後消失，或上游可以重新觸發，[local worker](/backend/knowledge-cards/local-worker/) 通常足夠。

接近真實網路服務的例子包括：

- request 完成後寫一筆非關鍵 [audit log](/backend/knowledge-cards/audit-log/)
- 在同一服務內批次刷新短生命週期快取
- 定期清理 memory repository 裡的過期資料

這類設計的主要風險是生命週期。worker 要能停止、記錄錯誤、控制 queue full，並在 shutdown 時有明確策略。語言教材通常會處理這一層，例如 Go 的 `Run(ctx)`、[in-process channel](/backend/knowledge-cards/in-process-channel/) 與 [worker pool](/backend/knowledge-cards/worker-pool/)。

## 【判讀】durable queue 承擔可重試工作

[Durable queue](/backend/knowledge-cards/durable-queue/) 的核心責任是讓工作在 process 重啟、暫時失敗或 consumer 下線後仍能被處理。當事件可以延後，但需要可靠送達與重試，應評估 broker queue。

接近真實網路服務的例子包括：

- 付款成功後寄送 email、簡訊與推播
- 上傳影片後排隊轉檔
- 訂單成立後建立出貨任務

這類設計的主要風險是 [delivery semantics](/backend/knowledge-cards/delivery-semantics/)。服務要決定 [ack/nack](/backend/knowledge-cards/ack-nack/)、retry、[dead-letter queue](/backend/knowledge-cards/dead-letter-queue/)、[poison message](/backend/knowledge-cards/poison-message/) 與 [idempotency](/backend/knowledge-cards/idempotency/)。RabbitMQ、NATS JetStream、Redis Streams 都可以承擔部分 durable delivery，但模型不同。

## 【判讀】stream 承擔可重播事件序列

stream 的核心責任是保存事件序列，讓 consumer 可以依自己的進度讀取。當資料需要 replay、多個 consumer group、offset 或 [partition](/backend/knowledge-cards/partition/) ordering，stream 模型會比單純 queue 更合適。

接近真實網路服務的例子包括：

- 使用者行為事件進入分析 pipeline
- 訂單事件同時給推薦、風控、報表系統消費
- IoT sensor readings 需要持續聚合與回放

這類設計的主要風險是順序、保留期限與 schema 演進。Kafka、Redis Streams、NATS JetStream 都提供不同程度的 stream 能力；選型時要看 [throughput](/backend/knowledge-cards/throughput/)、consumer group、保留策略與操作成本。

## 【判讀】pub/sub 承擔即時 fan-out

[Pub/Sub](/backend/knowledge-cards/pub-sub/) 的核心責任是把訊息即時傳給目前訂閱者。當訊息偏向即時通知，且訂閱者離線後可以透過 [offline catch-up](/backend/knowledge-cards/offline-catchup/) 補狀態，[pub/sub](/backend/knowledge-cards/pub-sub/) 通常是好候選。

接近真實網路服務的例子包括：

- [WebSocket](/backend/knowledge-cards/websocket/) server 跨節點廣播 [topic](/backend/knowledge-cards/topic/) update
- presence 狀態變更通知在線 client
- [dashboard](/backend/knowledge-cards/dashboard/) 即時刷新目前任務進度

這類設計的主要風險是 [reliability boundary](/backend/knowledge-cards/reliability-boundary/)。pub/sub 適合即時 [fan-out](/backend/knowledge-cards/fan-out/)；若訊息需要 [offline catch-up](/backend/knowledge-cards/offline-catchup/)、audit 或 [strong reliability](/backend/knowledge-cards/strong-reliability/)，通常還需要 [durable queue](/backend/knowledge-cards/durable-queue/)、[event log](/backend/knowledge-cards/event-log/) 或資料庫狀態搭配。

## 【判讀】outbox 承擔資料寫入與事件補送

outbox 的核心責任是把業務資料寫入和待發事件放進同一個資料庫交易，再由 publisher 補送。當狀態更新成功後必須可靠發布事件，outbox 是常見選型。

接近真實網路服務的例子包括：

- 訂單寫入成功後必須發布 `order.created`
- 付款狀態更新後必須通知出貨與報表系統
- 帳號停用後必須可靠通知所有安全相關服務

這類設計的主要風險是半成功。outbox 讓事件至少會被發現並補送；consumer 仍需要 idempotency，因為補送與重試可能造成重複投遞。

## 【判讀】用業務形狀反推 broker 候選

反推的核心責任是把「目前場景需要的吞吐、延遲、保留窗口與操作承擔」轉成 broker 候選、不是從 vendor 規格表挑工具。先決定需求形狀、再對齊量級訊號、最後才挑工具。

接近真實網路服務的反推路徑：

- 感測器一秒上報幾百筆、可接受偶發遺失、後端只需即時聚合 → broker 候選是 MQTT broker / NATS、量級訊號 sub-ms 延遲 + 萬到十萬 msg/sec
- 訂單事件需要多個下游服務各自 replay、保留 7 天以上 → broker 候選是 Kafka / Pulsar、量級訊號 partition 化吞吐 + retention 天 / 週 / 月可設
- 寄信、轉檔等可重試任務、不要遺失但允許短暫延遲 → broker 候選是 RabbitMQ / SQS、量級訊號萬級 msg/sec + ack/nack + dead-letter
- 跨節點即時通知在線 client、訂閱者離線可放棄 → broker 候選是 Redis Pub/Sub / NATS、量級訊號 sub-ms + 即時廣播、不保留

反推的目的是把「broker 比較」轉成「需求對齊」、避免從 vendor 規格表開始挑工具。下面四個維度是反推時要對齊的量級訊號。

### 吞吐量訊號

吞吐評估的核心問題是「broker 在我的 topology 下能撐多少」、不是「broker 規格上限」。同一個 broker 在不同 partition / queue / consumer / 訊息大小下、實際吞吐可以差一個量級。

實務量級（典型值、視配置與部署）：

| broker 類型             | 單節點典型吞吐                    | 量級擴張條件                            |
| ----------------------- | --------------------------------- | --------------------------------------- |
| MQTT broker             | 萬到十萬 msg/sec                  | 連線數 / topic 樹深度                   |
| RabbitMQ classic queue  | 萬級 msg/sec                      | quorum queue / stream / cluster scaling |
| Redis Streams           | 十萬 msg/sec                      | shard / consumer group                  |
| NATS JetStream          | 十萬到百萬 msg/sec                | subject hierarchy / cluster             |
| Kafka                   | 百萬 msg/sec（partition + batch） | partition 數 + batch.size + linger.ms   |
| Managed queue（SQS 等） | 視 account quota                  | region / 訊息大小                       |

對齊的問題是尖峰打進來後 broker 是否仍有 headroom（見 [0.5 流量與資料量評估](/backend/00-service-selection/traffic-data-scale/)）。穩定流量 × 尖峰倍率 × [fan-out](/backend/knowledge-cards/fan-out/) 倍率才是真正要對齊的數字。

### 延遲訊號

延遲評估的核心問題是「業務能容忍 P99 多少」、跟 broker 級延遲特性對齊。請求-應答、fire-and-forget、事件流的可容忍延遲是不同量級。

實務量級：

- sub-ms 到個位數 ms：MQTT broker、NATS、Redis Pub/Sub — 即時通知 / 控制信號 / IoT 上報
- 個位數 ms：RabbitMQ classic queue、Redis Streams — 任務隊列 / 中等延遲事件
- 十 ms 到百 ms：Kafka（低 batch）、managed pub/sub — 事件流 / 分析 pipeline
- 百 ms 以上：Kafka 高 batch、SQS standard — 批次處理 / 容忍延遲的補送

陷阱是把「broker 內部延遲」當成「端到端延遲」。實際端到端通常被 [consumer](/backend/knowledge-cards/consumer/) 處理時間 + 下游 I/O 主導、不是 broker 傳遞時間。

### 保留窗口訊號

保留窗口的核心問題是「事件需要被未來多久內的 consumer 讀到」。任務隊列吃掉就丟、事件流要可 replay、分析 pipeline 要留週級到月級。

實務量級：

- 不保留 / 短期：Redis Pub/Sub、MQTT QoS 0 — 只給「現在」訂閱者
- queue 級（持久但 ack 後刪）：RabbitMQ classic queue、SQS（最長 14 天）
- 中期（小時到天、受 RAM）：Redis Streams
- 天到月級（log-based、[retention](/backend/knowledge-cards/retention/) policy）：Kafka、Pulsar、NATS JetStream
- 永久 / tiered：Kafka tiered storage、Pulsar tiered storage

保留窗口直接影響成本：log-based broker 的儲存成本隨保留期線性增加、queue-based broker 的成本主要由「待處理深度」決定。

### 操作複雜度訊號

複雜度評估的核心問題是「團隊願意承擔哪些日常運維」、不是「broker 安裝多難」。安裝跟運維是不同量級工作。

實務量級：

- 低（managed）：SQS、Google Pub/Sub — quota / IAM / DLQ drain 是主要工作
- 低到中（self-host 但運維輕）：Redis Streams、NATS — 跟 Redis / NATS 本體運維捆綁
- 中（broker 級運維）：RabbitMQ — Erlang / clustering / mirrored vs quorum / network partition 處理
- 高（平台級運維）：Kafka self-host — partition rebalance / [consumer lag](/backend/knowledge-cards/consumer-lag/) / KRaft / topic governance / 跨 cluster 路由

複雜度的真正成本不在初期 setup、在「事故時誰能讀懂訊號」。挑 broker 時要問「下次 lag 暴增、團隊能在多久內找到原因」、這比 broker 規格表更接近真實業務考慮。

### 反推的常見陷阱

把「broker 規格上限」當需求對齊基準、會導致過度選型。Kafka 規格上百萬 msg/sec 不代表你需要 — 多數任務隊列場景在 RabbitMQ 萬級吞吐就足夠、Kafka 的 partition / consumer group / retention 治理成本反而是負擔。

把「現在吞吐」當未來基準、會導致欠選型。新 broker 通常要支撐 2-3 年成長、評估時要乘上預期成長倍率再對齊量級訊號。

把「規格表」當「實測值」、會在實際 topology 出問題。Broker 規格數字通常在最佳化測試環境得到、實際 production 受訊息大小 / consumer 速度 / 網路延遲 / replication factor 影響、實測常見差距 30%-60%。

## 【檢查】進入實作前的概念邊界清單

當以下問題都能回答時，代表本章的概念層已完成，可以進入訊息傳遞實作章節：

1. 每種事件的投遞語意是否明確（可遺失、可重試、可重播）
2. 事件失敗後的路徑是否明確（retry、DLQ、replay）
3. consumer 的去重責任是否明確（idempotency 範圍與語意鍵）
4. 壓力保護條件是否明確（lag、[queue depth](/backend/knowledge-cards/queue-depth/)、降級觸發）

下一步建議路由：

- [03-message-queue](/backend/03-message-queue/)
- [08-incident-response](/backend/08-incident-response/)

## 小結

非同步選型要先看工作需要什麼保證。本地工作用 [local worker](/backend/knowledge-cards/local-worker/)，可重試工作用 [durable queue](/backend/knowledge-cards/durable-queue/)，可重播事件序列用 stream，即時 [fan-out](/backend/knowledge-cards/fan-out/) 用 [pub/sub](/backend/knowledge-cards/pub-sub/)，資料寫入與事件發布一致性用 outbox。分類清楚後，RabbitMQ、Kafka、NATS、Redis Streams 等工具比較才有意義。
