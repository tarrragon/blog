---
title: "Composite Partition Key"
date: 2026-05-27
description: "多欄位合成 partition key 把單一 logical hot key 拆成多個物理 shard、寫入分散讀取 fan-out"
weight: 368
---

Composite partition key 的核心概念是「用多個欄位拼接成 partition key — 例如 `event_id#shard_id`、`tenant_id + user_id_hash`、`userId_random` — 把單一 logical key 寫入分散到 N 個物理 partition」。它是 [Hot Partition](/backend/knowledge-cards/hot-partition/) 的標準治療手段、跟 [Database Sharding](/backend/knowledge-cards/database-sharding/) 不同層（後者是跨 cluster 的 application-level、composite key 是單表內 partition layout）。

## 概念位置

Composite partition key 在 KV / document DB 的 partition 抽象層運作 — DynamoDB、Cosmos DB、MongoDB sharded cluster 都用同一套思路。隨 composite 方式不同分兩型：*random shard*（`event_id#random(0,N-1)`、寫完全分散、讀必須 fan-out 全部 N 個 shard）跟 *calculated shard*（`event_id#hash(user_id) % N`、同 user 寫到固定 shard、單 user 讀不 fan-out、跨 user 讀才 fan-out）。Cosmos DB 的 *synthetic partition key*、MongoDB 的 *hashed shard key*、DynamoDB 的 *write sharding suffix* 都是這個概念的 vendor 命名。

跟 partition layout 是分散式 SQL 透明 range 的 [Range Sharding](/backend/knowledge-cards/range-sharding/) 區隔 — 後者不需要 application 操心 key 設計、composite key 是 application-managed 的明確介面。

## 可觀察訊號與例子

需要 composite partition key 的訊號是「整體 utilization 低、少數 partition WCU / RU 飆到上限、p99 latency 隨單一 logical key 流量線性惡化」。對應案例：DynamoDB 售票場景單一 `event_id`（一場演唱會）天然集中、composite `event_id#shard` + random suffix 把 IOPS 從單 partition 1000 WCU 上限拆到 N × 1000；Cosmos DB synthetic key 把 fanout 設 10-100 之間平衡寫分散跟讀成本。MongoDB hashed shard key 則犧牲 range query 換取均勻分散。

## 設計責任

設計 composite key 必須先 audit *讀寫比例* — 寫密集 + 讀範圍小（單 user 自己的 timeline）適合 calculated shard、讀寫都跨 logical key（全平台 aggregation）random shard 也吃得消；讀密集 + 跨 logical key fan-out 成本爆炸時要回頭重設 shard 數或加 secondary index。fanout 數量是核心參數：太少（< 10）寫入仍可能集中、太多（> 100）讀放大成本壓垮 RU / WCU 預算。Resharding（改 shard 數）成本極高 — 設計階段就要按最壞峰值估 N、留 buffer、寫進 schema 設計文件而不是只寫 application code。
