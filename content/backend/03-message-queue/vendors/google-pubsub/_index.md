---
title: "Google Cloud Pub/Sub"
date: 2026-05-01
description: "GCP managed pub/sub、global routing、push/pull"
weight: 6
---

Cloud Pub/Sub 是 GCP managed pub/sub 服務、global routing、自動 scaling、push 與 pull 兩種 delivery 模式。適合 GCP 生態內的事件分發、跨服務 decoupling、Dataflow 整合。

## 適用場景

- GCP 生態事件分發
- 跨 region 全球訊息路由
- Push delivery（HTTP endpoint）
- Dataflow / BigQuery streaming integration

## 不適用場景

- 需要嚴格 ordering（雖支援 ordering key 但有限制）
- 跨雲 / 跨平台
- 極端低延遲

## 跟其他 vendor 的取捨

- vs `aws-sqs`：類似定位、不同雲；Pub/Sub 是 pub/sub model（一對多），SQS 是 queue（一對一）
- vs `kafka`：Pub/Sub managed；Kafka 自管或 Confluent
- vs Pub/Sub Lite：lower-cost zonal 變體

## 預計實作話題

- Topic / Subscription 設計
- Push vs Pull delivery
- Ordering key 限制
- Dead-letter topic
- Pub/Sub Lite 適用判斷
