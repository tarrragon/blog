---
title: "AWS SQS"
date: 2026-05-01
description: "AWS managed queue、簡單可靠、無 ordering（standard）"
weight: 5
tags: ["backend", "message-queue", "vendor"]
---

AWS SQS 是 AWS managed queue 服務、承擔三個責任：訊息排隊與重試（visibility timeout + DLQ）、解耦 producer / consumer（無 broker 運維）、AWS 生態原生整合（Lambda / EventBridge / Step Functions）。設計取捨偏向「極簡 API + managed 運維、用 visibility timeout 取代 broker ACK、無原生 ordering（standard queue）」。

對「AWS 生態 task queue、不想自管 broker、配合 Lambda 事件處理」這條路徑、SQS 是首選。本頁先給最短路徑、再展開日常 SendMessage / ReceiveMessage 操作與 visibility timeout 設計、最後進階治理（FIFO、DLQ、IAM、VPC endpoint）跟排錯。

## 本章目標

讀完本章後、你應該能：

1. 用 AWS CLI 建 standard / FIFO queue、發送與接收訊息
2. 設計 visibility timeout 對齊 consumer 處理時間
3. 配置 DLQ（dead-letter queue）與 maxReceiveCount
4. 區分 long polling vs short polling、配合 Lambda event source mapping
5. 評估 IAM policy、VPC endpoint、cross-account 訪問等治理場景

## 最短路徑：5 分鐘把 SQS 跑起來

```bash
# 1. 建 queue（回傳 QueueUrl、後續操作都用它）
aws sqs create-queue --queue-name demo-queue

# 2. 發送訊息
aws sqs send-message --queue-url <url> --message-body "hello"

# 3. 接收訊息（long polling、最多等 20 秒）
aws sqs receive-message --queue-url <url> --wait-time-seconds 20
```

