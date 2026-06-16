---
title: "Redis Streams"
date: 2026-05-01
description: "Redis 生態內的 streams、append-only log + consumer group"
weight: 4
tags: ["backend", "message-queue", "vendor"]
---

Redis Streams 是 Redis 5.0 引入的 append-only log data type、承擔三個責任：輕量 event stream（XADD / XREAD）、consumer group 與 pending entries list（XREADGROUP / XACK）、Redis 生態內整合（避免額外引入 Kafka）。設計取捨偏向「跟 Redis 本體生命週期綁定、低延遲 + 記憶體成本、適合中等規模」。Redis vendor 細節見 [02 redis](/backend/02-cache-redis/vendors/redis/)。

對「已用 Redis、需要輕量 stream、不想引入額外基礎設施」這條路徑、Redis Streams 是務實選擇。本頁先給最短路徑、再展開日常 XADD/XREAD 操作與 consumer group 設計、最後進階治理（PEL、retention、Cluster 影響）跟排錯。

## 本章目標

讀完本章後、你應該能：

1. 用 redis-cli XADD / XREAD 操作 stream
2. 設計 consumer group + XCLAIM 處理 consumer 失敗的訊息接管
3. 看懂 pending entries list（PEL）累積訊號、定位 consumer 健康
4. 設計 MAXLEN / MINID retention 對齊記憶體預算
5. 評估 Redis Cluster 對 Streams 的影響與限制

## 最短路徑：5 分鐘把 Redis Streams 跑起來

```bash
# 1. 啟動 Redis（已有 Redis 跳過）
docker run -d --name redis -p 6379:6379 redis:7

# 2. XADD 寫入 stream（'*' 由 Redis 產生遞增 entry ID）
docker exec redis redis-cli XADD mystream '*' field1 value1

# 3. XREAD 讀取（從 0 起讀、最多 10 筆）
docker exec redis redis-cli XREAD COUNT 10 STREAMS mystream 0

# 4. 建 consumer group 後用 group 模式讀（'>' 取未投遞訊息、進 PEL 等 ack）
docker exec redis redis-cli XGROUP CREATE mystream mygroup 0
docker exec redis redis-cli XREADGROUP GROUP mygroup consumer1 COUNT 10 STREAMS mystream '>'
```

