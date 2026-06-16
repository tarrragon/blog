---
title: "模組三：訊息佇列與事件傳遞"
date: 2026-04-22
description: "整理 durable queue、broker、retry、outbox 與 idempotency 的後端實務"
weight: 3
tags: ["backend", "message-queue", "event-delivery"]
---

訊息佇列模組的核心目標是說明事件離開單一 process 後，如何處理持久化、重試、[重複投遞](/backend/knowledge-cards/duplicate-delivery/)與 [consumer](/backend/knowledge-cards/consumer) 協調。語言教材會先處理本地 [queue](/backend/knowledge-cards/queue) abstraction、publisher port、processor 與 [idempotency](/backend/knowledge-cards/idempotency) interface；本模組負責 [broker](/backend/knowledge-cards/broker/) 的具體語意。

## Vendor / Platform 清單

實作時的常用選擇見 [vendors](/backend/03-message-queue/vendors/) — T1 收錄 RabbitMQ / Kafka / NATS / Redis Streams / AWS SQS / Google Pub/Sub，每個 vendor 有定位、適用場景、取捨與預計實作話題的骨架。

Deep article（vendor 自身的配置、故障、容量）跟 migration playbook（跨 vendor 遷移流程）的撰寫進度見 [vendors/](/backend/03-message-queue/vendors/) 的「內容覆蓋進度」段。

## 暫定分類

| 分類          | 內容方向                                                                                                                                                                                                 |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| RabbitMQ      | exchange、queue、routing key、[ack/nack](/backend/knowledge-cards/ack-nack)、[dead-letter queue](/backend/knowledge-cards/dead-letter-queue)                                                             |
| NATS          | subject、consumer、JetStream、at-least-once delivery                                                                                                                                                     |
| Kafka         | [topic](/backend/knowledge-cards/topic)、[partition](/backend/knowledge-cards/partition)、[consumer group](/backend/knowledge-cards/consumer-group)、[offset](/backend/knowledge-cards/offset)、ordering |
| Redis Streams | stream、consumer group、pending entry、claim                                                                                                                                                             |
| Outbox        | [transaction](/backend/knowledge-cards/transaction) outbox、poller、publisher、重試策略                                                                                                                  |
| Idempotency   | idempotency key、dedup store、replay safety                                                                                                                                                              |

## 選型入口

訊息佇列選型的核心判斷是工作離開 request 或 process 後需要什麼投遞保證。當工作需要排隊、重試、跨服務傳遞、多 consumer 協作或事件補送時，[broker](/backend/knowledge-cards/broker) 與 outbox 值得優先評估。

RabbitMQ 適合明確 routing、[ack/nack](/backend/knowledge-cards/ack-nack/) 與工作佇列；NATS 適合 subject-based messaging 與較輕量的服務通訊，搭配 JetStream 可加入持久化；Kafka 適合高吞吐事件流、partition 與長期 replay；Redis Streams 適合 Redis 生態內的 stream 與 consumer group；[outbox](/backend/knowledge-cards/outbox-pattern/) 解決資料寫入與事件發布的一致性；[idempotency](/backend/knowledge-cards/idempotency/) 解決重複投遞造成的結果穩定性；[retry budget](/backend/knowledge-cards/retry-budget/) 與 [jitter](/backend/knowledge-cards/jitter/) 則控制故障期間的重試壓力。

接近真實網路服務的例子包括付款後寄信、影片轉檔、訂單事件傳給多個系統、IoT readings pipeline 與跨節點通知。這些場景的共同問題是 [delivery semantics](/backend/knowledge-cards/delivery-semantics)，因此本模組會先處理 broker 模型、retry、[DLQ](/backend/knowledge-cards/dead-letter-queue/)、outbox 與 consumer 設計。

## 與語言教材的分工

語言教材處理本地 [backpressure](/backend/knowledge-cards/backpressure)、processor 邊界、port / [Message Protocol](/backend/knowledge-cards/message-protocol/) 設計與單一 process 內的去重。Backend message queue 模組處理 broker selection、ack/nack、DLQ、consumer group、outbox 與跨 process 重試。

## 案例驅動讀法

佇列案例的核心讀法是先辨識遷移的是「資料路徑」還是「治理路徑」，再決定先做 broker 切換還是治理收斂。

