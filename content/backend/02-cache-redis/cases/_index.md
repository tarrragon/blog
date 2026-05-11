---
title: "模組二案例正文"
date: 2026-05-07
description: "快取策略與快取平台演進案例入口。"
weight: 80
tags: ["backend", "cache", "case-study"]
---

這個資料夾的核心責任是把快取與 Redis 的轉換壓力寫成可回寫正文，而不是只列工具名稱。

## 案例列表

| 章節                                                                             | 主題                     | 核心責任                                         |
| -------------------------------------------------------------------------------- | ------------------------ | ------------------------------------------------ |
| [2.C1](/backend/02-cache-redis/cases/meta-cache-consistency-upgrade/)            | Meta cache 一致性升級    | 把 invalidation 不一致問題轉成可觀測與可治理流程 |
| [2.C2](/backend/02-cache-redis/cases/meta-mcrouter-global-cache-routing/)        | Meta mcrouter 快取路由   | 把單叢集快取演進到跨區路由與失效隔離             |
| [2.C3](/backend/02-cache-redis/cases/shopify-cache-serialization-migration/)     | Shopify 快取序列化遷移   | 把快取 payload 格式遷移做成雙軌相容與回退        |
| [2.C4](/backend/02-cache-redis/cases/meta-cachelib-kangaroo-tiered-cache/)       | Meta CacheLib 分層快取   | 把 DRAM-only 快取演進到記憶體/快閃分層架構       |
| [2.C5](/backend/02-cache-redis/cases/shopify-write-through-cache-at-scale/)      | Shopify write-through    | 把 read-heavy 路徑轉成寫入同步快取策略           |
| [2.C6](/backend/02-cache-redis/cases/netflix-evcache-global-cache-layer/)        | Netflix EVCache          | 把本地快取演進成跨區分散式快取層                 |
| [2.C7](/backend/02-cache-redis/cases/cloudflare-cache-reserve-tiered-storage/)   | Cloudflare Cache Reserve | 把邊緣快取延伸到持久層降低回源壓力               |
| [2.C8](/backend/02-cache-redis/cases/meta-tao-social-graph-cache-evolution/)     | Meta TAO                 | 把 graph cache 演進成可擴展的一致性資料層        |
| [2.C9](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/) | 反例：快取切換失敗       | 快取策略切換若無防線會觸發 stampede 與回源雪崩   |
| [2.C10](/backend/02-cache-redis/cases/contrast-cache-strategy-by-scale/)         | 對照：規模差異下快取策略 | 小中大型服務用同一快取策略會造成不同失敗型態     |
