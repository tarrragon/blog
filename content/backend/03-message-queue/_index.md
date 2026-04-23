---
title: "模組三：訊息佇列與事件傳遞"
date: 2026-04-22
description: "整理 durable queue、broker、retry、outbox 與 idempotency 的後端實務"
weight: 3
---

訊息佇列模組的核心目標是說明事件離開單一 process 後，如何處理持久化、重試、重複投遞與 consumer 協調。語言教材會先處理本地 queue abstraction、publisher port、processor 與 idempotency interface；本模組負責 broker 的具體語意。

## 暫定分類

| 分類          | 內容方向                                                  |
| ------------- | --------------------------------------------------------- |
| RabbitMQ      | exchange、queue、routing key、ack/nack、dead-letter queue |
| NATS          | subject、consumer、JetStream、at-least-once delivery      |
| Kafka         | topic、partition、consumer group、offset、ordering        |
| Redis Streams | stream、consumer group、pending entry、claim              |
| Outbox        | transaction outbox、poller、publisher、重試策略           |
| Idempotency   | idempotency key、dedup store、replay safety               |

## 與語言教材的分工

語言教材處理本地 backpressure、processor 邊界、port / protocol 設計與單一 process 內的去重。Backend message queue 模組處理 broker selection、ack/nack、DLQ、consumer group、outbox 與跨 process 重試。

## 相關語言章節

- [Go：channel](../../go/04-concurrency/channel/)
- [Go 進階：非阻塞送出與事件丟棄策略](../../go-advanced/01-concurrency-patterns/non-blocking-send/)
- [Go 進階：多來源 event 融合](../../go-advanced/04-architecture-boundaries/event-fusion/)
- [Go 進階：Durable queue、outbox 與 idempotency](../../go-advanced/07-distributed-operations/outbox-idempotency/)

## 章節列表

| 章節                            | 主題                      | 關鍵收穫                                                     |
| ------------------------------- | ------------------------- | ------------------------------------------------------------ |
| [3.1](broker-basics/)           | broker 基礎與投遞模型     | 看懂 exchange、topic、consumer 與 delivery semantics         |
| [3.2](durable-queue/)           | durable queue 與重試策略   | 規劃持久化、ack/nack、DLQ 與 retry                           |
| [3.3](outbox-pattern/)          | outbox pattern 與發佈一致性 | 把交易寫入與事件發佈分離                                      |
| [3.4](consumer-design/)         | consumer 設計與去重        | 設計 idempotency、checkpoint 與 replay safety               |
