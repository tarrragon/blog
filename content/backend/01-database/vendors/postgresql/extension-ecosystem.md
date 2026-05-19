---
title: "PostgreSQL Extension Ecosystem：把 PG 變成 vector DB / time-series / sharded 的 plugin 生態"
date: 2026-05-19
description: "PG 的 extension 機制不只是 plugin、是 *結構性產品線擴張* — pgvector 讓 PG 變 vector DB、TimescaleDB 變 time-series、Citus 變 sharded、PostGIS 變 GIS。本文走 PG extension lifecycle、6 個 production-critical extension（pg_stat_statements / pg_partman / pg_repack / pgvector / TimescaleDB / PostGIS）、5 production 踩雷（extension version 跟 PG version 對齊 / managed PG 限制 / upgrade order / shared_preload_libraries 衝突 / extension 跟 logical replication 互動）、cloud vendor 對 extension 的限制"
weight: 26
tags: ["backend", "database", "postgresql", "extension", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 PG 在 OLTP 譜系的定位、本文聚焦 *extension ecosystem* — PG 結構性產品線擴張的機制。

---

## Extension 不只是 plugin、是產品線擴張

PG extension 機制讓 *第三方加新 type / function / operator / index access method / planner hook*、深度整合到 PG core。對比其他 DB 的 plugin model（MySQL plugin / MongoDB plugin）、PG extension 是 *更深的 SPI*。

結果：

- pgvector → PG 變 vector similarity search DB（取代 Pinecone / Weaviate）
- TimescaleDB → PG 變 time-series DB（取代 InfluxDB）
- Citus → PG 變 sharded cluster
- PostGIS → PG 變 GIS DB
- pg_cron → PG 變 scheduled job runner
- pgvectorscale → 大規模 vector index

對 *vendor lock-in 敏感* / *想統一 stack* 的 org、PG extension 提供 *用 PG 取代多個 specialized DB* 的可能。

但 *統一 stack 的代價*：PG 主庫 ops 風險集中（一個 PG 掛 = vector / time-series / GIS / cron 全掛）、extension 跟 PG version 對齊矩陣多一道升級顧慮、規模上限通常比專業 DB 低（pgvector 100M+ vs Pinecone 10B+ / TimescaleDB 100K rows/s vs InfluxDB 500K+）。決策框架：*中小規模 + 已用 PG + 不想多管系統* → extension；*大規模 + 純該 workload + 有專業 team* → specialized DB。

## Extension Lifecycle

```sql
-- 看可用 extension
SELECT * FROM pg_available_extensions;

-- 安裝（在 OS 層、要有對應 package）
-- apt install postgresql-14-pg-stat-statements

-- Enable in DB
CREATE EXTENSION pg_stat_statements;

-- 確認
SELECT * FROM pg_extension;

-- 升級 extension
ALTER EXTENSION pg_stat_statements UPDATE;

-- 移除
DROP EXTENSION pg_stat_statements;
```

每個 extension 有：

- *Version* — 跟 PG version 綁定（如 pg_stat_statements 14 / 15 / 16）
- *Schema* — 安裝到 `public` 或專屬 schema
- *Dependencies* — 部分 extension 依賴其他（如 PostGIS 依賴 pg_trgm）
- *Trusted vs untrusted* — trusted 可以 non-superuser 安裝（PG 13+）

## 6 個 Production-Critical Extension

### 1. pg_stat_statements — Query stats（必裝）

任何 production PG cluster 都該裝：

```ini
# postgresql.conf
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.max = 5000
pg_stat_statements.track = all
```

```sql
CREATE EXTENSION pg_stat_statements;

-- Top 10 query by total time
SELECT query, calls, total_exec_time, mean_exec_time, rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC LIMIT 10;
```

對應 MySQL `events_statements_summary_by_digest`。詳見 [Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/)。

### 2. pg_partman — 自動 partition lifecycle

PG declarative partitioning 需要 *手動建 / drop partition*。pg_partman 自動化：

```sql
CREATE EXTENSION pg_partman SCHEMA partman;

-- 設 events 表自動 monthly partition
SELECT partman.create_parent(
    p_parent_table => 'public.events',
    p_control => 'created_at',
    p_type => 'range',
    p_interval => '1 month',
    p_premake => 6  -- 預先建 6 個未來 partition
);

-- 跑 maintenance（建未來 partition + drop 老 partition）
SELECT partman.run_maintenance(p_analyze => false);
-- 預設用 pg_cron 排程
```

對 *time-series partition* workload 必裝。詳見 [Declarative Partitioning](/backend/01-database/vendors/postgresql/declarative-partitioning/)。

### 3. pg_repack — Online table rewrite

詳見 [Online Schema Change](/backend/01-database/vendors/postgresql/online-schema-change/)。

### 4. pgvector — Vector similarity search

LLM embedding / semantic search 場景必裝：

```sql
CREATE EXTENSION vector;

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding VECTOR(1536)  -- OpenAI text-embedding-3-small 1536-dim
);

-- HNSW index（pgvector 0.5+）
CREATE INDEX ON documents USING HNSW (embedding vector_cosine_ops);

-- 找最相似的 5 個
SELECT * FROM documents
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;
```

對 *中小規模 RAG / semantic search* workload、pgvector 在 PG 內跑、不必跨 Pinecone / Weaviate / Qdrant 等獨立服務。

對 *超大規模* vector workload（> 1 億 vector）考慮 pgvectorscale（pgvector 的 streaming variant）或專業 vector DB。

### 5. TimescaleDB — Time-series 擴展

把 PG 變 time-series DB：

```sql
CREATE EXTENSION timescaledb;

CREATE TABLE metrics (
    time TIMESTAMPTZ NOT NULL,
    device_id INT,
    value DOUBLE PRECISION
);

-- 轉成 hypertable（auto-partition by time）
SELECT create_hypertable('metrics', 'time');

-- Continuous aggregate（materialized view 自動 refresh）
CREATE MATERIALIZED VIEW metrics_5min
WITH (timescaledb.continuous) AS
SELECT time_bucket('5 minutes', time) AS bucket,
       device_id, avg(value)
FROM metrics
GROUP BY bucket, device_id;
```

對 IoT / monitoring / financial tick data 場景、TimescaleDB 比純 PG 寫吞吐高 10x+。

### 6. PostGIS — GIS extension

地理 / 空間 query 業界標準：

```sql
CREATE EXTENSION postgis;

CREATE TABLE stores (
    id SERIAL PRIMARY KEY,
    name TEXT,
    location GEOGRAPHY(POINT, 4326)
);

CREATE INDEX ON stores USING GIST (location);

-- 找 1 km 內的 store
SELECT * FROM stores
WHERE ST_DWithin(location, ST_MakePoint(121.5, 25.05)::geography, 1000);
```

PostGIS 是 GIS workload 業界標準、其他 DB GIS 能力都對標 PostGIS。

## 其他常用 extension

除 6 個 production-critical 之外、以下是 *特定場景常用* 的 extension — 分四類：排程跟 utility（`pg_cron` / `pg_trgm` / `uuid-ossp`）、type 擴展（`hstore` / `citext` / `pgcrypto`）、跨 DB 整合（`postgres_fdw` / `mysql_fdw`）、observability / debug 工具（`pg_buffercache` / `pg_visibility` / `auto_explain`）：

| Extension        | 用途                                    |
| ---------------- | --------------------------------------- |
| `pg_cron`        | 排程 SQL job（不必外部 cron）           |
| `pg_trgm`        | Fuzzy string match / similarity         |
| `uuid-ossp`      | UUID 產生                               |
| `hstore`         | Key-value pair type                     |
| `citext`         | Case-insensitive text type              |
| `pgcrypto`       | 加密 / hash function                    |
| `postgres_fdw`   | PG → PG foreign table                   |
| `mysql_fdw`      | PG → MySQL foreign table                |
| `pg_buffercache` | Buffer pool 內容檢視                    |
| `pg_visibility`  | Visibility map 檢視（debug bloat）      |
| `auto_explain`   | Slow query 自動 log plan                |
| `wal2json`       | Logical decoding output 為 JSON         |
| `Citus`          | Distributed PG                          |
| `pgvector`       | Vector similarity                       |
| `pglogical`      | Logical replication（功能比 native 強） |
| `pg_squeeze`     | pg_repack 替代                          |

實務組合：observability 三件套（`pg_stat_statements` + `auto_explain` + `pg_buffercache`）幾乎是 production 標配；FDW 是「跨 DB query」的 escape hatch、但 cross-DB query 效能差、適合 reporting 不適合 OLTP。

## 5 個 Production 踩雷

### 1. Extension version 跟 PG version 對齊

PG cluster 升 14 → 15 後、extension（pg_stat_statements / pg_partman / pgvector 等）必須有對應 15 版本。早期升級 / niche extension 可能還沒釋出。

修法：

- 升 PG cluster 前 *先確認所有 extension 都有對應 PG version 釋出版本*
- 升完 PG cluster *立即跑 `ALTER EXTENSION xxx UPDATE`*
- Upgrade runbook 紀錄每個 extension 的版本兼容狀態

### 2. Managed PG 限制 extension 列表

AWS RDS / Aurora PG / Cloud SQL / Azure DB for PostgreSQL 各自有 *支援 extension 白名單*：

- 不在白名單的 extension 不能 install
- 部分 extension 限定特定 PG version
- Untrusted extension 通常不允許

常見 *managed 不支援* 的 extension：

- `pg_repack`（Aurora 有限支援、RDS 部分 version 支援）
- `pglogical`（部分 cloud 不支援）
- `pg_cron`（cloud 通常用 managed scheduler 取代）
- Custom extension（自寫 .so）

修法：

- 評估 managed PG 之前、先查 *vendor 支援 extension 列表*
- Self-hosted vs managed 的 *跨雲 portability* 議題：extension 是 lock-in source
- 如果 application 強依賴某 extension（如 PostGIS），確認 cloud 支援

### 3. Extension upgrade order

`pg_upgrade` 升 PG major version 後、extension 也要升。順序：

1. *pg_upgrade* PG binary + cluster
2. 對每個 DB 跑 `ALTER EXTENSION xxx UPDATE`
3. 部分 extension（如 PostGIS）需要 *特殊升級程序*（`SELECT postgis_extensions_upgrade()`）

修法：

- 升 PG 後 *先測 staging cluster* 確認 extension upgrade 流程
- PostGIS / TimescaleDB / Citus 有自己 upgrade 程序、必須遵循 vendor doc
- 升完跑 `\dx` 看每個 extension 版本

### 4. `shared_preload_libraries` 衝突

部分 extension（pg_stat_statements / auto_explain / TimescaleDB / Citus / pg_cron）必須在 `shared_preload_libraries` 加進去、需要 *重啟 PG*。

衝突情境：

- pg_partman + TimescaleDB 都用 background worker、worker 上限不夠
- `max_worker_processes` 預設 8、不夠時某些 extension 起不起來

修法：

- 列出所有 shared_preload extension、確認 order（部分有 dependency）
- 提高 `max_worker_processes = 16` / `max_parallel_workers = 8` 等
- 重啟 PG 才生效、計入 maintenance window

### 5. Extension 跟 logical replication 互動

Logical replication（pglogical / native）不自動 replicate extension state（function / type definition）。Subscriber 沒裝對應 extension、replicate event 失敗。

修法：

- Subscriber 必須 *先安裝* publisher 用的 extension
- Extension 版本 *publisher / subscriber 對齊*
- 對 extension-heavy schema、考慮用 *streaming replication*（physical）而非 logical

## Cloud Vendor 對 Extension 的支援

| Vendor                  | 常見 extension 支援                                    | 限制                                    |
| ----------------------- | ------------------------------------------------------ | --------------------------------------- |
| AWS RDS PostgreSQL      | pg_stat_statements / pg_partman / pgvector / pg_repack | 部分 version 限制 / 不能 install custom |
| AWS Aurora PostgreSQL   | 同 RDS、加 Aurora-specific                             | pg_repack 限版本                        |
| GCP Cloud SQL           | 標準 extension 廣支援                                  | pg_cron / pgvector OK                   |
| Azure DB for PostgreSQL | 廣泛支援 + Azure 整合                                  | Citus（managed 即 Cosmos DB for PG）    |
| Self-hosted             | 全部                                                   | 自己維護                                |

對 *extension-heavy* application、self-hosted PG 仍是必要選擇。Managed PG 適合 *標準 extension* workload。

## 何時用 PG extension 取代專業 DB

| 場景                                     | 用 extension 還是專業 DB                 |
| ---------------------------------------- | ---------------------------------------- |
| < 100M vector + RAG / semantic search    | pgvector（單一 stack 省 ops）            |
| 大規模 vector search > 10M with high QPS | 專業 vector DB（Pinecone / Qdrant）      |
| Time-series < 100 TB                     | TimescaleDB                              |
| Time-series > 100 TB + high cardinality  | 專業 TS DB（InfluxDB / VictoriaMetrics） |
| GIS                                      | PostGIS（業界標準）                      |
| Sharded < 10 TB + multi-tenant           | Citus                                    |
| Sharded > 100 TB                         | distributed SQL（CockroachDB / TiDB）    |
| Scheduled job                            | pg_cron（簡單）/ Airflow（複雜）         |

對中小規模、PG + extension 是 *簡化 stack* 的有效路徑。規模超過時、專業 DB 仍是首選。

## 跟其他模組整合

- [Citus Distributed](/backend/01-database/vendors/postgresql/citus-distributed/)：extension 一例、可看 extension model
- [Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/)：pg_stat_statements + auto_explain 必用
- [Online Schema Change](/backend/01-database/vendors/postgresql/online-schema-change/)：pg_repack 是 extension
- [Declarative Partitioning](/backend/01-database/vendors/postgresql/declarative-partitioning/)：pg_partman 是 extension
- [SQL Features Baseline](/backend/01-database/vendors/postgresql/sql-features-baseline/)：extension 是 PG 結構性領先之一

## 相關連結

- [PostgreSQL vendor overview](/backend/01-database/vendors/postgresql/)
- [PG SQL Features Baseline](/backend/01-database/vendors/postgresql/sql-features-baseline/)（extension 是結構優勢）
- [PG Citus Distributed](/backend/01-database/vendors/postgresql/citus-distributed/)（extension example）
- [PG Online Schema Change](/backend/01-database/vendors/postgresql/online-schema-change/)（pg_repack）
- [PG Declarative Partitioning](/backend/01-database/vendors/postgresql/declarative-partitioning/)（pg_partman）
- [PG Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/)（pg_stat_statements + auto_explain）
- 官方：[PG Extensions](https://www.postgresql.org/docs/current/extend-extensions.html) / [pgvector](https://github.com/pgvector/pgvector) / [TimescaleDB](https://docs.timescale.com/) / [PostGIS](https://postgis.net/)
