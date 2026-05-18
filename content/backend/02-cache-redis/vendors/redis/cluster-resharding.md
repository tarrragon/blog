---
title: "Redis Cluster Re-sharding：source = target，但 topology 重劃的 5 段流程"
date: 2026-05-19
description: "Redis cluster re-sharding 是 5 type migration 漏類實證 — source / target 同 cluster、無 schema / paradigm 差、但 16384 slot 重分配是核心；本文涵蓋 4 種 re-sharding driver、slot migration 機制、redis-cli --cluster rebalance / reshard 工具、5 個 production 踩雷（cluster busy / replica lag / client cache stale / cross-slot transaction / monitor gap）"
weight: 13
tags: ["backend", "cache", "redis", "cluster", "resharding", "topology", "deep-article"]
---

> 本文是 [Redis](/backend/02-cache-redis/vendors/redis/) overview 的 implementation-layer deep article。本文是 [Migration playbook methodology](/posts/migration-playbook-methodology/) 「何時不該套」段的第 3 項實證（容量重新規劃 / re-sharding）— source / target 同 vendor 同 cluster、但 *data topology 重劃*、不在 5 type 內。

## Source = Target，但 topology 重劃

Migration 通常假設 *source 跟 target 是不同 cluster / vendor*；re-sharding 是 *同 cluster 內的 slot 重分配*、source 跟 target 是 *同一個 Redis Cluster 的不同 state*：

```text
Before re-shard:
  Cluster A: [node1: slots 0-5460] [node2: slots 5461-10921] [node3: slots 10922-16383]
              ~ 33% load           ~ 50% load              ~ 17% load (heavy imbalance)

After re-shard:
  Cluster A: [node1: slots 0-4095] [node2: slots 4096-8191] [node3: slots 8192-12287] [node4: slots 12288-16383]
              ~ 25% load           ~ 25% load              ~ 25% load              ~ 25% load
```

source 跟 target 是 *同 cluster*、區別在 *slot 對 node 的 mapping*。Application connection string 不變、cluster API 不變、data model 不變。但 *slot migration 期間* application 行為跟 *normal operation* 差很多 — 這是 re-sharding 主要工作。

跑 [diff dimension audit](/report/content-structure-by-max-diff-dimension/) 對 Redis cluster re-sharding：

| 維度                 | 評估                                  | 等級         |
| -------------------- | ------------------------------------- | ------------ |
| Schema / API         | 同 Redis、無變                        | Low          |
| Operational model    | 同 Redis Cluster、operational 不變    | Low          |
| Abstraction / paradigm | 同 Redis Cluster、無 paradigm 差    | Low          |
| Number of components | 同 1 個（cluster）                    | Low          |
| Application change   | 多數不改、client cluster mode 自處理   | Low          |
| **Data topology**    | **重劃** — slot mapping 跟 node 數    | **New axis** |

5 維皆 Low、對映 Type B drop-in；但 *data topology* 是 5 type 沒有的 *第 6 維度*。本文採用 *re-sharding-specific 結構*、不是 5 type 任一個。

## 4 種 re-sharding driver

不同 driver 對應不同 re-sharding 策略：

| Driver                | 觸發場景                                                     | 對應 re-sharding 操作                                    |
| --------------------- | ------------------------------------------------------------ | -------------------------------------------------------- |
| Slot imbalance        | 業務熱點打到部分 slot、單 node CPU / memory 80%+              | Rebalance（slot 重分配、不加 node）                      |
| Capacity expansion    | 整 cluster memory / throughput 上限快到、要加 node            | Add node + slot migration（從現有 node 搬部分 slot 過去）|
| Node decommission     | 老 node 硬體淘汰 / cloud instance 換代                        | Drain（該 node 的 slot 全搬走）+ remove                  |
| Hash tag refactor     | 業務 access pattern 變、需要 co-located key 群重分組          | Application-side migration（不是 cluster-level）         |

前 3 種是 cluster-internal、用 `redis-cli --cluster` 工具完成；第 4 種需要 application 端 dual-write + migration、本文不展開。

## Slot migration 機制

Redis Cluster 16384 個 slot、每個 key 經 `CRC16(key) % 16384` 對應 slot。Slot migration 過程：

```text
Source node:     [slot N: MIGRATING to dest]
Dest node:       [slot N: IMPORTING from source]
                 ↓
Source node:     SCAN slot N → for each key:
                 1. DUMP key (serialize value)
                 2. send to dest via MIGRATE command
                 3. dest RESTORE key
                 4. source DEL key
                 ↓
Source node:     [slot N: OWNED by dest]
Dest node:       [slot N: OWNED]
                 ↓
跨 cluster broadcast: slot N 屬於 dest
```

期間 client 行為：

