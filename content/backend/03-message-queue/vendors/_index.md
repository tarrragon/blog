---
title: "訊息佇列 Vendor 清單"
date: 2026-05-01
description: "規劃 broker、event streaming 與 managed queue 的服務頁撰寫順序與判準"
weight: 90
tags: ["backend", "message-queue", "vendor"]
---

訊息佇列 Vendor 清單的核心責任是把 broker 名稱放回 delivery semantics、processing semantics、replay boundary 與操作治理的判斷。每個服務頁先回答它提供哪種投遞與消費模型，再討論 ordering、retention、consumer group、DLQ、managed 邊界與案例回寫。選 broker 之前、佇列這塊能力先過一次買 vs 建：自管 broker（RabbitMQ、Kafka）自己扛 ordering、retention、DLQ 的運維、managed（SQS、SNS、MSK、Confluent Cloud）把這層交出去、雲端原生事件匯流更省 — 逐能力的判讀見 [0.22 能力級買 vs 建](/backend/00-service-selection/capability-buy-vs-build/)。

## 讀法

佇列服務要從處理語意進入。讀者如果要處理一般工作佇列，先回到 [3.2 durable queue](/backend/03-message-queue/durable-queue/)；如果要處理事件流與 replay，先回到 [3.4 consumer design](/backend/03-message-queue/consumer-design/)；如果問題是資料庫交易與事件發布一致性，先回到 [3.3 outbox pattern](/backend/03-message-queue/outbox-pattern/)。

## 教學順序同步

佇列服務頁的教學順序是先建立 work queue baseline，再進入 event log、managed delivery、lightweight messaging 與 embedded stream。這個順序對齊 checkout E3：讀者先理解 delivery、processing、recovery 三層語意，再比較 broker、managed queue、pub/sub 與 stream 如何影響 retry、DLQ、ordering 與 replay。

## T1 服務頁大綱

| 服務                                                                     | 類型               | 頁面要回答的核心問題                                                 |
| ------------------------------------------------------------------------ | ------------------ | -------------------------------------------------------------------- |
| [RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/)                  | Classic broker     | exchange、routing、ack/nack 與 DLQ 如何支援工作分派                  |
| [Apache Kafka](/backend/03-message-queue/vendors/kafka/)                 | Event streaming    | partition、offset、retention 與 replay 如何支援事件流                |
| [NATS](/backend/03-message-queue/vendors/nats/)                          | Messaging / stream | subject、JetStream、low-latency 與 durability 如何取捨               |
| [Redis Streams](/backend/03-message-queue/vendors/redis-streams/)        | Embedded stream    | Redis 生態中的 stream、consumer group 與 pending entry 邊界          |
| [AWS SQS](/backend/03-message-queue/vendors/aws-sqs/)                    | Managed queue      | standard / FIFO、visibility timeout 與 DLQ 如何支援 managed delivery |
| [Google Cloud Pub/Sub](/backend/03-message-queue/vendors/google-pubsub/) | Managed pub/sub    | topic / subscription、push / pull 與 global delivery 如何取捨        |

## 內容覆蓋進度

每個 vendor 服務頁下會擴充兩類文章：deep article（vendor 自身的配置、故障、容量、走 [6-section 模板](/posts/vendor-deep-article-methodology/)）跟 migration playbook（跨 vendor 遷移流程、走 [6-type 結構](/posts/migration-playbook-methodology/)）。「→ X」代表遷移到 X 的 playbook、「↔ X」代表雙向遷移、其他形式代表 same-vendor 的 topology / version / config 變動。

<!-- TODO(merge): main 與 feat/backend_03 worktree 並行開發 03。feat/backend_03 深化 6 個 vendor 的 per-vendor _index.md overview；main（本表 + RabbitMQ deep article）寫 deep article。合併時須對齊本覆蓋表、並確認 deep article 與對方 overview 深化無重複。 -->

