---
title: "0.3 非同步與事件傳遞選型"
date: 2026-04-23
description: "區分背景工作、durable queue、stream、pub/sub 與 outbox 的選型邊界"
weight: 3
---

非同步與事件傳遞選型的核心原則是先判斷工作離開 request 後需要什麼保證。背景工作、[durable queue](../knowledge-cards/durable-queue/)、stream、[pub/sub](../knowledge-cards/pub-sub/) 與 outbox 都能讓流程非同步化，但它們對持久化、重試、順序、[fan-out](../knowledge-cards/fan-out/) 與一致性的承諾不同。

## 本章目標

學完本章後，你將能夠：

1. 區分本地背景工作、[broker](../knowledge-cards/broker/) [queue](../knowledge-cards/queue/)、stream、[pub/sub](../knowledge-cards/pub-sub/) 與 outbox
2. 用投遞保證、重試需求與 [fan-out](../knowledge-cards/fan-out/) 需求判斷服務類型
3. 看懂 RabbitMQ、Kafka、NATS、Redis Streams 這類工具的選型入口
4. 把非同步設計轉成可檢查的工程判斷

---

## 【觀察】非同步需求來自 request 邊界外的工作

非同步處理通常從一個現象開始：某件事適合在 request 結束後繼續做。這可能是因為工作太慢、需要重試、需要多個 [consumer](../knowledge-cards/consumer/)、需要跨服務傳遞，或需要在資料庫交易後補送事件。

| 需求訊號                                   | 代表的工程問題                 | 常見服務方向  |
| ------------------------------------------ | ------------------------------ | ------------- |
| 工作只需要離開 request，但留在同一 process | 背景處理與生命週期             | [local worker](../knowledge-cards/local-worker/)  |
| 工作需要 process 重啟後仍存在              | 持久化與重試                   | [durable queue](../knowledge-cards/durable-queue/) |
| 多個 consumer 要各自追進度                 | replay、[offset](../knowledge-cards/offset/)、[consumer group](../knowledge-cards/consumer-group/) | stream / [log](../knowledge-cards/log/)  |
| 多個訂閱者即時收到訊息                     | [fan-out](../knowledge-cards/fan-out/) 與即時通知 | [pub/sub](../knowledge-cards/pub-sub/)       |
| 資料寫入和事件發布要一起可靠               | 交易一致性與補送               | outbox        |

這張表是索引。選型時要看事件是否能遺失、是否會重複、是否要重播、是否要多個服務各自消費。

## 【判讀】local worker 承擔 process 內背景工作

[Local worker](../knowledge-cards/local-worker/) 的核心責任是把工作從 request 等待時間中拆出來，但仍留在同一個 process 裡。當工作可以接受 process 重啟後消失，或上游可以重新觸發，[local worker](../knowledge-cards/local-worker/) 通常足夠。

接近真實網路服務的例子包括：

- request 完成後寫一筆非關鍵 [audit log](../knowledge-cards/audit-log/)
- 在同一服務內批次刷新短生命週期快取
- 定期清理 memory repository 裡的過期資料

這類設計的主要風險是生命週期。worker 要能停止、記錄錯誤、控制 queue full，並在 shutdown 時有明確策略。語言教材通常會處理這一層，例如 Go 的 `Run(ctx)`、[in-process channel](../knowledge-cards/in-process-channel/) 與 [worker pool](../knowledge-cards/worker-pool/)。

## 【判讀】durable queue 承擔可重試工作

[Durable queue](../knowledge-cards/durable-queue/) 的核心責任是讓工作在 process 重啟、暫時失敗或 consumer 下線後仍能被處理。當事件可以延後，但需要可靠送達與重試，應評估 broker queue。

接近真實網路服務的例子包括：

- 付款成功後寄送 email、簡訊與推播
- 上傳影片後排隊轉檔
- 訂單成立後建立出貨任務

