---
title: "NATS"
date: 2026-05-01
description: "Lightweight messaging、JetStream 加持久化與 streams"
weight: 3
---

NATS 是 lightweight high-performance messaging system、subject-based routing、JetStream 提供 persistence / streams / KV store。適合微服務通訊、IoT、edge 場景、需要簡單 broker 但保留 streaming 能力。

## 適用場景

- 微服務間 messaging
- Subject-based routing（hierarchical wildcards）
- IoT / edge / 低資源環境
- 需要 messaging + KV + Object Store 一體
- Request/Reply pattern

## 不適用場景

- 需要 Kafka 等級的 throughput 與 retention
- 大型企業生態整合（社群相對小）
- 需要複雜 broker routing（exchange model）

## 跟其他 vendor 的取捨

- vs `rabbitmq`：NATS 更輕量、subject 模型不同於 exchange
- vs `kafka`：JetStream 提供類似能力但規模較小
- vs `redis-streams`：類似但 NATS 是專用 messaging

## 預計實作話題

- Core NATS vs JetStream
- Stream / Consumer 設計
- Cluster / Supercluster / Leaf node
- JetStream KV / Object Store
- Synadia Cloud（NATS managed）
