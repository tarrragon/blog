---
title: "Redis Streams"
date: 2026-05-01
description: "Redis 生態內的 streams、append-only log + consumer group"
weight: 4
---

Redis Streams 是 Redis 5.0 引入的 append-only log data type、提供 consumer group 與 pending entries list。適合 Redis 生態內的輕量 event stream、stream processing 入門、避免額外引入 Kafka 的場景。Redis vendor 細節見 [02 redis](/backend/02-cache-redis/vendors/redis/)。

## 適用場景

- 已用 Redis、需要輕量 stream 不想再引入 Kafka
- Stream processing 入門 / 中等規模
- 低延遲 event distribution
- Pub/Sub 想要持久化升級

## 不適用場景

- 大規模長期 retention（記憶體成本）
- 高吞吐（百萬 msg/sec）— 用 Kafka
- 跨系統事件總線（生態不夠）

## 跟其他 vendor 的取捨

- vs `kafka`：Redis Streams 輕量、避免額外基礎設施；規模有極限
- vs `nats` JetStream：類似定位、Redis 偏 in-memory
- vs Redis Pub/Sub：Streams 持久化、Pub/Sub fire-and-forget

## 預計實作話題

- Consumer group 與 pending entries
- XADD / XREAD / XCLAIM 操作
- Memory 與 retention 取捨
- Stream + Functions（Redis 7+）