這類設計的主要風險是 [delivery semantics](../knowledge-cards/delivery-semantics/)。服務要決定 [ack/nack](../knowledge-cards/ack-nack/)、retry、[dead-letter queue](../knowledge-cards/dead-letter-queue/)、[poison message](../knowledge-cards/poison-message/) 與 [idempotency](../knowledge-cards/idempotency/)。RabbitMQ、NATS JetStream、Redis Streams 都可以承擔部分 durable delivery，但模型不同。

## 【判讀】stream 承擔可重播事件序列

stream 的核心責任是保存事件序列，讓 consumer 可以依自己的進度讀取。當資料需要 replay、多個 consumer group、offset 或 [partition](../knowledge-cards/partition/) ordering，stream 模型會比單純 queue 更合適。

接近真實網路服務的例子包括：

- 使用者行為事件進入分析 pipeline
- 訂單事件同時給推薦、風控、報表系統消費
- IoT sensor readings 需要持續聚合與回放

這類設計的主要風險是順序、保留期限與 schema 演進。Kafka、Redis Streams、NATS JetStream 都提供不同程度的 stream 能力；選型時要看 throughput、consumer group、保留策略與操作成本。

## 【判讀】pub/sub 承擔即時 fan-out

[Pub/Sub](../knowledge-cards/pub-sub/) 的核心責任是把訊息即時傳給目前訂閱者。當訊息偏向即時通知，且訂閱者離線後可以透過 [offline catch-up](../knowledge-cards/offline-catchup/) 補狀態，[pub/sub](../knowledge-cards/pub-sub) 通常是好候選。

接近真實網路服務的例子包括：

- [WebSocket](../knowledge-cards/websocket/) server 跨節點廣播 [topic](../knowledge-cards/topic/) update
- presence 狀態變更通知在線 client
- [dashboard](../knowledge-cards/dashboard/) 即時刷新目前任務進度

這類設計的主要風險是 [reliability boundary](../knowledge-cards/reliability-boundary/)。pub/sub 適合即時 [fan-out](../knowledge-cards/fan-out/)；若訊息需要 [offline catch-up](../knowledge-cards/offline-catchup/)、audit 或 [strong reliability](../knowledge-cards/strong-reliability/)，通常還需要 [durable queue](../knowledge-cards/durable-queue/)、[event log](../knowledge-cards/event-log/) 或資料庫狀態搭配。

## 【判讀】outbox 承擔資料寫入與事件補送

outbox 的核心責任是把業務資料寫入和待發事件放進同一個資料庫交易，再由 publisher 補送。當狀態更新成功後必須可靠發布事件，outbox 是常見選型。

接近真實網路服務的例子包括：

- 訂單寫入成功後必須發布 `order.created`
- 付款狀態更新後必須通知出貨與報表系統
- 帳號停用後必須可靠通知所有安全相關服務

這類設計的主要風險是半成功。outbox 讓事件至少會被發現並補送；consumer 仍需要 idempotency，因為補送與重試可能造成重複投遞。

## 【檢查】進入實作前的概念邊界清單

當以下問題都能回答時，代表本章的概念層已完成，可以進入訊息傳遞實作章節：

1. 每種事件的投遞語意是否明確（可遺失、可重試、可重播）
2. 事件失敗後的路徑是否明確（retry、DLQ、replay）
3. consumer 的去重責任是否明確（idempotency 範圍與語意鍵）
4. 壓力保護條件是否明確（lag、[queue depth](../knowledge-cards/queue-depth/)、降級觸發）

下一步建議路由：

- [03-message-queue](../03-message-queue/)
- [08-incident-response](../08-incident-response/)

## 小結

非同步選型要先看工作需要什麼保證。本地工作用 [local worker](../knowledge-cards/local-worker/)，可重試工作用 [durable queue](../knowledge-cards/durable-queue/)，可重播事件序列用 stream，即時 [fan-out](../knowledge-cards/fan-out/) 用 [pub/sub](../knowledge-cards/pub-sub/)，資料寫入與事件發布一致性用 outbox。分類清楚後，RabbitMQ、Kafka、NATS、Redis Streams 等工具比較才有意義。
