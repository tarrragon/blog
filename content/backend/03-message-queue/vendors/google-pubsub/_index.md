---
title: "Google Cloud Pub/Sub"
date: 2026-05-01
description: "GCP managed pub/sub、global routing、push/pull"
weight: 6
tags: ["backend", "message-queue", "vendor"]
---

Google Cloud Pub/Sub 是 GCP managed pub/sub 服務、承擔三個責任：全球 topic 路由（無 region 概念）、彈性 delivery（push 跟 pull 並存）、GCP 生態整合（BigQuery / Dataflow / Cloud Run）。設計取捨偏向「topic 是 first-class、subscription 各自進度、ack deadline 控制重試」、跟 Kafka 的 partition / consumer group 思路不同。

對「GCP 生態事件分發、跨 region 全球路由、push HTTP endpoint 接收事件、Dataflow streaming」這條路徑、Pub/Sub 是首選。本頁先給最短路徑、再展開日常 topic / subscription 操作與 ack deadline 設計、最後進階治理（ordering、DLT、push endpoint、IAM）跟排錯。

## 本章目標

讀完本章後、你應該能：

1. 用 gcloud CLI 建 topic / subscription、publish / pull 訊息
2. 區分 push vs pull subscription、選擇對應的 delivery 模型
3. 設計 ack deadline 與 ackExtension、處理長任務
4. 配置 dead-letter topic 與 retry policy
5. 評估 ordering key、Pub/Sub Lite、BigQuery subscription 等延伸場景

## 最短路徑：5 分鐘把 Pub/Sub 跑起來

```bash
# 1. 建 topic
# TODO: gcloud pubsub topics create demo-topic

# 2. 建 subscription（pull 模式）
# TODO: gcloud pubsub subscriptions create demo-sub --topic=demo-topic

# 3. publish + pull 驗證
# TODO: gcloud pubsub topics publish demo-topic --message="hello"
# TODO: gcloud pubsub subscriptions pull demo-sub --auto-ack
```

