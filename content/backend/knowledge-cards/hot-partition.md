---
title: "Hot Partition"
date: 2026-05-12
description: "說明分散式 KV / OLTP 中、單一 partition 流量遠超其他的容量問題"
weight: 228
---

Hot partition 的核心概念是「partition 之間流量不均、最熱 partition 先 saturate、整體名義容量達不到」。partition key 設計不均勻是主因。可先對照 [Saturation Point](/backend/knowledge-cards/saturation-point/)。

## 跟其他概念的關係

DynamoDB / Cosmos DB / Bigtable / Cassandra 都用 partition 拆分資料、容量上限 = 每 partition 上限 × partition 數。但若 partition key 集中在少數 key（例如 event_id 一個演唱會、user_id 一個爆紅 KOL）、實際容量遠低於名義。Aurora / 傳統 RDB 沒 partition 抽象、但 hot row（高頻寫的單列）會引發 lock contention、效果類似。可先對照 [Saturation Point](/backend/knowledge-cards/saturation-point/)。

## 可觀察訊號與例子

hot partition 的訊號是「整體 utilization 低、但 throughput 上不去 + p99 latency 飆」。對應案例：[Amazon Ads 9000 萬 RPS](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) — partition key 設計均勻避免 hot；[Tixcraft 售票](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — 同一場演唱會（event_id）天然容易 hot、必須用 composite key 或 write sharding 分散。

## 判斷條件與後果

Partition key 的判斷條件是最壞場景下單一 partition 收到多少流量。key 集中在少數值時（一場演唱會的 event_id），實際的容量上限是單一 partition 的上限，名義上的「每 partition 上限乘 partition 數」到不了。分散的手段各有代價：composite key（event_id + user_id_hash）把同一場活動分到多個 partition，查整場活動時要讀多個 partition；write sharding（event_id + random_suffix）分散寫入，讀取時要把各個 suffix 合併；time-bucket（event_id + minute）依時間分散，同一分鐘內的爆量仍集中在一個 partition。上線之後才發現 hot partition 時，resharding 要搬移既有資料並改寫存取的 key，成本遠高於設計初期就評估最壞場景。
