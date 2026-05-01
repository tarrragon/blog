---
title: "RabbitMQ"
date: 2026-05-01
description: "Classic message broker、AMQP routing 為主"
weight: 1
---

RabbitMQ 是 AMQP 協議實作的 classic broker、exchange / queue / binding / routing key 模型靈活、適合 task queue 與複雜 routing 場景。多用於 worker pool、RPC over messaging、跨服務 task dispatch。

## 適用場景

- Task queue / worker pool
- 複雜 routing（topic / fanout / direct / headers exchange）
- 需要強 ack/nack 語意與 DLQ
- 中等吞吐（萬級 msg/sec）

## 不適用場景

- 需要長期 replay / event sourcing
- 極高吞吐（百萬 msg/sec）— 用 Kafka
- 需要嚴格 partition ordering

## 跟其他 vendor 的取捨

- vs `kafka`：RabbitMQ 是 broker / queue 模型；Kafka 是 log / streaming 模型
- vs `nats`：NATS 更輕量；RabbitMQ routing 更豐富
- vs `aws-sqs`：SQS managed 但 routing 簡單

## 預計實作話題

- Exchange types 與 routing 設計
- Quorum queue（取代 mirrored queue）
- Streams（RabbitMQ 3.9+ 的 log-style queue）
- Dead-letter exchange
- RabbitMQ on Kubernetes（Cluster Operator）
