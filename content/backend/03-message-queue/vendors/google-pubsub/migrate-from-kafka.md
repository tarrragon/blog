---
title: "Kafka → Google Cloud Pub/Sub：從 partition 到 topic-subscription 的模型轉換"
date: 2026-06-22
description: "從 Apache Kafka 遷移到 Google Cloud Pub/Sub，處理 partition → topic 模型轉換、ordering 語意差異、consumer group → subscription 對應、offset → ack deadline 切換的階段化流程"
weight: 12
tags: ["backend", "message-queue", "kafka", "google-pubsub", "migration"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [Apache Kafka](/backend/03-message-queue/vendors/kafka/)（source）跟 [Google Cloud Pub/Sub](/backend/03-message-queue/vendors/google-pubsub/)（target）。跑 6 維 diff dimension audit 後判定為 **Type E paradigm shift**：兩者投遞模型本質不同（partition-based log vs topic-subscription pub/sub）。

## 為什麼從 Kafka 遷到 Pub/Sub

這個遷移的 driver 通常是平台策略：

- **All-in GCP**：組織決定收斂到 GCP 生態，Kafka 是唯一非 GCP 的 stateful 服務，維運孤島成本高
- **運維簡化**：自管 Kafka cluster 的 broker、ZooKeeper/KRaft、partition rebalance、retention 管理需要專職團隊；Pub/Sub 是全託管
- **GCP 整合**：下游是 BigQuery、Dataflow、Cloud Run — Pub/Sub 原生串接，Kafka 要加 connector 層
- **全球路由**：Pub/Sub topic 是 global（不綁 region），Kafka 需要 MirrorMaker 做跨 region 同步

遷移的工作量不在資料搬遷（message queue 通常不搬歷史資料），在 **模型轉換** — Kafka 的 partition ordering、consumer group、offset commit 跟 Pub/Sub 的 topic-subscription、ack deadline、ordering key 是不同抽象。

## 6 維 diff dimension audit

| 維度                   | 評估                                                               | 等級               |
| ---------------------- | ------------------------------------------------------------------ | ------------------ |
| Schema / API           | Kafka producer/consumer API → Pub/Sub client library，完全不同 API | High               |
| Operational model      | 自管 broker/ZK/KRaft → 全託管                                      | High（方向：簡化） |
| Abstraction / paradigm | partition-based log vs topic-subscription pub/sub                  | High               |
| Number of components   | Kafka + Schema Registry + Connect → Pub/Sub + (optional) Dataflow  | Medium             |
| Application change     | Producer/Consumer 全部改寫                                         | High               |
| Data topology          | Partition × offset → Topic × subscription × ack                    | High               |

五維 High — **Type E paradigm shift**，是兩套模型的橋接，工程量遠超 drop-in 或翻譯。

## 模型差異對照

遷移前必須理解兩套模型的對應關係。對應不是一對一 — 有些概念在對方沒有直接等價物。

| Kafka 概念          | Pub/Sub 對應                     | 差異重點                                                                                       |
| ------------------- | -------------------------------- | ---------------------------------------------------------------------------------------------- |
| Topic               | Topic                            | 名稱相同但語意不同：Kafka topic 有 partition，Pub/Sub topic 沒有                               |
| Partition           | 無直接對應                       | Pub/Sub 的 ordering 用 ordering key 實現，但 ordering key 不保證全域順序                       |
| Consumer group      | Subscription                     | 每個 subscription 獨立消費 topic 的全部訊息，類似 Kafka 的 consumer group                      |
| Offset              | 無直接對應                       | Pub/Sub 用 ack/nack 而非 offset commit。ack 後訊息不可重讀（除非用 seek）                      |
| Offset commit       | Ack                              | Kafka 可以 commit 到任意 offset（replay）；Pub/Sub ack 是 per-message、seek 可以回到 timestamp |
| Retention           | Message retention                | Kafka retention 期內可任意 seek；Pub/Sub retention 期內可用 timestamp seek                     |
| Consumer lag        | Oldest unacked message age       | 觀測指標不同：Kafka 看 offset lag、Pub/Sub 看 oldest_unacked_message_age                       |
| Partition rebalance | 無（Pub/Sub 自動負載分散）       | Kafka rebalance 是操作痛點，Pub/Sub 消除了這個概念                                             |
| Schema Registry     | Pub/Sub Schema                   | Pub/Sub 原生支援 Avro/Protobuf schema validation                                               |
| Kafka Connect       | Dataflow / BigQuery subscription | 下游整合的對應工具不同                                                                         |

### Ordering 語意是最大差異

Kafka 的 ordering 保證是 partition 內全域有序。同一個 partition 的訊息按寫入順序消費，consumer group 內每個 partition 只有一個 consumer。

Pub/Sub 預設不保證 ordering。要 ordering 需開啟 ordering key — 同一 ordering key 的訊息有序，但不同 ordering key 之間無序。ordering key 的並行度由 key 的 cardinality 決定（類似 Kafka 的 partition key）。

遷移時的判斷：

- 若 Kafka 的 ordering 只依賴 partition key（常見），ordering key 直接對應
- 若依賴 partition 內的全域順序（少見但存在），需要重新設計 — Pub/Sub 沒有 partition 全域順序的概念
- 若完全不需要 ordering（fan-out 場景），Pub/Sub 預設行為更簡單

### Component 數量轉換

Kafka 生態的 Schema Registry 在 Pub/Sub 由原生 Schema 功能替代（topic-level schema validation）；Kafka Connect 的 sink connector 由 BigQuery subscription 或 Dataflow job 替代。Dataflow 不是必要 — 簡單的 push/pull consumer 不需要 Dataflow，只有 stream processing（windowed aggregation、join）才需要。

## 階段一：Producer 遷移（雙寫）

雙寫策略是 paradigm shift 遷移的標準起手。Application 同時把訊息寫入 Kafka 和 Pub/Sub，consumer 仍從 Kafka 消費。

### Producer 改造

```python
# 示意：雙寫 wrapper（實際生產用各自語言的 client library）
def publish_order_event(event):
    # 原有 Kafka producer
    kafka_producer.send("order-events", key=event.order_id, value=event.to_bytes())

    # 新增 Pub/Sub producer
    pubsub_publisher.publish(
        "projects/my-project/topics/order-events",
        data=event.to_bytes(),
        ordering_key=event.order_id  # 對應 Kafka partition key
    )
```

### 雙寫驗證

| 驗證項目      | 方法                                              | 通過條件                         |
| ------------- | ------------------------------------------------- | -------------------------------- |
| 訊息數量一致  | 比對 Kafka produce count 與 Pub/Sub publish count | 差異 < 0.01%（允許 timing 差異） |
| Ordering 一致 | 同一 ordering key 的訊息在兩端順序相同            | 抽樣驗證 100 個 key              |
| Latency 影響  | 監控 request latency 變化                         | p99 增加 < 10ms                  |
| 失敗隔離      | Pub/Sub publish 失敗不影響 Kafka publish          | Pub/Sub timeout 時 Kafka 正常    |

雙寫的失敗隔離要嚴格設計。Pub/Sub publish 失敗時，application 應該 log + metric 但不 block request。Kafka 是已驗證的正式路徑，Pub/Sub 在這個階段是 shadow。

## 階段二：Consumer 遷移（逐 subscription 切換）

Producer 雙寫穩定後，逐一把 consumer 從 Kafka 切到 Pub/Sub subscription。

### Consumer 改造重點

**Ack 模型差異**：Kafka consumer 是 poll + commit offset；Pub/Sub 是 pull（或 push）+ per-message ack。

```python
# Kafka consumer pattern
for msg in kafka_consumer:
    process(msg)
    kafka_consumer.commit()

# Pub/Sub pull subscriber pattern
def callback(message):
    try:
        process(message.data)
        message.ack()
    except Exception:
        message.nack()  # 會被重新投遞

subscriber.subscribe("projects/my-project/subscriptions/order-processor", callback=callback)
```

**Idempotency 更重要**：Pub/Sub 的 at-least-once delivery 加上 ack deadline 機制，redelivery 比 Kafka 更容易觸發（ack deadline 內沒 ack 就重投）。Consumer 的 [idempotency](/backend/knowledge-cards/idempotency/) 設計要比 Kafka 時更嚴格。

**Flow control**：Pub/Sub client library 支援 `max_outstanding_messages` 和 `max_outstanding_bytes` 做 [backpressure](/backend/knowledge-cards/backpressure/) 控制，對應 Kafka 的 `max.poll.records`。

### 切換順序

依 consumer 的重要度和複雜度排序：

1. 先切 stateless consumer（log pipeline、metrics aggregation）— 低風險
2. 再切有 side effect 但 idempotent 的 consumer（search index sync、notification）
3. 最後切核心 consumer（payment processing、inventory update）— 需要完整 idempotency 驗證

每切一組 consumer：

1. 建立對應的 Pub/Sub subscription
2. 部署新 consumer（讀 Pub/Sub）
3. 驗證處理正確性（比對 Kafka consumer 和 Pub/Sub consumer 的輸出）
4. 停止舊 Kafka consumer
5. 觀察 7 天無異常

## 階段三：停止雙寫

所有 consumer 切完後：

1. 停止 Kafka producer（移除雙寫邏輯）
2. 觀察 Kafka topic 不再有新訊息
3. 等 Kafka retention 過期
4. 下線 Kafka cluster

Kafka cluster 不要在 consumer 切完後立即下線。保留 retention period + 7 天作為回退保險。

## 回退路徑

Type E 遷移的回退要在每個階段都設計：

- **階段一回退**：移除 Pub/Sub publish 邏輯，Kafka 路徑不受影響
- **階段二回退**：重啟 Kafka consumer、停止 Pub/Sub subscriber。Kafka 的 offset 要確認是否仍在 retention 內
- **階段三回退**：如果 Kafka 已下線，需要重新建 cluster 並從 Pub/Sub 反向雙寫回 Kafka — 成本高，所以階段三前要確認穩定

回退的關鍵指標：consumer lag（Pub/Sub 的 `oldest_unacked_message_age`）持續上升、error rate 上升、或 redelivery rate 異常。

## 遷移後的監控對照

| Kafka 監控指標        | Pub/Sub 對應指標                                     | 來源             |
| --------------------- | ---------------------------------------------------- | ---------------- |
| Consumer lag (offset) | `subscription/oldest_unacked_message_age`            | Cloud Monitoring |
| Produce rate          | `topic/send_message_operation_count`                 | Cloud Monitoring |
| Consume rate          | `subscription/pull_message_operation_count`          | Cloud Monitoring |
| Redelivery count      | `subscription/dead_letter_message_count` + nack rate | Cloud Monitoring |
| Broker disk usage     | 無需關注（fully managed）                            | N/A              |
| Rebalance events      | 無（Pub/Sub 自動分散）                               | N/A              |

## 不適合遷移的場景

以下場景 Kafka → Pub/Sub 的 ROI 不成立：

- **需要 exactly-once semantics**：Kafka 的 transactional producer + idempotent producer 提供 exactly-once；Pub/Sub 是 at-least-once，application 層做 dedup
- **需要長期 replay**：Kafka retention 可設數月甚至永久（tiered storage）；Pub/Sub message retention 最長 31 天（若需超過 31 天的 replay，可用 BigQuery subscription 做長期歸檔，但查詢模式不同於 Kafka 的 offset-based replay）
- **大量 ordering 依賴**：如果 Kafka topology 重度依賴 partition ordering 且 key cardinality 低，Pub/Sub ordering key 的並行度會比 Kafka 差
- **使用 Kafka Streams / ksqlDB 做 stateful processing**：stream processing 邏輯跟 Kafka 綁定（state store backed by changelog topic），遷到 Pub/Sub 要同時遷移 processing 框架（→ Dataflow / Beam），工程量額外翻倍且 API 完全不同
- **多雲 / 非 GCP 環境**：Pub/Sub 是 GCP-only，跨雲場景反而讓 Kafka 更合理

## 交接路由

- Source vendor overview：[Apache Kafka](/backend/03-message-queue/vendors/kafka/)
- Target vendor overview：[Google Cloud Pub/Sub](/backend/03-message-queue/vendors/google-pubsub/)
- Pub/Sub 操作細節：[Push / Pull / Ack Flow Control](/backend/03-message-queue/vendors/google-pubsub/push-pull-ack-flow-control/)、[Ordering / DLT / Schema](/backend/03-message-queue/vendors/google-pubsub/ordering-dlt-schema/)
- Consumer idempotency：[3.4 Consumer Design](/backend/03-message-queue/consumer-design/)、[3.6 Processing Recovery Semantics](/backend/03-message-queue/processing-recovery-semantics/)
- 反向路徑（SQS → Pub/Sub）：[AWS SQS → Google Pub/Sub](/backend/03-message-queue/vendors/aws-sqs/migrate-to-google-pubsub/)
