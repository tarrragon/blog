---
title: "DragonflyDB"
date: 2026-05-01
description: "高效能 Redis / Memcached 相容替代、多核架構"
weight: 4
tags: ["backend", "cache", "vendor"]
---

DragonflyDB 是 C++ 重寫的 in-memory store、承擔三個責任：Redis / Memcached protocol 相容（drop-in 替換）、shared-nothing 多核架構（充分利用 CPU）、高 memory efficiency。設計取捨偏向「協議相容但效能大幅提升」、宣稱比 Redis 高 25 倍 throughput。授權從 Apache 2.0 改 BSL（Business Source License）、商業使用有限制。

對「需要極高 single-instance throughput、多核機器希望充分利用 CPU、Redis drop-in 但要 scale up 而非 out」這條路徑、DragonflyDB 是值得評估的替代。

## 本章目標

讀完本章後、你應該能：

1. 跑起 DragonflyDB、用 redis-cli 驗證 protocol 相容
2. 評估從 Redis 遷移的相容性風險（unsupported commands）
3. 看懂 shared-nothing 多核架構跟 Redis I/O thread 的差異
4. 評估 BSL 授權對你的商業使用影響
5. 區分 DragonflyDB 跟 Redis Cluster / Garnet / KeyDB 的選用判讀

## 最短路徑：5 分鐘把 DragonflyDB 跑起來

```bash
# 1. 啟動 DragonflyDB
# TODO: docker run -d --name dragonfly -p 6379:6379 docker.dragonflydb.io/dragonflydb/dragonfly

# 2. 用 redis-cli 驗證
# TODO: redis-cli SET foo bar / GET foo / INFO server

# 3. 用既有 Redis client library 直接連
# TODO: 無需改 code
```