- Key 在 source 端（未 migrate）：source 直接 serve
- Key 在 dest 端（已 migrate）：source 回 `-ASK` redirect、client 重發到 dest
- 寫入 MIGRATING slot 的新 key：source serve、之後也會 migrate
- Application 不需要改 code、cluster-aware client 自動處理 `-ASK` redirect

## redis-cli --cluster 工具

production 用 official tool、不要手寫 slot migration：

```bash
# 1. Rebalance（slot 重分配、適合 imbalance）
redis-cli --cluster rebalance 10.0.0.1:6379 \
  --cluster-use-empty-masters \
  --cluster-threshold 5

# 2. Reshard（指定來源 → 目標、適合 capacity expansion）
redis-cli --cluster reshard 10.0.0.1:6379 \
  --cluster-from <source-node-id> \
  --cluster-to <dest-node-id> \
  --cluster-slots 4096 \
  --cluster-yes

# 3. Add-node（加新 node 進 cluster）
redis-cli --cluster add-node 10.0.0.4:6379 10.0.0.1:6379 \
  --cluster-master-id <existing-master-id>

# 4. Del-node（移除 node、需先 drain slot）
redis-cli --cluster del-node 10.0.0.1:6379 <node-to-remove>
```

關鍵：

- `--cluster-threshold 5`：load 差異超過 5% 才 rebalance、避免反覆觸發
- `--cluster-slots`：一次 migrate 多少 slot；太大 lock 久、太小步驟多
- Rebalance / reshard 過程 cluster 仍 serve traffic、但 *latency 升高*（migration overhead）

## 5 段執行流程

```text
1. Pre-resharding analysis
   - 當前 slot 分佈跟 load
   - Hot key 識別（CLUSTER COUNTKEYSINSLOT）
   - 預估 migration 時間

2. Backup checkpoint
   - BGSAVE on all master
   - 確認 replica 跟得上（replication offset diff < 10MB）

3. Execute re-sharding
   - 用 redis-cli --cluster 工具
   - Monitor cluster health（CLUSTER INFO + CLUSTER NODES）
   - Migration 期間 application 端 latency baseline 比對

4. Verify
   - Slot distribution 對 expected mapping
   - Application traffic pattern 對 baseline
   - 跑 cross-node sanity check

5. Cleanup
   - 舊 node（若 decommission）reset / 釋放
   - Monitoring dashboard 更新 (Prometheus target / Grafana panel)
   - Document new topology
```

整體 1-7 天、依 cluster 大小（10GB ~ 1 小時、TB 級 1-3 天）。

## Production 故障演練

### Case 1：Cluster busy 期間 application timeout

**徵兆**：re-sharding 跑到一半、application 端開始大量 `CLUSTER BUSY` error / `OOM` warning / latency p99 從 5ms 跳到 200-2000ms；某些 batch operation 完全失敗。

**根因**：MIGRATE command 對單 key 是 *blocking*（DUMP + send + RESTORE + DEL atomic）— 大 value（HASH / SORTED SET / LIST 含 100K+ entry）migration 可能 lock node 數秒；同期間其他 query 阻塞。

**修法**：

1. **Pre-resharding audit**：`MEMORY USAGE` 跑 sample key、找 > 1MB 的 *fat key*、列出單獨處理
2. **MIGRATE timeout 調**：`redis.conf` 設 `cluster-migration-timeout 10000`（10s）、避免單 key migration 卡爆 cluster
3. **降低並行**：`--cluster-pipeline 1` 一次只搬一個 slot（預設 10）、減少 CPU 壓力
4. **Fat key refactor**：production 不該有 1M+ entry 的 collection、refactor 拆分

### Case 2：Replica lag during re-sharding

**徵兆**：reshard 完成後、replica 顯示 stale data 數分鐘、application 端 read from replica 拿到舊值。

**根因**：master 端 slot migration 產生大量 `DEL` + `RESTORE` 命令、replication stream 量爆、replica 跟不上、accumulated lag。

**修法**：

1. **Pre-resharding 確認 replica lag < 5MB**、否則先 fix replica issue 再開始
2. **Throttle migration**：用 `--cluster-replace` + lower pipeline、放慢 master 寫入速度
3. **Application 端 read-write split policy**：reshard 期間強制 read from master、暫時放棄 replica read
4. **預備計畫**：若 lag > 30s 撐了 5+ 分鐘、考慮暫停 reshard、wait replica catch up

### Case 3：Client-side topology cache stale

**徵兆**：reshard 完、application 端持續報 `MOVED <slot> <new-node>` redirect、但隔 30s 又 redirect 一次；某些 client 直接 connection refused（連到已 decommission node）。

**根因**：cluster-aware client（lettuce / Jedis cluster mode）有 *topology cache*、reshard 後不主動 refresh；遇 MOVED 後 refresh 一次、但 cache TTL 內可能繼續用舊 mapping。

**修法**：