最短路徑驗證「queue 建得起來、能發能收」。實際應用配合 SDK / Lambda、見[日常操作](#日常操作與決策形狀)。指令對真實 AWS 需設定 credentials 與 region；本機要先驗證可加 `--endpoint-url` 指向 SQS-相容的 local 模擬器跑同一組指令。

## 日常操作與決策形狀

### AWS CLI 與 SDK

子議題：

- AWS CLI 指令對照表（create-queue / send-message / receive-message / delete-message / set-queue-attributes）
- SDK 配置：region / credentials / retry policy / timeout
- Batch operation（SendMessageBatch、DeleteMessageBatch、最多 10 條）
- 對應指令範例：`aws sqs get-queue-attributes --queue-url <url>`

### Standard vs FIFO queue

子議題：

- Standard：高吞吐、at-least-once、無 ordering、適合多數 task queue
- FIFO：exactly-once-ish（去重 5 分鐘窗口）、ordering（per MessageGroupId）、吞吐受限（3000 msg/sec with batching）
- 選擇判讀（ordering 需求 vs 吞吐）

### Visibility timeout 與 in-flight

[Visibility timeout](/backend/knowledge-cards/in-flight/) 是 SQS 的 delivery 控制機制、取代 broker ACK：

- 訊息被接收後變 in-flight、其他 consumer 看不到
- Consumer 處理完呼叫 DeleteMessage、否則 timeout 後回到 queue
- ChangeMessageVisibility 動態延長（長任務）
- 預設 30 秒、上限 12 小時

### DLQ 設計（dead-letter queue）

子議題：

- maxReceiveCount：訊息被接收 N 次後送 DLQ
- DLQ 監控與 alarm（CloudWatch metric）
- Redrive policy（從 DLQ 重新放回 main queue）
- 對應 [poison message](/backend/knowledge-cards/poison-message/) 處理思路

## 進階主題（按需閱讀）

visibility timeout、polling、Lambda event source 與 cost 已展開為 deep article：[visibility timeout / long polling / Lambda + cost](visibility-polling-lambda-cost/)。下列子議題段保留選題判讀入口。

### Long polling vs Short polling

子議題：

- Short polling（預設）：立即回應、可能空回（高 cost）
- Long polling（WaitTimeSeconds 1-20）：等到有訊息或超時
- 對 cost 與 latency 的取捨

### SQS + Lambda event source mapping

子議題：

- Lambda 自動 poll SQS（managed event source）
- Batch size / batch window 配置
- Partial batch failure（ReportBatchItemFailures）
- 對應 [3.C8 Cloudflare Queues](/backend/03-message-queue/cases/cloudflare-queues-global-delivery-model/) 的全球交付對照

### IAM / Cross-account 訪問

子議題：

- Queue policy（resource-based）vs IAM policy（identity-based）
- Cross-account producer / consumer 設定
- Encryption（SSE-SQS / SSE-KMS）

### VPC endpoint（私網訪問）

子議題：

- Interface endpoint（PrivateLink）
- 適合不想經 public internet 的場景
- 跟 NAT Gateway 的 cost 對照

### CloudWatch metric 與 alarm

子議題：

- ApproximateNumberOfMessagesVisible（queue depth）
- ApproximateAgeOfOldestMessage（lag 訊號）
- NumberOfMessagesSent / Received / Deleted
- Alarm 設計（depth 暴增、age 超 SLO）

### Cost 模型

子議題：

- Request cost（每百萬 request）
- Data transfer cost（跨 region 才有）
- FIFO 比 standard 貴的判讀
- 對應 [0.6 成本取捨](/backend/00-service-selection/cost-risk-tradeoffs/)

## 排錯快速判讀

### Message 反覆 redelivery（看到同訊息多次）

操作原則：visibility timeout 設定 < consumer 處理時間、訊息回 queue 又被另一 consumer 領走。

```bash
aws sqs get-queue-attributes --queue-url <url> --attribute-names VisibilityTimeout
# 新建 queue 預設 VisibilityTimeout 為 30 秒、處理時間長於此值就會看到 redelivery
```

調整：延長 VisibilityTimeout 或 consumer 主動 ChangeMessageVisibility。

### DLQ 累積

操作原則：先看 DLQ 訊息內容、判斷 poison message vs 下游卡。

判讀路徑：訊息格式錯（永遠失敗）→ 下游服務 down（暫時失敗、可 redrive）→ consumer bug。

### Throttling（account quota）

操作原則：超過 account-level SendMessage / ReceiveMessage TPS、看 CloudWatch ThrottledRequests。處理：requeue exchange、quota 申請。

### IAM 權限錯

操作原則：access denied 大多是 queue policy 跟 IAM policy 互動。判讀：用 IAM Policy Simulator 或 CloudTrail 看 deny 原因。

### Lambda event source 失敗

操作原則：Lambda 失敗會自動 retry、超過 retry 進 DLQ。看 Lambda 的 DLQ 跟 SQS 的 DLQ 分工。

## 何時改走其他服務

| 需求形狀                     | 改走                                                                                                |
| ---------------------------- | --------------------------------------------------------------------------------------------------- |
| 需要 streaming / replay      | AWS Kinesis / [Kafka](/backend/03-message-queue/vendors/kafka/) / MSK                               |
| 需要 pub/sub fan-out         | AWS SNS（搭配 SQS 做 fan-out）/ EventBridge                                                         |
| 需要複雜 routing             | [RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/) on EC2                                      |
| 跨雲 / 跨平台                | [Kafka](/backend/03-message-queue/vendors/kafka/) / [NATS](/backend/03-message-queue/vendors/nats/) |
| 嚴格低延遲（< 100ms）        | [NATS](/backend/03-message-queue/vendors/nats/) / Redis                                             |
| Workflow + durable execution | AWS Step Functions / Temporal                                                                       |

## 不在本頁內的主題

- SNS / EventBridge 細節（另開 cloud event routing 章節）
- Step Functions / Lambda 完整功能
- AWS SDK 各語言完整 API

## 案例回寫

### SQS 專屬案例（C48-C59）

| 案例                                                                                            | 主討論議題                               |
| ----------------------------------------------------------------------------------------------- | ---------------------------------------- |
| [3.C48 Airbnb Dynein](/backend/03-message-queue/cases/sqs-airbnb-dynein-delayed-jobs/)          | 分散式延遲任務 / at-least-once + DLQ     |
| [3.C49 Airbnb Inspekt](/backend/03-message-queue/cases/sqs-airbnb-inspekt-data-protection/)     | Visibility timeout 當隱式 retry          |
| [3.C50 Capital One](/backend/03-message-queue/cases/sqs-capital-one-visibility-timeout/)        | Visibility timeout / Lambda event source |
| [3.C51 Atlassian JiRT](/backend/03-message-queue/cases/sqs-atlassian-jirt-kinesis-sqs/)         | Kinesis + per-consumer SQS               |
| [3.C52 Nielsen Spark on EKS](/backend/03-message-queue/cases/sqs-nielsen-spark-eks-dual-queue/) | 雙 SQS / queue depth autoscale           |
| [3.C53 FINRA Large File](/backend/03-message-queue/cases/sqs-finra-large-file-service/)         | S3 → SQS 合規 / IAM 多層稽核             |
| [3.C54 Twitch EventSub](/backend/03-message-queue/cases/sqs-twitch-eventsub-fanout/)            | SNS-SQS fan-out + Dispatcher             |
| [3.C55 SmugMug search](/backend/03-message-queue/cases/sqs-smugmug-search-pipeline/)            | Workload generator / 平行 scan + replay  |
| [3.C56 PostNL EBE](/backend/03-message-queue/cases/sqs-postnl-mission-critical-ebe/)            | 完整 DLQ + redrive + 隔離 stack          |
| [3.C57 Lob sqs-consumer](/backend/03-message-queue/cases/sqs-lob-sqs-consumer-library/)         | Client library / SDK v3 / FIFO bug       |
| [3.C58 Twilio webhook](/backend/03-message-queue/cases/sqs-twilio-webhook-buffer/)              | Webhook → SQS buffer / FIFO 300 TPS      |
| [3.C59 Rapid7 scale](/backend/03-message-queue/cases/sqs-rapid7-scale-billion-messages/)        | 100 億 msg/day 規模參考點                |

### 跨 vendor 對照

| 案例                                                                                               | 對 SQS 的對應                                          |
| -------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| [3.C2 VMware → MSK](/backend/03-message-queue/cases/vmware-kafka-to-msk/)                          | 反面對照：何時 managed queue 不夠用、要升 streaming    |
| [3.C8 Cloudflare Queues](/backend/03-message-queue/cases/cloudflare-queues-global-delivery-model/) | 全球交付對照（SQS 是 region-scoped）                   |
| [3.C10 規模對照](/backend/03-message-queue/cases/contrast-queue-model-by-scale/)                   | 小型直接用 SQS / 中型補 idempotency / 大型補 streaming |

## 下一步路由

- 上游概念：[0.3 非同步選型](/backend/00-service-selection/async-delivery-selection/)、[3.1 broker basics](/backend/03-message-queue/broker-basics/)
- 平行 vendor：[Google Pub/Sub](/backend/03-message-queue/vendors/google-pubsub/)、[RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/)
- 下游能力：[3.2 durable queue](/backend/03-message-queue/durable-queue/)、[3.4 consumer 設計](/backend/03-message-queue/consumer-design/)
