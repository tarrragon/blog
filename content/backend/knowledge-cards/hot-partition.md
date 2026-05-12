---
title: "Hot Partition"
date: 2026-05-12
description: "說明分散式 KV / OLTP 中、單一 partition 流量遠超其他的容量問題"
weight: 227
---

Hot partition 的核心概念是「partition 之間流量不均、最熱 partition 先 saturate、整體名義容量達不到」。partition key 設計不均勻是主因。可先對照 [Saturation Point](/backend/knowledge-cards/saturation-point/)。

## 概念位置

DynamoDB / Cosmos DB / Bigtable / Cassandra 都用 partition 拆分資料、容量上限 = 每 partition 上限 × partition 數。但若 partition key 集中在少數 key（例如 event_id 一個演唱會、user_id 一個爆紅 KOL）、實際容量遠低於名義。Aurora / 傳統 RDB 沒 partition 抽象、但 hot row（高頻寫的單列）會引發 lock contention、效果類似。可先對照 [Saturation Point](/backend/knowledge-cards/saturation-point/)。

## 可觀察訊號與例子

hot partition 的訊號是「整體 utilization 低、但 throughput 上不去 + p99 latency 飆」。對應案例：[Amazon Ads 9000 萬 RPS](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) — partition key 設計均勻避免 hot；[Tixcraft 售票](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — 同一場演唱會（event_id）天然容易 hot、必須用 composite key 或 write sharding 分散。

## 設計責任

設計 partition key 時、要主動評估「在最壞場景下、單一 partition 會吃多少流量」。常見手段：composite key（event_id + user_id_hash）、write sharding（event_id + random_suffix）、time-bucket（event_id + minute）。發現 hot partition 後、resharding 通常是高成本工程、要在設計初期避免。