| 案例                                                                                         | 先看章節                                                                                           | 回寫目標                                    |
| -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| [3.C1 Meta：FOQS 全域遷移](/backend/03-message-queue/cases/meta-foqs-global-migration/)      | [3.1](/backend/03-message-queue/broker-basics/)、[3.2](/backend/03-message-queue/durable-queue/)   | 把跨區 queue 路由與可用性邊界前置           |
| [3.C2 VMware：Kafka -> MSK](/backend/03-message-queue/cases/vmware-kafka-to-msk/)            | [3.1](/backend/03-message-queue/broker-basics/)、[3.4](/backend/03-message-queue/consumer-design/) | 把 managed broker 遷移轉成 ACL/lag/回退治理 |
| [3.C3 LinkedIn：TopicGC](/backend/03-message-queue/cases/linkedin-topicgc-kafka-governance/) | [3.4](/backend/03-message-queue/consumer-design/)                                                  | 把 topic 生命週期治理納入可靠性成本模型     |

## 跨語言適配評估

訊息佇列使用方式會受語言的 worker model、錯誤處理、序列化、背景任務框架與 idempotency 設計影響。同步 runtime 要控制 consumer thread 數量與 ack [timeout](/backend/knowledge-cards/timeout)；async runtime 要處理 backpressure 與 long-running handler；輕量並發 runtime 要限制同時處理量，避免 consumer 擴張超過下游容量。強型別語言適合建立 event schema 與 command model；動態語言要補足 payload validation、dead-letter 診斷與重播測試。

## 章節列表

| 章節                                                                  | 主題                                                                   | 關鍵收穫                                                                              |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| [3.1](/backend/03-message-queue/broker-basics/)                       | broker 基礎與投遞模型                                                  | 看懂 exchange、topic、consumer 與 delivery semantics                                  |
| [3.2](/backend/03-message-queue/durable-queue/)                       | [durable queue](/backend/knowledge-cards/durable-queue) 與重試策略     | 規劃持久化、ack/nack、DLQ 與 retry                                                    |
| [3.3](/backend/03-message-queue/outbox-pattern/)                      | [outbox pattern](/backend/knowledge-cards/outbox-pattern) 與發佈一致性 | 把交易寫入與事件發佈分離                                                              |
| [3.4](/backend/03-message-queue/consumer-design/)                     | consumer 設計與去重                                                    | 設計 idempotency、[checkpoint](/backend/knowledge-cards/checkpoint/) 與 replay safety |
| [3.5](/backend/03-message-queue/red-team-delivery-layer/)             | 攻擊者視角（紅隊）：傳遞層弱點判讀                                     | 用重放、重複、毒訊息與延遲累積檢查非同步傳遞邊界                                      |
| [3.6](/backend/03-message-queue/processing-recovery-semantics/)       | Processing Semantics 與 Recovery Semantics                             | 分辨投遞成功、處理成功與恢復成功                                                      |
| [3.7](/backend/03-message-queue/event-contract-replay-boundary/)      | Event Contract 與 Replay Boundary                                      | 定義 event schema、idempotency key、replay window 與補償邊界                          |
| [3.8](/backend/03-message-queue/queue-consumer-retry-replay-handoff/) | Queue Consumer Retry 與 Replay Handoff 實作示範                        | 以訂單事件 consumer 示範 evidence、DLQ、replay runbook 與 decision log                |
| [3.C](/backend/03-message-queue/cases/)                               | 轉換案例正文                                                           | 把 queue 架構、broker 遷移與 topic 治理轉成可操作案例                                 |

反例與規模對照入口： [3.C9 反例](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/) / [3.C10 對照](/backend/03-message-queue/cases/contrast-queue-model-by-scale/)。

