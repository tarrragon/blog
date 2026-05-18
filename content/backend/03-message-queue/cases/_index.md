---
title: "模組三案例正文"
date: 2026-05-07
description: "訊息佇列與事件傳遞的轉換案例入口、含通用案例與 6 個 vendor 的真實 production case 庫。"
weight: 80
tags: ["backend", "message-queue", "case-study"]
---

這個資料夾的核心責任是把 broker、queue 與語義治理的轉換壓力落到可執行判讀、並提供各 vendor 的真實 production case 庫支撐撰寫。案例不是事後舉例、是寫作 finding 的 source — 章節該討論的議題從 case 反推、不是先寫章節再找案例填。

## 通用案例（跨 vendor / 反例 / 規模對照）

| 章節                                                                              | 主題                        | 核心責任                                          |
| --------------------------------------------------------------------------------- | --------------------------- | ------------------------------------------------- |
| [3.C1](/backend/03-message-queue/cases/meta-foqs-global-migration/)               | Meta FOQS 全域遷移          | 區域佇列如何升級到 disaster-ready 架構            |
| [3.C2](/backend/03-message-queue/cases/vmware-kafka-to-msk/)                      | VMware Kafka → MSK          | 自管 broker 轉 managed streaming 的治理重點       |
| [3.C3](/backend/03-message-queue/cases/linkedin-topicgc-kafka-governance/)        | LinkedIn TopicGC            | topic 生命週期治理如何影響叢集可靠性              |
| [3.C4](/backend/03-message-queue/cases/linkedin-kafka-tiered-clusters/)           | LinkedIn Kafka 分層         | 把單叢集使用模式轉成分層叢集治理                  |
| [3.C5](/backend/03-message-queue/cases/slack-job-queue-kafka-redis/)              | Slack Job Queue             | 背景工作通道轉成 Kafka + Redis 組合               |
| [3.C6](/backend/03-message-queue/cases/uber-kafka-infrastructure-evolution/)      | Uber Kafka 基礎設施         | 把事件平台演進成多租戶共享能力                    |
| [3.C7](/backend/03-message-queue/cases/linkedin-kafka-self-healing-automation/)   | LinkedIn Self-healing Kafka | 把手動維運轉成自動修復治理                        |
| [3.C8](/backend/03-message-queue/cases/cloudflare-queues-global-delivery-model/)  | Cloudflare Queues           | 把全球佇列傳遞模型轉成可治理交付路徑              |
| [3.C9](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/) | 反例：語義切換失敗          | at-least-once / exactly-once 語義誤配造成資料錯亂 |
| [3.C10](/backend/03-message-queue/cases/contrast-queue-model-by-scale/)           | 對照：規模差異下佇列模型    | 同一佇列模型在不同規模下有不同治理與失敗邊界      |

## Kafka 案例

| 章節                                                                             | 公司 / 主題                | 對應 Kafka 大綱章節                            |
| -------------------------------------------------------------------------------- | -------------------------- | ---------------------------------------------- |
| [3.C11](/backend/03-message-queue/cases/kafka-pinterest-tiered-storage/)         | Pinterest Tiered Storage   | Tiered storage                                 |
| [3.C12](/backend/03-message-queue/cases/kafka-pinterest-shallow-mirror/)         | Pinterest Shallow Mirror   | Cross-region MirrorMaker                       |
| [3.C13](/backend/03-message-queue/cases/kafka-shopify-debezium-cdc/)             | Shopify Debezium CDC       | Kafka Connect / CDC                            |
| [3.C14](/backend/03-message-queue/cases/kafka-yelp-schematizer/)                 | Yelp Schematizer           | Schema Registry / Schema evolution             |
| [3.C15](/backend/03-message-queue/cases/kafka-airbnb-spark-streaming-rebalance/) | Airbnb Spark Streaming     | Consumer 設計 / partition + consumer group     |
| [3.C16](/backend/03-message-queue/cases/kafka-robinhood-faust-python-streaming/) | Robinhood Faust            | 跨語言 client / stream processing              |
| [3.C17](/backend/03-message-queue/cases/kafka-walmart-mps-rebalance/)            | Walmart MPS                | Rebalance storm / consumer lag / multi-tenant  |
| [3.C18](/backend/03-message-queue/cases/kafka-wix-greyhound-troubleshooting/)    | Wix Greyhound              | Consumer lag / observability / poison message  |
| [3.C19](/backend/03-message-queue/cases/kafka-wix-multi-cluster-migration/)      | Wix Multi-cluster          | Topic 生命週期 / 分層叢集                      |
| [3.C20](/backend/03-message-queue/cases/kafka-spotify-event-delivery-exodus/)    | Spotify 遷出 Kafka（反例） | Replication 失敗模式 / producer 可靠性         |
| [3.C21](/backend/03-message-queue/cases/kafka-goldman-sachs-msk-migration/)      | Goldman Sachs MSK          | Cross-region MirrorMaker / managed broker 遷移 |
| [3.C22](/backend/03-message-queue/cases/kafka-trivago-keda-scale-to-zero/)       | Trivago KEDA               | Consumer lag / autoscaling                     |