| Vendor                          | Deep article                                                                                                            | Migration playbook                                                     |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| [Kafka](kafka/)                 | —                                                                                                                       | [↔ NATS](kafka/migrate-from-to-nats/) / [→ MSK](kafka/migrate-to-msk/) |
| [RabbitMQ](rabbitmq/)           | [dlq-retry-escalation](rabbitmq/dlq-retry-escalation/) / [quorum-vs-mirrored-queue](rabbitmq/quorum-vs-mirrored-queue/) | —                                                                      |
| [NATS](nats/)                   | [jetstream-durability-consumer](nats/jetstream-durability-consumer/)                                                    | —                                                                      |
| [Redis Streams](redis-streams/) | [consumer-group-pel-recovery](redis-streams/consumer-group-pel-recovery/)                                               | —                                                                      |

其他 T1 vendor（AWS SQS / Google Pub/Sub）的 deep article 尚未開始（兩者為 managed SaaS、本機無法 docker 驗證、待以官方文件 + case 補）。對應的 backlog 議題見上方「T1 服務頁大綱」段每個服務頁要回答的核心問題、跟各 vendor `_index.md` 的「預計實作話題」段。

## 服務頁撰寫欄位

| 欄位     | 佇列服務頁要保留的問題                                                             |
| -------- | ---------------------------------------------------------------------------------- |
| 服務責任 | 它承擔 work queue、event log、pub/sub、stream 還是 workflow handoff                |
| 適用壓力 | throughput、ordering、fan-out、retention、replay、managed operation 哪個壓力最明顯 |
| 替代邊界 | broker、event streaming、managed queue、workflow engine 的機會成本                 |
| 操作成本 | partition、consumer lag、DLQ drain、schema、ACL、upgrade、quota                    |
| Evidence | publish rate、consume rate、lag、redelivery、DLQ depth、replay window              |
| 案例回寫 | Meta FOQS、VMware MSK、LinkedIn TopicGC 如何提供治理判準                           |

服務責任段要先分辨投遞成功與處理成功。Broker 可以保存訊息與重新投遞，但 consumer 的 idempotency、side effect、checkpoint 與補償流程才決定業務結果是否可恢復。

適用壓力段要保留副作用語言。寄信、轉檔、invoice、search index sync、webhook fan-out 與 audit event 的 retry、ordering、DLQ 與 replay 條件不同，服務頁要分別展開。

## 服務頁標準章節

| 章節                 | 佇列服務頁要補的內容                                                      |
| -------------------- | ------------------------------------------------------------------------- |
| 服務定位             | 它是 work queue、event log、pub/sub、embedded stream 還是 workflow engine |
| 本章目標             | 讀者能判斷 delivery、processing、recovery、ordering 與 replay 邊界        |
| 最短判讀路徑         | 用「是否需要 durable retry、fan-out、ordering、replay」快速定位工具類型   |
| 日常操作與決策形狀   | ack/nack、visibility timeout、DLQ、consumer group、schema、quota          |
| 核心取捨表           | RabbitMQ、Kafka、SQS、Pub/Sub、NATS、Redis Streams 的機會成本             |
| 進階主題             | partition、retention、exactly-once claims、multi-region、managed quota    |
| 排錯與失敗快速判讀   | lag、redelivery、DLQ depth、poison message、consumer pause、offset        |
| 何時改走其他服務     | human workflow 轉 workflow engine、同步查詢回 API、正式狀態回 database    |
| 不在本頁內的主題     | 完整 client API、framework adapter、所有 broker plugin                    |
| 案例回寫與下一步路由 | 回到 3.C cases、6.12 replay verification、8.19 decision log               |

## 跨 vendor 議題對照

橫向議題在不同 vendor 用不同旋鈕達成。本表把同一議題在 6 個 vendor 的對應位置列出、確保大綱不缺漏議題、且讀者跨 vendor 查找對照位置時有索引。

