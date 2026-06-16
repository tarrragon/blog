---
title: "RabbitMQ"
date: 2026-05-01
description: "Classic message broker、AMQP routing 為主"
weight: 1
tags: ["backend", "message-queue", "vendor"]
---

RabbitMQ 是 AMQP 協議實作的 classic broker、承擔三個責任：訊息持久化與重試（durable queue + ack/nack）、靈活路由（exchange + routing key + binding）、跨服務任務分派（worker pool + DLQ）。設計取捨偏向「處理即承諾、broker 負責重新投遞、consumer 負責 idempotency」、可靠性建立在 ack 機制而非 replication。

對「任務隊列、worker pool、複雜 routing、RPC over messaging」這條路徑、RabbitMQ 是業界主流。本頁先給最短路徑、再展開日常 publisher / consumer 操作與 exchange 設計、最後進階治理（quorum queue、cluster、federation）跟排錯。

## 本章目標

讀完本章後、你應該能：

1. 用 docker 跑起 RabbitMQ + management UI、驗證 broker 健康
2. 用 CLI / Management API 建 exchange、queue、binding
3. 設計 exchange type（direct / fanout / topic / headers）對齊路由需求
4. 看懂 queue depth、unacked、connection / channel 數量訊號、定位故障層
5. 評估 quorum queue、stream、federation、shovel 等規模化議題

## 最短路徑：5 分鐘把 RabbitMQ 跑起來

```bash
# 1. 啟動 RabbitMQ + management plugin
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management

# 2. 建 exchange / queue / binding（rabbitmqadmin 可重現、Management UI 在 http://localhost:15672、預設 guest/guest）
docker exec rabbitmq rabbitmqadmin declare exchange name=demo.direct type=direct
docker exec rabbitmq rabbitmqadmin declare queue name=demo.q
docker exec rabbitmq rabbitmqadmin declare binding source=demo.direct destination=demo.q routing_key=demo

# 3. 用 rabbitmqctl 驗證 broker 狀態
docker exec rabbitmq rabbitmqctl list_queues
docker exec rabbitmq rabbitmqctl list_exchanges
docker exec rabbitmq rabbitmqctl list_bindings
```

