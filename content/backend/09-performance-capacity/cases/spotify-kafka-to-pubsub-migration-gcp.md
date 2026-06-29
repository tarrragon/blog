---
title: "9.C9 Spotify：從自管 Kafka 遷移到 GCP Pub/Sub 的事件交付系統"
date: 2026-05-12
description: "Spotify 把自管 Kafka 事件系統遷移到 Google Cloud Pub/Sub、避免自管 broker 的容量規劃成本"
weight: 9
tags: ["backend", "performance", "capacity", "case-study", "mq-stream", "gcp", "sustained-growth"]
---

這個案例的核心責任是說明「事件交付系統的容量規劃，靠 managed service 卸載 vs 自管 broker」的長期成本對照。Spotify 從 Kafka 遷到 Pub/Sub 的驅動力是 *容量規劃的工程成本* 在 sustained growth 下變得不划算、Kafka 能力本身不是瓶頸。

## 觀察

Spotify 在 Google Cloud 的遷移敘述（引自 [Spotify's journey to cloud](https://cloud.google.com/blog/products/gcp/spotifys-journey-to-cloud-why-spotify-migrated-its-event-delivery-system-from-kafka-to-google-cloud-pubsub)）：

| 指標       | 內容                                     |
| ---------- | ---------------------------------------- |
| 用戶規模   | 7500 萬 + 用戶（遷移時期）               |
| 遷移系統   | Event Delivery System（事件交付）        |
| 遷出技術   | 自管 Apache Kafka                        |
| 遷入技術   | Google Cloud Pub/Sub                     |
| 大數據生態 | BigQuery / Dataflow / Dataproc / Pub/Sub |

關鍵動機：「moving event delivery to a managed service」— 卸下 Kafka broker 的容量規劃與運維負擔。

## 判讀

Spotify 遷移揭露三個 broker 容量規劃的長期工程問題。

1. **自管 broker 的容量規劃是長期 tax**：Kafka cluster 需要 partition planning、broker 數量、副本因子、disk capacity、network bandwidth、ZooKeeper / KRaft 治理 — 每個維度都要持續規劃、每次擴容都是工程專案。對應 [03 訊息佇列模組](/backend/03-message-queue/) 的 broker basics 與 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/) 的人力成本評估。
2. **managed service 的容量是 trade-off、不是免費午餐**：Pub/Sub 自動 scaling、但 vendor lock-in、cost-per-message 累積、message ordering / latency 特性跟 Kafka 不同。遷移本身要驗證 *業務語意* 跟 Pub/Sub 兼容。對應 [03.4 broker basics](/backend/03-message-queue/broker-basics/)。
3. **遷移本身是容量規劃題目**：把 7500 萬用戶的事件交付從 A 平台搬到 B 平台、不能停機、不能丟 message。這個遷移過程本身就是高併發容量工程。對應 [01.3 schema migration rollout evidence](/backend/01-database/schema-migration-rollout-evidence/) 的同類流程。

需要警惕：Spotify 這個決定不是「Kafka 不好」、是「Spotify 規模下、自管 Kafka 的工程投入不划算」。對中小團隊、自管 Kafka 可能是更便宜的選項。讀案例時要看 *規模門檻* 跟 *團隊能力*。

## 策略

可重用的工程做法：

1. **broker 自管 vs managed 是長期 TCO 評估**：算「平日運維 + 容量擴容 + 故障處理 + 升級遷移」的人力成本、不只算「broker 雲端費用」。對應 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/)。
2. **遷移分階段：dual write → shadow → cutover**：先寫兩邊、驗證一致性、再切流量。對應 [01.3 schema migration rollout evidence](/backend/01-database/schema-migration-rollout-evidence/) 的同類流程。
3. **業務語意對映是遷移關鍵**：Kafka 的 partition / offset / consumer group 在 Pub/Sub 對映成不同概念（subscription / ordering key / message attribute）、不是 1:1。

跨平台等效：AWS SNS / SQS / Kinesis、Amazon MSK（managed Kafka）、Azure Service Bus / Event Hubs / Event Grid 都是對等候選。差異是 message ordering 保證、delivery guarantee、cost model。

## 下一步路由

- 想評估 broker 自管 vs managed → [03 訊息佇列模組](/backend/03-message-queue/) + [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/)
- 想做大規模 message 系統遷移 → [01.3 schema migration rollout evidence](/backend/01-database/schema-migration-rollout-evidence/) 的對等流程
- 想理解 broker 容量規劃 → [03.4 broker basics](/backend/03-message-queue/broker-basics/)
- 對照其他事件型負載 → [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)

## 引用源

- [Spotify's journey to cloud: why Spotify migrated its event delivery system from Kafka to Google Cloud Pub/Sub](https://cloud.google.com/blog/products/gcp/spotifys-journey-to-cloud-why-spotify-migrated-its-event-delivery-system-from-kafka-to-google-cloud-pubsub)
- [Spotify chooses Google Cloud Platform](https://cloud.google.com/blog/products/gcp/spotify-chooses-google-cloud-platform-to-power-data-infrastructure/)
- [Spotify's experiments with stream processing on Google Cloud Dataflow](https://cloud.google.com/blog/products/gcp/spotifys-experiments-with-stream-processing-on-google-cloud-dataflow)
