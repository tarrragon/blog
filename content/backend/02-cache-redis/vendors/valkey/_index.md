---
title: "Valkey"
date: 2026-05-01
description: "Redis fork、Linux Foundation 託管、BSD 授權"
weight: 2
tags: ["backend", "cache", "vendor"]
---

Valkey 是 2024 年從 Redis 7.2.4 fork 的開源專案、承擔三個責任：維持 Redis API 相容（drop-in 替換）、提供 OSI 認可的開源授權（BSD 3-clause）、由 Linux Foundation 託管避免單一公司控制。設計取捨偏向「相容 Redis 既有 client / 工具 + 開源治理透明 + 多雲廠商共同維護」、不追求功能超越 Redis Inc。

對「既有 Redis 部署、需要 OSI 認可授權、多雲避免 vendor lock-in、合規敏感」這條路徑、Valkey 是 Redis 的替代首選。AWS / Google / Oracle / Ericsson 等共同支援、AWS ElastiCache 已把 Valkey 設為 default engine。

## 本章目標

讀完本章後、你應該能：

1. 跑起 Valkey、用 redis-cli 驗證 API 相容性
2. 評估從 Redis 遷移到 Valkey 的相容性風險（module / Stack 功能）
3. 看懂 Valkey vs Redis Inc 的版本對應跟功能差距
4. 評估管雲端 managed Valkey（ElastiCache）的選用判斷
5. 區分 Valkey 跟 Redis 商業版本對你的合規 / 採購 / SLA 影響

## 最短路徑：5 分鐘把 Valkey 跑起來

```bash
# 1. 啟動 Valkey（Redis API 相容、可直接用 redis-cli）
docker run -d --name valkey -p 6379:6379 valkey/valkey:8

# 2. 驗證讀寫（valkey-cli 與 redis-cli 命令一致）
docker exec valkey valkey-cli SET foo bar   # → OK
docker exec valkey valkey-cli GET foo       # → bar

# 3. 確認版本：Valkey 同時回報相容的 redis_version 與自身 valkey_version
docker exec valkey valkey-cli INFO server | grep -E "redis_version|valkey_version|server_name"
# redis_version:7.2.4    ← client library 以此判斷相容性（fork 自 Redis 7.2.4）
# server_name:valkey
# valkey_version:8.1.8   ← Valkey 自身版本
```

