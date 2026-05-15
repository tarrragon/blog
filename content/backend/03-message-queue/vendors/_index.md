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
