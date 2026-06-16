---
title: "Google Pub/Sub push vs pull：不是實作偏好，是下游容量的判讀"
date: 2026-06-16
description: "Pub/Sub 的 push 與 pull subscription 常被當成實作偏好二選一，但它其實是一個容量判讀：push 把流量瞬間打到 endpoint，pull 讓 consumer 自己節流。下游有 RPS 限制就只能 pull。本文展開 subscription 模型、ack deadline、flow control 與 dead-letter topic，5 個把 push/pull 與 ack deadline 寫成下游打爆與重投的 production 踩坑"
weight: 11
tags: ["backend", "message-queue", "google-pubsub", "push-pull", "ack-deadline", "deep-article"]
---

> 本文是 [Google Cloud Pub/Sub](/backend/03-message-queue/vendors/google-pubsub/) overview 的 implementation-layer deep article。選型層（Pub/Sub vs Kafka / SQS）見 overview；本文只處理「決定用 Pub/Sub 後，subscription 與 ack 怎麼設」。Pub/Sub 是 managed SaaS、無法本機 docker 驗證，本文 config 依 [Pub/Sub 官方文件](https://cloud.google.com/pubsub/docs/subscriber) 與下列 production case、最後檢查日 2026-06-16；引數與計費以官方為準。

## push vs pull 不是實作偏好

把 Pub/Sub 的 subscription 設成 push 還是 pull，常被當成「看團隊習慣」的實作選擇。但它其實是一個關於下游容量的判讀。差別在流量控制權在誰手上：push subscription 由 Pub/Sub 主動把訊息 HTTP POST 到目標 endpoint——流量節奏由 Pub/Sub 決定，尖峰時瞬間打過來；pull subscription 由 consumer 主動拉，要拉多少、多快由 consumer 自己控制。

[Mercari 的 LINE 整合](/backend/03-message-queue/cases/pubsub-mercari-line-flow-control/)把這個判讀講得很具體：Braze webhook 進來轉成 Pub/Sub event，下游要呼叫 LINE API——而 **LINE API 有 RPS 限制**。如果用 push，Pub/Sub 會把訊息瞬間打到 worker、worker 再打 LINE、直接超過 LINE 的 RPS 上限。所以他們用 pull subscription，worker「精確控制每秒處理訊息數」來對齊 LINE 的限制。這個案例揭露的原則是——**push vs pull 不是實作偏好，是「下游能不能承受 push 的流量衝擊」的判讀**：下游有速率限制、處理能力有限、或需要平滑流量，就走 pull 自我節流。

本文展開 subscription 模型、ack deadline、flow control 與 dead-letter topic——這些決定了訊息怎麼被可靠地、以下游能承受的速度消費。

## 核心概念：subscription、ack deadline 與 flow control

Pub/Sub 把「topic（發布）」跟「subscription（訂閱）」分開，可靠消費的旋鈕都在 subscription 上。

**一個 topic、多個 subscription、各自獨立**。發布者發到 topic，每個 subscription 收到一份完整的訊息流、各自維護消費進度。這天然支援 fanout（多個服務各建一個 subscription）。[Mercari 的另一個案例](/backend/03-message-queue/cases/pubsub-mercari-item-feed-dlt/)還揭露 topic 的雙重角色——它同時是「dispatch」跟「load-leveling buffer」，突發流量先進 topic 緩衝、consumer 按自己節奏消化。

**ack deadline 是 Pub/Sub 版的可見性逾時**。consumer 收到訊息後，有一段 ack deadline 來處理並 `ack`。在 deadline 內沒 ack，Pub/Sub 重新投遞（at-least-once）。跟 [SQS visibility timeout](/backend/03-message-queue/vendors/aws-sqs/visibility-polling-lambda-cost/) 同樣是雙邊風險：太短→處理中就重投、太長→失敗後恢復慢。處理中可用 `modifyAckDeadline`（client library 通常自動 lease extension）延長。

**flow control 限制 client 端同時持有的未 ack 量**。pull subscription 的 client library 可設 `max_outstanding_messages` / `max_outstanding_bytes`——consumer 最多同時持有多少未 ack 訊息。這是 consumer 端自我節流的旋鈕，避免一次拉太多撐爆自己或下游。Mercari 對齊 LINE RPS 靠的就是這層控制。

**dead-letter topic（DLT）給毒訊息出口**。subscription 設 dead-letter policy（`maxDeliveryAttempts` + dead-letter topic）後，重投超過上限的訊息被轉到 DLT，不再阻塞後續。Mercari item feed 正是「重試多次仍失敗送 DLT、後續訊息優先處理」——避免 poison message 卡住 pipeline。

## 配置：subscription + ack deadline + DLT（依官方文件）

Pub/Sub 是 managed、以下 gcloud 依官方文件（未本機 docker 驗證、引數以官方為準）：

```bash
# 1. 建 topic + dead-letter topic
gcloud pubsub topics create orders
gcloud pubsub topics create orders-dlt

# 2. pull subscription：ack deadline + dead-letter policy
gcloud pubsub subscriptions create orders-worker \
  --topic=orders \
  --ack-deadline=60 \
  --dead-letter-topic=orders-dlt \
  --max-delivery-attempts=5

# 3. consumer 端 flow control（client library、以 Python 為例、概念跨語言一致）
#    flow_control = FlowControl(max_messages=100, max_bytes=10*1024*1024)
#    subscriber.subscribe(sub_path, callback=handle, flow_control=flow_control)
#    handle 內：處理成功 message.ack()、失敗 message.nack()

# push subscription（僅當下游能承受 Pub/Sub 主動推的流量時）：
# gcloud pubsub subscriptions create orders-push \
#   --topic=orders --push-endpoint=https://my-svc/handler --ack-deadline=60
```

判讀：

- 下游有 RPS 限制 / 處理能力有限 → pull + flow control（self-throttle，Mercari 模式）
- 下游能吸收推送尖峰、要 serverless 簡單 → push
- `ack-deadline` 略高於處理時間；長任務靠 client library 的 lease extension
- `max-delivery-attempts` + DLT 給毒訊息出口

## Production 故障演練

### Case 1：用 push、下游被瞬間流量打爆

**徵兆**：流量尖峰時下游 endpoint 5xx 暴增、或下游的第三方 API 回 429（rate limited），訊息大量重投惡化。

**根因**：用 push subscription，Pub/Sub 把訊息瞬間 POST 到 endpoint，超過下游（或下游依賴的外部 API）的處理 / 速率上限。正是 [Mercari LINE](/backend/03-message-queue/cases/pubsub-mercari-line-flow-control/) 要避開的情形。

**修法**：

1. 下游有速率限制改用 pull subscription + flow control，由 consumer 自我節流
2. flow control 的 `max_outstanding_messages` 對齊下游能承受的並發
3. push 只用在下游能吸收推送尖峰的場景
4. push 場景下游要自己擋（rate limit / 佇列），不能假設 Pub/Sub 會幫你平滑

### Case 2：ack deadline 太短、訊息處理中就被重投

**徵兆**：同一則訊息被處理多次，尤其處理較慢時；訂閱的 redelivery 指標偏高。

**根因**：ack deadline 設得比處理時間短，訊息在處理途中 deadline 到期、Pub/Sub 重投。跟 SQS visibility timeout 太短同類。

**修法**：

1. ack deadline 設成略高於處理時間 p99
2. 用 client library 的自動 lease extension（modifyAckDeadline）處理長尾任務
3. 消費端冪等——at-least-once 本來就可能重投（見 [6.12 idempotency](/backend/06-reliability/idempotency-replay/)）
4. 監控 redelivery 率，偏高代表 deadline 偏短或處理變慢

### Case 3：沒設 DLT、毒訊息一直重投阻塞

**徵兆**：某則訊息一直失敗、一直被重投，後續訊息處理被拖慢。

**根因**：subscription 沒設 dead-letter policy。處理失敗（nack 或沒 ack）的訊息一再重投、沒有上限與出口，毒訊息反覆消耗 consumer。

**修法**：

1. 設 dead-letter policy（`max-delivery-attempts` + DLT），重投達上限轉 DLT
2. DLT 是另一個 topic，要有處理 / 告警流程（Mercari「送 DLT、後續訊息優先處理」）
3. `max-delivery-attempts` 平衡暫時性失敗重試與毒訊息隔離
4. 對照 [SQS redrive](/backend/03-message-queue/vendors/aws-sqs/visibility-polling-lambda-cost/)：兩者都是 managed 原生 DLQ/DLT、比自建省事

### Case 4：flow control 沒設、consumer 一次拉太多撐爆

**徵兆**：consumer 記憶體暴增 / OOM，或一次拉太多把下游打爆。

**根因**：pull subscription 沒設 flow control，client library 預設可能持有大量未 ack 訊息，consumer 端記憶體與下游壓力失控。

**修法**：

1. 設 `max_outstanding_messages` / `max_outstanding_bytes` 限制同時持有量
2. 對齊 consumer 處理能力與下游容量（Mercari 對齊 LINE RPS）
3. 監控 consumer 記憶體與未 ack 數，調 flow control 參數
4. flow control 是 pull 自我節流的核心，不設等於放棄背壓

### Case 5：誤用 ordering key、吞吐受限

**徵兆**：開了 message ordering 後吞吐明顯下降、特定 ordering key 的訊息處理變慢。

**根因**：Pub/Sub 的順序保證是 per-ordering-key 的——同一個 ordering key 的訊息嚴格按序、必須序列處理（前一則 ack 才處理下一則）。把所有訊息塞同一個 ordering key 等於序列化整條流、吞吐崩。

**修法**：

1. ordering key 用細粒度（per-entity，如 per-user），讓不同 key 可並行
2. 不需要嚴格順序的就別開 ordering（預設無序、吞吐高）
3. 評估順序需求的真實範圍——多數場景只需 per-entity 順序，不是全域
4. 嚴格全域順序 + 高吞吐有本質衝突，重新審視需求或走 [Kafka](/backend/03-message-queue/vendors/kafka/) 的 partition 模型

## Capacity / cost 邊界

Pub/Sub 的容量判讀（managed、無 broker 運維）：

| 訊號                                             | 健康區間               | 警戒與動作                                                |
| ------------------------------------------------ | ---------------------- | --------------------------------------------------------- |
| subscription backlog（未 ack 數 / 最舊訊息 age） | 在 SLA 內              | 持續成長 → consumer 跟不上、加 consumer / 調 flow control |
| redelivery 率                                    | 低                     | 偏高 → ack deadline 太短 / 下游失敗                       |
| DLT 深度                                         | 低且有處理流程         | 成長 → 上游系統性失敗                                     |
| consumer 記憶體 / 未 ack 量                      | 在 flow control 限制內 | 暴增 → flow control 沒設好                                |
| 訊息量（計費基礎）                               | 對齊預算               | 暴增 → 評估 throughput 計費、batch / 壓縮                 |

撞牆後的路由判斷：

- **需要長期保留 + 任意 replay**：Pub/Sub 有 retention（可設、seek 到時間點）但事件流長期 replay + 生態走 [Kafka](/backend/03-message-queue/vendors/kafka/)。
- **嚴格全域順序 + 高吞吐**：Pub/Sub ordering 是 per-key 序列化，全域順序高吞吐走 Kafka partition 設計。
- **不在 GCP 生態**：Pub/Sub 綁 GCP，跨雲走 [Kafka](/backend/03-message-queue/vendors/kafka/) / [NATS](/backend/03-message-queue/vendors/nats/) 或對應雲的 managed（[SQS](/backend/03-message-queue/vendors/aws-sqs/)）。
- **複雜 routing（topic exchange 式）**：Pub/Sub 是 topic→subscription 扇出，複雜 routing 規則走 [RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/) exchange。

## 整合 / 下一步

push/pull 判讀與 ack 是 Pub/Sub 可靠消費的核心，它跟其他議題交織：

- **跟 [3.4 consumer design](/backend/03-message-queue/consumer-design/)**：push/pull、ack deadline、flow control 是 consumer 設計的具體選項。
- **跟 [6.12 idempotency / replay](/backend/06-reliability/idempotency-replay/)**：at-least-once + 重投要求消費冪等。
- **跟 [SQS visibility timeout](/backend/03-message-queue/vendors/aws-sqs/visibility-polling-lambda-cost/)**：ack deadline 對應 visibility timeout、DLT 對應 redrive，兩個 managed queue 的可靠消費模型高度對位、可對照閱讀。
- **跟 webhook buffer 模式**：Pub/Sub topic 當 load-leveling buffer（Mercari）對應 [SQS Twilio webhook buffer](/backend/03-message-queue/cases/sqs-twilio-webhook-buffer/)——把不可控的外部 webhook 流量先緩衝再按自己節奏消化。

## 相關連結

- 上游 vendor 頁：[Google Cloud Pub/Sub](/backend/03-message-queue/vendors/google-pubsub/)
- 對照 vendor：[AWS SQS visibility timeout](/backend/03-message-queue/vendors/aws-sqs/visibility-polling-lambda-cost/)、[RabbitMQ DLQ](/backend/03-message-queue/vendors/rabbitmq/dlq-retry-escalation/)
- 對應案例：[3.C65 Mercari LINE flow control](/backend/03-message-queue/cases/pubsub-mercari-line-flow-control/)、[3.C64 Mercari item feed DLT](/backend/03-message-queue/cases/pubsub-mercari-item-feed-dlt/)
- 上游概念：[3.4 consumer design](/backend/03-message-queue/consumer-design/)
