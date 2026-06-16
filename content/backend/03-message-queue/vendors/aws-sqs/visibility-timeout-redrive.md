---
title: "AWS SQS visibility timeout：一個旋鈕、兩個相反的失敗模式"
date: 2026-06-16
description: "SQS 的 visibility timeout 是同一個旋鈕控制兩個相反的風險：設太短，訊息還在處理就重新可見、被重複消費；設太長，consumer 掛掉後訊息要等很久才重派、retry 變慢。本文展開 in-flight 訊息與 visibility 的生命週期、redrive policy 到 DLQ、5 個把 visibility timeout 與 in-flight 上限寫成事故的 production 踩坑"
weight: 11
tags: ["backend", "message-queue", "aws-sqs", "visibility-timeout", "dlq", "deep-article"]
---

<!-- TODO(merge): feat/backend_03 worktree 同時在深化 03 vendor overview。本檔是 main 上新增的 deep article、未動 aws-sqs/_index.md。合併後須檢查：(1) 與對方主題重複 (2) aws-sqs/_index.md 是否加 deep-article 指標 (3) vendors/_index.md 覆蓋表合併。 -->

> 本文是 [AWS SQS](/backend/03-message-queue/vendors/aws-sqs/) overview 的 implementation-layer deep article。選型層（SQS vs Kafka / RabbitMQ、standard vs FIFO）見 overview；本文只處理「決定用 SQS 後，visibility timeout 與 redrive 怎麼設」。SQS 是 managed SaaS、無法本機 docker 驗證，本文 config 依 [AWS SQS 官方文件](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html) 與下列 production case、最後檢查日 2026-06-16；引數與計費以官方為準。

## 一個旋鈕、兩個相反的失敗模式

SQS 沒有「ack」這個動作——它用 visibility timeout 模擬。consumer `ReceiveMessage` 取出一則訊息時，這則訊息不會從 queue 刪除，而是變成「不可見」（in-flight）一段時間，這段時間就是 visibility timeout。consumer 處理成功後呼叫 `DeleteMessage` 才真正移除；如果在 visibility timeout 內沒刪除（處理失敗或 crash），訊息重新變可見、被重新派發。

這個設計把「重試」跟「重複」綁在同一個旋鈕上，而且方向相反。[Capital One 的 SQS + Lambda 實務](/backend/03-message-queue/cases/sqs-capital-one-visibility-timeout/)講得很清楚：visibility timeout 應該設成「**比最大處理時間略高**」——因為：

- 設**太短**：訊息還在處理中就到期、重新變可見、被另一個 consumer 取走重複處理。同一筆業務跑兩次。
- 設**太長**：consumer 真的掛了之後，訊息要等滿這個（過長的）timeout 才會重新可見，retry 被拖慢、恢復遲緩。

沒有「正確的萬用值」——它取決於處理時間分布。本文展開 visibility 與 in-flight 的生命週期、redrive 到 DLQ 的機制、以及這個旋鈕怎麼被設錯成事故。

## 核心概念：in-flight 與 visibility 的生命週期

SQS 的可靠消費圍繞「訊息的可見性狀態」運轉。

**ReceiveMessage 讓訊息進 in-flight**。一則被取出的訊息進入 in-flight 狀態、對其他 consumer 不可見、計時 visibility timeout。SQS 對單一 queue 的 in-flight 訊息數有上限（standard queue 約 120,000），達上限後 ReceiveMessage 收不到新訊息——這是消費停滯的一個隱藏原因。

**DeleteMessage 才是真正的「ack」**。處理成功必須明確 `DeleteMessage`（用 receipt handle）。沒刪除的訊息在 visibility timeout 到期後重新可見。這是 at-least-once 的根源——crash 或漏刪都會導致重派。

**ChangeMessageVisibility 動態延長**。處理中發現需要更久，可以用 `ChangeMessageVisibility` 延長這則訊息的 timeout（heartbeat 模式），不必一開始就把 queue 的 visibility timeout 設超長。長任務的正解是這個，不是把全 queue timeout 拉到很長。

**redrive policy 把重派上限導到 DLQ**。queue 設 `RedrivePolicy`（`maxReceiveCount` + `deadLetterTargetArn`）後，一則訊息被 receive 超過 maxReceiveCount 次（即重派太多次、一直沒被刪除）就自動移到 DLQ。這是 SQS 原生的毒訊息出口——不像 [Redis Streams 要自建 DLQ](/backend/03-message-queue/vendors/redis-streams/consumer-group-pel-recovery/)。

**standard 是 at-least-once、FIFO 是 exactly-once-ish**。standard queue 盡力一次、可能重複、不保證順序；FIFO queue（`.fifo` 結尾）用 message group id 保證組內順序 + 去重（5 分鐘 dedup window）。需要嚴格順序 / 不重複走 FIFO，代價是吞吐上限較低。

