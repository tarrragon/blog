---
title: "訊息佇列 Vendor 清單"
date: 2026-05-01
description: "規劃 broker、event streaming 與 managed queue 的服務頁撰寫順序與判準"
weight: 90
tags: ["backend", "message-queue", "vendor"]
---

訊息佇列 Vendor 清單的核心責任是把 broker 名稱放回 delivery semantics、processing semantics、replay boundary 與操作治理的判斷。每個服務頁先回答它提供哪種投遞與消費模型，再討論 ordering、retention、consumer group、DLQ、managed 邊界與案例回寫。

## 讀法

佇列服務要從處理語意進入。讀者如果要處理一般工作佇列，先回到 [3.2 durable queue](/backend/03-message-queue/durable-queue/)；如果要處理事件流與 replay，先回到 [3.4 consumer design](/backend/03-message-queue/consumer-design/)；如果問題是資料庫交易與事件發布一致性，先回到 [3.3 outbox pattern](/backend/03-message-queue/outbox-pattern/)。

## T1 服務頁大綱

| 服務                                                                     | 類型               | 頁面要回答的核心問題                                                 |
| ------------------------------------------------------------------------ | ------------------ | -------------------------------------------------------------------- |
| [RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/)                  | Classic broker     | exchange、routing、ack/nack 與 DLQ 如何支援工作分派                  |
| [Apache Kafka](/backend/03-message-queue/vendors/kafka/)                 | Event streaming    | partition、offset、retention 與 replay 如何支援事件流                |
| [NATS](/backend/03-message-queue/vendors/nats/)                          | Messaging / stream | subject、JetStream、low-latency 與 durability 如何取捨               |
| [Redis Streams](/backend/03-message-queue/vendors/redis-streams/)        | Embedded stream    | Redis 生態中的 stream、consumer group 與 pending entry 邊界          |
| [AWS SQS](/backend/03-message-queue/vendors/aws-sqs/)                    | Managed queue      | standard / FIFO、visibility timeout 與 DLQ 如何支援 managed delivery |
| [Google Cloud Pub/Sub](/backend/03-message-queue/vendors/google-pubsub/) | Managed pub/sub    | topic / subscription、push / pull 與 global delivery 如何取捨        |

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
| 主討論案例         | C1/C3/C4/C6/C7           | 待補（C9/C10 通用）        | 待補（C8/C10 通用）             | C5 / C10 通用               | C2 反面 / C8 / C10       | C8 / C10                |

對照表的用途有三：

- 寫某 vendor 頁時、檢查橫向議題是否都有對應的進階主題子段、避免缺漏
- 讀者在 vendor 間遷移時、知道對應旋鈕在另一個 vendor 叫什麼
- 補案例時、看哪幾個 vendor 案例稀薄（RabbitMQ / NATS / Redis Streams / Pub/Sub）、優先補

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
| Q1   | RabbitMQ / AWS SQS          | 建立 work queue、ack、visibility timeout 與 DLQ baseline          |
| Q2   | Kafka / Google Pub/Sub      | 建立 event log、managed pub/sub、retention 與 replay 判準         |
| Q3   | NATS / Redis Streams        | 建立 lightweight messaging 與 embedded stream 的邊界              |
| Q4   | Pulsar / Kinesis / Temporal | 補 multi-tenant streaming、managed stream 與 workflow engine 對照 |

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
- 規劃：[0.17 後端真實服務討論大綱](/backend/00-service-selection/service-entity-discussion-outline/)
