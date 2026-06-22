---
title: "KeyDB"
date: 2026-06-16
description: "Redis multi-threaded fork、active-replication、Snap 採用"
weight: 6
tags: ["backend", "cache", "vendor"]
---

KeyDB 是 Redis 的 multi-threaded fork、承擔三個責任：把 Redis 的命令執行從單執行緒改成多執行緒（不只 I/O、連命令處理都多核）、提供 active-active 多主複製（兩個 master 互相同步、都可寫）、維持 Redis protocol 相容（drop-in 替換）。設計取捨偏向「沿用 Redis 生態 + 單實例榨多核 + 多主寫入」、是 Redis 單執行緒撞牆但又不想重寫 client 的中間選項。

對「單 key 極熱、Redis Cluster 切不開、需要單實例多執行緒撐單 partition」這條路徑、KeyDB 是值得評估的 fork。[Snap 在 GCP 上用 KeyDB](/backend/09-performance-capacity/cases/snap-gcp-keydb-cross-cloud/) 是這條路線最大的公開採用者——但要注意該案例的主因是 multi-cloud 架構下的 cross-cloud latency 治理（把 cache 跟 application 放同一個 cloud），KeyDB 的 multi-threaded 單實例吞吐是附帶優勢、不是 Snap 採用的主要驅動。

## 本章目標

讀完本章後、你應該能：

1. 跑起 KeyDB、用 redis-cli 驗證 protocol 相容
2. 評估 multi-threaded 命令執行跟 Redis I/O threads 的差異
3. 判斷 active-active 多主複製適用與衝突風險
4. 評估 KeyDB on FLASH 對大 dataset 的成本意義
5. 區分 KeyDB 跟 DragonflyDB / Redis Cluster 的選用判讀，並評估 Snap 收購後的治理風險

## 最短路徑：5 分鐘把 KeyDB 跑起來

```bash
# 1. 啟動 KeyDB（--server-threads 開多執行緒、命令執行也多核）
docker run -d --name keydb -p 6379:6379 \
  eqalpha/keydb keydb-server --server-threads 4

# 2. 用 redis-cli 驗證（KeyDB 100% Redis protocol 相容）
redis-cli SET foo bar    # → OK
redis-cli GET foo        # → bar

# 3. 確認版本（KeyDB 回報 redis_version、client 以此判斷相容性）
redis-cli INFO server | grep -E "redis_version|redis_mode"
# redis_version:6.3.4    ← KeyDB 的版本方案、client library 以此協商相容
# redis_mode:standalone
```

