---
title: "PostgreSQL Partition Redesign：當 monthly partition 越跑越慢"
date: 2026-05-19
description: "PostgreSQL partition redesign 是 Type F「topology re-layout」第 2 個 dogfood — 從 monthly partition 改 daily / 從 range 改 list / 從單軸改 sub-partition；6 維 audit 皆 Low + topology 軸 High；涵蓋 partition 不平衡偵測、ATTACH/DETACH 線上重劃、5 個 production 踩雷、跟 partition_pruning + autovacuum 整合"
weight: 44
tags: ["backend", "database", "postgresql", "partition", "topology", "type-f", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。對應 [#127 Type F「Topology re-layout」](/report/content-structure-by-max-diff-dimension/) 第 2 個 dogfood（第 1 個是 [Redis cluster re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)）— 驗證 Type F anatomy 在不同 vendor 上的通用性。

## 為什麼 monthly partition 越跑越慢

上線時 monthly range partition 設計很合理 — 每月一個 partition、12 個月一年、partition_pruning 在 `WHERE event_time >= '2026-05-01'` 時跑單 partition、查詢快。但業務跑了 18 個月後：

- 每月 partition size 從 50GB 漲到 500GB（流量 10x）
- 單月查詢 `WHERE event_time BETWEEN '2026-05-01' AND '2026-05-15'` 仍掃整月 500GB（partition_pruning 粒度只到 month）
- Vacuum 一個月 partition 需要 6-8 小時、跑不進 maintenance window
- DROP 老 partition 釋放 storage 是 monthly cadence、但 retention policy 要求 daily granularity

partition 設計需要 *redesign*、不是「optimize」 — 從 monthly range partition 改成 daily range partition、partition 數量從 36 個（3 年 retention）變 1095 個。

[diff dimension audit](/report/content-structure-by-max-diff-dimension/) 結果：

| 維度               | 評估                                             | 等級     |
| ------------------ | ------------------------------------------------ | -------- |
| Schema / API       | 同 PostgreSQL、同 table 定義、partition key 不變 | Low      |
| Operational model  | 同 PostgreSQL operational stack                  | Low      |
| Paradigm           | 同 OLTP RDBMS                                    | Low      |
| Components         | 同 1 個 DB                                       | Low      |
| Application change | 不改（partition_pruning 透明）                   | Low      |
| **Data topology**  | **Partition strategy 從 monthly → daily**        | **High** |

6 維皆 Low + topology High = [Type F「Topology re-layout」](/report/content-structure-by-max-diff-dimension/)。

## Pre-layout analysis：partition 不平衡偵測

執行 redesign 前必須先量化當前 topology：

```sql
-- 1. 每 partition size + row count
SELECT
  child.relname AS partition_name,
  pg_size_pretty(pg_relation_size(child.oid)) AS size,
  child.reltuples::bigint AS estimated_rows,
  pg_stat_get_last_vacuum_time(child.oid) AS last_vacuum
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname = 'events'
ORDER BY pg_relation_size(child.oid) DESC;

-- 2. partition_pruning 命中率
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM events
WHERE event_time BETWEEN '2026-05-01' AND '2026-05-15';
-- 期望: 只 scan 1 partition (target: daily) 或 1 partition (current: monthly)
-- 觀察: monthly 設計下、即使 query 只跨 15 天、planner 仍 scan 整月 partition (~500GB)

-- 3. 找 partition imbalance
SELECT
  to_char(event_time, 'YYYY-MM') AS month,
  count(*) AS row_count
FROM events
GROUP BY 1
ORDER BY 2 DESC;
-- 找 hot month / cold month、判斷 redesign 後分佈
```

Pre-layout 階段的 output：

- **當前 topology 量化**：36 monthly partition、總 size 1.8TB、最大 partition 500GB、最小 50GB
- **Hot key 分佈**：80% 流量集中最近 3 個月
- **Redesign 目標**：daily partition、最近 3 個月 hot daily / 3 個月 + 之前 cold weekly / 1 年 + 之前 monthly（sub-partition strategy）
- **Migration scope**：1095 個 partition 不直接全建、按 retention policy 階段性

## Re-layout 機制：ATTACH / DETACH 線上重劃

PostgreSQL 不支援「直接改 partition strategy」、必須走 *新 partition tree + 資料搬遷*：

```sql
-- 1. 建新 daily partition table (parallel to events)
CREATE TABLE events_daily (
  id bigint,
  event_time timestamptz NOT NULL,
  payload jsonb
) PARTITION BY RANGE (event_time);

-- 2. 預建未來 90 天 daily partition
SELECT
  format(
    'CREATE TABLE events_daily_%s PARTITION OF events_daily FOR VALUES FROM (%L) TO (%L)',
    to_char(d, 'YYYY_MM_DD'), d, d + interval '1 day'
  )
FROM generate_series(current_date, current_date + interval '90 days', interval '1 day') AS d;

-- 3. dual-write phase: application 同寫 events + events_daily
-- (用 trigger 或 application-side)
CREATE OR REPLACE FUNCTION dual_write_events() RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO events_daily VALUES (NEW.*);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER events_dual_write
AFTER INSERT ON events
FOR EACH ROW EXECUTE FUNCTION dual_write_events();

-- 4. backfill historical data per partition
INSERT INTO events_daily
SELECT * FROM events
WHERE event_time >= '2026-05-01' AND event_time < '2026-05-02';
-- ... 每天跑一個 day partition、avoid long transaction

-- 5. cutover: rename swap
BEGIN;
ALTER TABLE events RENAME TO events_old;
ALTER TABLE events_daily RENAME TO events;
DROP TRIGGER events_dual_write ON events_old;
COMMIT;

-- 6. 觀察 1-2 週、DROP events_old
```

關鍵：rename swap 是 *single transaction*、cutover 瞬間發生；application connection 不需重連、但 prepared statement cache 可能要刷新。

## Execution flow per-step

5 段、每段含 rollback boundary：

| Step             | 動作                                                           | Rollback boundary                                      |
| ---------------- | -------------------------------------------------------------- | ------------------------------------------------------ |
| 1 預建 partition | 建 events_daily + 90 天 partition、不影響 production           | DROP events_daily、無 impact                           |
| 2 Dual-write     | 加 trigger 同寫兩端、observe diff                              | DROP trigger、events_daily 留作 cleanup                |
| 3 Backfill       | 逐日 backfill 歷史資料、用 CHECK constraint 確保完整性         | DROP backfilled partition、不影響 source events        |
| 4 Verify         | 對 sample query 跑 events vs events_daily、確認 row count 一致 | 仍在 dual-write、發現 diff 可暫停 cutover              |
| 5 Cutover        | Rename swap                                                    | **不可逆**、回退需 reverse rename + dual-write restart |

Step 5 是不可逆邊界、應該排在 *低流量 maintenance window* 跑、且 cutover 前必須有 backup checkpoint。

## Production 故障演練

### Case 1：Backfill 期間 long transaction 阻塞 vacuum

**徵兆**：backfill 跑 6 小時的 `INSERT INTO events_daily SELECT * FROM events WHERE ...`、期間 events 表的 autovacuum 完全不跑、dead tuple 累積、production query 變慢。

**根因**：PostgreSQL transaction 期間 *xmin horizon 鎖死*、vacuum 只能回收「不會被任何 active transaction 看到」的 dead tuple；long backfill = long open transaction、vacuum 失效。

**修法**：

1. **拆 batch INSERT**：每日 backfill 拆成 small batch（10 萬 row 一個 transaction）、每個 commit 釋放 xmin
2. **用 COPY 不用 INSERT**：`COPY events_daily FROM (SELECT * FROM events WHERE ...)` 是 PG 對 batch 最快 + 對 vacuum 影響小
3. **Backfill 跑在 standby**：用 logical replication 從 standby 拉資料、不在 primary 跑長 transaction

### Case 2：Trigger dual-write 對 application 造成 latency

**徵兆**：加 trigger 後 application 寫入 latency p99 從 5ms 漲到 25-50ms；high-throughput batch job 直接 timeout。

**根因**：每筆 INSERT 都觸發 trigger function 跑一次 INSERT 到 events_daily、IO 雙倍、index 也雙倍維護。

**修法**：

1. **改 application-side dual-write**：application code 顯式寫兩端、用 connection pool batch 攤平 IO
2. **用 logical replication slot**：events → events_daily 用 logical replication 取代 trigger、降 IO 衝擊
3. **dual-write 時間最小化**：trigger 只在 backfill + verify 期間打開、cutover 前關掉

### Case 3：Partition_pruning 沒命中、planner 仍掃所有 partition

**徵兆**：cutover 完成後、application 端某些 query latency 從 200ms 跳到 5000ms；EXPLAIN 顯示 `Append` 下面所有 1095 個 partition 都被 scan。

**根因**：partition 數量爆到 1000+、planner planning_time 對某些 query 變長（含 prepared statement 沒帶 partition key bound）；或 query 用了 `WHERE event_time = some_function(now())`、planning-time pruning 不觸發。

**修法**：

1. **`enable_partition_pruning = on`** 預設、確認沒被 disable
2. **PG 11+ runtime pruning**：prepared statement 用 generic plan、runtime pruning 補位
3. **Sub-partition strategy**：1095 個 daily 太多、改 *最近 90 天 daily / 之前 monthly* 混合 strategy、減 partition count
4. **Planner statistics**：跑 `ANALYZE` 重建 statistics、partition 樹太大時 planner 需新 stats

### Case 4：Constraint exclusion 失敗、跨 partition unique 不 enforce

**徵兆**：cutover 後發現某 user 的 event 在多個 partition 都有、unique constraint `(user_id, event_id)` 沒 enforce；data audit 抓到 duplicate。

**根因**：PostgreSQL partition table 的 `UNIQUE` constraint *必須包含 partition key*；本來 monthly partition 下 `UNIQUE (user_id, event_id)` 加上 `event_time`（partition key）變 `UNIQUE (user_id, event_id, event_time)`、實際語意是「同月同 user 同 event_id 唯一」；改 daily 後變「同日同 user 同 event_id 唯一」— unique scope 從月變天、原本月內跨日 dedup 失效。

**修法**：

1. **Pre-redesign**：明示 unique constraint 的 *時間 scope*、redesign 後 scope 縮小是否可接受
2. **Application-side dedup**：跨 partition 唯一性走 application 層 lookup（用 Redis SETEX 暫存 key）
3. **退到 non-partitioned dedup 表**：建獨立 user_events_dedup 表、application 寫入前先 lookup

### Case 5：DROP 老 partition 太頻繁、shared_buffers cache miss 爆

**徵兆**：daily partition 上線後、每天凌晨 cron DROP `events_2025_05_18`（90 天前）；DROP 後 shared_buffers 大量 invalidate、application 端 query latency p99 從 10ms 跳到 100-200ms 持續 30 分鐘。

**根因**：PostgreSQL shared_buffers cache 對被 DROP 表的 page 全部 invalidate；DROP 大 partition（10GB+）後 cache hit rate 從 99% 掉到 60%、application 等 disk IO。

**修法**：

1. **DROP 跑在 off-peak**：凌晨 3-4 點 cron、避開業務高峰
2. **預熱 next partition**：DROP 前用 `pg_prewarm` 主動 load 熱 partition 進 cache
3. **改 DETACH + DROP TABLE delayed**：DETACH 是 fast、DROP TABLE 排到 weekly batch、降頻率

## Capacity / cost

| 維度                  | Monthly partition (current) | Daily partition (target)     | Trade-off                              |
| --------------------- | --------------------------- | ---------------------------- | -------------------------------------- |
| Partition count       | 36 (3 年 retention)         | 1095 (3 年 retention)        | 30x partition count、planner cost 略升 |
| Single partition size | 50-500GB                    | 1-20GB                       | Daily 更易 vacuum                      |
| DROP old data         | Monthly cadence             | Daily cadence                | 更細 retention 控制                    |
| Query latency         | 跨 partition 多時 50-200ms  | 跨 partition 少時 5-50ms     | Daily 多數 query 更快                  |
| Planning time         | 5-10ms                      | 50-100ms (對 generic plan)   | Planning overhead + 1 order            |
| Maintenance window    | Vacuum 1 partition 6 小時   | Vacuum 1 partition 5-30 分鐘 | 維護視窗更小、可日跑                   |

**判讀**：daily partition 適合 *高流量 + 跨日查詢多 + retention 細的場景*；超大 partition (TB 級單日) 仍要 sub-partition 拆。

## 整合 / 下一步

### 跟 [autovacuum tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/) 整合

Daily partition 後 autovacuum 行為：

- 每 daily partition 獨立 autovacuum、scale_factor + threshold per-partition tuning
- `autovacuum_max_workers` 要從 3 拉到 6-10（partition 數爆）
- Cold partition (> 30 天) `autovacuum_enabled = false`、不浪費 CPU

### 跟 [Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/) 整合

Failover 期間 partition migration 不能跑、必須在 stable cluster state 執行；Patroni promote 後重新評估 partition health。

### 跟 [Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/) 整合

`publish_via_partition_root = true` 讓 publication 從 parent 角度看；CDC consumer 不需要對每個 partition 設 subscription。

### 下一步議題

- **跨 daily partition 的 archive strategy**：archive 到 S3 cold storage、daily granularity 給更細 retention 控制
- **pg_partman extension**：自動建 daily partition、不用 cron；但要先確認 Aurora / RDS 支援
- **Sub-partitioning**：未來流量爆時用「daily by time + list by tenant」雙軸 partition

## 相關連結

- 上游 vendor 頁：[PostgreSQL](/backend/01-database/vendors/postgresql/)
- 平行 deep article：[Declarative Partitioning](/backend/01-database/vendors/postgresql/declarative-partitioning/)（partition 基礎）/ [Autovacuum Tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)
- 平行 Type F dogfood：[Redis Cluster Re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)（dogfood #1）/ [MongoDB Shard + Multi-DC](/backend/01-database/vendors/mongodb/shard-expansion-multi-dc/)（dogfood #3、F-multi-region sub-type）
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/) / [#127 Process content 結構由最大差異維度決定](/report/content-structure-by-max-diff-dimension/) / [#128 Data topology 是第 6 audit 維度](/report/data-topology-as-audit-dimension/)
