---
title: "DragonflyDB → Redis / Valkey：回退到標準生態的遷移路徑"
date: 2026-06-22
description: "從 DragonflyDB 遷回 Redis 或 Valkey，處理 snapshotting → RDB/AOF 差異、HA 架構切換與 Cluster mode 重建的階段化流程"
weight: 11
tags: ["backend", "cache", "dragonflydb", "redis", "valkey", "migration", "drop-in"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/)（source）跟 [Redis](/backend/02-cache-redis/vendors/redis/) / [Valkey](/backend/02-cache-redis/vendors/valkey/)（target）。反向路徑見 [Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/)。跑 6 維 diff dimension audit 後判定為 **Type B drop-in**（RESP 協定相容），但 HA 和持久化有差異需要處理。

## 為什麼從 DragonflyDB 遷回

DragonflyDB 遷回 Redis/Valkey 的 driver 跟正向遷移互為鏡像：

- **Redis Modules 需求**：業務開始需要 RedisJSON、RediSearch 或 RedisTimeSeries，DragonflyDB 不支援 Redis Modules 生態
- **Cluster mode 需求**：DragonflyDB 設計為單機 scale-up，當資料量超過單機記憶體上限（數 TB）或需要跨 node sharding 時，Redis Cluster 或 Valkey Cluster 是成熟選擇
- **Sentinel / HA 生態**：DragonflyDB 的 HA 用自家 replication，不支援 Sentinel。若團隊已有 Sentinel 或 Operator 基礎設施，回到 Redis/Valkey 整合成本更低
- **BSL 授權疑慮**：DragonflyDB 是 BSL 1.1（4 年後轉 Apache 2.0），部分組織偏好 BSD（Valkey）或即使是 RSALv2（Redis）的已知授權

## 6 維 diff dimension audit

| 維度                   | 評估                                                                             | 等級   |
| ---------------------- | -------------------------------------------------------------------------------- | ------ |
| Schema / API           | RESP 相容、data types 一致                                                       | Low    |
| Operational model      | DragonflyDB replication → Sentinel/Cluster；snapshotting → RDB+AOF               | Medium |
| Abstraction / paradigm | 相同（key-value cache）                                                          | Low    |
| Number of components   | DragonflyDB 1-2 nodes → Redis primary + replica + Sentinel（或 Cluster 6 nodes） | Medium |
| Application change     | endpoint 換、client config 微調（無 API 差異）                                   | Low    |
| Data topology          | DragonflyDB snapshot → Redis RDB 相容                                            | Low    |

全域 Low-Medium → **Type B drop-in**，工作重心在 HA 架構切換和持久化模式對齊。

## 相容性確認

DragonflyDB → Redis 的相容方向跟 Redis → DragonflyDB 相反 — Redis 是 superset，回到 Redis 不會有功能缺失。但有幾個操作面差異需要處理：

| DragonflyDB 行為      | Redis 行為                              | 處理方式                                                                                                                              |
| --------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Multi-threaded 吞吐量 | 單主線程（I/O threads 輔助）            | 回到 Redis 後 throughput 下降是預期行為；若單機不夠需要 Cluster 分片                                                                  |
| Fork-less snapshot    | BGSAVE fork + COW                       | 關注 [persistence fork latency](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)，大 dataset 的 fork 會造成延遲 spike |
| 自家 replication      | Redis replication + Sentinel 或 Cluster | 需要重建 HA 架構，見下方階段二                                                                                                        |
| 無 AOF                | AOF + RDB 混合持久化                    | 依需求決定是否開 AOF；純 cache 場景可只用 RDB                                                                                         |
| 無 Cluster mode       | Redis Cluster 或 Valkey Cluster         | 資料量大時需要規劃 sharding                                                                                                           |

## 階段一：資料匯出

DragonflyDB 支援 `SAVE` / `BGSAVE` 產生 RDB 格式 snapshot，跟 Redis RDB 相容。

