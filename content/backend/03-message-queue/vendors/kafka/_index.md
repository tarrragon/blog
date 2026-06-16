---
title: "Apache Kafka"
date: 2026-05-01
description: "Distributed event streaming platform、log-based 模型"
weight: 2
tags: ["backend", "message-queue", "vendor"]
---

Kafka 是 distributed event streaming platform、承擔三個責任：log-based 訊息儲存（partition + replication）、事件流分發（consumer group 各自進度）、跨系統事件總線（schema-aware contract）。設計取捨偏向「寫入即承諾、可長期保留、多 consumer 各自 replay」、broker 級可靠性與 consumer 端 idempotency 拆開、broker 不負責業務正確性。

對「事件驅動架構、CDC、跨系統事件分發、長期保留 + replay」這條路徑、Kafka 是業界事實標準。本頁先給最短路徑、再展開日常 producer / consumer 操作與 topic 設計、最後進階治理（多租戶、跨區、自動修復）跟排錯。

## 本章目標

讀完本章後、你應該能：

1. 用 docker-compose 跑起 Kafka + KRaft、驗證 broker 健康
2. 用 CLI 建 topic、produce / consume 訊息、看 partition 分布
3. 設計 producer acks / idempotence / consumer commit 策略對齊 [delivery semantics](/backend/knowledge-cards/delivery-semantics/)
4. 看懂 [consumer lag](/backend/knowledge-cards/consumer-lag/)、ISR shrink、rebalance 訊號、定位故障層
5. 評估 multi-tenant、cross-region、tiered storage、self-healing 等規模化議題

## 最短路徑：5 分鐘把 Kafka 跑起來

最短路徑用 KRaft 模式（取代 ZooKeeper、單節點即可跑）、避免初學者卡在 ZK 安裝。

```bash
# 1. 啟動 Kafka（apache/kafka 內建 KRaft、單一容器即含 broker + controller）
docker run -d --name kafka -p 9092:9092 apache/kafka:latest

# 2. 建 topic（CLI 在容器內 /opt/kafka/bin/）
docker exec kafka /opt/kafka/bin/kafka-topics.sh --create --topic demo --partitions 3 \
  --bootstrap-server localhost:9092
docker exec kafka /opt/kafka/bin/kafka-topics.sh --describe --topic demo \
  --bootstrap-server localhost:9092

# 3. 驗證 produce / consume
docker exec kafka bash -c "echo hello | /opt/kafka/bin/kafka-console-producer.sh \
  --topic demo --bootstrap-server localhost:9092"
docker exec kafka /opt/kafka/bin/kafka-console-consumer.sh --topic demo \
  --from-beginning --max-messages 1 --bootstrap-server localhost:9092
```