最短路徑驗證「DragonflyDB 起來、Redis client 可用」。實際遷移評估見 [Redis 相容邊界](#redis-相容邊界)。

## 日常操作與決策形狀

### CLI 與 client API

子議題：

- 直接用 redis-cli（DragonflyDB 100% wire-protocol 相容）
- 所有 Redis client library 自動相容
- 沒有 dragonfly-cli、用 INFO 命令確認 server type

### Redis 相容邊界

DragonflyDB 相容大多數 Redis commands、但部分行為差異。子議題：

- ✅ Core data types / commands / persistence / pub-sub / transactions
- ⚠️ 部分 Module 不支援（RedisJSON 有自家版、RedisSearch 沒有）
- ⚠️ Lua scripting：支援但效能取捨不同
- ❌ Cluster mode：DragonflyDB 是 single-instance scale-up、沒有 Redis Cluster mode（單 instance 已能處理 Redis Cluster 規模）

對應指令：`INFO server` 確認 dragonfly version + 配置。

### 配置與調優

子議題：

- `--threads`：thread 數量、預設 CPU core 數
- `--maxmemory`：memory limit、行為跟 Redis 類似
- `--cache_mode`：傳統 cache 模式 vs DragonflyDB 預設模式
- `--snapshot_cron`：snapshot 策略

## 進階主題（按需閱讀）

### Shared-nothing 多核架構

子議題：

- 每個 thread 管自己的 partition、no shared state
- VLL（Very Lightweight Lock）取代 Redis 的 single-thread model
- Hash 分到不同 thread、靠 epoll 跟 io_uring 做 I/O
- 跟 Redis I/O threads 的對比：Redis 仍 single main thread、只 I/O 多線；DragonflyDB 完全多線

### Memory efficiency

子議題：

- 用 dashtable（DragonflyDB 自製 hash table）取代 Redis dict
- Snapshot 用 fork-less 機制、避免大記憶體 fork 開銷
- 同樣 dataset 通常比 Redis 省 20-40% memory（依資料形狀）

### BSL 授權影響

子議題：

- BSL（Business Source License）：商業使用受限、4 年後轉 Apache 2.0
- 限制：不可作為 managed DragonflyDB service 對外提供
- 內部使用無限制（多數企業場景）
- 對 SaaS 供應商：要審慎評估

### 跟 KeyDB / Garnet 的對比

子議題：

- **KeyDB**：Redis fork、multi-threaded、Snap 收購後相對停滯
- **Garnet**（Microsoft）：研究用、極高 throughput、生態淺
- **DragonflyDB**：商業化最積極、生態最活躍

### Scale-up vs Scale-out

子議題：

- DragonflyDB 哲學：single instance 撐到很大規模（廠商宣稱 1TB+ memory / 6.4M QPS）
- Redis 哲學：single instance 有上限、靠 Cluster sharding
- 何時 scale-up 不夠：跨 region / 跨 AZ HA 需求 → 仍需 replica / sentinel

### 從 Redis 遷移

子議題：

- 評估 module 使用：列出當前 modules、確認 DragonflyDB 對應
- 評估 Cluster mode 使用：DragonflyDB 不支援 Cluster mode、要評估能否回到 single instance
- 遷移路徑：replica 模式雙寫 / 直接 cutover
- 對應 BSL 授權影響評估

## 排錯快速判讀

### Performance 不如預期

操作原則：先確認 thread 數對齊 CPU core、再看 memory pressure。

```bash
# TODO: INFO server | grep -E "dragonfly_version|threads"
# TODO: INFO memory
```

判讀：thread < core → 沒充分利用 CPU；memory > 50% maxmemory → 影響 throughput。

### Command 不支援

操作原則：DragonflyDB 不支援全部 Redis commands、看 dragonflydb.io/docs/api/redis 確認。

判讀路徑：client error「unknown command」→ 確認 DragonflyDB 對應實作狀態。

### Cluster mode client 連不上

操作原則：DragonflyDB 不支援 Redis Cluster mode、若 client 配置 cluster mode 會連不上。判讀：改回 standalone client config。

### Module 不可用

對應 KeyDB / Garnet 的對照思路：DragonflyDB 自家 modules 偏少、Redis Stack modules 大多沒有 fork。

### BSL 授權商業使用問題

操作原則：商業使用前審 license terms、若是 managed service 對外提供、需聯絡 DragonflyDB 取得商業 license。

## 何時改走其他服務

| 需求形狀                      | 改走                                                                                                |
| ----------------------------- | --------------------------------------------------------------------------------------------------- |
| 需要 Redis Cluster mode       | [Redis](/backend/02-cache-redis/vendors/redis/) / [Valkey](/backend/02-cache-redis/vendors/valkey/) |
| 需要 OSI 認可開源授權         | [Valkey](/backend/02-cache-redis/vendors/valkey/)                                                   |
| 需要 Redis Stack 完整 modules | [Redis](/backend/02-cache-redis/vendors/redis/)                                                     |
| 純 KV 不需 data types         | [Memcached](/backend/02-cache-redis/vendors/memcached/)                                             |
| AWS managed                   | [AWS ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/)（無 Dragonfly managed）         |
| Multi-threaded Redis fork     | KeyDB（停滯中）                                                                                     |

## 不在本頁內的主題

- DragonflyDB internal 架構細節（dashtable、VLL 等）
- BSL 授權法律解讀（請諮詢律師）
- 各語言 client 完整對應表
- 詳細 benchmark methodology

## 案例回寫

### 直接相關案例（沿用 Redis-compatible 同源案例 + 待補 DragonflyDB-specific case）

DragonflyDB 2022 年開源、wire-protocol 與 Redis 相容、Redis 上的 cache pattern 案例可作為框架參考。Production case 仍累積中。

| 案例                                                                                               | 對 DragonflyDB 的對應                                                              |
| -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| [2.C5 Shopify write-through](/backend/02-cache-redis/cases/shopify-write-through-cache-at-scale/)  | Write-through 模式在 DragonflyDB 上行為一致、單 instance 多核可承接更大 throughput |
| [2.C3 Shopify serialization](/backend/02-cache-redis/cases/shopify-cache-serialization-migration/) | Payload 雙軌遷移 client-side 實作、DragonflyDB 跟 Redis 共用 API、遷移路徑相同     |

**待補 DragonflyDB-specific 案例**：早期採用者 benchmark 報告、從 Redis Cluster 收回 single-instance 的遷移案例、BSL 授權實際商業使用評估、multi-core 加速效果的 production 實測。

### 跨 vendor 對照

| 案例                                                                                                | 對 DragonflyDB 的對應                                                                        |
| --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| [2.C10 規模對照](/backend/02-cache-redis/cases/contrast-cache-strategy-by-scale/)                   | DragonflyDB 擅長 scale-up、中大型 single instance 取代 Redis Cluster 是核心賣點              |
| [2.C9 Cache Stampede](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/)     | TTL jitter 通用、DragonflyDB 行為跟 Redis 一致、多核擴展不會消除 stampede 風險               |
| [2.C4 Meta CacheLib + Kangaroo](/backend/02-cache-redis/cases/meta-cachelib-kangaroo-tiered-cache/) | 分層 cache 議題對照、DragonflyDB 強調 memory efficiency 取代 flash tier 的部分需求           |
| [2.C1 Meta cache consistency](/backend/02-cache-redis/cases/meta-cache-consistency-upgrade/)        | 一致性治理框架通用、但 DragonflyDB 無 Cluster mode、shard move 議題不同（單 instance scope） |

## 下一步路由

- 上游概念：[2.2 Cache Aside](/backend/02-cache-redis/cache-aside/)、[2.3 TTL eviction](/backend/02-cache-redis/ttl-eviction/)
- 平行 vendor：[Redis](/backend/02-cache-redis/vendors/redis/)、[Valkey](/backend/02-cache-redis/vendors/valkey/)
- 下游能力：[2.6 high concurrency](/backend/02-cache-redis/high-concurrency-access/)