最短路徑驗證「topic / subscription 建得起來、能發能收」。實際應用見[日常操作](#日常操作與決策形狀)。

## 日常操作與決策形狀

### gcloud CLI 與 client library

子議題：

- gcloud CLI 指令對照表（topics / subscriptions / publish / pull / ack）
- Client library 配置：credentials / flow control / async vs sync
- Batch publish（提高吞吐、增加延遲的取捨）
- 對應指令範例：`gcloud pubsub subscriptions describe <sub>`

### Topic / Subscription 設計

[Topic](/backend/knowledge-cards/topic/) 是 first-class entity、跟 Kafka 不同的是 subscription 才是 consumer 抽象：

- 1 topic ↔ N subscription（fan-out 內建）
- Subscription 各自進度（無 consumer group 概念）
- Subscription expiration policy（閒置 N 天自動刪）

### Push vs Pull subscription

子議題：

- Push：Pub/Sub 主動 POST 到 HTTP endpoint、適合無狀態 worker / Cloud Run
- Pull：consumer 主動拉取、適合長 worker / 需要 flow control
- Push endpoint 要求（HTTPS、認證）
- 兩者的可靠性 / latency / cost 對照

### Ack deadline 與 ack extension

子議題：

- Ack deadline：subscription 等待 ack 的時間（預設 10 秒、上限 600 秒）
- Modify ack deadline（長任務動態延長）
- Client library 的自動 ack extension
- 跟 SQS visibility timeout 的對照（語意類似、機制不同）

## 進階主題（按需閱讀）

### Ordering key

子議題：

- 啟用 ordering 的限制（subscription 設定 enableMessageOrdering）
- Ordering 在 push 跟 pull 的差異
- 跟 Kafka partition + key 的對照
- 性能影響（throughput 受限）

### Dead-letter topic

子議題：

- 設定 max delivery attempt、超過送到 DLT
- DLT 是另一個 topic、可以再訂閱重處理
- 跟 SQS DLQ 的差異（DLT 是 topic、不是 queue）

### Pub/Sub Lite

子議題：

- Pub/Sub Lite vs Pub/Sub（partition-based、zonal、cost 低）
- 何時用 Lite（高吞吐、確定 region）
- 何時用 standard（global routing 內建）

### BigQuery subscription / Cloud Storage subscription

子議題：

- BigQuery subscription：訊息直接寫入 BQ table（無需 Dataflow）
- Cloud Storage subscription：訊息批次寫入 GCS object
- 適合 streaming analytics / data lake 場景

### Schema enforcement

子議題：

- Topic 綁定 schema（Avro / Protobuf）
- Schema evolution
- 跟 Kafka Schema Registry 的對照

### IAM / Service Account

子議題：

- Pub/Sub IAM role（publisher / subscriber / viewer）
- Service Account 認證（push endpoint 用）
- VPC Service Controls

## 排錯快速判讀

### Subscriber backlog（unacked messages 累積）

操作原則：先看是 push 還是 pull、再定位 endpoint 失敗 vs flow control 限制。

```bash
# TODO: gcloud pubsub subscriptions describe <sub>
```

判讀：CloudWatch metric 的 `num_undelivered_messages` 與 `oldest_unacked_message_age`。

### Push endpoint 500（retry storm）

操作原則：push endpoint 持續 500、Pub/Sub 會 backoff retry、看 retry policy 設定。判讀：endpoint 健康 vs 訊息毒性。

### Ordering key 限制誤用

操作原則：啟用 ordering 後 throughput 變低、單一 ordering key 是順序的。判讀：throughput 是否被 ordering 限制、可拆 ordering key。

### IAM 權限錯

操作原則：publish / pull / ack 各自需要不同 IAM role。判讀：用 Cloud Logging 看 deny 原因。

### Subscription expired

操作原則：閒置太久 subscription 被 GC。判讀：subscription expiration policy 設定 + 監控 lastReceiveTime。

## 何時改走其他服務

| 需求形狀                            | 改走                                                                                                |
| ----------------------------------- | --------------------------------------------------------------------------------------------------- |
| 需要 streaming + replay long window | [Kafka](/backend/03-message-queue/vendors/kafka/) / Confluent Cloud                                 |
| 需要 partition + consumer group     | [Kafka](/backend/03-message-queue/vendors/kafka/) / Pub/Sub Lite                                    |
| 需要複雜 routing                    | [RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/) on GKE                                      |
| 跨雲 / 跨平台                       | [Kafka](/backend/03-message-queue/vendors/kafka/) / [NATS](/backend/03-message-queue/vendors/nats/) |
| AWS 生態                            | [AWS SQS](/backend/03-message-queue/vendors/aws-sqs/) / SNS                                         |
| Workflow + durable execution        | Google Workflows / Temporal                                                                         |

## 不在本頁內的主題

- Dataflow / BigQuery 完整功能（另開 streaming analytics 章節）
- Cloud Run / Functions 整合細節
- 各語言 client 完整 API

## 案例回寫

### Pub/Sub 專屬案例（C60-C69）

| 案例                                                                                                    | 主討論議題                           |
| ------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| [3.C60 Spotify Event Delivery](/backend/03-message-queue/cases/pubsub-spotify-event-delivery-platform/) | 從 Kafka 遷入 / 自建 dedup           |
| [3.C61 Spotify autoscaling](/backend/03-message-queue/cases/pubsub-spotify-autoscaling-consumers/)      | Backlog ≠ healthy / autoscale 反效果 |
| [3.C62 Spotify GCS export](/backend/03-message-queue/cases/pubsub-spotify-cloud-storage-export/)        | Ack = end-to-end commit              |
| [3.C63 Mercari Actionable History](/backend/03-message-queue/cases/pubsub-mercari-actionable-history/)  | Ack deadline 是 batch-level（陷阱）  |
| [3.C64 Mercari Item Feed DLT](/backend/03-message-queue/cases/pubsub-mercari-item-feed-dlt/)            | DLT 防 poison message 阻塞           |
| [3.C65 Mercari LINE flow control](/backend/03-message-queue/cases/pubsub-mercari-line-flow-control/)    | Pull subscription 對齊外部 RPS       |
| [3.C66 Mercari B2C gRPC pusher](/backend/03-message-queue/cases/pubsub-mercari-b2c-grpc-pusher/)        | 自建 push / 長 job + 動態 RPS        |
| [3.C67 Niantic Pokémon GO](/backend/03-message-queue/cases/pubsub-niantic-pokemon-go-telemetry/)        | Elastic buffer / BQ streaming        |
| [3.C68 Wix clickstream](/backend/03-message-queue/cases/pubsub-wix-clickstream-dashboard/)              | Pub/Sub + Dataflow + BQ 教科書組合   |
| [3.C69 Twitter Ad Engagement](/backend/03-message-queue/cases/pubsub-twitter-ad-engagement/)            | 多 topic 切分取代 partition          |

### 跨 vendor 對照

| 案例                                                                                               | 對 Pub/Sub 的對應                                       |
| -------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| [3.C8 Cloudflare Queues](/backend/03-message-queue/cases/cloudflare-queues-global-delivery-model/) | 全球交付對照：Pub/Sub global routing 內建               |
| [3.C10 規模對照](/backend/03-message-queue/cases/contrast-queue-model-by-scale/)                   | 中小型直接用 / 大型考慮 Pub/Sub Lite / 超大跨雲走 Kafka |
| [3.C20 Spotify 遷出 Kafka](/backend/03-message-queue/cases/kafka-spotify-event-delivery-exodus/)   | Pub/Sub 遷入的源頭（為何遷出 Kafka）                    |

**IAM + Service Account 缺直接 customer engineering case**：customer engineering blog 著墨少、建議撰寫該段時依 GCP 官方 IAM 文件 + 通用安全原則。

## 下一步路由

- 上游概念：[0.3 非同步選型](/backend/00-service-selection/async-delivery-selection/)、[3.1 broker basics](/backend/03-message-queue/broker-basics/)
- 平行 vendor：[AWS SQS](/backend/03-message-queue/vendors/aws-sqs/)、[Kafka](/backend/03-message-queue/vendors/kafka/)
- 下游能力：[3.4 consumer 設計](/backend/03-message-queue/consumer-design/)、[6.12 idempotency / replay](/backend/06-reliability/idempotency-replay/)