最短路徑驗證「broker 起來、UI 能訪、能 enqueue/dequeue」。實際寫程式用 AMQP client、見[日常操作](#日常操作與決策形狀)。

## 日常操作與決策形狀

### CLI 與 client API

子議題：

- CLI 指令對照表（rabbitmqctl / rabbitmq-diagnostics / rabbitmqadmin）
- Management API 形狀（HTTP API、適合自動化）
- AMQP client 配置：connection / channel / consumer prefetch / publisher confirm
- 對應指令範例：`rabbitmqctl list_queues name messages messages_unacknowledged consumers`

### Exchange types 與 routing 設計

[Exchange](/backend/knowledge-cards/broker/) 承擔訊息分流責任、不同 type 對應不同路由語意。子議題：

- Direct：精準 routing key 匹配（point-to-point）
- Fanout：忽略 routing key、廣播到所有 binding queue
- Topic：層級式 routing key（`*` 單層、`#` 多層萬用字元）
- Headers：依 message header 路由（少用）
- 對應指令：宣告 exchange / queue / binding 的 CLI 與 client 範例

### Queue 設計與 ack/nack 策略

[Ack/nack](/backend/knowledge-cards/ack-nack/) 是 RabbitMQ 的 delivery 控制點。子議題：

- Durable queue vs transient queue
- Manual ack vs auto ack（後者等同 at-most-once）
- Prefetch 設定（[backpressure](/backend/knowledge-cards/backpressure/) + 併發控制）
- [Dead-letter exchange](/backend/knowledge-cards/dead-letter-queue/)（DLX）配置
- Message TTL 與 queue length limit

## 進階主題（按需閱讀）

本段主題已展開為 deep article：[classic vs quorum vs stream 選型](queue-types-classic-quorum-stream/)、[network partition 與 cluster 一致性](network-partition-clustering/)、[DLQ retry escalation](dlq-retry-escalation/)。下列子議題段保留選題判讀入口。

### Classic queue vs Quorum queue vs Stream

子議題：

- Classic queue：原生持久化 queue、mirrored queue 已 deprecated
- Quorum queue：Raft-based、取代 mirrored、跨節點一致性
- Stream（3.9+）：append-only log、log-based 模型、類似 Kafka 但仍是 RabbitMQ 體系
- 三種模型的選擇判讀（throughput、retention、replay 需求）

### Federation 與 Shovel

子議題：

- Federation：upstream / downstream broker 鏈接、適合鬆耦合跨資料中心
- Shovel：點對點轉發、適合單純訊息搬運
- 跨區 / 多 cluster 場景的選擇

### Erlang clustering 與 network partition

子議題：

- Cluster 拓樸（disc node、ram node）
- `cluster_partition_handling` 策略（ignore、autoheal、pause_minority）
- 腦裂偵測與處理

### 多 vhost / 多租戶

子議題：

- Vhost 隔離（namespace、ACL、user permission）
- User / Role / Permission 設計
- Per-vhost resource limit（max connection、max queue）

### Prefetch 與 consumer 併發控制

子議題：

- Prefetch count 對 throughput / fairness 的影響
- Channel-level vs Consumer-level prefetch
- 配合 [retry budget](/backend/knowledge-cards/retry-budget/) 控制重試壓力

### RabbitMQ Cluster Operator（K8s）

子議題：

- Cluster Operator vs 自管 StatefulSet
- 持久化卷（PVC）與資料保護
- 升級流程（rolling restart 與資料完整性）

### Plugin 機制與多協議

子議題：

- MQTT plugin（IoT 場景、橋接 device-to-broker）
- STOMP plugin
- 對應 [3.1 broker basics 的 QoS / ACK 機制橋接](/backend/03-message-queue/broker-basics/#語意保證的不同實作機制)

## 排錯快速判讀

### Queue 堆積（messages 增加、unacked 不收斂）

操作原則：先看 consumer 是否存在、再看 ack 速率 vs publish 速率、最後看 prefetch / poison message。

```bash
rabbitmqctl list_queues name messages messages_unacknowledged consumers
```

判讀路徑：無 consumer（client crash）→ consumer 慢（下游卡）→ poison message 卡住（看單一 message redelivery 次數）。

### Connection / Channel limit

操作原則：client 設計不當會用滿 connection / channel，看每個 connection 的 channel 數。

```bash
rabbitmqctl list_connections
rabbitmqctl list_channels
```

### Disk alarm 觸發

操作原則：disk 低於 `disk_free_limit`、broker 暫停 publisher。判讀：保留期太長 / 訊息大小 / 未消費 queue 過大。

### Memory alarm 觸發

操作原則：記憶體超過 watermark、broker 觸發 [paging](/backend/knowledge-cards/buffer/)、publisher 變慢。判讀路徑：訊息累積、consumer 失聯、queue 設定錯誤。

### Network partition（腦裂）

操作原則：cluster 節點互相不可達、看 `cluster_partition_handling` 與 partition log。對應 [3.C9 語義誤配](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/) 思路。

## 何時改走其他服務

| 需求形狀                     | 改走                                                                |
| ---------------------------- | ------------------------------------------------------------------- |
| 高吞吐事件流、長期 replay    | [Kafka](/backend/03-message-queue/vendors/kafka/)                   |
| Managed queue（AWS 生態）    | [AWS SQS](/backend/03-message-queue/vendors/aws-sqs/)               |
| Managed pub/sub（GCP 生態）  | [Google Pub/Sub](/backend/03-message-queue/vendors/google-pubsub/)  |
| 輕量 messaging + 微服務      | [NATS](/backend/03-message-queue/vendors/nats/)                     |
| Redis 生態 stream            | [Redis Streams](/backend/03-message-queue/vendors/redis-streams/)   |
| IoT device 接入              | EMQX / HiveMQ / Mosquitto（MQTT broker、或用 RabbitMQ MQTT plugin） |
| Workflow + durable execution | Temporal（T4 候選）                                                 |

## 不在本頁內的主題

- 各語言 AMQP client 完整 API（依官方文件）
- 所有 plugin 細節（只列主流 plugin）
- RabbitMQ Streams 跟 Kafka 的詳細對照（見 [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/)）

## 案例回寫

### RabbitMQ 專屬案例（C23-C33）

| 案例                                                                                                                 | 主討論議題                                  |
| -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| [3.C23 Bloomberg vhost 多租戶](/backend/03-message-queue/cases/rabbitmq-bloomberg-multi-tenant-vhost/)               | 多 vhost + 自助平台化                       |
| [3.C24 SoundCloud fan-out](/backend/03-message-queue/cases/rabbitmq-soundcloud-fanout-audio/)                        | 音訊處理 pipeline 分隊列                    |
| [3.C25 Indeed Delay + DLQ](/backend/03-message-queue/cases/rabbitmq-indeed-delay-dlq-escalation/)                    | 三層 retry escalation                       |
| [3.C26 GoCardless Hutch](/backend/03-message-queue/cases/rabbitmq-gocardless-hutch-service-mesh/)                    | 單一 topic exchange 服務 mesh               |
| [3.C27 Zalando AWS](/backend/03-message-queue/cases/rabbitmq-zalando-aws-master-selection/)                          | 雲端自動 master selection / federation 升級 |
| [3.C28 WeWork hash ordering](/backend/03-message-queue/cases/rabbitmq-wework-consistent-hash-ordering/)              | Consistent hash exchange / per-key ordering |
| [3.C29 WeWork Bunny channel pool](/backend/03-message-queue/cases/rabbitmq-wework-bunny-channel-pool/)               | AMQP channel 不可跨執行緒                   |
| [3.C30 Runtastic mirrored bottleneck](/backend/03-message-queue/cases/rabbitmq-runtastic-mirrored-queue-bottleneck/) | Mirrored queue 網路成本                     |
| [3.C31 Mozilla Pulse](/backend/03-message-queue/cases/rabbitmq-mozilla-pulse-naming-isolation/)                      | ACL + naming 取代 vhost（反向）             |
| [3.C32 LoyaltyLion monitoring](/backend/03-message-queue/cases/rabbitmq-loyaltylion-monitoring-thousands/)           | 大規模 queue topology 監控                  |
| [3.C33 Wargaming game portal](/backend/03-message-queue/cases/rabbitmq-wargaming-game-portal-decoupling/)            | 異步解耦 game server / portal               |

### 跨 vendor 對照

| 案例                                                                                             | 對 RabbitMQ 的對應                             |
| ------------------------------------------------------------------------------------------------ | ---------------------------------------------- |
| [3.C9 反例：語義誤配](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/) | manual ack + DLX + idempotency 三層責任邊界    |
| [3.C10 規模對照](/backend/03-message-queue/cases/contrast-queue-model-by-scale/)                 | 小型直接用 / 中型補 idempotency / 大型分 vhost |

**MQTT plugin + Cluster Operator 缺直接 customer case**：可補 RabbitMQ 官方 native MQTT blog 跟 K8s Operator docs、後續若有 customer 案例可加。

## 下一步路由

- 上游概念：[0.3 非同步選型](/backend/00-service-selection/async-delivery-selection/)、[3.1 broker basics](/backend/03-message-queue/broker-basics/)
- 平行 vendor：[Kafka](/backend/03-message-queue/vendors/kafka/)、[NATS](/backend/03-message-queue/vendors/nats/)
- 下游能力：[3.2 durable queue](/backend/03-message-queue/durable-queue/)、[3.4 consumer 設計](/backend/03-message-queue/consumer-design/)