## RabbitMQ 案例

| 章節                                                                                   | 公司 / 主題                    | 對應 RabbitMQ 大綱章節                     |
| -------------------------------------------------------------------------------------- | ------------------------------ | ------------------------------------------ |
| [3.C23](/backend/03-message-queue/cases/rabbitmq-bloomberg-multi-tenant-vhost/)        | Bloomberg vhost 多租戶         | 多 vhost + 多租戶 / Erlang clustering      |
| [3.C24](/backend/03-message-queue/cases/rabbitmq-soundcloud-fanout-audio/)             | SoundCloud fan-out 音訊        | Prefetch + consumer 併發 / Streams         |
| [3.C25](/backend/03-message-queue/cases/rabbitmq-indeed-delay-dlq-escalation/)         | Indeed Delay + DLQ             | Dead-letter exchange / retry 策略          |
| [3.C26](/backend/03-message-queue/cases/rabbitmq-gocardless-hutch-service-mesh/)       | GoCardless Hutch service mesh  | Exchange types / 多 vhost（反向）          |
| [3.C27](/backend/03-message-queue/cases/rabbitmq-zalando-aws-master-selection/)        | Zalando AWS master selection   | Erlang clustering / Federation / Operator  |
| [3.C28](/backend/03-message-queue/cases/rabbitmq-wework-consistent-hash-ordering/)     | WeWork consistent hash         | Exchange types / partition-level ordering  |
| [3.C29](/backend/03-message-queue/cases/rabbitmq-wework-bunny-channel-pool/)           | WeWork Bunny channel pool      | Prefetch + consumer 併發（client lib）     |
| [3.C30](/backend/03-message-queue/cases/rabbitmq-runtastic-mirrored-queue-bottleneck/) | Runtastic mirrored queue 瓶頸  | Mirrored queue → Quorum queue 遷移         |
| [3.C31](/backend/03-message-queue/cases/rabbitmq-mozilla-pulse-naming-isolation/)      | Mozilla Pulse naming isolation | 多 vhost + 多租戶（反向：用 ACL + naming） |
| [3.C32](/backend/03-message-queue/cases/rabbitmq-loyaltylion-monitoring-thousands/)    | LoyaltyLion 監控數千 queue     | 監控觀測 / Operator                        |
| [3.C33](/backend/03-message-queue/cases/rabbitmq-wargaming-game-portal-decoupling/)    | Wargaming game portal 解耦     | Federation + Shovel / 多 vhost             |

## NATS 案例

