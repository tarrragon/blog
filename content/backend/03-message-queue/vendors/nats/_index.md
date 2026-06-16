---
title: "NATS"
date: 2026-05-01
description: "Lightweight messaging、JetStream 加持久化與 streams"
weight: 3
tags: ["backend", "message-queue", "vendor"]
---

NATS 是 lightweight high-performance messaging system、承擔三個責任：subject-based routing（hierarchical wildcards）、low-latency messaging（Core NATS、fire-and-forget）、選擇性持久化（JetStream、streams + KV + Object Store）。設計取捨偏向「協議極簡、運維輕、必要時才開持久化」、適合微服務通訊跟 edge 場景。

對「微服務 messaging、IoT/edge、Request/Reply、需要 messaging + KV 一體」這條路徑、NATS 是輕量首選。本頁先給最短路徑、再展開日常 publish / subscribe 與 subject 設計、最後進階治理（JetStream、supercluster、leaf node）跟排錯。

## 本章目標

讀完本章後、你應該能：

1. 用 nats-server 跑起 NATS（含 JetStream）、驗證 broker 健康
2. 用 nats CLI publish / subscribe、看 subject hierarchy 匹配
3. 區分 Core NATS（fire-and-forget）vs JetStream（durable）的選用判讀
4. 看懂 stream 配置、consumer 配置、pending 訊號
5. 評估 supercluster、leaf node、KV / Object Store 等延伸場景

## 最短路徑：5 分鐘把 NATS 跑起來

```bash
# 1. 啟動 NATS server（-js 開 JetStream、-m 8222 開監控埠）
docker run -d --name nats -p 4222:4222 -p 8222:8222 nats:latest -js -m 8222

# 2. 用 nats CLI publish / subscribe（CLI 可用 natsio/nats-box 容器）
#    docker run --rm --network host natsio/nats-box nats <subcommand>
nats --server nats://localhost:4222 pub demo.hello "world"
nats --server nats://localhost:4222 sub "demo.>"   # 另開一個 shell 持續訂閱

# 3. 建 JetStream stream + pull consumer（持久化 + ack）
nats --server nats://localhost:4222 stream add demo --subjects 'demo.>' \
  --storage file --retention limits --discard old --defaults
nats --server nats://localhost:4222 consumer add demo worker \
  --pull --deliver all --ack explicit --filter 'demo.>' --defaults
```