1. **Client config**：lettuce `clusterTopologyRefreshOptions(...)` 設較短 refresh interval（60s）+ `enablePeriodicRefresh()`
2. **Reshard 完後 trigger refresh**：application 端可主動發 `CLUSTER NODES` 拿最新 topology、不依賴 client lib 自動 refresh
3. **Graceful client shutdown / restart**：對 latency-sensitive 服務、reshard 完 rolling restart application pod、避免 stale cache
4. **Decommissioned node 保留 5 分鐘**：不立刻 stop node、給 stale client 自然 retry 機會

### Case 4：Cross-slot transaction 失敗

**徵兆**：application 用 `MULTI/EXEC` 跨多 key、reshard 期間部分 transaction 報 `MOVED` error、整個 transaction 失敗、business logic 不一致。

**根因**：Redis Cluster transaction 要求 *所有 key 在同 slot*（用 hash tag `{user:123}`）；reshard 期間如果 transaction 內某 key migrate 到 dest、cluster topology 暫時 inconsistent、transaction 拒絕。

**修法**：

1. **Pre-resharding audit**：grep application code 找 MULTI / pipeline 使用、確認所有都用 hash tag co-locate
2. **Reshard 期間 application 端加 retry**：transaction failure 後 backoff retry、cluster stabilize 後成功
3. **架構**：transaction-heavy 場景考慮不用 Redis Cluster、用 Redis Sentinel single master（無 slot 概念）

### Case 5：Monitor visibility gap during reshard

**徵兆**：reshard 期間 Prometheus dashboard 對某 node 的 metric 突然顯示 *錯位* — load = 95% 但 slot count 顯示 6% slot；SOC 不知道 node 健康狀況。

**根因**：Prometheus exporter 對 *slot count* 跟 *traffic load* 分開計算；reshard 期間 slot count 已 migrate 但流量仍打 source node（client cache stale）— metric 看似矛盾。

**修法**：

1. **Reshard 期間關 alert**：knownmaintenance window、Prometheus silence alert
2. **加 reshard-aware metric**：用 `redis_cluster_migration_slots` 量化 in-flight migration
3. **Dashboard 加註解**：reshard 期間 SOC 看 dashboard 知道是 *normal anomaly*

## Capacity / cost

| 維度                    | 估算                                                        | 警戒                                                          |
| ----------------------- | ----------------------------------------------------------- | ------------------------------------------------------------- |
| Slot migration 速度     | 1-10K key / sec（依 key size + network）                     | TB 級 10K key / sec → 1 天                                  |
| Application latency impact | p99 +50-200% during migration                             | 設 latency budget、超出暫停                                  |
| Memory / node           | 不變、但 temporary 雙寫期間 +5-15%                          | 不能在 memory 90%+ 時 reshard                                |
| Network bandwidth       | 跨 node 大流量、~100-500 Mbps per migration stream         | 跨 AZ reshard egress cost 注意                                |
| Recovery time           | Reshard 失敗回退 = 反向 reshard（時間相同）                 | 不能在 incident 期間 reshard                                  |

實務 default：

- 跑在 *低流量時段*（夜間 / 週末）
- Throughput 容忍度 < 50% 再 reshard、不要 80%+ 時操作
- 預留 *回退 window* — reshard 卡住時能 abort + 恢復原狀

## 整合 / 下一步

### 跟 [Redis → DragonflyDB migration](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/) 對位

DragonflyDB 設計上 *單機效能取代 cluster*、re-sharding 議題消失；如果 cluster re-sharding 頻繁觸發、評估直接遷 DragonflyDB 是否更便宜。

### 跟 [Sentinel HA](/backend/02-cache-redis/vendors/redis/) 對比

Sentinel 模式無 slot 概念、re-sharding 不適用；但 *manual sharding by application* 場景仍可能需要類似 topology re-layout、application 端要自己處理。

### 跟 Redis 7+ Function / Cluster v2

Redis 7 推 Cluster v2 跟 Functions、slot migration 機制部分升級；keyspace migration 仍是核心議題、但 API 跟 monitoring 改進。

### 下一步議題

- **Auto-rebalance via operator**：Redis Enterprise / Aiven 等 managed Redis 提供自動 rebalance、不需手動觸發
- **Cross-DC slot migration**：跨 region cluster slot migration 對 latency / cost 影響大、通常用 *application-level sharding* 取代 cluster-level
- **Hash tag 治理**：application code grep / lint 強制 hash tag、避免 cross-slot transaction 反模式

## 相關連結

- 上游 vendor 頁：[Redis](/backend/02-cache-redis/vendors/redis/)
- 平行 migration playbook：[Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/)
- 對位 deep article：[PostgreSQL major version upgrade](/backend/01-database/vendors/postgresql/major-version-upgrade/)（另一個 5 type 漏類驗證）
- Methodology：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/) / [Migration playbook methodology](/posts/migration-playbook-methodology/)（本文驗證 *容量重劃漏類*）