| 章節                                                                        | 公司 / 主題                  | 對應 NATS 大綱章節                             |
| --------------------------------------------------------------------------- | ---------------------------- | ---------------------------------------------- |
| [3.C34](/backend/03-message-queue/cases/nats-netlify-data-plane-fanout/)    | Netlify 全球資料平面 fan-out | Core NATS vs JetStream / subject-based routing |
| [3.C35](/backend/03-message-queue/cases/nats-form3-multi-cloud-payments/)   | Form3 多雲低延遲支付         | Cluster + Supercluster + Leaf node / JetStream |
| [3.C36](/backend/03-message-queue/cases/nats-intelecy-industrial-iot/)      | Intelecy 工業 IoT            | JetStream stream / Subject-based ACL           |
| [3.C37](/backend/03-message-queue/cases/nats-machinemetrics-edge-to-cloud/) | MachineMetrics edge to cloud | Leaf node / KV + Object Store / 多租戶 ACL     |
| [3.C38](/backend/03-message-queue/cases/nats-clarifai-async-task-queue/)    | Clarifai NATS Streaming ML   | JetStream consumer 設計 / Queue groups         |
| [3.C39](/backend/03-message-queue/cases/nats-choria-orchestration-fleet/)   | Choria fleet orchestration   | Request/Reply / Queue groups / Supercluster    |
| [3.C40](/backend/03-message-queue/cases/nats-resgate-realtime-api-gateway/) | Resgate WebSocket-to-NATS    | Request/Reply / Subject ACL / Core NATS        |
| [3.C41](/backend/03-message-queue/cases/nats-iflow-ot-it-integration/)      | i-flow OT/IT 整合            | Cluster + Supercluster + Leaf node             |

## Redis Streams 案例

| 章節                                                                                      | 公司 / 主題                     | 對應 Redis Streams 大綱章節              |
| ----------------------------------------------------------------------------------------- | ------------------------------- | ---------------------------------------- |
| [3.C42](/backend/03-message-queue/cases/redis-streams-bitso-reliable-streams/)            | Bitso Reliable Streams + DLQ    | Consumer group + PEL / XCLAIM / Sentinel |
| [3.C43](/backend/03-message-queue/cases/redis-streams-arcjet-replace-kafka/)              | Arcjet 取代 Kafka 省 6 位數 $   | Retention / Memory 取捨                  |
| [3.C44](/backend/03-message-queue/cases/redis-streams-harness-event-driven-state/)        | Harness CD async state transfer | Consumer group + PEL / XCLAIM / Memory   |
| [3.C45](/backend/03-message-queue/cases/redis-streams-klaxit-rust-log-pipeline/)          | Klaxit Rust + Heroku Logplex    | XADD / XREADGROUP / Consumer group       |
| [3.C46](/backend/03-message-queue/cases/redis-streams-learning-com-event-source-retreat/) | Learning.com 退場（反例）       | Memory + retention / Sentinel 可靠性     |
| [3.C47](/backend/03-message-queue/cases/redis-streams-mateusz-php-microservices/)         | PHP 微服務 + S3 hybrid          | XADD/XREAD / Retention / Memory          |

## AWS SQS 案例

| 章節                                                                         | 公司 / 主題                       | 對應 SQS 大綱章節                       |
| ---------------------------------------------------------------------------- | --------------------------------- | --------------------------------------- |
| [3.C48](/backend/03-message-queue/cases/sqs-airbnb-dynein-delayed-jobs/)     | Airbnb Dynein 延遲任務            | Standard vs FIFO / DLQ 設計             |
| [3.C49](/backend/03-message-queue/cases/sqs-airbnb-inspekt-data-protection/) | Airbnb Inspekt visibility timeout | Visibility timeout + in-flight          |
| [3.C50](/backend/03-message-queue/cases/sqs-capital-one-visibility-timeout/) | Capital One visibility timeout    | Visibility timeout / SQS + Lambda       |
| [3.C51](/backend/03-message-queue/cases/sqs-atlassian-jirt-kinesis-sqs/)     | Atlassian JiRT Kinesis + SQS      | Standard vs FIFO / fan-out subscription |
| [3.C52](/backend/03-message-queue/cases/sqs-nielsen-spark-eks-dual-queue/)   | Nielsen Spark on EKS 雙 SQS       | CloudWatch metric / autoscaling         |
| [3.C53](/backend/03-message-queue/cases/sqs-finra-large-file-service/)       | FINRA S3 → SQS 合規               | SQS + Lambda / IAM 多層                 |
| [3.C54](/backend/03-message-queue/cases/sqs-twitch-eventsub-fanout/)         | Twitch EventSub SNS+SQS           | Standard queue / SNS-SQS fan-out        |
| [3.C55](/backend/03-message-queue/cases/sqs-smugmug-search-pipeline/)        | SmugMug 搜尋管線 backfill         | Standard queue / Long polling / Lambda  |
| [3.C56](/backend/03-message-queue/cases/sqs-postnl-mission-critical-ebe/)    | PostNL EBE 完整 DLQ + redrive     | DLQ 設計 / CloudWatch alarm / Cost      |
| [3.C57](/backend/03-message-queue/cases/sqs-lob-sqs-consumer-library/)       | Lob @lob/sqs-consumer             | Standard vs FIFO / Client library       |
| [3.C58](/backend/03-message-queue/cases/sqs-twilio-webhook-buffer/)          | Twilio SQS 緩衝 webhook           | Long polling / Standard vs FIFO         |
| [3.C59](/backend/03-message-queue/cases/sqs-rapid7-scale-billion-messages/)  | Rapid7 100 億 msg/day 規模        | Cost 模型 / Standard queue              |