最短路徑驗證「Redis 起來、stream 能寫能讀」。實際用 consumer group 場景見[日常操作](#日常操作與決策形狀)。

## 日常操作與決策形狀

### XADD / XREAD / XREADGROUP

子議題：

- XADD：寫入 entry、`*` 自動 ID vs 手動 ID
- XREAD：簡單讀取（無 consumer group、適合單 consumer）
- XREADGROUP：consumer group 模式、配合 ACK
- 對應指令範例：`XADD`、`XREAD`、`XREADGROUP`、`XACK`、`XPENDING`

### Consumer group 與 PEL

[Consumer group](/backend/knowledge-cards/consumer-group/) 是 Streams 的核心抽象、配合 Pending Entries List（PEL）追蹤未 ack 訊息。子議題：

- XGROUP CREATE / SETID / DESTROY
- XACK：明確 ack
- XPENDING：查 PEL 狀態
- XCLAIM / XAUTOCLAIM：consumer 失敗時接管訊息

### Retention：MAXLEN / MINID

子議題：

- MAXLEN：保留最近 N 個 entry（近似或精確）
- MINID：保留 ID 大於某值的 entry
- XADD 寫入時帶 MAXLEN（最常用）
- XTRIM 手動修剪

## 進階主題（按需閱讀）

PEL 失敗接管、retention 與 cluster 影響已展開為 deep article：[XCLAIM/PEL 失敗接管與 cluster 影響](xclaim-pel-recovery/)。下列子議題段保留選題判讀入口。

### XCLAIM 與 consumer 失敗接管

子議題：

- Idle time 判讀（min-idle-time 參數）
- XAUTOCLAIM（Redis 6.2+、自動接管）
- 接管後的去重責任（仍需 [idempotency](/backend/knowledge-cards/idempotency/)）

### Memory 與 retention 取捨

子議題：

- Stream 佔用 Redis 記憶體、MAXLEN 是主要旋鈕
- 近似修剪（`~` 標記）vs 精確修剪的性能差異
- 配合 `maxmemory-policy` 與 eviction（注意 stream 不會被 eviction）

### Redis Cluster 對 Streams 的影響

子議題：

- Stream key 只在單一 shard（無 partition 概念）
- 多 stream 跨 shard 的設計（用 hash tag 控制分布）
- Cluster failover 對 PEL 一致性的影響

### Stream + Functions（Redis 7+）

子議題：

- Redis Functions（取代 Lua scripting）
- Stream 處理寫成 Redis-side function
- 適用 / 不適用場景

### Redis Sentinel / Cluster 對可靠性的影響

子議題：

- Replication lag 對 Streams 一致性的影響
- AOF 與 RDB 對 Stream 持久化的差異
- Failover 期間 PEL 是否完整

## 排錯快速判讀

### PEL 累積（XPENDING 數字持續增長）

操作原則：先看是單一 consumer 還是整 group 都累積、再定位 consumer 失敗 vs ACK 漏寫。

```bash
redis-cli XPENDING mystream mygroup
# 回傳 PEL 總數 + 每個 consumer 的待 ack 數、定位累積集中在哪個 consumer
```

判讀路徑：consumer crash 沒 ACK → consumer 慢 → ACK 程式碼漏寫。

### Memory pressure（stream 佔用過大）

操作原則：MAXLEN 沒設或設太大、stream 持續增長。判讀：用 `MEMORY USAGE` 看 stream 佔用、調整 MAXLEN。

### 跨 shard stream 限制

操作原則：Streams 不支援 partition、單 stream 受單 shard 容量限制。設計：用 hash tag 強制分散到多 stream。

### Consumer 重平衡（無原生機制）

操作原則：consumer group 沒有自動 rebalance、要手動 XCLAIM 接管。看 idle time 與 XPENDING 判斷該接管哪些。

### Failover 後 PEL 不一致

操作原則：Sentinel / Cluster failover 後、replica 升 primary、PEL 可能不完整。對應 [3.C9 語義誤配](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/) 的思路。

## 何時改走其他服務

| 需求形狀                                 | 改走                                                                                                            |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| 高吞吐 / 長期 retention                  | [Kafka](/backend/03-message-queue/vendors/kafka/)                                                               |
| 複雜 routing                             | [RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/)                                                         |
| 跨節點 stream（partition + replication） | [Kafka](/backend/03-message-queue/vendors/kafka/) / Pulsar                                                      |
| 輕量 messaging（不需 Redis）             | [NATS](/backend/03-message-queue/vendors/nats/)                                                                 |
| Managed queue                            | [SQS](/backend/03-message-queue/vendors/aws-sqs/) / [Pub/Sub](/backend/03-message-queue/vendors/google-pubsub/) |
| Redis Pub/Sub（fire-and-forget）         | Redis Pub/Sub（同 Redis、不持久化）                                                                             |

## 不在本頁內的主題

- Redis 本體運維（見 [02 cache 模組 redis vendor](/backend/02-cache-redis/vendors/redis/)）
- 各語言 Redis client 完整 API
- Redis Pub/Sub 細節（不是 Streams、語意不同）

## 案例回寫

### Redis Streams 專屬案例（C42-C47）

| 案例                                                                                                        | 主討論議題                                     |
| ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| [3.C42 Bitso Reliable Streams](/backend/03-message-queue/cases/redis-streams-bitso-reliable-streams/)       | 自建抽象層 + DLQ + idempotency                 |
| [3.C43 Arcjet 取代 Kafka](/backend/03-message-queue/cases/redis-streams-arcjet-replace-kafka/)              | Janitor 自寫 retention / 6 位數 → $1k          |
| [3.C44 Harness event-driven](/backend/03-message-queue/cases/redis-streams-harness-event-driven-state/)     | XAUTOCLAIM head-of-line / 監控缺口             |
| [3.C45 Klaxit Rust + Logplex](/backend/03-message-queue/cases/redis-streams-klaxit-rust-log-pipeline/)      | High-throughput log ingestion / consumer group |
| [3.C46 Learning.com 退場](/backend/03-message-queue/cases/redis-streams-learning-com-event-source-retreat/) | （反例）長期事件儲存壓垮 Redis                 |
| [3.C47 PHP + S3 hybrid](/backend/03-message-queue/cases/redis-streams-mateusz-php-microservices/)           | Payload 大小限制 / hybrid storage              |

### 跨 vendor 對照

| 案例                                                                                   | 對 Redis Streams 的對應                        |
| -------------------------------------------------------------------------------------- | ---------------------------------------------- |
| [3.C5 Slack Kafka+Redis](/backend/03-message-queue/cases/slack-job-queue-kafka-redis/) | 多 broker 組合：Kafka 處理量、Redis 處理即時性 |
| [3.C10 規模對照](/backend/03-message-queue/cases/contrast-queue-model-by-scale/)       | 中等規模 / Redis 生態內 / 不跨 shard           |

**Stream + Functions / Redis Cluster on Streams 缺直接 customer case**：公開資料多在 single-instance / Sentinel 規模、Cluster 跟 Functions 案例稀薄、撰寫該段時要明示。

## 下一步路由

- 上游概念：[0.3 非同步選型](/backend/00-service-selection/async-delivery-selection/)、[3.1 broker basics](/backend/03-message-queue/broker-basics/)
- Redis 本體：[02 cache 模組](/backend/02-cache-redis/)
- 平行 vendor：[Kafka](/backend/03-message-queue/vendors/kafka/)、[NATS](/backend/03-message-queue/vendors/nats/)
- 下游能力：[3.4 consumer 設計](/backend/03-message-queue/consumer-design/)
