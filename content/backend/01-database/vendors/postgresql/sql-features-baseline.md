---
title: "PostgreSQL SQL Features：PG 早就有的、MySQL 8.0 才補的、PG 仍領先的"
date: 2026-05-19
description: "PG 在 SQL features 上長期領先 MySQL — CTE / window function / lateral / partial index / FTS / JSONB / GIN index / materialized view 在 PG 早 5-15 年。MySQL 8.0（2018）補多數但 *index / storage / extension* 層仍是 PG 結構優勢。本文整理 PG 早期就有的特性、MySQL 8.0 補的差異、PG 仍領先的、跟 MySQL modern-sql-features sibling 反向視角"
weight: 19
tags: ["backend", "database", "postgresql", "sql-features", "baseline", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 PG 在 OLTP 譜系的定位、本文聚焦 *SQL features baseline* — PG 早期就有的、MySQL 8.0 才補的、PG 仍領先的、給從 MySQL 評估 PG 的讀者 reference。

---

## PG SQL 工程深度的歷史錨點

PG 在 SQL feature 上長期領先 MySQL：

- 2009 (PG 8.4)：CTE / window function / recursive query
- 2013 (PG 9.3)：lateral derived table / materialized view
- 2014 (PG 9.4)：JSONB / partial index 早就有 / GIN index
- 2015 (PG 9.5)：UPSERT (`ON CONFLICT`)
- 2017 (PG 10)：declarative partitioning / logical replication / multi-column statistics

MySQL 8.0（2018）才補 CTE / window / lateral / JSON_TABLE / hash join — *PG 早 9 年起步*。

對 *從 MySQL 評估 PG* 的讀者來說、PG 的 SQL 工程深度不只是「該有的都有」、更多是「PG 結構性領先的特性 + MySQL 8.0 補了哪些 + PG 仍領先哪些」。

跟 [MySQL Modern SQL Features](/backend/01-database/vendors/mysql/modern-sql-features/) 對比視角：

- MySQL 8.0 視角：「我終於補齊 + 跟 PG 對比」
- PG 視角：「我長期領先 + MySQL 8.0 才追上某些、其他我仍領先」

## PG 結構性領先特性（MySQL 沒對應 / 弱對應）

### 1. Materialized View

PG 9.3+ 內建 materialized view：

```sql
CREATE MATERIALIZED VIEW orders_summary AS
SELECT user_id, COUNT(*) AS order_count, SUM(amount) AS total
FROM orders GROUP BY user_id;

-- 手動 refresh
REFRESH MATERIALIZED VIEW orders_summary;
-- 或 concurrent refresh（PG 9.4+、不 lock read）
REFRESH MATERIALIZED VIEW CONCURRENTLY orders_summary;
```

用途：

- 預計算複雜 aggregation、查詢時極快
- Concurrent refresh 不 lock read
- 可建 index on materialized view

**MySQL 對應**：沒原生 materialized view。常見替代：

- Trigger + summary table（手動維護）
- Application 層 caching layer
- 用 view + cache layer（不是 materialization）

MySQL 8.0+ 仍無原生 materialized view。

### 2. Partial Index

PG 預設支援 partial index — 對 *滿足條件的 row* 才建 index：

```sql
-- 只對 active user 建 index
CREATE INDEX idx_users_active_email ON users(email) WHERE status = 'active';

-- Index size 比 full index 小很多、query 性能跟 full index 一樣
SELECT * FROM users WHERE status = 'active' AND email = 'x@y.com';
```

用途：

- *Soft-delete* 場景：對 `deleted_at IS NULL` 建 partial index
- *Hot subset* 場景：對 `status = 'pending'` 等熱資料建 partial
- Index 大小 / 寫入成本大降

**MySQL 對應**：MySQL 沒原生 partial index。MySQL 8.0+ 有 *functional index* 但跟 partial 不同。MySQL 替代：

- Generated column + index（接近、但維護複雜）
- 或接受 full index cost

### 3. Foreign Data Wrapper (FDW)

PG FDW 讓 query 跨外部資料源：

```sql
CREATE EXTENSION postgres_fdw;

CREATE SERVER remote_db FOREIGN DATA WRAPPER postgres_fdw
OPTIONS (host 'remote.example.com', dbname 'analytics');

CREATE USER MAPPING FOR localuser SERVER remote_db
OPTIONS (user 'remoteuser', password '...');

CREATE FOREIGN TABLE remote_orders (id INT, ...) SERVER remote_db OPTIONS (table_name 'orders');

-- 在 local PG query remote table
SELECT * FROM remote_orders WHERE id = 100;
```

支援 FDW：`postgres_fdw` / `mysql_fdw` / `oracle_fdw` / `mongo_fdw` / `file_fdw` / `redis_fdw` 等。

**MySQL 對應**：MySQL 8.0+ 有 FEDERATED engine（受限、不推薦）。實務上 MySQL 跨 DB query 用 application 層處理。

### 4. JSONB + GIN Index（PG 結構性優勢）

PG JSONB 是 *binary 儲存* + 可 *直接 GIN index*：

```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    metadata JSONB
);

-- GIN index over JSONB
CREATE INDEX idx_products_metadata ON products USING GIN (metadata);

-- 快 query
SELECT * FROM products WHERE metadata @> '{"category": "shoes"}';
SELECT * FROM products WHERE metadata @? '$.variants[*].price > 100';
```

**MySQL 對應**：MySQL 8.0 JSON_TABLE 是 SQL standard、但 *index 必須 generated column workaround*（不能 GIN index over JSON）。

詳見 [MySQL Modern SQL Features](/backend/01-database/vendors/mysql/modern-sql-features/) JSON_TABLE vs PG JSONB 對比段。

### 5. Range Types + Exclusion Constraints

PG range types + exclusion constraints 防止 *時間範圍重疊*：

```sql
CREATE TABLE reservations (
    id SERIAL PRIMARY KEY,
    room_id INT,
    during TSRANGE,
    EXCLUDE USING GIST (room_id WITH =, during WITH &&)
);

-- INSERT 重疊 booking 自動 reject
INSERT INTO reservations (room_id, during)
VALUES (1, '[2026-05-19 10:00, 2026-05-19 12:00)');
INSERT INTO reservations (room_id, during)
VALUES (1, '[2026-05-19 11:00, 2026-05-19 13:00)');
-- ERROR: conflicting key value violates exclusion constraint
```

**MySQL 對應**：完全沒對應、必須 application 層 enforce。

### 6. CHECK Constraint + Domain Type

PG `CHECK` constraint 真執行（MySQL 8.0 才補）+ user-defined `DOMAIN`：

```sql
CREATE DOMAIN positive_int AS INT CHECK (VALUE > 0);
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    quantity positive_int NOT NULL,
    amount DECIMAL CHECK (amount >= 0)
);
```

**MySQL 對應**：8.0+ 有 CHECK constraint enforcement（5.7 可寫但不執行）。沒 user-defined DOMAIN。

### 7. Extension Ecosystem

PG extension 是 *結構優勢*：

- `pg_partman`：自動 partition lifecycle
- `pg_repack`：online table rewrite
- `pg_stat_statements`：query stats
- `pgvector`：vector similarity search
- `pg_cron`：scheduled job
- `PostGIS`：GIS
- `TimescaleDB`：time-series
- `Citus`：sharding

**MySQL 對應**：MySQL plugin 機制有、生態遠遠不如。詳見 *PG Extension Ecosystem* 篇（待寫）。

## MySQL 8.0 補齊的 PG 既有特性

| 特性                  | PG 推出    | MySQL 推出    | 差異後說明                                    |
| --------------------- | ---------- | ------------- | --------------------------------------------- |
| CTE                   | 8.4 (2009) | 8.0 (2018)    | MySQL 補語法、行為 PG 12+ 跟 MySQL 接近       |
| Window function       | 8.4 (2009) | 8.0 (2018)    | 兩家都標準、frame spec 細節有差               |
| Lateral derived table | 9.3 (2013) | 8.0.14 (2019) | MySQL 後加、planner 不如 PG 成熟              |
| Hash join             | 早就有     | 8.0.18 (2019) | MySQL 受限（equality on indexed column）      |
| JSON_TABLE            | 17 (2024)  | 8.0 (2018)    | MySQL 較早、PG 17+ 補進、PG 自己有 JSONB 路線 |
| CHECK constraint      | 早就有     | 8.0 (2018)    | MySQL 5.7 可寫但不執行                        |
| Role-based auth       | 早就有     | 8.0 (2018)    | -                                             |
| Atomic DDL            | 早就有     | 8.0 (2018)    | -                                             |
| Common keyword        | 完整       | 8.0 補        | MySQL 5.7 缺很多 (window/rank/lateral 等)     |

MySQL 8.0 是 *補齊 9 年 SQL standard 落後*、不是 *新領先 PG*。

## PG 仍領先的特性

對應「MySQL 8.0 補了 → PG 仍沒輸」的視角。以下 14 條中、*production 影響最大* 的是 Materialized view / Partial index / JSONB GIN / Full-text search 跟 Range / Exclusion constraints（schema-level expressiveness）；*次要但常用* 的是 Multi-column statistics 跟 Procedural language；*非典型但 niche 重要* 的是 User-defined DOMAIN / Generic table inheritance（讀者不必然知道、但 ORM 跟 schema migration 工具會用）：

| PG 領先特性               | MySQL 對應狀態                              | 補充                                  |
| ------------------------- | ------------------------------------------- | ------------------------------------- |
| Materialized view         | 無原生                                      | application-side 重算成本高           |
| Partial index             | 無（functional index 不等同）               | 對 boolean / status column 救 storage |
| FDW                       | 弱（FEDERATED engine 不推薦）               | 跨 DB query escape hatch              |
| JSONB GIN index           | 無（generated column workaround）           | JSON workload 結構性差                |
| Range types               | 無                                          | booking / availability schema 救命    |
| Exclusion constraints     | 無                                          | range overlap 防護                    |
| User-defined DOMAIN       | 無                                          | column-level type constraint          |
| Extension ecosystem       | 弱                                          | pgvector / TimescaleDB / PostGIS      |
| Full-text search 成熟     | InnoDB FTS 較弱                             | tsvector + GIN + pg_trgm 三層         |
| Multi-column statistics   | 8.0 histograms 部分對應、PG 更廣            | planner 更準                          |
| Procedural language       | PL/pgSQL + 多語言（PL/Python / PL/Perl 等） | Stored procedure（不擴語言）          |
| Recursive CTE 深度        | Unlimited                                   | 1000（cte_max_recursion_depth）       |
| LSN-based replication     | 簡潔                                        | binlog file+position（GTID 緩解）     |
| Generic table inheritance | 早就有                                      | 無（multi-tenant schema 結構用）      |

## 對「從 MySQL 評估 PG」的讀者

讀者通常從 MySQL 8.0 過來、問題是 *「PG 比 MySQL 強在哪、弱在哪」*：

### PG 比 MySQL 強

- *SQL 工程深度*：上面列的 7 個結構優勢
- *Extension ecosystem*：pgvector / TimescaleDB / Citus / pg_partman 等
- *Optimizer*：planner 對複雜 query 更成熟
- *Concurrency model*：MVCC + 少 lock（[MVCC + Lock Model](/backend/01-database/vendors/postgresql/mvcc-lock-model/)）

### PG 比 MySQL 弱

- *Replication 機制簡潔度*：MySQL GTID 比 PG WAL + replication slot 配置簡單（[Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)）
- *Sharding ecosystem*：Vitess / PlanetScale 比 Citus 規模驗證高
- *Operational tooling 廣度*：pt-toolkit / gh-ost / Orchestrator 等
- *VACUUM 維護*：PG MVCC 必須 VACUUM、autovacuum 配錯議題多（[Autovacuum Tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)）

### 選 PG 的核心 driver

對 SQL 工程深度、extension、複雜 query / OLAP-style workload 的場景、PG 仍是首選。對純簡單 OLTP + 大規模 sharding、MySQL + Vitess 仍 competitive。

## 跟其他模組整合

- [MVCC + Lock Model](/backend/01-database/vendors/postgresql/mvcc-lock-model/)：PG MVCC 是 SQL feature 的並行控制基礎
- [Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/)：PG planner 對 window / CTE / hash join 成熟
- [Citus Distributed](/backend/01-database/vendors/postgresql/citus-distributed/)：extension 之一、體現 extension 生態
- [Autovacuum Tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)：MVCC 代價、跟 SQL feature 並行控制相關

## 相關連結

- [PostgreSQL vendor overview](/backend/01-database/vendors/postgresql/)
- [PG MVCC + Lock Model](/backend/01-database/vendors/postgresql/mvcc-lock-model/)（concurrency 基礎）
- [PG Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/)（planner 成熟度）
- [PG Citus Distributed](/backend/01-database/vendors/postgresql/citus-distributed/)（extension example）
- [PG Autovacuum Tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)（MVCC 維護）
- [MySQL Modern SQL Features](/backend/01-database/vendors/mysql/modern-sql-features/)（sibling、反向視角）
- 官方：[PostgreSQL Features](https://www.postgresql.org/about/featurematrix/)
