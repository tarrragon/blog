---
title: "PostgreSQL autovacuum tuning：為什麼你的 autovacuum 永遠追不上 bloat"
date: 2026-05-18
description: "MVCC 怎麼產生 dead tuple、autovacuum cost-based throttle 為什麼預設保守、per-table tuning 怎麼設、5 個 production 踩雷（cost_limit 太低 / 長 transaction blocks vacuum / anti-wraparound 在 peak / partition vacuum 滿 worker / index bloat 沒處理）、跟 partitioning + monitoring 整合"
weight: 12
tags: ["backend", "database", "postgresql", "autovacuum", "vacuum", "performance", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 PostgreSQL MVCC 的 vacuum 必要性、本文聚焦 *autovacuum 在 production write-heavy workload 為什麼追不上* 的根因 + 各維度 tuning。

## 你的 autovacuum 永遠追不上 bloat — 為什麼

write-heavy table 的常見故事：上線時表 10GB、3 個月後 30GB、6 個月 80GB；DBA 看 `pg_stat_user_tables` 發現 `n_dead_tup` 比 `n_live_tup` 還多、`pg_stat_progress_vacuum` 顯示 autovacuum 一直在跑、但 dead tuple 從沒清乾淨。表本身才 5M row、實際磁碟卻佔 80GB。

這不是 PostgreSQL bug、是 autovacuum *cost-based throttling 預設保守* 的設計意圖 — autovacuum 不該影響 OLTP query 性能、所以每跑一段就 sleep。預設 `autovacuum_vacuum_cost_limit=200` + `autovacuum_vacuum_cost_delay=2ms` 在 write-heavy 表（每秒幾千 UPDATE）下、清理速度 *永遠慢於* dead tuple 產生速度。預設配置適合 read-heavy / write-light workload；OLTP write-heavy 必須調。

## MVCC 跟 dead tuple：vacuum 在解什麼

PostgreSQL MVCC：每次 UPDATE 都是 *insert new row + mark old row as deleted*；DELETE 是 *mark as deleted、不立刻釋放空間*。dead tuple 在 disk 上佔位、但不能被 query 讀到。autovacuum 的責任：

1. **回收 dead tuple 空間** 供新 row reuse（不縮 table 大小、是 free space map）
2. **更新 visibility map** 讓 index-only scan 跳過 heap fetch
3. **凍結老 row 的 xid**（freeze）避免 xid wraparound 災難
4. **重整 index B-tree** 標記 dead pointer（不刪 index page）

Vacuum 不縮表 — 真要縮要跑 `VACUUM FULL`（全表 exclusive lock、production 不能跑）或 `pg_repack`（online repack tool）。預期 vacuum 只能 *讓表停止長大*、不能 *讓表變小*。

## Tuning：cost-based throttle 跟 trigger threshold

### Cost-based throttle（全 instance）

```ini
# postgresql.conf
autovacuum_vacuum_cost_limit = 2000          # 預設 200、production 拉 5-10 倍
autovacuum_vacuum_cost_delay = 2ms            # 預設 2ms、不太需要動
autovacuum_max_workers = 6                    # 預設 3、CPU 多時拉到 6-10
maintenance_work_mem = 1GB                    # 預設 64MB、單一 vacuum 用的記憶體
```

直覺：

- `cost_limit` 是每個 cycle 能消費多少「cost」、cost 由 page read / dirty / hit 加總；拉高 = 每次 cycle 處理更多 page
- 拉 `cost_limit` 比 `cost_delay` 直接 — delay 太低（< 1ms）OS scheduler 抖動就無效
- `max_workers` 限同時跑的 vacuum；partition 多時容易爆滿、要拉
- `maintenance_work_mem` 影響 index vacuum 速度、SSD 環境 1-2GB 是 sweet spot

### Per-table override（精準到 hot table）

```sql
-- 對 hot write-heavy 表加強
ALTER TABLE events SET (
  autovacuum_vacuum_scale_factor = 0.05,      -- 預設 0.2、5% dead 就觸發
  autovacuum_vacuum_threshold = 1000,          -- 預設 50、絕對值底線
  autovacuum_vacuum_cost_limit = 5000,         -- 該表獨立 cost_limit
  autovacuum_analyze_scale_factor = 0.05,      -- analyze 也跟著
  autovacuum_freeze_max_age = 100000000        -- anti-wraparound 提前
);

-- 對 append-only 表（log table）降頻
ALTER TABLE audit_log SET (
  autovacuum_vacuum_scale_factor = 0.5,        -- 50% dead 才觸發（極少 UPDATE / DELETE）
  autovacuum_freeze_max_age = 1000000000       -- freeze 延後
);
```

關鍵：*hot table 比 default 緊、cold table 比 default 鬆*、不要把所有表用同套配置。Production cluster 通常 5-20 個 hot table 需要 per-table tuning。

## Production 故障演練

### Case 1：write-heavy hot table，autovacuum 永遠跑不完

**徵兆**：`pg_stat_user_tables.n_dead_tup` 持續高於 `n_live_tup`、`pg_stat_progress_vacuum` 顯示某表 vacuum 跑了 6+ 小時還在 `scanning heap`、表 size 持續長大。

**根因**：default `cost_limit=200` 對該表 write rate（~5000 UPDATE/s）下、vacuum 處理速度 < dead tuple 產生速度；單次 autovacuum 跑完整表要 12 小時、但表 5% bloat 觸發又啟動下一輪。

**修法**：

1. 對該表 `ALTER TABLE ... SET (autovacuum_vacuum_cost_limit = 10000)` — 該表 vacuum 不受全 instance 限制
2. `maintenance_work_mem` 拉到 2GB（單 vacuum）
3. 短期：手動 `VACUUM (VERBOSE, ANALYZE) events;` 在 maintenance window 跑、catch up
4. 長期：考慮 partitioning — partition 後 vacuum 只動最近 partition、不掃整表

### Case 2：長 transaction 卡住 vacuum 的 xmin horizon

**徵兆**：autovacuum 看似有跑、但 `n_dead_tup` 不降；`pg_stat_activity` 看到一個跑了 8 小時的 SELECT（report query 或 idle in transaction）。

**根因**：vacuum 只能回收「不會被任何 active transaction 看到」的 dead tuple；長 transaction 的 xmin 鎖死 vacuum 能回收的範圍、即使 autovacuum 不停跑、能回收的 row 數為 0。

**修法**：

1. **預防**：application 端用 `statement_timeout` + `idle_in_transaction_session_timeout`（30 分鐘）強制終止 long transaction
2. **偵測**：`SELECT pid, now() - xact_start FROM pg_stat_activity WHERE state = 'idle in transaction'` 定期掃
3. **臨時**：kill 長 transaction（`pg_cancel_backend(pid)` / `pg_terminate_backend(pid)`）、autovacuum 下次跑就能回收
4. **架構**：報表 query 跑在 standby、不要在 primary 開 long transaction

### Case 3：Anti-wraparound vacuum 在 peak 觸發

**徵兆**：production 流量高峰時 PostgreSQL CPU 100%、`pg_stat_progress_vacuum` 顯示 anti-wraparound vacuum 正在跑、application latency 暴漲；log 出現 `database "myapp" must be vacuumed within X transactions`。

**根因**：autovacuum_freeze_max_age（預設 200M）到了、PostgreSQL *強制* 跑 anti-wraparound vacuum（即使在 peak）；這個 vacuum *不受 cost_limit 限制*、跑到完才停、表大時要幾小時、跟 OLTP query 搶 IO。

**修法**：

1. **預防**：`autovacuum_freeze_max_age` 拉到 1B（10 億）、給 freeze 更多時間在 off-peak 自然發生
2. **per-table freeze**：hot table 設 `autovacuum_freeze_max_age = 100M`（提前在 off-peak freeze）、cold table 設 800M（避免不必要 freeze）
3. **緊急**：手動跑 `VACUUM (FREEZE, VERBOSE) table_name;` 在 maintenance window 預先 freeze
4. **監測**：`SELECT relname, age(relfrozenxid) FROM pg_class WHERE relkind = 'r' ORDER BY age(relfrozenxid) DESC LIMIT 20;` 看哪些表逼近 wraparound

### Case 4：Partition table 把 autovacuum_max_workers 跑滿

**徵兆**：partition 後（時間 partition、12 個月分區）、autovacuum 跑很慢、`pg_stat_activity` 看到 3 個 autovacuum worker 都在跑 partition 表、其他 hot table queue 等很久。

**根因**：`autovacuum_max_workers=3` 預設、每個 partition 算獨立 table；100 個 partition 中 50 個都需要 vacuum、worker 滿、其他 table 排隊。

**修法**：

1. 拉 `autovacuum_max_workers` 到 6-10（依 CPU core 數）
2. cold partition 設 `autovacuum_enabled = false`（已不寫的舊 partition）、減少 worker 競爭
3. partition 數量本身要克制 — 100+ partition 是訊號該重新評估 partition strategy

### Case 5：Index bloat 沒被 vacuum 處理

**徵兆**：表 vacuum 跑完了、`n_dead_tup` 為 0、但 index size 持續長大；query 用該 index 越來越慢、跟 sequential scan 差不多。

**根因**：autovacuum 只處理 *heap*（table data）跟 *index leaf pages*；index B-tree 內部結構 fragmentation 不被 vacuum 處理。dead pointer 留在 index leaf page、查詢仍 traverse 過、IO 多。

**修法**：

1. `REINDEX CONCURRENTLY` 線上重建 index（PG 12+）、不鎖表
2. 監測 index bloat：`pgstattuple_approx` extension 或 `pg_repack`
3. 預防：B-tree index 設計避免 high cardinality + 大量 UPDATE 同欄位（typical 場景：status column update）；考慮 *partial index* 或 *hash index*（PG 10+ logged）
4. 大量 bloat index 用 `pg_repack` 重建（不需要 superuser、不鎖表）

## 容量規劃

vacuum capacity 用 *跟得上 dead tuple 產生速度* 衡量：

| 維度                            | 估算方式                                                            | 警戒                                         |
| ------------------------------- | ------------------------------------------------------------------- | -------------------------------------------- |
| dead tuple 產生 rate            | `UPDATE/s + DELETE/s + ~10% INSERT/s（HOT update miss）`            | 跟 vacuum rate 對比                          |
| vacuum 處理 rate                | `cost_limit / cost_delay × page_size`、~MB/s 數量級                  | 跟 dead tuple rate 對比                      |
| autovacuum_max_workers          | partition 數 + hot table 數 / 3-5                                   | 100+ partition 必須拉 worker                 |
| maintenance_work_mem            | 1-2GB / vacuum worker                                                | 全 worker 跑時的記憶體上限要 sizing          |
| anti-wraparound 觸發頻率        | 預設 200M xid、write-heavy ~ 1-2 週觸發一次                          | 拉到 1B 後 ~ 2-3 月一次                      |
| Bloat ratio                     | `pg_stat_user_tables.n_dead_tup / n_live_tup`                       | > 50% 表示 vacuum 追不上                     |

實務 default：

- OLTP write-heavy（事件 / 訂單）：cost_limit 2000-5000、scale_factor 0.05、freeze_max_age 100M
- OLTP read-heavy（user / config）：default 即可
- Append-only log：scale_factor 0.5、freeze_max_age 800M、`autovacuum_enabled = false` for cold partition

## 整合 / 下一步

### 跟 [partitioning](/backend/01-database/vendors/postgresql/declarative-partitioning/) 整合

partitioning 是 vacuum 問題的長期解：

- 大表（> 100GB）vacuum 時間隨 size 線性、partition 後 vacuum 只動最近 partition
- Cold partition `autovacuum_enabled = false` 完全停掉、新數據只在 hot partition
- 缺點：partition 數量爆炸時、autovacuum_max_workers 也要拉

### 跟 monitoring 整合

關鍵 metric：

```sql
-- bloat 比例
SELECT relname, n_dead_tup, n_live_tup,
       round(n_dead_tup::numeric / nullif(n_live_tup, 0) * 100, 1) AS dead_pct
FROM pg_stat_user_tables
WHERE n_live_tup > 1000
ORDER BY n_dead_tup DESC LIMIT 20;

-- vacuum 進度
SELECT * FROM pg_stat_progress_vacuum;

-- xid wraparound 距離
SELECT datname, age(datfrozenxid) FROM pg_database ORDER BY age DESC;
```

Prometheus alert 三條：`dead_pct > 30`、`vacuum_running_seconds > 3600`、`xid_age > 500000000`。

### 跟 backup window

VACUUM FREEZE 在 backup 前跑能減少 backup size（freeze tuple 不需要 special handling）：

1. 每週 maintenance window 跑 `VACUUM (FREEZE, ANALYZE) hot_table` — 預先 freeze + 更新 stats
2. backup 前避免長 transaction、確保 vacuum 能跑

### 下一步議題

- **HOT update 跟 fillfactor**：UPDATE 同頁可重用空間、fillfactor 80 為 hot table 留 20% buffer
- **`pg_repack` vs `VACUUM FULL`**：online vs offline、長期維護工具選擇
- **PostgreSQL 14+ parallel vacuum**：index vacuum 平行化、大表受益明顯

## 相關連結

- 上游 vendor 頁：[PostgreSQL](/backend/01-database/vendors/postgresql/)
- 上游 chapter：[High Concurrency Access](/backend/01-database/high-concurrency-access/) — vacuum 是 concurrency 治理一環
- 平行 deep article：[Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/) / [Declarative Partitioning](/backend/01-database/vendors/postgresql/declarative-partitioning/)
- Methodology：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)