```bash
# 在 DragonflyDB 觸發 snapshot
redis-cli -h dragonfly-host BGSAVE

# 等 BGSAVE 完成
redis-cli -h dragonfly-host LASTSAVE

# 複製 snapshot 檔案到 Redis 資料目錄
cp /dragonfly-data/dump.rdb /redis-data/dump.rdb
```

RDB 載入驗證：

```bash
# 啟動 Redis 載入 RDB
redis-server --dbfilename dump.rdb --dir /redis-data

# 驗證 key count
redis-cli DBSIZE
```

若 DragonflyDB 跑的是較新版本產出的 RDB，先在測試環境驗證 Redis 能正常載入。DragonflyDB 的 RDB 基於 Redis 6.x 格式，Redis 7.x 和 Valkey 8.x 向下相容無問題。

## 階段二：HA 架構重建

DragonflyDB 回到 Redis/Valkey 後，HA 需要從 DragonflyDB replication 切換到 Sentinel 或 Cluster。

### Sentinel 路徑（適合非分片場景）

1 primary + N replica + 3 Sentinel nodes。配置見 [Sentinel HA Failover](/backend/02-cache-redis/vendors/redis/sentinel-ha-failover/)。

### Cluster 路徑（適合需要分片的場景）

最小 3 primary + 3 replica。配置見 [Redis Cluster Resharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)。

選擇依據：資料量 < 單機記憶體的 70% 用 Sentinel，需要水平擴展用 Cluster。

## 階段三：Client 切換

Application 的 Redis client 不需要改 API — DragonflyDB 跟 Redis 用同一套 RESP 協定。需要改的只有：

1. **Endpoint**：從 DragonflyDB host:port 改為 Redis primary（或 Sentinel/Cluster endpoint）
2. **認證**：若 DragonflyDB 用 `requirepass`，Redis 同參數；若要升級到 ACL 趁此機會配置
3. **Sentinel/Cluster 配置**：client library 需要啟用 Sentinel discovery 或 Cluster mode

```python
# 切換前：直連 DragonflyDB
r = redis.Redis(host="dragonfly-host", port=6379, password="secret")

# 切換後：Sentinel 模式
sentinel = redis.Sentinel([("sentinel-1", 26379), ("sentinel-2", 26379), ("sentinel-3", 26379)])
r = sentinel.master_for("mymaster", password="secret")
```

## 階段四：效能 baseline 與回退

### 效能預期

回到 Redis 後，單機 throughput 會低於 DragonflyDB（Redis 單主線程 vs DragonflyDB 多線程）。建立 baseline 時要跟 Redis 的歷史數據比，不是跟 DragonflyDB 比。

| 指標        | 預期變化                          | 應對                                  |
| ----------- | --------------------------------- | ------------------------------------- |
| 吞吐量      | 下降（單線程限制）                | Cluster 分片或 read replica 分散      |
| Latency p99 | BGSAVE 期間可能有 spike           | 調整 BGSAVE 排程避開高峰              |
| 記憶體使用  | 上升 ~30%（Redis 記憶體效率較低） | 預先調整 maxmemory 和 eviction policy |

### 回退路徑

回退到 DragonflyDB：把 Redis 的 RDB dump 回 DragonflyDB 載入，endpoint 改回。Cache 資料可重建，即使 RDB 不搬，DragonflyDB 重啟後 cache miss 回源到 DB 即可。

DragonflyDB 在遷移完成後保留 7 天再下線。

## 交接路由

- Source vendor：[DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/)
- Target vendor：[Redis](/backend/02-cache-redis/vendors/redis/) / [Valkey](/backend/02-cache-redis/vendors/valkey/)
- 反向路徑：[Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/)
- HA 重建：[Sentinel HA Failover](/backend/02-cache-redis/vendors/redis/sentinel-ha-failover/)、[Cluster Resharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)
- 持久化注意：[Persistence Fork Latency](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)
