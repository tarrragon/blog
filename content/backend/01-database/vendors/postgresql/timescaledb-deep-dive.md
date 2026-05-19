---
title: "TimescaleDB Deep Dive：Hypertable / Continuous Aggregate / Compression 把 PG 變 Time-Series DB"
date: 2026-05-19
description: "TimescaleDB 是 PG extension（不是 fork）、用 *hypertable* 自動 partition by time、加 *continuous aggregate* 做 incremental materialized view、加 *compression* 對舊 chunk 壓 90%+、把 PG 變成 InfluxDB / Prometheus 級 time-series DB。本文走 hypertable 機制、continuous aggregate 跟普通 MV 差異、compression policy、retention policy、5 production 踩雷（chunk size 不對 / CAGG refresh 落後 / compression 後 update 限制 / hypertable 不能加 FK / TimescaleDB 跟 PG 主版本對齊）、跟 PG 原生 partitioning 對比"
weight: 29
tags: ["backend", "database", "postgresql", "timescaledb", "time-series", "extension", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 PG 在 OLTP 譜系的定位、本文聚焦 *TimescaleDB extension* — 用 PG 解 time-series workload 的路徑、跟 [extension-ecosystem](/backend/01-database/vendors/postgresql/extension-ecosystem/) 是 *單一 extension 細節 vs ecosystem 全景* 的關係。

---

## TimescaleDB 是 PG 的 *Time-Series Specialization*

TimescaleDB 不是獨立 DB、是 PG extension：

```sql
CREATE EXTENSION timescaledb;
```

加完後、PG 多三個 time-series 專屬機制：

1. **Hypertable**：對 time column 自動 partition、應用層看是一張表
2. **Continuous aggregate**：incremental refresh 的 materialized view
3. **Compression**：對舊 chunk 壓縮（columnar-like format）

跟專業 time-series DB（InfluxDB / Prometheus / VictoriaMetrics）對比、TimescaleDB 的賣點不是「最快」而是「PG ecosystem 一致」：

| 維度             | TimescaleDB                        | InfluxDB           | Prometheus              |
| ---------------- | ---------------------------------- | ------------------ | ----------------------- |
| Query 語言       | 標準 SQL                           | InfluxQL / Flux    | PromQL                  |
| 寫入效能         | 中（10-100K rows/s）               | 高（500K+ rows/s） | 中（pull-based scrape） |
| 壓縮             | 90%+（columnar compression）       | 高                 | 高                      |
| Join             | 完整 SQL join                      | 弱                 | 不支援                  |
| 跟既有 PG schema | 同一個 DB、可 join                 | 獨立               | 獨立                    |
| 生態             | 完整 PG ecosystem                  | 自家 ecosystem     | 自家 ecosystem          |
| Open source      | Apache 2.0（部分功能 TSL license） | MIT                | Apache 2.0              |

**何時選 TimescaleDB**：

- Application 已用 PG、不想多管一套 time-series DB
- 需要 join time-series 跟 application 表（user / device metadata）
- 不需 InfluxDB 級寫入速度（< 100K rows/s）
- Team SQL 熟、PromQL / Flux 學習成本不想付

## Hypertable：自動 Time-based Partitioning

普通 PG 表變 hypertable：

```sql
CREATE TABLE sensor_data (
    time        TIMESTAMPTZ NOT NULL,
    sensor_id   INTEGER NOT NULL,
    temperature DOUBLE PRECISION,
    humidity    DOUBLE PRECISION
);

-- 變 hypertable、按 time 自動 partition
SELECT create_hypertable('sensor_data', 'time');
```

Hypertable 機制：

- 後台自動拆 *chunk*（child partition）by time interval（預設 7 天）
- Application 看到的是 `sensor_data` 一張表、實際資料分散在 `_timescaledb_internal._hyper_*_chunk` 表
- Query 自動 chunk pruning（只掃命中時間範圍的 chunk）

**Chunk interval 選擇**很關鍵：

| Chunk interval | 適用                          | 問題                     |
| -------------- | ----------------------------- | ------------------------ |
| 1 小時         | 高頻 metrics（每秒 100+ row） | Chunk 太多、catalog 膨脹 |
| 1 天           | 中高頻（每秒 10-100 row）     | OK                       |
| 7 天（預設）   | 中頻（每分鐘 row）            | OK                       |
| 30 天          | 低頻（每小時 row）            | OK                       |

通用原則：*每個 chunk 25% RAM*、超過退化 disk IO。Production 監控 `chunk_size` 跟 `shared_buffers` ratio 自動調。

**Multi-dimensional hypertable**（time + space partition）：

```sql
-- 按 time + device_id 雙維 partition
SELECT create_hypertable('sensor_data', 'time',
    partitioning_column => 'sensor_id',
    number_partitions => 16
);
```

適用 sensor 數 1000+ 的 IoT workload、單 chunk 太大時用 space partition 拆。

## Continuous Aggregate（CAGG）：Incremental Materialized View

普通 PG materialized view 是 *全量重算*、TimescaleDB CAGG 是 *incremental refresh*：

```sql
-- 1 小時粒度聚合
CREATE MATERIALIZED VIEW sensor_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS hour,
    sensor_id,
    avg(temperature) AS avg_temp,
    max(temperature) AS max_temp,
    min(temperature) AS min_temp,
    count(*) AS sample_count
FROM sensor_data
GROUP BY hour, sensor_id;

-- 加 refresh policy（每 30 分鐘 refresh 過去 1 天）
SELECT add_continuous_aggregate_policy('sensor_hourly',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '30 minutes',
    schedule_interval => INTERVAL '30 minutes'
);
```

CAGG 機制：

- 記錄哪些 time bucket 已 materialize、哪些 stale
- Refresh 時只重算 stale bucket、不全量
- Query CAGG 自動 fallback 到原 hypertable 補最新資料（real-time aggregation）

**CAGG vs 普通 MV 對比**：

| 維度               | TimescaleDB CAGG  | 普通 PG MV            |
| ------------------ | ----------------- | --------------------- |
| Refresh 模式       | Incremental       | 全量重算              |
| Refresh 時間       | 秒級              | 表大時數十分鐘        |
| Real-time fallback | 自動補最新        | 不支援、需手動 union  |
| Storage            | 多一份 aggregated | 多一份 aggregated     |
| Policy             | 內建排程          | 需 pg_cron / 外部排程 |

**CAGG hierarchy**（多層聚合）：

```sql
-- 從 1 hour CAGG 再聚合到 1 day
CREATE MATERIALIZED VIEW sensor_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', hour) AS day,
    sensor_id,
    avg(avg_temp) AS daily_avg
FROM sensor_hourly
GROUP BY day, sensor_id;
```

Application query 不同時間範圍時自動命中對應粒度、不必每次掃原始資料。

## Compression：把舊 Chunk 壓 90%+

舊 chunk 可以開啟 compression：

```sql
-- 開啟 compression（必須先設定 segment by）
ALTER TABLE sensor_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'sensor_id',
    timescaledb.compress_orderby = 'time DESC'
);

-- 自動壓縮 policy：7 天前 chunk 壓
SELECT add_compression_policy('sensor_data', INTERVAL '7 days');
```

Compression 機制：

- 把 chunk 內 row 按 `segmentby` 分組
- 每組內按 `orderby` 排序後、把每 column 變成 *columnar array*
- 對 array 用 type-specific 壓縮（Gorilla for float / delta-of-delta for timestamp / dictionary for string）

實際壓縮率：

| Workload                          | 壓縮率 |
| --------------------------------- | ------ |
| IoT sensor（重複值多）            | 95-98% |
| Application metrics               | 90-95% |
| Trade tick（隨機浮點）            | 70-85% |
| Log line（高 cardinality string） | 50-70% |

**Compression 限制**（重要）：

- 壓縮後 chunk **不能 UPDATE / DELETE 單 row**（要先 decompress）
- 壓縮後 chunk **不能加 column**（要 decompress 所有 chunk）
- 壓縮後 chunk 只能 *append new row*、不能改舊 row
- DDL 變更（加 column / 改 index）需 decompress

實務：compression 是 *write-once cold data* 的工具、active OLTP chunk 不開。

## Retention Policy：自動刪舊資料

```sql
-- 1 年前 chunk 自動刪
SELECT add_retention_policy('sensor_data', INTERVAL '1 year');
```

Retention drop 整個 chunk（不是 DELETE row）、O(1) 操作、不產生 bloat。

CAGG 有獨立 retention：

```sql
-- 原始資料只留 30 天、aggregated 留 5 年
SELECT add_retention_policy('sensor_data', INTERVAL '30 days');
SELECT add_retention_policy('sensor_hourly', INTERVAL '5 years');
```

這是 TimescaleDB 跟普通 PG partitioning 最大的價值差 — 普通 PG 要自己寫 cron drop partition、TimescaleDB policy 內建。

## 5 個 Production 踩雷

### Case 1：Chunk size 不對、catalog 膨脹

**情境**：sensor 每秒寫 10 row、chunk_interval 設 1 小時、一年產 8760 chunk、`pg_class` 撐到 200 萬 row、planner 變慢。

修法：

- Chunk 數量上限 ~10000、超過 catalog overhead 出現
- 重設 chunk_interval：`SELECT set_chunk_time_interval('sensor_data', INTERVAL '1 day');`
- 已存在 chunk 不會自動 merge、要靠 retention drop 自然消化

### Case 2：CAGG refresh 落後 real-time

**情境**：CAGG refresh policy 每 1 小時跑、application 期待「即時 dashboard」、看到的數字落後 1 小時。

修法：

- 縮短 `schedule_interval`（5 分鐘）
- 用 `real-time aggregation`（預設 ON、CAGG 自動 union 原始資料）
- 確認 `materialized_only = false`（real-time aggregation 開啟）

```sql
ALTER MATERIALIZED VIEW sensor_hourly SET (timescaledb.materialized_only = false);
```

### Case 3：Compression 後想 UPDATE

**情境**：發現某個歷史 row 數值錯、想 UPDATE、報錯 *cannot update/delete from compressed chunk*。

修法：

```sql
-- 找到該 chunk 並 decompress
SELECT decompress_chunk(c) FROM show_chunks('sensor_data',
    older_than => INTERVAL '7 days') c WHERE c::text LIKE '%_5_chunk';

-- UPDATE 完再 compress 回去
UPDATE sensor_data SET temperature = 22.5 WHERE ...;
SELECT compress_chunk(...);
```

或設計階段就避免 — compression 用在 *immutable data*、有可能改的留未壓。

### Case 4：Hypertable 不能加 FK 到 non-hypertable

**情境**：想對 `sensor_data` 加 FK 到 `sensors` 表、報錯 *foreign key constraints with hypertables are not supported*。

修法：

- Application 層維護 referential integrity
- 或反過來：`sensors` 可以 FK 到 hypertable（特定方向支援）
- TimescaleDB 2.11+ 部分支援 FK from hypertable、但限制多

### Case 5：TimescaleDB 跟 PG 主版本對齊

**情境**：PG 升級 14 → 16、TimescaleDB extension 沒對應升級、PG 啟動 fail。

TimescaleDB 跟 PG 版本對齊矩陣：

| TimescaleDB | 支援 PG version |
| ----------- | --------------- |
| 2.11+       | 13, 14, 15      |
| 2.13+       | 13, 14, 15, 16  |
| 2.15+       | 14, 15, 16      |
| 2.17+       | 14, 15, 16, 17  |

修法：

- 升 PG 前先升 TimescaleDB 到支援目標 PG 版本的 extension
- Production 升級順序：TimescaleDB minor upgrade → PG major upgrade → TimescaleDB final upgrade
- Cloud managed（Timescale Cloud）自動處理

## 跟 PG 原生 Partitioning 對比

PG 10+ 有 declarative partitioning、不一定要 TimescaleDB：

| 維度                 | TimescaleDB hypertable | PG declarative partitioning    |
| -------------------- | ---------------------- | ------------------------------ |
| 自動建 chunk         | 是                     | 否（需手動或 pg_partman）      |
| Chunk pruning        | 自動                   | 自動（需 partition key）       |
| Retention 內建       | 是                     | 否（pg_partman 或自寫 cron）   |
| Compression          | 內建 columnar          | 否                             |
| Continuous aggregate | 內建                   | 否（自寫 incremental refresh） |
| 跨 chunk index       | 統一 management        | Per-partition index            |
| Cardinality limit    | 10000+ chunk OK        | 1000+ partition 就慢           |

何時用原生 partitioning（不用 TimescaleDB）：

- 不需要 compression / CAGG
- Partition 數 < 1000
- 已用 pg_partman 不想換
- 公司禁用 TSL license（TimescaleDB 部分功能受限）

何時用 TimescaleDB：

- 高頻 time-series（compression 必要）
- 需要 CAGG（手寫 incremental MV 成本高）
- Partition 數 > 1000
- IoT / metrics / observability workload

詳細 partitioning 機制看 [declarative-partitioning](/backend/01-database/vendors/postgresql/declarative-partitioning/)。

## 相關連結

- [extension-ecosystem](/backend/01-database/vendors/postgresql/extension-ecosystem/)：PG extension 全景
- [declarative-partitioning](/backend/01-database/vendors/postgresql/declarative-partitioning/)：原生 partitioning
- [jsonb-deep-dive](/backend/01-database/vendors/postgresql/jsonb-deep-dive/)：IoT payload 用 JSONB 儲存
- [autovacuum-tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)：hypertable autovacuum 行為
- [major-version-upgrade](/backend/01-database/vendors/postgresql/major-version-upgrade/)：TimescaleDB + PG 升級順序

## 下一步

- 看 [extension-ecosystem](/backend/01-database/vendors/postgresql/extension-ecosystem/) 了解其他 PG 擴展選項
- 回 [PostgreSQL overview](/backend/01-database/vendors/postgresql/) 看全圖