## Google Pub/Sub 案例

| 章節                                                                             | 公司 / 主題                      | 對應 Pub/Sub 大綱章節                         |
| -------------------------------------------------------------------------------- | -------------------------------- | --------------------------------------------- |
| [3.C60](/backend/03-message-queue/cases/pubsub-spotify-event-delivery-platform/) | Spotify Event Delivery 遷入      | Pub/Sub vs Lite / Push vs Pull / Ack deadline |
| [3.C61](/backend/03-message-queue/cases/pubsub-spotify-autoscaling-consumers/)   | Spotify Autoscaling 反效果       | Ack deadline / autoscaling signal             |
| [3.C62](/backend/03-message-queue/cases/pubsub-spotify-cloud-storage-export/)    | Spotify reliable GCS export      | Ack deadline / Cloud Storage subscription     |
| [3.C63](/backend/03-message-queue/cases/pubsub-mercari-actionable-history/)      | Mercari ack deadline batch-level | Ack deadline / Push vs Pull / Ordering        |
| [3.C64](/backend/03-message-queue/cases/pubsub-mercari-item-feed-dlt/)           | Mercari Item Feed DLT            | Dead-letter topic / Push vs Pull              |
| [3.C65](/backend/03-message-queue/cases/pubsub-mercari-line-flow-control/)       | Mercari LINE 對齊外部 RPS        | Push vs Pull subscription                     |
| [3.C66](/backend/03-message-queue/cases/pubsub-mercari-b2c-grpc-pusher/)         | Mercari B2C 自建 gRPC pusher     | Push vs Pull / Ordering 應用層處理            |
| [3.C67](/backend/03-message-queue/cases/pubsub-niantic-pokemon-go-telemetry/)    | Niantic Pokémon GO telemetry     | BigQuery subscription（pattern 對照）         |
| [3.C68](/backend/03-message-queue/cases/pubsub-wix-clickstream-dashboard/)       | Wix clickstream + Dataflow + BQ  | BigQuery subscription / Push vs Pull          |
| [3.C69](/backend/03-message-queue/cases/pubsub-twitter-ad-engagement/)           | Twitter Ad Engagement topic 切分 | Schema enforcement / Ordering key             |

## 案例覆蓋缺口（待補）

下列大綱章節在本案例庫中**公開 customer-side case 偏弱或缺**、撰寫正文時要明示「以下分析依官方文件 / KIP / 通用模式推導、非 case-driven」：

- **Kafka KRaft**：缺 customer-side 一手案例、目前依官方 KIP-833 / Confluent 公告為準
- **RabbitMQ MQTT plugin + 多協議**：缺 IoT 廠商 customer case、可補 RabbitMQ 官方 native MQTT blog
- **RabbitMQ Cluster Operator（K8s）**：缺直接案例、Zalando 案例是 pre-K8s 對照
- **Redis Streams + Functions（Redis 7+）**：公開 customer case 幾乎沒有
- **Redis Cluster on Streams**：公開 case 多在 single-instance / Sentinel 規模、Cluster 案例少
- **Pub/Sub IAM + Service Account**：customer engineering blog 著墨少、建議依 GCP 官方 IAM 文件 + 通用安全原則

案例庫總計 69 個、其中 Kafka 17 個（含通用層 5）、RabbitMQ 11 個、NATS 8 個、Redis Streams 6 個、SQS 12 個（含通用層 1）、Pub/Sub 10 個、純通用 / 反例 4 個。
