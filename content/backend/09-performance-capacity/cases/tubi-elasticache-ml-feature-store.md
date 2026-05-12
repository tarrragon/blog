---
title: "9.C25 Tubi：從 ScyllaDB 遷到 ElastiCache、ML feature store 達 sub-10ms p99"
date: 2026-05-12
description: "Tubi 把 ML 推薦的 feature store 從 ScyllaDB 遷到 ElastiCache for Redis、99 百分位延遲降到 10ms 以下"
weight: 25
tags: ["backend", "performance", "capacity", "case-study", "cache", "aws", "low-latency-sustained"]
---

這個案例的核心責任是說明「ML feature store 的延遲敏感層」工程選型。即時推薦（首頁 carousel、播放後下一支）需要在 100ms 內生成、ML inference 之前的 feature lookup 通常吃 30-50ms — 把 lookup 壓到 10ms 以下、整個推薦延遲才有預算空間。

## 觀察

Tubi 在 ElastiCache 的關鍵敘述（引自 [ElastiCache Customers](https://aws.amazon.com/elasticache/customers/)）：

| 指標     | 數字                               |
| -------- | ---------------------------------- |
| 工作負載 | ML inference feature store         |
| p99 延遲 | < 10 ms                            |
| 遷移路徑 | ScyllaDB → ElastiCache for Redis   |
| 業務場景 | 串流推薦（free streaming service） |

## 判讀

Tubi 案例揭露三個 ML feature store 容量設計重點。

1. **feature store 是 ML inference 的 critical path**：每個推薦請求都要查 N 個 feature（user_profile、item_metadata、recent_interactions、similar_users 等）、每個 feature 查詢都吃 latency budget。對應 [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/) 的多 stage budget 分解。
2. **ScyllaDB → ElastiCache 是「持久 KV → 純 cache」的權衡**：ScyllaDB 是 Cassandra-compatible 高吞吐 KV、提供 durability；ElastiCache 是 in-memory cache、可以 cache miss。Tubi 選 cache 是判斷「feature 可以重新計算」、durability 不必、純 in-memory 更快。對應 [02 快取模組](/backend/02-cache-redis/) 的 cache vs durable store 選型。
3. **p99 才是 ML 系統的容量門檻**：ML 系統的 user-perceived latency 是 *最後完成的 inference*、不是平均。p50 快沒用、p99 慢用戶就看到 loading spinner。對應 [9.4 Saturation Discovery](/backend/09-performance-capacity/) 的 latency percentile 分析、跟 [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) 的長尾延遲議題同類。

需要警惕：

- 「sub-10ms p99」沒指明 *p999 / p9999*。p9999 通常比 p99 高一個量級、會出現在實際 user-perceived 體驗。
- ElastiCache 的 sub-10ms 是 *cache hit 路徑* — cache miss 路徑會回到 ScyllaDB 或重新計算、延遲可能 100ms+。容量規劃要考慮 cache hit rate 跟 miss recovery 兩條路徑。

## 策略

可重用的工程做法：

1. **ML feature store 用「兩層 cache」設計**：L1 是 in-process cache（最熱的 features）、L2 是 ElastiCache / Memcached（次熱）、L3 才是持久 store（ScyllaDB / DynamoDB / S3 + Parquet）。對應 [02 快取模組](/backend/02-cache-redis/) 的 cache hierarchy。
2. **feature 可重算 → 用 cache、feature 必須持久 → 用 store**：判斷依據是「重算成本」跟「資料一致性需求」。對應 [02.4 cache copy freshness boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/)。
3. **p99 / p999 反推單個 stage latency 上限**：每個 stage（network、cache lookup、feature aggregation、model inference、response serialization）給一個 latency budget、總和等於整體 SLO。對應 [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/)、跟 [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) 同樣的反推思維。

跨平台等效：AWS ElastiCache for Redis / Valkey / MemoryDB、GCP Memorystore for Redis、Azure Cache for Redis 都可實作對等架構。專為 ML feature store 設計的還有 Feast / Tecton / Hopsworks 等開源 + 商業方案、底層常用 Redis-compatible store。

## 下一步路由

- 想規劃 ML feature store → [02 快取模組](/backend/02-cache-redis/) + [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/)
- 想做 p99 / p999 反推 → [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) + [9.4 Saturation Discovery](/backend/09-performance-capacity/)
- 對照其他 cache 案例 → [9.C6 Tinder ElastiCache](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/)（配對引擎）
- 想理解 cache hierarchy → [02 快取模組](/backend/02-cache-redis/)

## 引用源

- [Amazon ElastiCache Customers](https://aws.amazon.com/elasticache/customers/)
- [Build an ultra-low latency online feature store for real-time inferencing using Amazon ElastiCache for Redis](https://aws.amazon.com/blogs/database/build-an-ultra-low-latency-online-feature-store-for-real-time-inferencing-using-amazon-elasticache-for-redis/)