| 議題               | Kafka                    | RabbitMQ                   | NATS                            | Redis Streams               | AWS SQS                  | Pub/Sub                 |
| ------------------ | ------------------------ | -------------------------- | ------------------------------- | --------------------------- | ------------------------ | ----------------------- |
| 多租戶配額 / 隔離  | quota + ACL              | vhost + user permission    | account + subject ACL           | Redis ACL                   | IAM policy               | IAM + Service Account   |
| 跨區 / 全球交付    | MirrorMaker 2            | Federation / Shovel        | Supercluster + Leaf node        | Redis Cluster（受限）       | Cross-region replication | 內建 global routing     |
| Topic 生命週期治理 | TopicGC、auto-cleanup    | vhost / queue lifecycle    | Stream lifecycle                | MAXLEN / XTRIM              | DLQ + redrive policy     | Subscription expiration |
| 自動修復           | Self-healing automation  | cluster_partition_handling | JetStream raft                  | Sentinel / Cluster failover | managed 內建             | managed 內建            |
| Delivery 機制      | acks + idempotence + ISR | manual ack + DLX           | JetStream ack + AckWait         | XACK + XCLAIM + PEL         | visibility timeout + DLQ | ack deadline + DLT      |
| 路由模型           | partition + key          | exchange + routing key     | subject + wildcard              | stream key（無 partition）  | queue URL                | topic + subscription    |
| 持久化模型         | log + retention policy   | durable queue + TTL        | JetStream storage               | append-only log（RAM）      | managed durable          | managed durable         |
| Schema 治理        | Schema Registry          | （無原生）                 | （無原生、靠 JSON Schema 慣例） | （無）                      | （無）                   | Schema enforcement      |
| 主討論案例         | C1/C3-C7 + C11-C22       | C23-C33                    | C34-C41                         | C42-C47                     | C48-C59 + C2 反面        | C60-C69                 |

對照表的用途有三：

- 寫某 vendor 頁時、檢查橫向議題是否都有對應的進階主題子段、避免缺漏
- 讀者在 vendor 間遷移時、知道對應旋鈕在另一個 vendor 叫什麼
- 未來擴充案例時、依 [cases/_index 的「案例覆蓋缺口」段](/backend/03-message-queue/cases/) 判定優先補的章節

下面 8 段把對照表的每行展開、避免單純的表格成為「終點」。每段先解釋議題本質、再展開不同 vendor 的 mechanism 差異、最後給選型判讀。

### 路由模型

路由模型決定「訊息怎麼送到對的 consumer」、不是同概念換名字。**Kafka** partition + key 透過 hash 把訊息落在固定 partition、consumer group 靠 rebalance 綁定 partition 跟 consumer；**RabbitMQ** exchange + routing key 透過 binding rule 比對、可 broadcast（fanout）/ 精準（direct）/ pattern（topic + `*` 單層 / `#` 多層）；**NATS** subject + wildcard（`*` 單層、`>` 多層）讓 subscriber 用 pattern 訂閱主題層級；**Redis Streams** 是單一 stream key、無 partition、跨 shard 要靠 hash tag 強制分散；**SQS** queue URL 直接對應、無 routing 邏輯；**Pub/Sub** topic + subscription、subscription 是 first-class entity（跟 Kafka topic + consumer group 不同）。

選型判讀：需要 fan-out 多 subscriber → fanout exchange / subject pattern / multi-subscription；需要 per-key ordering → Kafka partition+key / RabbitMQ consistent hash exchange / NATS queue group；不需 routing 邏輯 → SQS 最簡單。

### Delivery 機制

