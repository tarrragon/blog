---
title: "PostgreSQL Query Optimization：EXPLAIN ANALYZE / pg_hint_plan / auto_explain 三層工具跟 4 個 case"
date: 2026-05-19
description: "PG query 慢的根因常是 *planner 選錯 plan 或 statistics 過時*。本文從 4 個 production case 開場（seq scan vs index / hash vs nested loop / 多 column 統計缺 / parallel query 沒觸發）、走 EXPLAIN / EXPLAIN ANALYZE / auto_explain 三層工具、pg_hint_plan extension 跟 planner GUC 取捨、5 production 踩雷（ANALYZE 過時 / multi-column statistics / cost-base setting 不對齊硬體 / random_page_cost SSD 沒調 / parallel query 配置）、跟 MySQL query-optimization sibling 對比"
weight: 21
tags: ["backend", "database", "postgresql", "query-optimization", "explain", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 PG 在 OLTP 譜系的定位、本文聚焦 *query optimization* — EXPLAIN ANALYZE / auto_explain / pg_hint_plan 三層工具跟 4 個實際 case。

---

## 4 個常見 production case

PG query 慢的 root cause 多數是 *planner 選錯 plan*。從以下 4 個 case 進入 query optimization：

### Case 1：5 秒 → 50ms — Seq scan vs index

```sql
-- 慢 (5 秒)
SELECT o.id, o.amount, c.name
FROM orders o JOIN customers c ON o.customer_id = c.id
WHERE c.region = 'TW' AND o.created_at > '2026-05-01';
```

`EXPLAIN (ANALYZE, BUFFERS)`：

```text
Hash Join  (cost=20000..50000 rows=100 width=...) (actual time=4900..5000 rows=10000)
  ->  Seq Scan on customers c  (cost=0..20000 rows=1000000 width=...)
      Filter: (region = 'TW')
      Rows Removed by Filter: 900000
  ->  Hash  (cost=...)
      ->  Index Scan on orders_created_idx
```

問題：`customers.region` 沒 index、planner 選 seq scan、實際 region=TW 只 10% row。修法：

```sql
CREATE INDEX CONCURRENTLY idx_customers_region ON customers(region);
ANALYZE customers;  -- 更新 statistics、讓 planner 看到新 index
```

加完 5 秒降 50ms。

### Case 2：30 秒 → 200ms — Hash join 沒觸發、用 nested loop

```sql
SELECT u.name, count(o.id)
FROM users u LEFT JOIN orders o ON o.user_id = u.id
GROUP BY u.name;
```

EXPLAIN ANALYZE 顯示 *Nested Loop* 跑 1M 次 inner loop、執行 30 秒。Planner 估錯 row count、選 nested loop。Hash join 應該 < 200ms。

修法：

```sql
ANALYZE users;
ANALYZE orders;
-- 提高 default_statistics_target 對 critical column
ALTER TABLE orders ALTER COLUMN user_id SET STATISTICS 1000;
ANALYZE orders;
```

統計精度提升、planner 估 row count 準、自動切 hash join。

### Case 3：8 秒 → 100ms — Multi-column 統計缺

```sql
SELECT * FROM orders WHERE status = 'pending' AND region = 'TW';
```

`status = 'pending'` 5% row、`region = 'TW'` 10% row。Planner 假設兩 column 獨立、估 0.5% (5K row)。實際 status='pending' 跟 region='TW' 強相關（TW 訂單多 pending）、實際 4% (40K row)。Planner 估錯 8x、選錯 plan。

修法（PG 10+）：

```sql
CREATE STATISTICS stats_orders_status_region (dependencies, ndistinct, mcv)
ON status, region FROM orders;
ANALYZE orders;
-- 之後 planner 知道 status+region 相關度、估準
```

### Case 4：20 秒 → 5 秒 — Parallel query 沒觸發

```sql
SELECT region, count(*), sum(amount) FROM orders GROUP BY region;
```

`orders` 100M row、預期 PG parallel scan + parallel aggregate、實際 single worker 跑 20 秒。

EXPLAIN：`Workers Planned: 0`。

修法：

```ini
# postgresql.conf
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
max_worker_processes = 16
parallel_setup_cost = 100        # 預設 1000、降低讓 planner 更敢 parallel
parallel_tuple_cost = 0.01       # 預設 0.1
```

並行後 5 秒。

## EXPLAIN 三層工具

### Tool 1：EXPLAIN — Plan preview

```sql
EXPLAIN SELECT ...;
```

輸出每個 node 的 *估計* cost / row count / width。**用於 quick plan check**。

關鍵欄位：

- `Plan node 類型`：`Seq Scan` < `Index Scan` < `Index Only Scan`、警訊看 *unexpected* node type
- `cost=START..END`：planner 估的 cost、START 是 startup cost、END 是 total
- `rows`：估計 output row 數
- `width`：每 row average byte（影響 sort / hash memory）

### Tool 2：EXPLAIN ANALYZE — 實際執行 + 對比 estimate

```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE) SELECT ...;
```

差別：實際 *跑 query*、輸出實際 row count / time、跟 estimate 對比：

```text
Hash Join  (cost=20000..50000 rows=100) (actual time=400..500 rows=10000 loops=1)
```

`rows=100 (estimate)` vs `rows=10000 (actual)` — 估錯 100x、planner 可能選錯 plan。`BUFFERS` 顯示 disk read vs buffer cache hit。

**注意**：EXPLAIN ANALYZE *實際跑 query*、修改性 query（UPDATE / DELETE）會真的改 data。讀 query 安全。修改性 query 包 transaction：

```sql
BEGIN;
EXPLAIN ANALYZE UPDATE orders SET status = 'x' WHERE ...;
ROLLBACK;
```

### Tool 3：auto_explain — Production query 自動 capture

`auto_explain` extension 自動 log slow query 的 plan：

```ini
# postgresql.conf
shared_preload_libraries = 'auto_explain'
auto_explain.log_min_duration = '1s'    # 超過 1 秒 log plan
auto_explain.log_analyze = on            # 含 ANALYZE 統計
auto_explain.log_buffers = on
auto_explain.log_format = 'json'         # JSON 格式給工具消費
```

Production slow query 自動進 log、不必手動 EXPLAIN。組合 pg_stat_statements + auto_explain 是 PG 標準 query observability。

## pg_hint_plan vs Planner GUC

PG 兩種方式 nudge planner：

### Planner GUC（global）

`postgresql.conf` 內：

- `enable_seqscan = off` — 禁用 seq scan（force index）
- `enable_nestloop = off` — 禁用 nested loop（force hash/merge join）
- `random_page_cost = 1.1` — SSD 設低（預設 4 是 HDD assumption）
- `effective_cache_size = '16GB'` — buffer pool + OS cache 估、影響 planner

GUC 是 *global* — 影響所有 query。對 *單一 query 用 hint*：

### pg_hint_plan extension（per-query hint）

```sql
-- 強制特定 plan
/*+ IndexScan(orders idx_orders_status) NestLoop(orders customers) */
SELECT ... FROM orders JOIN customers ON ...;
```

Hint 形態：

- `IndexScan(t1 idx_name)` — 強制 index scan
- `SeqScan(t1)` — 強制 seq scan
- `HashJoin(t1 t2)` / `NestLoop(t1 t2)` / `MergeJoin(t1 t2)`
- `Leading(t1 t2 t3)` — 強制 join order
- `Rows(t1 t2 #100)` — 強制 row 估計

**推薦**：

- 全 cluster 行為：用 GUC（如 `random_page_cost`）
- 單 query 行為：用 pg_hint_plan（不污染其他 query）
- 不要過度 hint — planner 多數時候 *是對的*、hint 是 last resort

## 5 個 Production 踩雷

### 1. Statistics 過時 — Planner 估錯 row count

`ANALYZE` 是 autovacuum 一部分、預設 *autovacuum_analyze_scale_factor=0.1*（10% row 變動才 analyze）。對 *快速 grow 的表*（log / event）、ANALYZE 跟不上、planner 用過時 statistics。

修法：

- 對 critical table 設 *較 aggressive autovacuum_analyze_scale_factor*：

   ```sql
   ALTER TABLE events SET (autovacuum_analyze_scale_factor = 0.02);
   ```

- 對 *大批量寫入後*、手動 `ANALYZE events;`
- 監控 `pg_stat_user_tables.last_analyze` — 跟 row count 比、判定是否需手動 trigger

### 2. Multi-column statistics — Planner 假設 column 獨立

如 Case 3、單 column statistics 對 *相關 column* 估錯。

修法：

- 對 *常一起 query 的 column 組合*、建 `CREATE STATISTICS`（PG 10+）
- 3 種 type：`dependencies`（functional dependency）、`ndistinct`（multi-column distinct count）、`mcv`（most common value combinations）
- 設完 *必須跑 ANALYZE* 才生效

### 3. Cost-base setting 不對齊硬體 — Planner 偏 seq scan

預設 `random_page_cost = 4`、`seq_page_cost = 1` 是 *HDD assumption*（random IO 比 sequential 慢 4x）。SSD / NVMe random / seq IO 差別小、planner 不該 4x penalty random。

修法：

```sql
-- SSD
ALTER SYSTEM SET random_page_cost = 1.1;

-- NVMe
ALTER SYSTEM SET random_page_cost = 1.0;

SELECT pg_reload_conf();
```

`random_page_cost` 改了 planner 對 index scan 的 cost 估計更準、自動選 index 更積極。

### 4. `effective_cache_size` 不對齊實際 RAM

`effective_cache_size` 預設 4 GB、planner 假設 buffer pool + OS cache 共 4 GB。實際 server 64 GB RAM、`shared_buffers = 16GB`、OS page cache ~30 GB、實際可用 cache 46 GB。

修法：

```sql
ALTER SYSTEM SET effective_cache_size = '46GB';  -- shared_buffers + OS cache 估
```

提升後 planner 估 query 多數 page 在 cache、降低 *估計 random IO cost*、選 index 更積極。

### 5. Parallel query 不觸發

預設 `max_parallel_workers_per_gather = 2`、有些 workload 不夠。或 *table size 太小*、`min_parallel_table_scan_size = 8MB` 預設、小表不 parallel。

修法：

```sql
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET parallel_setup_cost = 100;
ALTER SYSTEM SET parallel_tuple_cost = 0.01;
ALTER SYSTEM SET min_parallel_table_scan_size = '0';  -- 任何 size 都 parallel
```

監控 `EXPLAIN` 的 `Workers Planned` 數量、看是否真 parallel。

## 觀測 metric

Production 持續 monitor：

- `pg_stat_statements`：每個 query digest 累計 calls / time / rows / IO
- `auto_explain` log：slow query 的實際 plan + ANALYZE 統計
- `pg_stat_user_tables.last_analyze` / `last_autoanalyze`：statistics 新鮮度
- `pg_stat_user_indexes.idx_scan`：每個 index 使用次數 — 0 表示沒用、可考慮 drop

把這些丟進 Datadog / Prometheus（用 `postgres_exporter` / `pg_exporter`）做 trend analysis。

## 跟 MySQL Query Optimization 對照

| 維度                    | PG                                      | MySQL                                |
| ----------------------- | --------------------------------------- | ------------------------------------ |
| Query plan preview      | `EXPLAIN`                               | `EXPLAIN`                            |
| 實際執行統計            | `EXPLAIN ANALYZE`                       | `EXPLAIN ANALYZE` (8.0+)             |
| Auto-capture            | `auto_explain` extension                | `slow_query_log` + `pt-query-digest` |
| Optimizer trace         | log_planner_stats / log_executor_stats  | `optimizer_trace` (JSON)             |
| Per-query hint          | `pg_hint_plan` extension                | optimizer hint comment (`/*+ */`)    |
| Multi-column statistics | `CREATE STATISTICS`                     | 無原生（依賴 index 統計）            |
| Parallel query          | Full (scan / agg / join, PG 9.6+)       | 受限 (8.0 hash join)                 |
| Cost-base setting       | random_page_cost / effective_cache_size | 隱性、optimizer 預設                 |

PG planner 整體成熟、複雜 OLAP-style query 處理較好。MySQL 8.0 補了不少（histograms / hash join）但複雜 query 仍弱於 PG。詳見 [MySQL Query Optimization](/backend/01-database/vendors/mysql/query-optimization/)。

## 跟其他模組整合

### 跟 Autovacuum Tuning

ANALYZE 是 autovacuum 一部分、autovacuum 跟不上 → statistics 過時 → planner 估錯。詳見 [Autovacuum Tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)。

### 跟 Replication Topology

Standby 上跑 query 用同 statistics（streaming replication copy 整個 system catalog）、planner 行為一致。但 *standby 有 hot_standby_feedback* 影響 primary autovacuum / ANALYZE 行為。詳見 [Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)。

### 跟 Partitioning

Partition pruning 跟 query plan 緊密 — `EXPLAIN` 看是否 prune 對的 partition。詳見 [Declarative Partitioning](/backend/01-database/vendors/postgresql/declarative-partitioning/)。

## 何時用 pg_hint_plan vs GUC

| 情境                                       | 選擇                                                    |
| ------------------------------------------ | ------------------------------------------------------- |
| 全 cluster 行為（如 SSD random_page_cost） | GUC                                                     |
| 單一 critical query 強制特定 plan          | pg_hint_plan                                            |
| 暫時 disable 某類 plan 給 debug            | `SET enable_xxx=off` per-session                        |
| Production stable use                      | GUC + multi-column statistics 為主、hint 為 last resort |

## 相關連結

- [PostgreSQL vendor overview](/backend/01-database/vendors/postgresql/)
- [PG Autovacuum Tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)（ANALYZE 跟 statistics 新鮮度）
- [PG Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)（standby planner 行為）
- [PG Declarative Partitioning](/backend/01-database/vendors/postgresql/declarative-partitioning/)（partition pruning）
- [MySQL Query Optimization](/backend/01-database/vendors/mysql/query-optimization/)（sibling、不同 optimizer 成熟度）
- 官方：[EXPLAIN](https://www.postgresql.org/docs/current/sql-explain.html) / [pg_hint_plan](https://github.com/ossc-db/pg_hint_plan) / [auto_explain](https://www.postgresql.org/docs/current/auto-explain.html)
