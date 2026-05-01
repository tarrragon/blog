---
title: "DynamoDB"
date: 2026-05-01
description: "AWS managed key-value、cell-based scaling"
weight: 5
---

DynamoDB 是 AWS managed key-value store、partition-based scaling、可預測 P99 latency。適合需要 single-digit millisecond latency 與 elastic capacity 的場景、是 Amazon 自己 cell-based architecture 的代表實作。

## 適用場景

- key-value / single-table design 為主的查詢
- 需要可預測 P99 latency（<10ms）
- 流量 spiky、需要 on-demand capacity
- AWS 生態深度整合（Lambda / Streams / Kinesis）

## 不適用場景

- 複雜 ad-hoc query / JOIN
- 需要強一致 multi-row transaction
- 跨雲 / 跨平台需求

## 跟其他 vendor 的取捨

- vs `mongodb`：DynamoDB managed、partition 模型嚴格；MongoDB 自管彈性高
- vs `aurora`：Aurora 是 SQL；DynamoDB 是 NoSQL key-value
- vs Redis-as-DB：DynamoDB 持久化、Redis 主要記憶體

## 預計實作話題

- Single-table design pattern
- Partition key / sort key 設計
- DynamoDB Streams + Lambda
- On-demand vs provisioned capacity
- Global tables（跨區複製）
