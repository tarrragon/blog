---
title: "KeyDB → Redis / Valkey：從多線程 fork 回歸主線的遷移路徑"
date: 2026-06-22
description: "從 KeyDB 遷回 Redis 或 Valkey，處理 active-active replication 拆除、多線程 → 單線程效能差異、FLASH storage 移除與 Sentinel/Cluster 對齊"
weight: 11
tags: ["backend", "cache", "keydb", "redis", "valkey", "migration", "drop-in"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [KeyDB](/backend/02-cache-redis/vendors/keydb/)（source）跟 [Redis](/backend/02-cache-redis/vendors/redis/) / [Valkey](/backend/02-cache-redis/vendors/valkey/)（target）。跑 6 維 diff dimension audit 後判定為 **Type B drop-in**（KeyDB 是 Redis fork、RESP 相容、RDB/AOF 相容），但 active-active replication 跟 multi-threading 特性回退需要額外處理。

## 為什麼從 KeyDB 遷回

KeyDB 是 Snap 維護的 Redis fork，主要差異化在多線程和 active-active replication。遷回的 driver：

- **維護活躍度疑慮**：KeyDB 的 release cadence 跟 Redis/Valkey 主線比較慢，部分組織擔心長期維護與安全 patch 的及時性
- **Valkey 生態收斂**：Valkey 在 Linux Foundation 治理下快速演進（8.x 多線程改進），KeyDB 的多線程優勢逐漸縮小
- **Active-active 不再需要**：業務不再需要跨 region active-active、或改用 application 層處理衝突解析
- **社群與工具生態**：Redis/Valkey 的 client library、monitoring exporter、Operator 支援度更廣

## 6 維 diff dimension audit

| 維度                   | 評估                                                       | 等級   |
| ---------------------- | ---------------------------------------------------------- | ------ |
| Schema / API           | 完全相容（fork 自 Redis 6.x）                              | Low    |
| Operational model      | active-active → Sentinel/Cluster；multi-thread config 移除 | Medium |
| Abstraction / paradigm | 相同                                                       | Low    |
| Number of components   | 相近（1 primary + N replica + HA）                         | Low    |
| Application change     | endpoint 換、client config 微調                            | Low    |
| Data topology          | RDB/AOF 完全相容                                           | Low    |

Type B drop-in，工作重心在 active-active replication 拆除和效能 baseline 對齊。

## KeyDB 特有功能的處理

| KeyDB 特有功能                            | Redis/Valkey 對應                                                 | 遷移處理                                                                                   |
| ----------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Multi-threading（`server-threads`）       | Redis I/O threads / Valkey 8 async I/O                            | 回到 Redis 後吞吐量下降是預期，需要 benchmark 建立新 baseline                              |
| Active-active replication                 | 無原生等價。Redis 需要 application 層解衝突或用 CRDTs（社群方案） | 遷移前確認業務是否仍需 multi-master。不需要則直接切 Sentinel/Cluster                       |
| FLASH storage（`storage-provider flash`） | 無原生等價。Redis 純記憶體                                        | 遷移前把 FLASH 資料回收到記憶體，或接受遷移後記憶體需求上升。調整 `maxmemory`              |
| Subkey expires                            | Redis 無 subkey expire（只有 top-level key TTL）                  | 檢查 application 是否依賴 subkey expire；若有需要改寫為 top-level key 或用 sorted set 模擬 |
| `EXPIREMEMBER` 命令                       | Redis 無此命令                                                    | grep application code 確認未使用；若有需改寫                                               |

FLASH storage 的處理取決於冷資料比例。如果多數資料在 FLASH 上（用 `OBJECT FREQ` 確認），遷移後的 Redis 記憶體需求會大幅上升 — 要提前計算純記憶體所需容量，調整 instance 規格或改用更積極的 eviction policy。Subkey expires 和 `EXPIREMEMBER` 的影響範圍通常較小，但一旦 application 依賴就需要重構資料結構（用 top-level key + TTL 或 sorted set 模擬過期）。

### Active-active 拆除

若 KeyDB 的 active-active replication 正在使用，遷移前需要先收斂為單主寫入：

1. 選定一個 region 的 KeyDB 為 primary，其他 region 停止寫入
2. 等資料同步完成（replica 追上 primary offset）
3. 從 primary 做 RDB export
4. 用 RDB 建立 Redis/Valkey instance
5. 各 region 的 application 切到新的 Redis/Valkey（Sentinel 或 Cluster）

## 資料搬遷

KeyDB 的 RDB 和 AOF 與 Redis 格式相容，搬遷流程跟 DragonflyDB 回退類似：

```bash
# KeyDB 端觸發 BGSAVE
redis-cli -h keydb-host BGSAVE

# 複製 RDB 到 Redis/Valkey 資料目錄
scp keydb-host:/data/dump.rdb redis-host:/data/dump.rdb

# Redis/Valkey 載入
redis-server --dbfilename dump.rdb --dir /data
```

如果使用了 FLASH storage，RDB 只包含記憶體中的資料。FLASH 上的冷資料需要先用 `OBJECT FREQ` 確認存取頻率，決定是要 warm up 到記憶體再 export，還是接受遷移後冷資料 cache miss 回源。

## 效能差異預期

| 指標                  | KeyDB → Redis 變化                               | 應對                                                                                                                                            |
| --------------------- | ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 吞吐量                | 下降（KeyDB multi-thread → Redis single-thread） | 評估是否需要 Cluster 分片補償。Valkey 8 的 async I/O 可部分彌補                                                                                 |
| 記憶體                | 上升（若使用了 FLASH storage 被移除）            | 提前計算純記憶體所需容量，調整 instance 規格                                                                                                    |
| Latency p99           | BGSAVE fork spike 可能出現                       | KeyDB 的多線程降低了 fork 影響，回到 Redis 需要關注 [persistence fork latency](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/) |
| Active-active latency | 不適用（已拆除）                                 | N/A                                                                                                                                             |

## 回退路徑

Cache 資料可重建，回退方式：

1. Application endpoint 改回 KeyDB
2. 若 KeyDB 已下線，重啟 KeyDB 載入 Redis 的 RDB（格式相容）
3. Cache miss 回源到 DB 自然 warm up

KeyDB 保留 7 天再下線。

## 交接路由

- Source vendor：[KeyDB](/backend/02-cache-redis/vendors/keydb/)、[KeyDB Active-Active Replication](/backend/02-cache-redis/vendors/keydb/active-active-replication/)
- Target vendor：[Redis](/backend/02-cache-redis/vendors/redis/) / [Valkey](/backend/02-cache-redis/vendors/valkey/)
- HA 重建：[Sentinel HA Failover](/backend/02-cache-redis/vendors/redis/sentinel-ha-failover/)
- 效能參考：[Persistence Fork Latency](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)、[Connection Pipeline Latency](/backend/02-cache-redis/vendors/redis/connection-pipeline-latency/)
