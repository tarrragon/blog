---
title: "9.C6 Tinder：ElastiCache for Valkey 撐 4700 萬月活的配對引擎"
date: 2026-05-12
description: "Tinder 用 Amazon ElastiCache for Valkey 提供配對引擎所需的次毫秒延遲快取層"
weight: 6
tags: ["backend", "performance", "capacity", "case-study", "cache", "aws", "sustained-growth"]
---

這個案例的核心責任是說明「cache layer 在持續成長服務」的角色 — 不是峰值問題、是延遲 SLA 與成本曲線同時拉緊的長期工程議題。Tinder 的配對引擎需要在每次滑動都查多個快取（用戶 profile、距離、偏好過濾、推薦池），單次互動的延遲就是 UX 本身。

## 觀察

Tinder 在 ElastiCache for Valkey 的關鍵數字（引自 [ElastiCache customers](https://aws.amazon.com/elasticache/customers/)）：

| 指標     | 數字                    |
| -------- | ----------------------- |
| 月活用戶 | 約 4700 萬 MAU (2025)   |
| 配對累計 | 超過 10 億次配對        |
| 地理覆蓋 | 190 個國家              |
| 服務年數 | 自 2012 年起            |
| 延遲特性 | sub-millisecond latency |

ElastiCache for Redis 7.1 在 r7g.4xlarge 上可達單節點 100 萬 RPS、單 cluster 5 億 RPS（引自 [AWS Database Blog](https://aws.amazon.com/blogs/database/achieve-over-500-million-requests-per-second-per-cluster-with-amazon-elasticache-for-redis-7-1/)）。

## 判讀

Tinder 案例值得讀的是「快取在 long-running 服務的角色變化」。

1. **快取不是 DB 的補救、是主要服務面**：配對引擎每次互動讀 cache 不讀 DB、cache miss 是 *邊緣案例*。對應 [02 快取模組](/backend/02-cache-redis/) 的 cache-as-source-of-truth 與 [02.4 cache copy freshness boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/) 設計。
2. **次毫秒延遲是業務 KPI、不只是技術指標**：手指滑動之後 250ms 內必須給結果、否則「卡頓」。中間整個 chain（網路、cache、序列化）的 latency budget 必須緊。對應 [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/) 的 latency budget 反推。
3. **長期 sustained growth 的容量曲線是成本曲線**：47M MAU 沒有明顯峰谷、容量規劃變成「每月線性擴容 X%」的長期決策、不是峰值規劃。對應 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/) 的長期成本工程。

需要警惕：Tinder 的「configurable matching」業務邏輯複雜、快取資料的 schema 變化頻繁。一個 schema 變更可能讓既有 cache 全部 invalid、引發 cache stampede。對應 [02.6 cache migration stampede rollback](/backend/02-cache-redis/cache-migration-stampede-rollback/)。

## 策略

可重用的工程做法：

1. **cache layer 容量規劃跟 DB 容量規劃要分開**：cache 容量受 working set size 影響、DB 容量受 total dataset 影響、兩者擴容邏輯不一樣。對應 [02 快取模組](/backend/02-cache-redis/) 的 cache sizing。
2. **cache 命中率變化是業務變化的訊號**：突然命中率掉、可能是新功能影響 access pattern、不一定是 cache 容量問題。對應 [9.8 效能可觀測性](/backend/09-performance-capacity/) 的訊號治理。
3. **Valkey vs Redis OSS vs MemoryDB 是不同 trade-off**：Valkey（社群分支、AWS 主推）、Redis OSS（受授權變化影響）、MemoryDB（持久化）三者選擇影響長期 vendor lock-in。

跨平台等效：GCP Memorystore for Redis / Valkey、Azure Cache for Redis、自建 Redis Cluster + Sentinel 都可以實作對等架構。差異是 vendor 的 patch cadence 與容量擴張流程。

## 下一步路由

- 想設計 cache layer 容量 → [02 快取模組](/backend/02-cache-redis/) + [9.5 瓶頸定位流程](/backend/09-performance-capacity/)
- 想做 latency budget 反推 → [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/) + [9.1 壓測理論與系統行為](/backend/09-performance-capacity/)
- 想理解 cache stampede 風險 → [02.6 cache migration stampede rollback](/backend/02-cache-redis/cache-migration-stampede-rollback/)
- 對照其他 cache 案例 → [9.C5 Amazon Ads DynamoDB](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)（KV 高吞吐）

## 引用源

- [Amazon ElastiCache Customers](https://aws.amazon.com/elasticache/customers/)
- [Achieve over 500 million requests per second per cluster with ElastiCache for Redis 7.1](https://aws.amazon.com/blogs/database/achieve-over-500-million-requests-per-second-per-cluster-with-amazon-elasticache-for-redis-7-1/)
- [Optimize Redis Client Performance for ElastiCache and MemoryDB](https://aws.amazon.com/blogs/database/optimize-redis-client-performance-for-amazon-elasticache/)