最短路徑只驗證「broker 起來、能寫能讀」。實際寫程式用 producer / consumer client、見[日常操作](#日常操作與決策形狀)。

## 日常操作與決策形狀

### CLI 與 client API

子議題：

- CLI 指令對照表（kafka-topics / kafka-configs / kafka-consumer-groups / kafka-acls）
- Producer client 配置：acks / batch.size / linger.ms / compression / enable.idempotence
- Consumer client 配置：auto.offset.reset / enable.auto.commit / max.poll.records / max.poll.interval.ms
- 對應指令範例：`kafka-topics.sh --describe`、`kafka-consumer-groups.sh --describe --group <id>`

### Topic 設計

[Topic](/backend/knowledge-cards/topic/) 承擔事件的邏輯邊界。子議題：

- [Partition](/backend/knowledge-cards/partition/) 數規劃（並行度 vs metadata 成本）
- Replication factor 與 min.insync.replicas（資料保護等級）
- Retention policy（time-based vs size-based、compact vs delete）
- Key 策略（ordering 範圍、hot partition 避免）

### Producer 與 Consumer 設計

設計決定 [delivery semantics](/backend/knowledge-cards/delivery-semantics/) 實際達成。子議題：

- Producer：acks=0/1/all 對應的可靠性取捨、idempotence、transaction 邊界
- Consumer：commit 策略（auto vs manual）、commit 時機與 at-least-once / at-most-once 對應
- [Consumer group](/backend/knowledge-cards/consumer-group/)：rebalance protocol（eager vs cooperative）、static membership
- 對應指令：producer 配置範例、consumer 配置範例、`kafka-consumer-groups.sh --describe`

## 進階主題（按需閱讀）

本段主題多數已展開為 deep article：[consumer rebalance 與 lag 診斷](consumer-rebalance-lag-diagnosis/)、[replication / ISR / exactly-once](replication-isr-exactly-once/)、[retention 與 tiered storage](retention-tiered-storage/)、[Schema Registry 與 schema 演進](schema-registry-evolution/)、[multi-tenant quota 與 ACL 治理](multi-tenant-quota-acl/)。下列子議題段保留每個主題的選題判讀入口。

### Multi-tenant 與配額治理

對應案例 [3.C6 Uber Kafka 事件平台](/backend/03-message-queue/cases/uber-kafka-infrastructure-evolution/)。子議題：

- Producer / Consumer quota（byte rate、request rate）
- ACL 設計（principal、resource、operation）
- Topic 命名規範與 ownership
- 對應指令：`kafka-configs.sh --alter --add-config 'producer_byte_rate=...'`、`kafka-acls.sh --add`

### Cross-region 與分層叢集

對應案例 [3.C1 Meta FOQS](/backend/03-message-queue/cases/meta-foqs-global-migration/) 與 [3.C4 LinkedIn Tiered Clusters](/backend/03-message-queue/cases/linkedin-kafka-tiered-clusters/)。子議題：

- MirrorMaker 2 配置（active-active vs active-passive）
- 分層叢集策略（critical / standard / experimental）
- 跨區 consumer 路徑與 routing freshness

### Topic 生命週期治理

對應案例 [3.C3 LinkedIn TopicGC](/backend/03-message-queue/cases/linkedin-topicgc-kafka-governance/)。子議題：

- Topic 活躍判準（last produce / consume timestamp）
- 自動回收條件與稽核
- Metadata 壓力訊號（controller log、partition 數量上限）

### Replication 與 exactly-once 升級

對應案例 [3.C9 反例：語義誤配](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/)。子議題：

- acks=all + min.insync.replicas ≥ 2 + producer idempotence
- Kafka transaction 與 read_committed 邊界
- 端到端 exactly-once（Kafka Streams 場景）

### Self-healing 與自動修復

對應案例 [3.C7 LinkedIn Self-Healing](/backend/03-message-queue/cases/linkedin-kafka-self-healing-automation/)。子議題：

- 可自動修復故障類型（disk full、broker offline、under-replicated partition）
- 自動修復 vs 人工升級邊界
- 修復過程的證據鏈納入觀測

### KRaft 與 Schema Registry

子議題：

- KRaft mode 取代 ZooKeeper（運維簡化、metadata 治理）
- Schema Registry（Confluent / Apicurio）與 Avro / Protobuf
- Schema 演進策略（forward / backward / full compatibility）

### Tiered storage

子議題：

- 冷熱分層（hot tier on local disk、cold tier on S3）
- Retention 設計與成本
- Read 路徑差異（hot vs cold）

### Kafka Connect 與 CDC

子議題：

- Source connector / Sink connector 模型
- Debezium CDC pipeline 與 outbox 整合
- Connect cluster 治理與 schema evolution

## 排錯快速判讀

### Consumer lag 暴增

操作原則：先看 lag 是「均勻分布」還是「集中在少數 partition」、再定位 consumer 慢 vs partition 不平衡。

```bash
kafka-consumer-groups.sh --describe --group <id> --bootstrap-server localhost:9092
# 輸出含 CURRENT-OFFSET / LOG-END-OFFSET / LAG 逐 partition 列、可看 lag 集中在哪幾個 partition
```

判讀路徑：consumer 慢（CPU / GC / 下游 I/O）→ producer 突增 → partition 不平衡（key 分布）。

### ISR shrink 與 under-replicated partition

操作原則：ISR 縮小代表 follower 跟不上 leader、看 broker 健康 / 網路 / disk。

```bash
kafka-topics.sh --describe --under-replicated-partitions --bootstrap-server localhost:9092
# 輸出為空代表所有 partition 同步正常；列出的 partition 即 ISR 落後者
```

### Rebalance storm

操作原則：consumer 頻繁加入 / 離開觸發 rebalance、看 session.timeout.ms 與 max.poll.interval.ms。

### Offset reset 或重複消費

對應反例 [3.C9](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/)。判讀路徑：commit 策略錯誤、broker 端 offset 過期、auto.offset.reset = earliest。

### Schema 不相容

操作原則：producer 升級 schema、consumer 未升、看 compatibility level。

## 何時改走其他服務

| 需求形狀                           | 改走                                                                                         |
| ---------------------------------- | -------------------------------------------------------------------------------------------- |
| 任務隊列（中等吞吐、複雜 routing） | [RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/)                                      |
| Managed queue（AWS 生態、簡單）    | [AWS SQS](/backend/03-message-queue/vendors/aws-sqs/)                                        |
| Managed pub/sub（GCP 生態）        | [Google Pub/Sub](/backend/03-message-queue/vendors/google-pubsub/)                           |
| 輕量 messaging + 微服務通訊        | [NATS](/backend/03-message-queue/vendors/nats/)                                              |
| Redis 生態內 stream                | [Redis Streams](/backend/03-message-queue/vendors/redis-streams/)                            |
| Managed Kafka                      | AWS MSK / Confluent Cloud（見 [3.C2](/backend/03-message-queue/cases/vmware-kafka-to-msk/)） |
| Kafka 相容、單 binary              | Redpanda（T2 候選）                                                                          |
| 多租戶 + 分層儲存原生              | Apache Pulsar（T2 候選）                                                                     |

## 不在本頁內的主題

- 各語言 client API reference（依官方文件）
- Kafka Streams / ksqlDB（另開 stream processing 章節）
- Confluent 商業功能（Confluent Cloud、Control Center）

## 案例回寫

### 既有通用案例（C1-C10）

| 案例                                                                                                  | 主討論議題                     |
| ----------------------------------------------------------------------------------------------------- | ------------------------------ |
| [3.C1 Meta FOQS](/backend/03-message-queue/cases/meta-foqs-global-migration/)                         | 跨區 queue、tenant 遷移節奏    |
| [3.C2 VMware → MSK](/backend/03-message-queue/cases/vmware-kafka-to-msk/)                             | 自管轉 managed、ACL / cutover  |
| [3.C3 LinkedIn TopicGC](/backend/03-message-queue/cases/linkedin-topicgc-kafka-governance/)           | Topic 生命週期治理             |
| [3.C4 LinkedIn Tiered Clusters](/backend/03-message-queue/cases/linkedin-kafka-tiered-clusters/)      | 分層叢集策略                   |
| [3.C5 Slack Kafka+Redis](/backend/03-message-queue/cases/slack-job-queue-kafka-redis/)                | 多 broker 組合拓樸             |
| [3.C6 Uber Kafka](/backend/03-message-queue/cases/uber-kafka-infrastructure-evolution/)               | 多租戶 + 平台治理              |
| [3.C7 LinkedIn Self-Healing](/backend/03-message-queue/cases/linkedin-kafka-self-healing-automation/) | 自動修復                       |
| [3.C8 Cloudflare Queues](/backend/03-message-queue/cases/cloudflare-queues-global-delivery-model/)    | 全球交付（對比）               |
| [3.C9 反例：語義誤配](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/)      | Replication + idempotence 升級 |
| [3.C10 規模對照](/backend/03-message-queue/cases/contrast-queue-model-by-scale/)                      | 不同規模下的佇列模型           |

### Kafka 專屬案例（C11-C22）

| 案例                                                                                                    | 主討論議題                             |
| ------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| [3.C11 Pinterest Tiered Storage](/backend/03-message-queue/cases/kafka-pinterest-tiered-storage/)       | Broker-decoupled tiered storage / S3   |
| [3.C12 Pinterest Shallow Mirror](/backend/03-message-queue/cases/kafka-pinterest-shallow-mirror/)       | MirrorMaker CPU/memory 優化            |
| [3.C13 Shopify Debezium CDC](/backend/03-message-queue/cases/kafka-shopify-debezium-cdc/)               | Sharded MySQL CDC pipeline             |
| [3.C14 Yelp Schematizer](/backend/03-message-queue/cases/kafka-yelp-schematizer/)                       | Schema Registry + 強制 compatibility   |
| [3.C15 Airbnb Spark Streaming](/backend/03-message-queue/cases/kafka-airbnb-spark-streaming-rebalance/) | Partition-task 解耦 / data skew        |
| [3.C16 Robinhood Faust](/backend/03-message-queue/cases/kafka-robinhood-faust-python-streaming/)        | Python stream processing 生態          |
| [3.C17 Walmart MPS](/backend/03-message-queue/cases/kafka-walmart-mps-rebalance/)                       | Partition-consumer 1:1 解耦 / K8s 擴張 |
| [3.C18 Wix Greyhound](/backend/03-message-queue/cases/kafka-wix-greyhound-troubleshooting/)             | TLLSR consumer troubleshooting         |
| [3.C19 Wix Multi-cluster](/backend/03-message-queue/cases/kafka-wix-multi-cluster-migration/)           | Metadata scaling ceiling / 分群        |
| [3.C20 Spotify 遷出 Kafka](/backend/03-message-queue/cases/kafka-spotify-event-delivery-exodus/)        | （反例）early Kafka 版本可靠性硬限制   |
| [3.C21 Goldman Sachs MSK](/backend/03-message-queue/cases/kafka-goldman-sachs-msk-migration/)           | MM2 + LB + timeout 整合 pitfall        |
| [3.C22 Trivago KEDA](/backend/03-message-queue/cases/kafka-trivago-keda-scale-to-zero/)                 | Consumer lag 驅動 scale-to-zero        |

**KRaft 缺直接 customer case**：目前依官方 KIP-833 / Confluent 公告為準、後續若有 customer 一手案例可補。

## 下一步路由

- 上游概念：[0.3 非同步選型](/backend/00-service-selection/async-delivery-selection/)、[3.1 broker basics](/backend/03-message-queue/broker-basics/)
- 平行 vendor：[RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/)、[NATS](/backend/03-message-queue/vendors/nats/)
- 下游能力：[3.4 consumer 設計](/backend/03-message-queue/consumer-design/)、[6.12 idempotency / replay](/backend/06-reliability/idempotency-replay/)