最短路徑驗證「Core NATS + JetStream 都可用」。實際寫程式用 nats client library、見[日常操作](#日常操作與決策形狀)。

## 日常操作與決策形狀

### CLI 與 client API

子議題：

- nats CLI 指令對照表（pub / sub / stream / consumer / kv）
- 監控 endpoint（`/varz` / `/connz` / `/jsz` HTTP）
- Client library 配置：connection / reconnect / timeout / async / sync subscribe
- 對應指令範例：`nats stream info <name>`、`nats consumer info <stream> <consumer>`

### Subject hierarchy 與 wildcard

[Subject](/backend/knowledge-cards/topic/) 是 NATS 路由的核心、層級式設計：

- 層級用 `.` 分隔（例：`orders.created.us-west`）
- 單層 wildcard `*`（匹配一層）
- 多層 wildcard `>`（匹配剩餘所有層）
- Subject 命名規範與 ownership

### Core NATS vs JetStream

子議題：

- Core NATS：fire-and-forget、無持久化、極低延遲、適合即時通知 / 控制信號
- JetStream：append-only stream + durable consumer、適合需要 replay / 持久化的事件流
- 兩者並存設計（同一 NATS server 同時跑）

### Request/Reply 與 Queue groups

子議題：

- Request/Reply pattern（RPC over messaging）
- Queue groups（load balancing、多 subscriber 分擔同 subject）
- Pub/Sub vs Queue groups 的差異

## 進階主題（按需閱讀）

### JetStream stream 設計

子議題：

- Stream 配置（subjects、retention policy、storage type）
- File-based vs Memory-based storage
- MaxMsgs / MaxBytes / MaxAge（保留策略）
- Replicas（JetStream raft、跨節點一致性）

### JetStream consumer 設計

子議題：

- Durable vs ephemeral consumer
- Push vs pull consumer
- Ack 策略（explicit ack / all / none）
- AckWait + MaxDeliver + DeliverPolicy（重試控制）

### Cluster / Supercluster / Leaf node

子議題：

- Cluster：單一 region 多 broker、JetStream raft 同步
- Supercluster：跨 cluster gateway、跨區延展
- Leaf node：邊緣節點、subject mapping、適合 IoT / edge 場景
- 對應 [3.C8 Cloudflare Queues 全球交付](/backend/03-message-queue/cases/cloudflare-queues-global-delivery-model/) 的對照思路

### JetStream KV / Object Store

子議題：

- KV store（基於 JetStream、簡單 key-value）
- Object Store（基於 JetStream、大 blob）
- 何時用 NATS KV vs 真的 KV 服務（Redis / etcd）

### Subject-based ACL 與多租戶

子議題：

- Account 隔離（multi-tenancy 主機制）
- Subject-level permission（publish / subscribe）
- Cross-account import / export

## 排錯快速判讀

### Consumer pending 累積

操作原則：先看 pending 是 ack-pending 還是 stream backlog、再定位 consumer 慢 vs stream 寫入過快。

```bash
nats --server nats://localhost:4222 consumer info <stream> <consumer>
# 看 Unprocessed Messages（stream backlog）與 Redelivered / Acknowledgment Pending（ack-pending）區分兩種累積
```

### Stream 超 retention limit

操作原則：超 MaxBytes / MaxMsgs 時 stream 觸發 discard policy、看是 old discard 還是 new discard。

### Leaf node 連線不穩

操作原則：邊緣節點到 hub 的網路品質決定 subject mapping 延遲、看 reconnect 次數與 latency。

### Subject 路由錯誤

操作原則：wildcard 設計錯導致訂閱不到、或匹配過多。看 subject hierarchy 規範與實際 subject。

### JetStream raft 不一致

操作原則：replica 配置 R3 但只有 2 個健康節點、stream 變 read-only。看 cluster info 與 raft state。

## 何時改走其他服務

| 需求形狀                       | 改走                                                                                                            |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| 高吞吐事件流（百萬 msg/sec）   | [Kafka](/backend/03-message-queue/vendors/kafka/)                                                               |
| 複雜 routing（exchange model） | [RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/)                                                         |
| Managed queue（AWS / GCP）     | [SQS](/backend/03-message-queue/vendors/aws-sqs/) / [Pub/Sub](/backend/03-message-queue/vendors/google-pubsub/) |
| Redis 生態已存在               | [Redis Streams](/backend/03-message-queue/vendors/redis-streams/)                                               |
| 大型企業生態整合               | RabbitMQ / Kafka（社群更大）                                                                                    |
| Managed NATS                   | Synadia Cloud                                                                                                   |

## 不在本頁內的主題

- 各語言 client 完整 API（依官方文件）
- NATS 跟 gRPC 的對比（在分散式通訊章節）
- Synadia Cloud 商業功能

## 案例回寫

### NATS 專屬案例（C34-C41）

| 案例                                                                                            | 主討論議題                                  |
| ----------------------------------------------------------------------------------------------- | ------------------------------------------- |
| [3.C34 Netlify data plane](/backend/03-message-queue/cases/nats-netlify-data-plane-fanout/)     | 全球 metrics / logs fan-out                 |
| [3.C35 Form3 multi-cloud](/backend/03-message-queue/cases/nats-form3-multi-cloud-payments/)     | JetStream Leaf Node 跨雲低延遲支付          |
| [3.C36 Intelecy IoT](/backend/03-message-queue/cases/nats-intelecy-industrial-iot/)             | 工業 IoT / BoltDB → JetStream               |
| [3.C37 MachineMetrics edge](/backend/03-message-queue/cases/nats-machinemetrics-edge-to-cloud/) | Leaf node + KV + Object Store + 多租戶 Auth |
| [3.C38 Clarifai ML](/backend/03-message-queue/cases/nats-clarifai-async-task-queue/)            | NATS Streaming queue group / at-least-once  |
| [3.C39 Choria fleet](/backend/03-message-queue/cases/nats-choria-orchestration-fleet/)          | Request/Reply + Queue group / 50 萬 server  |
| [3.C40 Resgate API gateway](/backend/03-message-queue/cases/nats-resgate-realtime-api-gateway/) | Subject hierarchy 即 schema / Core NATS     |
| [3.C41 i-flow OT/IT](/backend/03-message-queue/cases/nats-iflow-ot-it-integration/)             | 多工廠 leaf node hub-and-spoke              |

### 跨 vendor 對照

| 案例                                                                                               | 對 NATS 的對應                                      |
| -------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| [3.C8 Cloudflare Queues](/backend/03-message-queue/cases/cloudflare-queues-global-delivery-model/) | 全球交付對照：leaf node + supercluster              |
| [3.C10 規模對照](/backend/03-message-queue/cases/contrast-queue-model-by-scale/)                   | 小型 messaging / 中型 JetStream / 大型 supercluster |

## 下一步路由

- 上游概念：[0.3 非同步選型](/backend/00-service-selection/async-delivery-selection/)、[3.1 broker basics](/backend/03-message-queue/broker-basics/)
- 平行 vendor：[Kafka](/backend/03-message-queue/vendors/kafka/)、[RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/)
- 下游能力：[3.4 consumer 設計](/backend/03-message-queue/consumer-design/)、[3.6 processing recovery semantics](/backend/03-message-queue/processing-recovery-semantics/)
