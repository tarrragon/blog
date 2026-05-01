---
title: "AWS SQS"
date: 2026-05-01
description: "AWS managed queue、簡單可靠、無 ordering（standard）"
weight: 5
---

SQS 是 AWS managed queue 服務、極簡 API、無維運成本。Standard queue 提供 at-least-once + 不保證 ordering；FIFO queue 提供 exactly-once + ordering 但 throughput 受限。適合 AWS 生態內的 task queue。

## 適用場景

- AWS 生態 task queue / decoupling
- 不在意 ordering 的高吞吐 standard queue
- 簡單 API、不想自管 broker
- Lambda + SQS event source

## 不適用場景

- 需要複雜 routing（broker model）
- 跨雲 / 跨平台
- 需要 streaming / replay
- 嚴格低延遲（<100ms）

## 跟其他 vendor 的取捨

- vs `rabbitmq`：SQS managed、routing 簡單
- vs `kafka` / `kinesis`：SQS 是 queue；Kinesis 是 stream
- vs `google-pubsub`：類似定位、不同雲

## 預計實作話題

- Standard vs FIFO queue
- Visibility timeout 與 in-flight 訊息
- DLQ 設計
- Long polling vs short polling
- SQS + Lambda event source mapping