## 配置：visibility timeout + redrive（依官方文件）

SQS 是 managed、以下 AWS CLI 依官方文件（未本機 docker 驗證、引數以官方為準）：

```bash
# 1. 建 DLQ
aws sqs create-queue --queue-name app-dlq

# 2. 建主 queue：visibility timeout 略高於最大處理時間 + redrive 到 DLQ
#    VisibilityTimeout 單位秒；maxReceiveCount 達標後移到 DLQ
aws sqs create-queue --queue-name app-work --attributes '{
  "VisibilityTimeout": "60",
  "RedrivePolicy": "{\"deadLetterTargetArn\":\"<dlq-arn>\",\"maxReceiveCount\":\"5\"}"
}'

# 3. consumer 流程（pseudo）：receive → 處理 → delete；長任務中途延長 visibility
#    aws sqs receive-message --queue-url <url> --wait-time-seconds 20   # long polling
#    處理中： aws sqs change-message-visibility --visibility-timeout 120 ...
#    成功後： aws sqs delete-message --receipt-handle <handle>
```

判讀：

- `VisibilityTimeout` 設成略高於處理時間的 p99（Capital One 原則），不是憑感覺
- 長任務用 `change-message-visibility` heartbeat 延長，不要把全 queue timeout 拉超長
- `--wait-time-seconds 20` 開 long polling（減少空輪詢與成本）
- `maxReceiveCount` 給毒訊息一個出口（DLQ），避免無限重派

## Production 故障演練

### Case 1：visibility timeout 太短、訊息被重複處理

**徵兆**：同一筆業務操作偶發執行兩次（重複發信、重複扣款），尤其在處理較慢時。

**根因**：visibility timeout 設得比實際處理時間短。訊息還在處理中就到期、重新可見、被另一個 consumer 取走，兩個 consumer 同時處理同一則。正是 [Capital One](/backend/03-message-queue/cases/sqs-capital-one-visibility-timeout/) 警告的「太短」風險。

**修法**：

1. visibility timeout 設成略高於處理時間 p99
2. 處理時間有長尾的用 `ChangeMessageVisibility` 在處理中延長，不靠固定值賭
3. 消費端冪等——at-least-once 本來就可能重複，冪等是必備保險（見 [6.12 idempotency](/backend/06-reliability/idempotency-replay/)）
4. 監控重複處理率，偏高代表 timeout 偏短或處理變慢

### Case 2：visibility timeout 太長、consumer 掛掉後 retry 遲緩

**徵兆**：某個 consumer crash 後，它正在處理的訊息很久都沒被重派、那批工作卡住。

**根因**：visibility timeout 設得過長（例如為了避免重複而設成 30 分鐘）。consumer crash 後，訊息要等滿這個 timeout 才重新可見，retry 被拖慢。這是「太長」的代價。

**修法**：

1. 不要為了避開重複而把 timeout 設超長——那只是把問題換成恢復遲緩
2. 用「略高於處理時間 + ChangeMessageVisibility 延長 + 冪等」的組合，而非單純拉長 timeout
3. 長任務的正解是 heartbeat 延長，不是一開始就設大
4. 評估恢復時間需求：crash 後能容忍多久才重派，反推 timeout 上界

### Case 3：長任務超過 timeout、處理完卻被重派

**徵兆**：一個長任務正常處理完、delete 了，但同一則訊息又被另一個 consumer 處理一次。

**根因**：任務處理時間超過 visibility timeout，訊息在處理途中就重新可見被別人取走；第一個 consumer 處理完 delete 時，receipt handle 可能已過期或第二個已在跑。

**修法**：

1. 處理中定期 `ChangeMessageVisibility` 延長（heartbeat），確保處理期間訊息一直不可見
2. 把超長任務拆小（單則訊息對應的工作量壓在可控時間內）
3. 真正的長時間工作流不該用 SQS 單則訊息扛，考慮 Step Functions / workflow engine
4. 冪等仍是底線——延長失敗時的最後防線

### Case 4：in-flight 上限打滿、ReceiveMessage 收不到新訊息

**徵兆**：queue 裡明明有大量訊息，但 consumer ReceiveMessage 一直拿到空、消費停滯。

**根因**：standard queue 的 in-flight 訊息數達到上限（約 120,000）。大量訊息被取出但遲遲沒 delete（處理慢、卡住），in-flight 堆滿，SQS 不再派發新訊息。

**修法**：

1. 加快處理 / 增加 consumer，讓 in-flight 訊息及時被 delete 釋放
2. 處理卡住的訊息走 redrive 到 DLQ，不要無限佔著 in-flight 額度
3. 監控 `ApproximateNumberOfMessagesNotVisible`（in-flight 數），接近上限要告警
4. 超大規模拆多 queue 分攤 in-flight 額度

### Case 5：redrive 沒設、毒訊息無限重派

**徵兆**：某則訊息一直處理失敗、一直重新可見、一直被重試，永遠不離開 queue。

