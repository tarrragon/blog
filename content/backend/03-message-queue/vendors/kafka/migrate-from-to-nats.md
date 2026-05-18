---
title: "Kafka ↔ NATS：不是 migration、是 messaging paradigm 重設計"
date: 2026-05-19
description: "Kafka 跟 NATS 不是同類產品（log-based event streaming vs subject-based messaging）、'migration' 字面上不成立；本文釐清兩家 paradigm 邊界、什麼情境真的能換、application 模式重設計的 5 個踩雷（consumer offset 觀念差 / retention model / exactly-once 假設 / schema registry 缺位 / fan-out 模式差）、跟 JetStream 對位 + 混合架構"
weight: 11
tags: ["backend", "message-queue", "kafka", "nats", "jetstream", "migration", "paradigm"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [Kafka](/backend/03-message-queue/vendors/kafka/) 跟 [NATS](/backend/03-message-queue/vendors/nats/)。跟前四篇 migration（schema 差 / drop-in / operational redesign / multi-tool 拆分）對照、本篇是 *paradigm shift* — 兩端不是「同類產品的不同實作」、是 *不同抽象層的 messaging system*。

## 「Kafka → NATS migration」字面上不成立

前面四篇 migration 都隱含一個前提：source 跟 target 是 *同類產品*、只是不同實作或 deployment 模型。「Kafka → NATS」字面上看起來也是 *messaging migration*、但實際上：

| 維度                  | Kafka                                                                | NATS Core                                                | NATS JetStream                                            |
| --------------------- | -------------------------------------------------------------------- | -------------------------------------------------------- | --------------------------------------------------------- |
| Core abstraction      | Distributed log（partition + offset）                                | Pub/Sub subject（fire-and-forget）                       | Stream（subject group + retention）                       |
| Message persistence   | Default persistent（log retention）                                  | **不持久化**（subscriber 缺席 = lost）                   | 持久化（K/V backend / file）                              |
| Delivery semantic     | At-least-once / exactly-once（事務）                                  | At-most-once                                              | At-least-once / exactly-once                              |
| Consumer model        | Consumer group + offset                                              | Subscriber + subject pattern                              | Durable consumer + pull / push                            |
| Ordering              | Per partition strict                                                 | 無 ordering guarantee                                     | Per stream / per consumer                                 |
| Replay                | 隨意 from offset                                                     | **無**                                                    | from sequence number                                      |
| Throughput            | 高（M msg/s）                                                         | 極高（10M+ msg/s）                                        | 中（100K-1M msg/s）                                       |
| Latency               | 5-50ms                                                                | < 1ms                                                     | 5-20ms                                                    |

Kafka 跟 NATS Core 是 *不同類產品* — 一個是 durable event log、一個是 transient pub/sub。「migration」需要先決定 *target 是 NATS Core 還是 JetStream*、然後判斷 *application 模式能否重設計* 對應。

## 什麼情境真的能換、什麼不能

| Application 模式                     | Kafka 適配度 | NATS Core 適配 | NATS JetStream 適配 | 「migration」可行性 |
| ------------------------------------ | ------------ | -------------- | ------------------- | ------------------- |
| Event sourcing（replay 過去事件）     | 強           | 不可（無 replay）| 中（JetStream replay）| 部分（移到 JetStream）|
| Microservice async messaging         | 強           | 強             | 強                  | 高                  |
| Real-time pub/sub（低延遲、可丟）     | 中           | 強             | 中                  | 高（移到 Core）     |
| 跨 service 命令 / RPC                | 弱（不適合）| 強（request-reply）| 弱                | 不需要遷            |
| 大量 log / metric / event collection | 強           | 弱             | 中                  | 低（保留 Kafka）    |
| Multi-tenant message bus             | 中           | 強             | 強                  | 高                  |
| Strict ordering + transactional      | 強           | 不可           | 中（per stream）     | 部分（部分功能犧牲）|
| 5+ 年歷史 retention                  | 強           | 不可           | 中（retention 設長） | 部分                |

**判讀**：

- *Microservice async messaging + 低延遲需求* → NATS Core 更合適、是 *真正的 migration*
- *Event sourcing + replay* → JetStream 部分對等、但 partition / offset 觀念變了
- *Log collection / event streaming* → 不該遷、保留 Kafka

## 為什麼會考慮這個 paradigm shift

實務上觸發評估 NATS 通常三條 driver：

1. **Cost + operational complexity**：Kafka cluster + ZooKeeper（或 KRaft）+ Schema Registry + Connect 是重資產、3-5 broker + ops 1+ FTE；NATS 單 binary、無依賴、輕量
2. **Latency 要求 < 1ms**：Kafka 對單 message latency 不是 SLA、NATS Core 是
3. **Multi-tenant / multi-region 簡化**：NATS 內建 *account* + *leaf node* 拓樸、跨 region 是 first-class

但這三條 driver 都 *只在特定 application 模式有效*。不是普世 better、是 *某類 workload 適合*。

## Migration 結構：application 重設計 + 部分 stream cutover

跟前面四篇 migration 結構都不同、Kafka ↔ NATS 是 *混合*：

1. **Phase 0：scope 判讀** — 列 application、區分「適合 NATS」vs「保留 Kafka」
2. **Phase 1：application code 重設計** — 不是 SDK 換、是 *messaging pattern 改*（event sourcing → message bus / consumer group → durable consumer）
3. **Phase 2：部分 stream parallel run** — 新 application 走 NATS、舊 application 持續 Kafka
4. **Phase 3：cutover 適合的 stream**
5. **Phase 4：長期混合架構** — Kafka 跟 NATS *共存*、不消滅一邊

整體不是 *一次 migration*、是 *漸進拆分*。多數 production 環境 *永遠* 是混合架構。

## Application 重設計範例：consumer group → durable consumer

```go
// Kafka 端 consumer group pattern
consumer := kafka.NewConsumer(&kafka.ConfigMap{
    "bootstrap.servers": "kafka:9092",
    "group.id":          "myapp-orders",
    "auto.offset.reset": "earliest",
})
consumer.SubscribeTopics([]string{"orders"}, nil)

for {
    msg, err := consumer.ReadMessage(-1)
    // process msg.Value
    consumer.CommitMessage(msg)
}
```

```go
// NATS JetStream durable consumer
js, _ := nc.JetStream()
sub, _ := js.PullSubscribe("orders.>", "myapp-orders",
    nats.AckExplicit(),
    nats.MaxAckPending(100),
)

for {
    msgs, _ := sub.Fetch(10, nats.MaxWait(5*time.Second))
    for _, msg := range msgs {
        // process msg.Data
        msg.Ack()
    }
}
```

差異：

- Kafka `auto.offset.reset` → NATS `DeliverPolicy`（多種選項）
- Kafka commit message → NATS explicit Ack（per message）
- Kafka partition → NATS subject hierarchy（`orders.>` 通配）
- Kafka rebalance → NATS 不需要、durable consumer 跨 instance 共享

Application 邏輯改動 30-60%、不是 SDK 換。

## Production 故障演練

### Case 1：Consumer offset 觀念差，replay 不對等

**徵兆**：application 設計「跑歷史 7 天事件 catch-up」、Kafka 設 `auto.offset.reset=earliest` + `seek_to(timestamp)` 跑；換 NATS JetStream 後找不到 `seek_to` 等價 API、catch-up 失敗。

**根因**：Kafka offset 是 *broker-side 維護 + consumer-side commit*；NATS JetStream 用 *sequence number* + `DeliverPolicy.ByStartTime`、但 time-based seek 精度低、且 application code 必須改。

**修法**：

1. **預先設計**：NATS JetStream 用 `DeliverPolicy.ByStartSequence` + 自管 sequence-time mapping
2. **保留 Kafka 給 replay-heavy use case**：不是所有 application 都遷
3. **混合架構**：歷史 replay 走 Kafka、新事件流走 NATS、application 處理雙來源

### Case 2：Retention model 差異、磁碟使用炸

**徵兆**：NATS JetStream stream 設 `retention=interest`（subscriber 收到就刪）、cutover 後 disk 持續長大；預期跟 Kafka log retention 7 天類似、實際資料留 30+ 天沒清。

**根因**：NATS JetStream retention 有 3 種：`limits` / `interest` / `workqueue`。`interest` 是 *至少一個 subscriber 還沒 ack 就保留*；application 端 silent consumer（已下線但沒 unsubscribe）讓 message 永留。

**修法**：

1. **預設 `retention=limits`**：用 `MaxAge` / `MaxBytes` 跟 Kafka log retention 對應、明確控制
2. **`interest` retention 慎用**：只在 *確認所有 subscriber lifecycle 受控* 場景
3. **Subscriber cleanup**：application graceful shutdown 必須主動 unsubscribe、不留 zombie consumer

### Case 3：Exactly-once 假設不對等

**徵兆**：cutover 後發現某 application（payment processor）開始出現 *duplicate transaction*；Kafka 端用 transactional producer + idempotent consumer 跑了 2 年沒問題。

**根因**：Kafka exactly-once 是 *producer transaction + consumer offset commit atomic*；NATS JetStream exactly-once 概念不一樣 — 是 *publish ack* + *consumer ack* 跨層 atomic、application 端要主動處理 idempotency。

**修法**：

1. **重新審視 application 端 idempotency**：用 message ID + dedup store（Redis SETEX）顯式 dedup
2. **NATS JetStream 對 exactly-once 不該假設「自動」**：application 端責任、不是 broker 端
3. **Payment / financial 場景慎遷**：保留 Kafka transactional pattern 較穩

### Case 4：Schema registry 缺位、ad-hoc schema 漂移

**徵兆**：NATS 部署 3 個月後、producer / consumer 間 schema 對不上、application bug；Kafka 端有 Confluent Schema Registry 強 enforce、NATS 沒對等服務。

**根因**：NATS 哲學是 *minimalist*、不內建 schema registry；application 自己決定 payload format。Kafka 生態的 Avro / Protobuf + Registry 模式不直接搬。

**修法**：

1. **外部 schema management**：用 BSR（Buf Schema Registry）或自家 Git-based registry、producer / consumer build-time 驗證
2. **NATS Object Store**：JetStream 提供 K/V + Object Store、可存 schema 文件
3. **接受紀律性 trade-off**：NATS 簡潔代價是 application 端紀律、不能靠 broker 強 enforce

### Case 5：Fan-out 模式跟 Kafka 不一致

**徵兆**：同一 event 要送 5 個 downstream service、Kafka 端用 consumer group + 5 個 group 跑；NATS 端設計 5 個 durable consumer、結果某些 message 漏 fan-out。

**根因**：Kafka consumer group 對 *同 group 內 partition 分配*、不同 group 各自完整消費；NATS JetStream `Durable consumer` 預設行為跟 group 不同 — *單 durable consumer 是 shared subscription*、要 fan-out 需多個獨立 durable。

**修法**：

1. **明確設計 fan-out**：N 個 downstream 對應 N 個 *獨立 durable consumer*、不共用
2. **用 `AckPolicy.None` + push subscriber**：不需要 ack 的 fan-out 場景、用 ephemeral push subscriber
3. **檢查 application stream config**：fan-out 失敗多半是 consumer config 錯、不是 NATS bug

## Capacity / cost 對照

| 維度                          | Kafka（self-managed）                        | NATS（JetStream）                              |
| ----------------------------- | -------------------------------------------- | ---------------------------------------------- |
| Cluster size baseline         | 3-5 broker + ZooKeeper / KRaft               | 3 server（含 JetStream cluster）              |
| RAM / broker baseline         | 16-64GB                                       | 2-16GB                                          |
| Storage requirement           | 高（log retention）                          | 中（JetStream file backend）                  |
| Operational FTE               | 0.5-2 FTE                                     | 0.1-0.3 FTE                                    |
| Throughput / single node      | 100K-1M msg/s                                 | NATS Core：10M+、JetStream：100K-1M           |
| Latency p99                   | 5-50ms                                        | NATS Core：< 1ms、JetStream：5-20ms          |
| Retention 1TB / month cost    | $400-800（含 HA）                            | $200-400                                       |
| Operational complexity        | 高（Schema Registry / Connect / Streams）    | 低                                              |
| Ecosystem maturity           | 高（10+ 年）                                  | 中（JetStream 2021+）                          |

**判讀**：簡單 messaging workload NATS 顯著便宜；complex event streaming（Schema Registry / Streams / Connect 重度用）Kafka 不替代。

## 整合 / 下一步

### 混合架構是 long-term default

多數 production 環境最終是 *Kafka + NATS 共存*：

```text
[event sourcing / log collection]        [microservice async messaging]
         Kafka                                       NATS
         │                                            │
         └──────── Bridge (Connect / Custom) ────────┘
```

NATS 跑微服務間 messaging、Kafka 跑 event log / analytics pipeline；中間用 Kafka Connect NATS connector 或自寫 bridge 同步必要 stream。

### 跟 [Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/) 對位

CDC pipeline 設計：

- DB → Debezium → Kafka topic（event sourcing 主軸）
- Kafka → NATS bridge → microservice fan-out
- 不直接 DB → Debezium → NATS（Debezium 不原生支援 NATS sink）

### 跟前 4 篇 migration 的結構對照

| 篇                          | Schema 差 | Operational 差 | Paradigm 差 | 結構               |
| --------------------------- | --------- | -------------- | ----------- | ------------------ |
| Splunk → Elastic            | 高        | 中             | 低          | 6-phase            |
| Redis → DragonflyDB         | 無        | 低             | 低          | 6-section + audit |
| PostgreSQL → Aurora         | 無        | 高             | 低          | hybrid             |
| Datadog → Grafana Stack     | 中        | 中             | 低          | parallel streams   |
| Kafka ↔ NATS（本篇）        | 中        | 中             | **高**      | partial + 混合     |

**結論**：migration 結構由 *最大差異維度* 決定、不是 universal phased playbook。

## 相關連結

- Source / target vendor：[Kafka](/backend/03-message-queue/vendors/kafka/) / [NATS](/backend/03-message-queue/vendors/nats/)
- 平行 vendor：[RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/) / [Redis Streams](/backend/03-message-queue/vendors/redis-streams/)
- 平行 migration playbook：[Splunk → Elastic Security](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/) / [Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/) / [PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/) / [Datadog → Grafana Stack](/backend/04-observability/vendors/datadog/migrate-to-grafana-stack/)
- Methodology：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)