實機驗證於 eqalpha/keydb image、最後檢查日 2026-06-16；`--server-threads` 是啟動參數（不在 `CONFIG GET` 內、改值要重啟）。多主複製見[進階主題](#active-active-多主複製)。

## 日常操作與決策形狀

### CLI 與 client API

子議題：

- 直接用 redis-cli / 所有 Redis client library（KeyDB 維持 Redis protocol）
- `--server-threads N` 設命令執行的執行緒數、對齊 CPU 核數
- `INFO server` 確認 redis_version（KeyDB 的版本對應 Redis 哪個 base）

### Multi-threaded 命令執行

KeyDB 跟 Redis I/O threads 的差異是核心賣點。子議題：

- Redis 6+ 的 I/O threads 只分擔 socket 讀寫、命令仍在 main thread；KeyDB 連命令執行都多執行緒
- `--server-threads` 對齊核數、單實例吞吐隨核數擴展
- 多執行緒下單 key 的並發保護由 KeyDB 內部處理、application 端語意不變

### Active-active 多主複製

子議題：

- 兩個（含以上）KeyDB master 互相複製、都可接受寫入
- 衝突解決用 last-write-wins（依時間戳）、不是強一致
- 適合跨 AZ / 跨 region 的讀寫就近、但要接受最終一致與衝突覆蓋風險

## 進階主題（按需閱讀）

### Active-active 多主複製

子議題：

- `replicaof` + `active-replica yes` 開雙向複製
- 衝突語意：同 key 並發寫入、last-write-wins、可能丟其中一側的寫入
- 適用：跨區讀寫就近、可容忍最終一致的 cache；不適用：需要強一致的 counter / lock

### KeyDB on FLASH

子議題：

- 把冷資料放 SSD、熱資料留記憶體、降低大 dataset 的記憶體成本
- 對應 [Meta CacheLib + Kangaroo](/backend/02-cache-redis/cases/meta-cachelib-kangaroo-tiered-cache/) 的 DRAM + flash 分層思路
- 代價：FLASH 路徑延遲高於純記憶體、適合冷熱分明的 workload

### 跟 DragonflyDB / Garnet 的對比

子議題：

- KeyDB：Redis fork（沿用 Redis code base、相容度高、base 版本較舊）
- DragonflyDB：C++ 從零重寫（架構更激進、shared-nothing、相容核心但非 fork）
- Garnet（Microsoft）：研究型高吞吐 store、生態淺
- 對應 [DragonflyDB 多核架構 deep article](/backend/02-cache-redis/vendors/dragonflydb/shared-nothing-multicore-architecture/) 的 fork vs 重寫光譜

### 治理風險（Snap 收購後）

子議題：

- KeyDB 公司 2022 年被 Snap 收購、開源版本的後續投入與 roadmap 不確定
- 評估採用前確認專案活躍度（commit 頻率、release cadence）
- 對長期依賴敏感的場景、Redis fork 光譜上的 [Valkey](/backend/02-cache-redis/vendors/valkey/)（Linux Foundation 治理）治理更穩

## 排錯快速判讀

### 多執行緒下吞吐沒提升

操作原則：先確認 `--server-threads` 對齊 CPU 核數、再看是否 CPU 密集 workload。判讀：thread < core → 沒用滿多核；單 key 極熱 → 仍受單 partition 限制。

### Active-active 衝突丟資料

操作原則：last-write-wins 下並發寫同 key 會覆蓋。判讀：跨區同 key 高頻寫入要改設計（key 分區到不同 master）、或改用強一致儲存。

### Protocol 相容問題

操作原則：KeyDB base 版本較舊（redis_version 6.x），用到 Redis 7+ 新命令會不支援。判讀：`INFO server` 確認 base 版本、對照 application 用到的命令。

## 何時改走其他服務

| 需求形狀                     | 改走                                                                                    |
| ---------------------------- | --------------------------------------------------------------------------------------- |
| 要最新 Redis 功能 / 治理穩定 | [Valkey](/backend/02-cache-redis/vendors/valkey/)（Linux Foundation、跟上 Redis）       |
| 更激進的多核 / 記憶體效率    | [DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/)（重寫、shared-nothing）     |
| 需要 Redis Cluster sharding  | [Redis](/backend/02-cache-redis/vendors/redis/) / Valkey Cluster                        |
| 純 KV、極簡運維              | [Memcached](/backend/02-cache-redis/vendors/memcached/)                                 |
| AWS managed                  | [AWS ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/)（無 managed KeyDB） |
| 需要強一致 + durability      | AWS MemoryDB                                                                            |

## 不在本頁內的主題

- KeyDB 完整 command reference（沿用 Redis、查 redis.io/commands）
- 各語言 client API（用 Redis client 即可）
- KeyDB on FLASH 詳細調參
- Active-replication 內部複製協定細節

## 案例回寫

### 直接相關案例

| 案例                                                                                               | 對 KeyDB 的對應                                                                                                                                                                                           |
| -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [9.C35 Snap KeyDB cross-cloud](/backend/09-performance-capacity/cases/snap-gcp-keydb-cross-cloud/) | Snap 在 GCP 部署 KeyDB cluster、主因是 multi-cloud 的 cross-cloud latency 治理（cache 與 application 共置同 cloud）；9.C35 另記 KeyDB multi-threaded「單實例 throughput 提升 5-10x」（通則、依 workload） |

**待補 KeyDB-specific 案例**：Snap 收購後的公開技術分享、KeyDB on FLASH 的 production 成本案例、active-active 多主複製的跨區衝突治理實例。

### 跨 vendor 對照

| 案例                                                                                                | 對 KeyDB 的對應                                                          |
| --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| [2.C4 Meta CacheLib + Kangaroo](/backend/02-cache-redis/cases/meta-cachelib-kangaroo-tiered-cache/) | KeyDB on FLASH 對應 DRAM + flash 分層的成本決策                          |
| [2.C9 Cache Stampede](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/)     | TTL jitter / singleflight 通用、KeyDB 多執行緒不消除 stampede 風險       |
| [2.C10 規模對照](/backend/02-cache-redis/cases/contrast-cache-strategy-by-scale/)                   | KeyDB 是「單實例多核撐大」的選項、介於 Redis Cluster 與 DragonflyDB 之間 |

## 下一步路由

- deep article：[KeyDB active-active 多主複製](/backend/02-cache-redis/vendors/keydb/active-active-replication/)（last-write-wins 衝突與跨區寫入）
- 上游概念：[2.6 high concurrency](/backend/02-cache-redis/high-concurrency-access/)（單執行緒邊界的四個選項）
- 平行 vendor：[DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/)、[Valkey](/backend/02-cache-redis/vendors/valkey/)、[Redis](/backend/02-cache-redis/vendors/redis/)
- 下游能力：[2.7 cache copy boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/)（跨區資料引力）
- 回退路徑：[KeyDB → Redis/Valkey](/backend/02-cache-redis/vendors/keydb/migrate-to-redis/)