第三步是相容性的關鍵證據：既有 Redis client library 看到 `redis_version:7.2.4` 就以 Redis 7.2.4 的行為運作、無需改 code；`valkey_version` 才是 Valkey 自身的演進線。實機驗證於 valkey/valkey:8 image、最後檢查日 2026-06-16。實際遷移路徑見[進階主題：從 Redis 遷移](#從-redis-遷移)。

## 日常操作與決策形狀

### CLI 與 client API

子議題：

- valkey-cli vs redis-cli：兩個 binary 都可連 Valkey、命令一致
- Client library 配置：所有 Redis client 自動相容（無需 Valkey-specific client）
- 對應指令範例：`INFO server` 顯示 valkey_version 而非 redis_version

### 跟 Redis 的相容邊界

子議題：

- Core data types / commands：100% 相容（fork 自 Redis 7.2.4）
- Eviction / persistence / cluster：相容
- Pub/Sub / Streams：相容
- **不相容**：Redis 7.4+ 引入的功能、Redis Stack 商業 modules

### 遷移評估

子議題：

- AOF / RDB 文件格式相容、可直接拷貝資料目錄
- Client library 完全相容、無需改 code
- 監控工具相容（RedisInsight 雖偏 Redis Inc、但基本命令通用）
- 需確認 modules 使用狀況（Stack modules 未必有 Valkey fork）

## 進階主題（按需閱讀）

### 從 Redis 遷移

子議題：

- 評估 module 使用：列出當前使用的 Redis modules、確認 Valkey 對應替代
- 評估 Redis 7.4+ 功能使用（Functions、CLIENT NO-TOUCH 等）
- 遷移路徑：rolling restart with replica swap / 雙寫 / 直接 cutover
- 對應雲端 managed：AWS ElastiCache for Valkey 自動遷移工具

### 授權合規評估

子議題：

- 為何 Redis 改 RSALv2 / SSPL — OSI 認知（不算 OSI 認可開源）
- Valkey BSD 3-clause — 商業使用無限制
- 對 SaaS 供應商：Redis 限制把 Redis 當成 service 對外提供、Valkey 無此限制
- 對企業 / 公部門：開源合規政策可能要求 OSI 認可、Valkey 通過、Redis 不過

### Module 生態相容性

子議題：

- Valkey 計畫自有 modules（valkey-search / valkey-bloom 等）
- Redis Stack modules（RedisJSON / RedisSearch）部分有 fork
- 評估你用的 modules 是否有 Valkey 替代、否則考慮遷 module-free 設計

### 雲端 managed Valkey

子議題：

- AWS ElastiCache for Valkey（成本比 Redis 低 ~20%、AWS 推）
- GCP Memorystore（規劃 Valkey 支援）
- Azure Cache（規劃中）
- managed 邊界跟 ElastiCache for Redis 一致

### 跟 Redis 8 的功能差距

子議題：

- Redis 8 新功能對 Valkey 的影響（功能落後幾個月）
- Valkey 自有 roadmap（valkey.io/blog 追蹤）
- 何時 Redis 新功能值得遷回（罕見、通常 Valkey 跟上）

## 排錯快速判讀

### Client 連不上（API 相容問題）

操作原則：先確認 Valkey 回報的相容版本、再對照 client library 支援到 Redis 哪個版本。

```bash
valkey-cli INFO server | grep -E "redis_version|valkey_version"
# redis_version:7.2.4    ← client library 用這個判斷相容性
# valkey_version:8.1.8
```

絕大多數情況直接相容、若失敗多是 client library 太舊（不支援 Redis 7.2 對應版本）。

### Module 不可用

操作原則：Valkey 對 Redis Stack modules 不一定有 fork、看 Valkey modules 清單。

### 監控工具相容性

操作原則：RedisInsight 連 Valkey 可能 partial 工作（部分 vendor-specific 命令缺）、用通用工具（valkey-cli、Prometheus + redis_exporter）較穩。

### Performance regression（vs Redis）

操作原則：Valkey 跟 Redis 7.2.4 為 baseline、效能應接近、差距 < 5% 屬於正常。明顯回歸要看 Valkey roadmap 是否有 known issue。

## 何時改走其他服務

| 需求形狀                      | 改走                                                                                     |
| ----------------------------- | ---------------------------------------------------------------------------------------- |
| 依賴 Redis Stack 商業 modules | [Redis](/backend/02-cache-redis/vendors/redis/)（Redis Inc 商業版）                      |
| 純 KV cache 不需 data types   | [Memcached](/backend/02-cache-redis/vendors/memcached/)                                  |
| 極高 throughput / 多核        | [DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/)                              |
| AWS managed                   | [AWS ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/)（已 default Valkey） |
| Durable Redis-compatible      | AWS MemoryDB                                                                             |
| 跨雲 fully-portable           | Valkey self-host（無 vendor lock-in）                                                    |

## 不在本頁內的主題

- 完整 Valkey command reference（valkey.io/commands）
- Linux Foundation governance 細節
- 各語言 client compatibility matrix
- Redis Stack module 對應替代清單

## 案例回寫

### 直接相關案例（沿用 Redis 同源案例 + 待補 Valkey-specific case）

Valkey 從 Redis 7.2.4 fork、API 與行為 100% 相容、Redis-on-Valkey 同源案例可直接套用。截至本文時 Valkey-specific production case 仍累積中。

| 案例                                                                                               | 對 Valkey 的對應                                                             |
| -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| [2.C3 Shopify serialization](/backend/02-cache-redis/cases/shopify-cache-serialization-migration/) | Payload 雙軌遷移策略 client-side 實作、Valkey 跟 Redis 行為一致              |
| [2.C5 Shopify write-through](/backend/02-cache-redis/cases/shopify-write-through-cache-at-scale/)  | Write-through 在 Valkey 上跟 Redis 同樣 API、無遷移風險                      |
| [2.C1 Meta cache consistency](/backend/02-cache-redis/cases/meta-cache-consistency-upgrade/)       | invalidation / shard move 一致性議題、Valkey Cluster 沿用 Redis Cluster 模型 |

**待補 Valkey-specific 案例**：Linux Foundation Valkey customer adoption stories、AWS ElastiCache for Valkey 客戶遷移個案、re:Invent 2025+ talks、企業 OSI 合規驅動的遷移路徑公開分享。

### 跨 vendor 對照

| 案例                                                                                            | 對 Valkey 的對應                                                                                   |
| ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| [2.C10 規模對照](/backend/02-cache-redis/cases/contrast-cache-strategy-by-scale/)               | Valkey 跟 Redis 規模化路徑一致（fork 同源）、小型 single / 中型 Sentinel / 大型 Cluster            |
| [2.C9 Cache Stampede](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/) | TTL jitter / [singleflight](/backend/knowledge-cards/singleflight/) 通用、Valkey 行為跟 Redis 一致 |
| [2.C2 Meta mcrouter](/backend/02-cache-redis/cases/meta-mcrouter-global-cache-routing/)         | Memcached routing 案例、Valkey 對應為 Cluster + client-side routing 或 Envoy Redis proxy           |
| [2.C6 Netflix EVCache](/backend/02-cache-redis/cases/netflix-evcache-global-cache-layer/)       | EVCache 為 Memcached based、Valkey 對應為 Global Datastore（ElastiCache for Valkey）               |

## 下一步路由

- 上游概念：[2.2 Cache Aside](/backend/02-cache-redis/cache-aside/)
- 平行 vendor：[Redis](/backend/02-cache-redis/vendors/redis/)（fork 源頭）、[ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/)
- 下游能力：跟 Redis 完全一致、見 Redis vendor 頁的下游連結
