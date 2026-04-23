---
title: "模組三：訊息佇列與事件傳遞"
date: 2026-04-22
description: "整理 durable queue、broker、retry、outbox 與 idempotency 的後端實務"
weight: 3
---

訊息佇列模組的核心目標是說明事件離開單一 process 後，如何處理持久化、重試、[重複投遞](../00-knowledge-cards/duplicate-delivery/)與 consumer 協調。語言教材會先處理本地 queue abstraction、publisher port、processor 與 idempotency interface；本模組負責 [broker](../00-knowledge-cards/broker/) 的具體語意。

## 暫定分類

| 分類          | 內容方向                                                  |
| ------------- | --------------------------------------------------------- |
| RabbitMQ      | exchange、queue、routing key、ack/nack、dead-letter queue |
| NATS          | subject、consumer、JetStream、at-least-once delivery      |
| Kafka         | topic、partition、consumer group、offset、ordering        |
| Redis Streams | stream、consumer group、pending entry、claim              |
| Outbox        | transaction outbox、poller、publisher、重試策略           |
| Idempotency   | idempotency key、dedup store、replay safety               |

## 選型入口

訊息佇列選型的核心判斷是工作離開 request 或 process 後需要什麼投遞保證。當工作需要排隊、重試、跨服務傳遞、多 consumer 協作或事件補送時，broker 與 outbox 值得優先評估。

RabbitMQ 適合明確 routing、[ack/nack](../00-knowledge-cards/ack-nack/) 與工作佇列；NATS 適合 subject-based messaging 與較輕量的服務通訊，搭配 JetStream 可加入持久化；Kafka 適合高吞吐事件流、partition 與長期 replay；Redis Streams 適合 Redis 生態內的 stream 與 consumer group；[outbox](../00-knowledge-cards/outbox-pattern/) 解決資料寫入與事件發布的一致性；[idempotency](../00-knowledge-cards/idempotency/) 解決重複投遞造成的結果穩定性；[retry budget](../00-knowledge-cards/retry-budget/) 與 [jitter](../00-knowledge-cards/jitter/) 則控制故障期間的重試壓力。

接近真實網路服務的例子包括付款後寄信、影片轉檔、訂單事件傳給多個系統、IoT readings pipeline 與跨節點通知。這些場景的共同問題是 delivery semantics，因此本模組會先處理 broker 模型、retry、[DLQ](../00-knowledge-cards/dead-letter-queue/)、outbox 與 consumer 設計。

## 與語言教材的分工

語言教材處理本地 backpressure、processor 邊界、port / protocol 設計與單一 process 內的去重。Backend message queue 模組處理 broker selection、ack/nack、DLQ、consumer group、outbox 與跨 process 重試。

## 跨語言適配評估

訊息佇列使用方式會受語言的 worker model、錯誤處理、序列化、背景任務框架與 idempotency 設計影響。同步 runtime 要控制 consumer thread 數量與 ack timeout；async runtime 要處理 backpressure 與 long-running handler；輕量並發 runtime 要限制同時處理量，避免 consumer 擴張超過下游容量。強型別語言適合建立 event schema 與 command model；動態語言要補足 payload validation、dead-letter 診斷與重播測試。

## 章節列表

| 章節                            | 主題                      | 關鍵收穫                                                     |
| ------------------------------- | ------------------------- | ------------------------------------------------------------ |
| [3.1](broker-basics/)           | broker 基礎與投遞模型     | 看懂 exchange、topic、consumer 與 delivery semantics         |
| [3.2](durable-queue/)           | durable queue 與重試策略   | 規劃持久化、ack/nack、DLQ 與 retry                           |
| [3.3](outbox-pattern/)          | outbox pattern 與發佈一致性 | 把交易寫入與事件發佈分離                                      |
| [3.4](consumer-design/)         | consumer 設計與去重        | 設計 idempotency、checkpoint 與 replay safety               |