**根因**：queue 沒設 `RedrivePolicy`。處理失敗的訊息在 visibility timeout 後一再重派，沒有上限、沒有出口，毒訊息卡在 queue 裡反覆消耗 consumer。

**修法**：

1. 一律設 `RedrivePolicy`（maxReceiveCount + DLQ），給毒訊息出口
2. maxReceiveCount 設合理值（例如 5），平衡「給暫時性失敗重試機會」與「毒訊息及早隔離」
3. DLQ 要有告警 + 處理流程，不是設了就忘
4. 對照 [RabbitMQ 的 DLX](/backend/03-message-queue/vendors/rabbitmq/dlq-retry-escalation/)：SQS redrive 是原生的、比 Redis Streams 自建 DLQ 省事

## Capacity / cost 邊界

SQS 的容量判讀（managed、無 broker 運維、但有計費與額度維度）：

| 訊號                                    | 健康區間               | 警戒與動作                                     |
| --------------------------------------- | ---------------------- | ---------------------------------------------- |
| `ApproximateNumberOfMessagesNotVisible` | 遠低於 ~120k in-flight | 接近上限 → 處理太慢、加 consumer / redrive     |
| 重複處理率                              | 低                     | 偏高 → visibility timeout 太短                 |
| DLQ 深度                                | 低且有處理流程         | 成長 → 上游系統性失敗、毒訊息累積              |
| 訊息 age（最舊未處理）                  | 在 SLA 內              | 偏高 → consumer 跟不上 / visibility 太長拖慢   |
| request 量（計費基礎）                  | 對齊預算               | 暴增 → 空輪詢多、開 long polling 降 request 數 |

撞牆後的路由判斷：

- **超大規模 + 成本敏感**：[Rapid7 用 SQS 撐百億訊息/日](/backend/03-message-queue/cases/sqs-rapid7-scale-billion-messages/)證明 SQS scale 沒問題，但 request-based 計費在這規模要認真算（long polling、batch 收發降 request 數）。對照 [0.6 成本取捨](/backend/00-service-selection/cost-risk-tradeoffs/)。
- **需要嚴格順序 / 不重複**：standard 是 at-least-once + 盡力順序，走 SQS FIFO（message group + dedup）或 [Kafka](/backend/03-message-queue/vendors/kafka/)（partition 內順序）。
- **需要長期保留 + replay**：SQS 訊息消費即刪、保留上限 14 天，事件流 replay 走 Kafka（log-based、長期保留）。
- **複雜 routing / fanout**：SQS 是點對點 queue，fanout 配 SNS（SNS→多 SQS）或走 [Pub/Sub](/backend/03-message-queue/vendors/google-pubsub/) / RabbitMQ exchange。

## 整合 / 下一步

visibility timeout 是 SQS 可靠消費的核心旋鈕，它跟其他議題交織：

- **跟 SQS + Lambda event source**：[Capital One](/backend/03-message-queue/cases/sqs-capital-one-visibility-timeout/) 指出 Lambda event source 的 scaling 非線性（初 5 connection、擴 60/min、上限 1000 並行 batch）、visibility timeout 要對齊 Lambda 函數 timeout。
- **跟 [3.4 consumer design](/backend/03-message-queue/consumer-design/)**：visibility timeout + delete + heartbeat 是 SQS 的 ack 模型，對應 consumer 設計的 ack 策略。
- **跟 [6.12 idempotency / replay](/backend/06-reliability/idempotency-replay/)**：standard queue at-least-once 要求消費冪等，這是 visibility timeout 雙邊風險的底線防護。
- **跟 [RabbitMQ DLQ](/backend/03-message-queue/vendors/rabbitmq/dlq-retry-escalation/) / [Redis Streams PEL](/backend/03-message-queue/vendors/redis-streams/consumer-group-pel-recovery/)**：三者的「重試上限後往哪去」對照——SQS redrive 原生、RabbitMQ DLX 原生、Redis Streams 自建。

## 相關連結

- 上游 vendor 頁：[AWS SQS](/backend/03-message-queue/vendors/aws-sqs/)
- 對照 vendor：[RabbitMQ DLQ 與分層 retry](/backend/03-message-queue/vendors/rabbitmq/dlq-retry-escalation/)、[Redis Streams consumer group + PEL](/backend/03-message-queue/vendors/redis-streams/consumer-group-pel-recovery/)
- 對應案例：[3.C50 Capital One visibility timeout](/backend/03-message-queue/cases/sqs-capital-one-visibility-timeout/)、[3.C59 Rapid7 百億訊息規模](/backend/03-message-queue/cases/sqs-rapid7-scale-billion-messages/)
- 上游概念：[3.4 consumer design](/backend/03-message-queue/consumer-design/)、[0.6 成本取捨](/backend/00-service-selection/cost-risk-tradeoffs/)