Delivery 機制是「broker 怎麼保證訊息被處理」、不同 vendor 用不同協議層級達成同語意。詳見 [3.1 broker-basics 的「語意保證的不同實作機制」](/backend/03-message-queue/broker-basics/#語意保證的不同實作機制)。三層核心旋鈕：**Kafka** acks（0/1/all）+ idempotence + ISR（min.insync.replicas）；**RabbitMQ** manual ack + DLX + prefetch；**NATS** JetStream ack + AckWait + MaxDeliver；**Redis Streams** XACK + XCLAIM + PEL；**SQS** visibility timeout + DLQ + maxReceiveCount；**Pub/Sub** ack deadline + DLT + ack extension。

選型判讀：寫入即承諾（事件流）→ Kafka acks=all + ISR；處理即承諾（任務隊列）→ RabbitMQ manual ack / SQS visibility timeout / Pub/Sub ack deadline；wire-level handshake（device 端）→ MQTT QoS（透過 RabbitMQ MQTT plugin 或 EMQX）。

### 持久化模型

持久化模型決定「訊息能保留多久、能不能 replay」。**Kafka** log + retention policy（time / size、compact / delete）— 訊息保留到 retention 過期、consumer 可任意 offset replay；**RabbitMQ** durable queue + TTL — 訊息持久化但 ack 後即刪、不能 replay；**NATS** JetStream storage（file / memory、配 MaxMsgs / MaxBytes / MaxAge）— 介於 log 跟 queue 之間；**Redis Streams** append-only log 但受 RAM 限制 — retention 短期、replay 視 MAXLEN 設定；**SQS / Pub/Sub** managed durable — SQS 最長 14 天、Pub/Sub 7 天、不適合長期 archive。

選型判讀：需要事件 replay（多 consumer 各自進度、長期保留）→ Kafka / Pulsar / JetStream；任務處理即刪（worker pool）→ RabbitMQ / SQS / Pub/Sub；中期 stream 但已在 Redis 生態 → Redis Streams + MAXLEN。

### Topic 生命週期治理

當 topic / queue 數量上萬、metadata 本身變成 broker 壓力。**Kafka** 早期靠人工管 topic、規模化後需 TopicGC（自動清理 unused topic）+ partition 數量上限；**RabbitMQ** vhost / queue lifecycle 通常手動、queue auto-delete + TTL 是常見 pattern；**NATS** JetStream stream 有 lifecycle policy（DiscardPolicy / MaxAge）；**Redis Streams** MAXLEN / XTRIM 手動修剪、無自動 GC；**SQS** DLQ + redrive policy 是 lifecycle 核心、queue 本身不自動刪；**Pub/Sub** subscription expiration policy（閒置 N 天自動刪）。

選型判讀：metadata 量大（topic 數 / partition 數）→ 需 Kafka TopicGC 模式；任務隊列 → 需 DLQ + redrive 規範；長期 stream → 需明示 retention policy。

### 自動修復

自動修復把 SRE 從人工值班轉到自動化、但層次不同。**Kafka** Self-healing（disk full / broker offline / under-replicated partition 自動處理）；**RabbitMQ** cluster_partition_handling（ignore / autoheal / pause_minority）— 偏向「腦裂處理策略」、不是全自動 SRE；**NATS** JetStream raft 自動 leader election + replica sync；**Redis Streams** 靠 Sentinel / Cluster failover、failover 期間 PEL 可能不一致；**SQS / Pub/Sub** managed 內建、不需用戶管。

選型判讀：自管要 24/7 → Kafka self-healing 或 NATS raft；不要值班 → managed（SQS / Pub/Sub）；中等規模容忍人工 → RabbitMQ cluster_partition_handling。

### 多租戶配額 / 隔離

隔離粒度跟 mechanism 不同。**Kafka** quota（byte rate / request rate）+ ACL（principal / resource / operation）— 流量級 + identity 級；**RabbitMQ** vhost + user permission — namespace 級隔離（最強）；**NATS** account + subject ACL — account 是 namespace、subject ACL 是細粒度權限；**Redis Streams** Redis ACL — command-level 權限；**SQS / Pub/Sub** IAM policy + Service Account — identity 級、無 namespace 概念。

選型判讀：跨 team 共用 cluster → 需 namespace 隔離（vhost / account）；多 client app → identity 隔離（IAM）；流量公平 → 需 quota（Kafka quota / 自建 rate limit）。

### 跨區 / 全球交付

跨區拓樸三類：mesh（broker 自己同步）vs hub-spoke（單向轉發）vs managed global。**Kafka** MirrorMaker 2 是 mesh（active-active / active-passive）；**RabbitMQ** Federation 是 hub-spoke（upstream → downstream 鬆耦合）、Shovel 是點對點搬運；**NATS** Supercluster + Leaf node 是 mesh + edge（適合 IoT 廠區）；**Redis Cluster** 跨區受限（Cluster 是 shard、不是 region）；**SQS** Cross-region replication（managed）；**Pub/Sub** 內建 global routing — 無需設定。

選型判讀：自管要 mesh → MirrorMaker 2 / NATS Supercluster；hub-spoke 簡單 → Federation；不想處理跨區 → Pub/Sub global 或 SQS replication。

### Schema 治理

Schema 強制度跨 vendor 差異最大。**Kafka** Schema Registry（Confluent / Apicurio）+ Avro / Protobuf — 強制 producer 帶 schema ID、enforce compatibility；**RabbitMQ** 無原生 schema 機制 — 靠 application 層約定；**NATS** 無原生、靠 JSON Schema 慣例；**Redis Streams** 無 schema 概念；**SQS** message attribute + body string — 無 enforce；**Pub/Sub** Schema enforcement（topic 綁 Avro / Protobuf schema）。

選型判讀：跨服務契約嚴 → Kafka + Schema Registry / Pub/Sub Schema enforcement；內部簡單通訊 → RabbitMQ / NATS 靠慣例；schema 演進頻繁 → 需 forward / backward / full compatibility 規範。

## 服務頁大綱對齊

6 個 vendor 頁套同樣的章節結構、方便讀者跨 vendor 跳讀。對齊參考 [LLM 模組 1.0 Ollama](/llm/01-local-llm-services/ollama/) 的「觀念 → 原理 → 操作指令」分層寫法：

1. **服務定位**（段首段、3 個責任 + 設計取捨）
2. **本章目標**（5 條可驗證能力 checklist）
3. **最短路徑**（5 分鐘可跑通的 install + verify、bash 範例 placeholder）
4. **日常操作與決策形狀**（CLI / API、路由設計、ack 策略三個子段）
5. **進階主題**（按需閱讀、每子段對應一個 case 或 vendor 專長議題）
6. **排錯快速判讀**（每情境：操作原則 + 指令 + 解法）
7. **何時改走其他服務**（對照表）
8. **不在本頁內的主題**（明確邊界）
9. **案例回寫**（cases/ 引用 + 主討論議題）
10. **下一步路由**（上游概念 / 平行 vendor / 下游能力）

每個章節「要回答的問題」「要包含的指令範例 placeholder」「對應 case」都已寫在各 vendor 頁的大綱、但未寫實際正文 — 等到撰寫批次（見下節）開始時才展開。

## 撰寫批次

| 批次 | 服務頁                      | 撰寫目的                                                          |
| ---- | --------------------------- | ----------------------------------------------------------------- |
| Q1   | RabbitMQ                    | 建立 work queue、routing、ack/nack 與 DLQ baseline                |
| Q2   | Kafka                       | 建立 event log、partition、retention 與 replay 判準               |
| Q3   | AWS SQS / Google Pub/Sub    | 建立 managed delivery、visibility timeout 與 cloud pub/sub 邊界   |
| Q4   | NATS / Redis Streams        | 建立 lightweight messaging 與 embedded stream 的邊界              |
| Q5   | Pulsar / Kinesis / Temporal | 補 multi-tenant streaming、managed stream 與 workflow engine 對照 |

## 後續候選

| 類型              | 候選服務                                                    | 寫作重點                                                        |
| ----------------- | ----------------------------------------------------------- | --------------------------------------------------------------- |
| Streaming         | Apache Pulsar、Redpanda、AWS Kinesis、Confluent Cloud / MSK | retention、partition、managed Kafka、serverless stream          |
| Managed event bus | AWS SNS、EventBridge、Azure Event Grid                      | fan-out、event routing、schema、cloud-native integration        |
| Enterprise queue  | Azure Service Bus、ActiveMQ、IBM MQ                         | enterprise integration、session、routing、DLQ                   |
| Workflow engine   | Temporal、Cadence                                           | durable workflow、activity retry、human / machine workflow 邊界 |
| Lightweight       | NSQ、ZeroMQ                                                 | simple broker、library messaging、durability trade-off          |
| IoT messaging     | MQTT、EMQX、HiveMQ、Mosquitto                               | device connection、QoS、topic hierarchy、edge constraints       |

主流覆蓋檢查的重點是分開 queue、stream、event bus、workflow 與 device messaging。Kafka / Pulsar / Kinesis 解 event stream；SQS / Service Bus 解 managed queue；SNS / EventBridge / Event Grid 解 cloud event routing；Temporal 解 workflow state；MQTT broker 解 IoT device delivery。

## 下一步路由

- 上游：[3.2 durable queue](/backend/03-message-queue/durable-queue/)
- 上游：[3.4 consumer design](/backend/03-message-queue/consumer-design/)
- 案例：[3.C 佇列案例正文](/backend/03-message-queue/cases/)
- 服務路徑：[3.8 Queue Consumer Retry 與 Replay Handoff](/backend/03-message-queue/queue-consumer-retry-replay-handoff/)
