---
title: "Apache Kafka"
date: 2026-05-01
description: "Distributed event streaming platform、log-based 模型"
weight: 2
---

Kafka 是 distributed event streaming platform、log-based 儲存模型、partition + consumer group 提供高吞吐與 ordering 保證。適合 event-driven 架構、CDC、stream processing、跨系統事件總線。

## 適用場景

- 高吞吐事件流（百萬 msg/sec）
- 需要長期 replay / event sourcing
- CDC（Debezium 整合）
- Stream processing（Kafka Streams / Flink）
- 跨系統事件總線

## 不適用場景

- 簡單 task queue（過度複雜）
- 需要複雜 routing（broker model）
- 低延遲 RPC-style messaging

## 跟其他 vendor 的取捨

- vs `rabbitmq`：見 RabbitMQ 篇
- vs `pulsar`（T2）：Pulsar 多租戶與分層儲存更原生
- vs `aws-msk` / Confluent Cloud：自管 vs managed
- vs Redpanda：Kafka 相容、C++ 重寫、單 binary

## 預計實作話題

- Partition / consumer group 設計
- Exactly-once semantics
- KRaft（取代 ZooKeeper）
- Schema Registry / Avro / Protobuf
- Kafka Connect 與 CDC
- Tiered storage