回退判讀寫法見 [0.C4 回退判讀寫法](/backend/00-service-selection/cases/post-scale-migration-language-tool-architecture/#回退判讀寫法)，queue 案例要優先保留 delivery semantics、lag、DLQ 與 replay 條件。

## 觀念網路補完方向

訊息佇列章節下一輪的核心責任是把「投遞成功」和「業務結果正確」分開。現有章節已經有 broker、durable queue、outbox 與 consumer design，但還需要補上 delivery semantics、processing semantics 與 recovery semantics 的三層關係，讓讀者知道 queue 失敗同時包括訊息遺失、重複副作用、順序錯亂、重播風險與下游壓力放大。

| 補完方向             | 需要回答的問題                                     | 主要路由                                                                                                                     |
| -------------------- | -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Delivery semantics   | broker 如何 ack、nack、redelivery、retry、送入 DLQ | [delivery semantics](/backend/knowledge-cards/delivery-semantics/)、[3.2](/backend/03-message-queue/durable-queue/)          |
| Processing semantics | consumer 的副作用是否能承受重複、亂序與部分失敗    | [idempotency](/backend/knowledge-cards/idempotency/)、[6.12](/backend/06-reliability/idempotency-replay/)                    |
| Recovery semantics   | replay、checkpoint、offset 與補償是否可重播與驗證  | [offset](/backend/knowledge-cards/offset/)、[8.19](/backend/08-incident-response/incident-decision-log/)                     |
| Outbox boundary      | 資料庫交易與事件發布是否有一致性邊界               | [outbox pattern](/backend/knowledge-cards/outbox-pattern/)、[1.3](/backend/01-database/transaction-boundary/)                |
| Poison handling      | 壞訊息是否會卡住 consumer 或被無限重試             | [poison message](/backend/knowledge-cards/poison-message/)、[dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) |

這些方向要用非同步服務自己的語意展開。寄信、開 invoice、更新 CRM、同步 search index、發 webhook 的副作用不同，retry、DLQ 與 replay 的判準也不同。

## 知識卡補強方向

佇列模組的 knowledge card 缺口集中在「處理語意」與「恢復語意」。已有 [consumer lag](/backend/knowledge-cards/consumer-lag/)、[retry budget](/backend/knowledge-cards/retry-budget/)、[poison message](/backend/knowledge-cards/poison-message/) 與 [offset](/backend/knowledge-cards/offset/) 可以作為第一批錨點。

第二批卡片已補上 [processing semantics](/backend/knowledge-cards/processing-semantics/)、[recovery semantics](/backend/knowledge-cards/recovery-semantics/)、[replay window](/backend/knowledge-cards/replay-window/)、[consumer pause](/backend/knowledge-cards/consumer-pause/)、[event schema compatibility](/backend/knowledge-cards/event-schema-compatibility/)、[DLQ drain](/backend/knowledge-cards/dlq-drain/) 與 [poison-message quarantine](/backend/knowledge-cards/poison-message-quarantine/)。這些卡片讓讀者能分辨「queue 有持久化」和「consumer 結果可恢復」分屬不同責任。

## 實作探討入口

佇列的第一條實作路徑是 [3.8 Queue Consumer Retry 與 Replay Handoff（實作示範）](/backend/03-message-queue/queue-consumer-retry-replay-handoff/)。這篇以 `order_created` consumer 為例，說明 idempotency evidence、DLQ handling、replay runbook 與 incident decision route 如何一起成立。

這條路徑的前置引用應該是 3.2 durable queue、3.3 outbox pattern、3.4 consumer design、[6.12 Idempotency 與 Replay 驗證](/backend/06-reliability/idempotency-replay/) 與 [6.23 Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/)。完成後可依 [Backend 學習路線](/backend/#學習路線) 進入下一條服務路徑。

佇列路徑的 artifact 對齊重點是「把投遞成功與處理成功拆開記錄」。對 [4.20](/backend/04-observability/observability-evidence-package/) 要交 `Source/Time range/Query link/Owner/Data quality`，並覆蓋 consumer lag、retry、DLQ 與 duplicate side-effect；對 [6.12](/backend/06-reliability/idempotency-replay/) / [6.23](/backend/06-reliability/verification-evidence-handoff/) / [6.8](/backend/06-reliability/release-gate/) 要交 `Gate decision/Checks/Stop condition/Rollback window/Owner`，呈現 replay 範圍、去重驗證與補償路徑；對 [8.19](/backend/08-incident-response/incident-decision-log/) 要交 `Timestamp/Decision/Context/Evidence/Owner/Expected effect/Rollback condition`，記錄 pause consumer、drain DLQ、重播啟停的決策序列。
