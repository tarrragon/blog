---
title: "MySQL → PostgreSQL：從 SQL dialect diff 跑出來的 Type A 6-phase migration"
date: 2026-05-19
description: "MySQL → PostgreSQL 是 Type A 高 schema 差 migration 的標準形態 — SQL dialect / collation / case sensitivity / replication 模型差異主導；用 pgloader / AWS DMS / 自管 dual-write 三條 path、5 個 production 踩雷（auto_increment vs SERIAL / charset 跟 collation / case sensitivity / index syntax / triggers）"
weight: 11
tags: ["backend", "database", "mysql", "postgresql", "migration", "schema-diff", "type-a"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [MySQL](/backend/01-database/vendors/mysql/) 跟 [PostgreSQL](/backend/01-database/vendors/postgresql/)。本文是 [Migration playbook methodology](/posts/migration-playbook-methodology/) Type A 的標準形態實證。

## 三類 SQL dialect diff sample：先看具體差距

```sql
-- 1. Auto increment / sequence
-- MySQL
CREATE TABLE users (id INT AUTO_INCREMENT PRIMARY KEY);
-- PostgreSQL
CREATE TABLE users (id SERIAL PRIMARY KEY);
-- 或 PG 10+:
CREATE TABLE users (id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY);

-- 2. String concatenation
-- MySQL: CONCAT(a, b) 或 a || b 在 ANSI mode
SELECT CONCAT(first_name, ' ', last_name) FROM users;
-- PostgreSQL: a || b 或 CONCAT(a, b)
SELECT first_name || ' ' || last_name FROM users;
-- 注意: PostgreSQL 對 NULL || x = NULL、MySQL CONCAT 對 NULL 處理不同

-- 3. UPSERT
-- MySQL
INSERT INTO users (id, name) VALUES (1, 'Alice')
ON DUPLICATE KEY UPDATE name = VALUES(name);
-- PostgreSQL (9.5+)
INSERT INTO users (id, name) VALUES (1, 'Alice')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

-- 4. Index hint / FORCE INDEX
-- MySQL
SELECT * FROM orders FORCE INDEX (idx_created_at) WHERE created_at > '2025-01-01';
-- PostgreSQL: 沒對應 syntax、依賴 planner + statistics
-- 必要時用 enable_seqscan=off 或 pg_hint_plan extension

-- 5. JSON path
-- MySQL 5.7+
SELECT data->'$.name' FROM events;
-- PostgreSQL
SELECT data->'name' FROM events;
SELECT data->>'name' FROM events;  -- 取出 text
```

5 個 sample 看出 MySQL → PostgreSQL 主要工作是 *SQL dialect translation*；不是 5-10 個函數差、是 *跨整個 application SQL surface 的 audit + 改寫*。對應 [diff dimension audit](/report/content-structure-by-max-diff-dimension/) 結果：

| 維度                   | 評估                                                   | 等級     |
| ---------------------- | ------------------------------------------------------ | -------- |
| Schema / API           | SQL dialect 差大、CREATE TABLE / INDEX / function 都差 | **High** |
| Operational model      | 兩者都 OLTP RDBMS、replication 概念對等但語法不同      | Medium   |
| Abstraction / paradigm | 同 SQL RDBMS                                           | Low      |
| Number of components   | 同 1 個                                                | Low      |
| Application change     | ORM 多數能 cover、raw SQL 必改                         | Medium   |

主導維度 Schema = High、走 [Type A 6-phase playbook](/posts/migration-playbook-methodology/) 標準結構。

## Phase 0：rule audit + SQL surface 盤點

```sql
-- 1. 列所有 stored procedure
SELECT routine_schema, routine_name, routine_type
FROM information_schema.routines
WHERE routine_schema NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema');

-- 2. 列所有 trigger
SELECT trigger_name, event_object_table, action_statement
FROM information_schema.triggers;

-- 3. 列所有 view
SELECT table_name, view_definition
FROM information_schema.views;

-- 4. 列所有 index 含 prefix length
SHOW INDEX FROM users;
-- PostgreSQL 對 prefix index 處理不同、要逐個 audit
```

Audit 主要產出三類清單：

- **Direct port**：標準 SQL feature、PG 直接接受
- **Translate**：MySQL-specific syntax、需要改寫（UPSERT / CONCAT NULL 行為 / index hint）
- **Refactor**：MySQL-specific behavior（auto_increment session-level / SELECT FOUND_ROWS / GROUP BY 寬鬆 / TEXT 隱性 cast）— 不能直接 port、application code 也要改

## Phase 1：schema 對位

| MySQL                        | PostgreSQL                                                |
| ---------------------------- | --------------------------------------------------------- |
| `INT AUTO_INCREMENT`         | `INT GENERATED ALWAYS AS IDENTITY` 或 `SERIAL`            |
| `TINYINT(1)` (boolean usage) | `BOOLEAN`                                                 |
| `DATETIME`                   | `TIMESTAMP WITHOUT TIME ZONE`                             |
| `DATETIME(6)` (microsecond)  | `TIMESTAMP(6)`                                            |
| `VARCHAR(N)` with charset    | `VARCHAR(N)` (UTF-8 always)                               |
| `TEXT`                       | `TEXT` (no length limit)                                  |
| `LONGTEXT`                   | `TEXT`                                                    |
| `JSON`                       | `JSONB` (推薦、indexed) 或 `JSON`                         |
| `ENUM('a','b','c')`          | 自定 `TYPE foo AS ENUM('a','b','c')` 或 `VARCHAR + CHECK` |
| `SET('a','b')`               | Array `TEXT[]` + CHECK                                    |
| `BINARY(N)`                  | `BYTEA`                                                   |
| Index prefix `KEY (col(10))` | Functional index `CREATE INDEX ON t (LEFT(col, 10))`      |
| `FULLTEXT INDEX`             | `tsvector` + GIN index                                    |
| Geographic types             | PostGIS extension（必須先裝）                             |

Schema 對位表存版控、application code refactor 時對照。

## Phase 2：Translation pipeline（3-tier 跟 Splunk → Elastic 類似）

### Tier 1：vendor / community tool

```bash
# pgloader：成熟工具、cover ~70-80% schema + data
pgloader mysql://user:pass@mysql-host/dbname \
         postgresql://user:pass@pg-host/dbname

# 或 AWS DMS（managed、適合 RDS / Aurora target）
# DMS task: Full Load + CDC
```

### Tier 2：自家 SQL refactor

對 ORM 不能 cover 的 raw SQL：

- Manual grep `application code` 找 `auto_increment` / `ON DUPLICATE KEY` / `FORCE INDEX` / `FOUND_ROWS()` / `CONCAT NULL`
- 寫 codemod / lint rule、CI 強制 check（PG-incompatible SQL block PR）

### Tier 3：tricky case manual

例：MySQL `SELECT * FROM t1, t2 WHERE t1.id = t2.id GROUP BY t1.id`（implicit GROUP BY 寬鬆）— PG 嚴格 GROUP BY 必須 list 所有 non-aggregate column；application code refactor 必要。

## Phase 3：Parallel run

雙寫 + 雙讀比對 1-2 個月：

```text
Application ──→ MySQL (write + read primary)
            └─→ PostgreSQL (write only + read shadow)
                                    ↓
                            Diff checker (latency / result diff)
```

`pt-table-checksum` (MySQL) + 自家 checksum scanner 對 sample table 跑 daily checksum、找 schema 對位錯。

## Phase 4：Cutover

- 設 application maintenance window（30 分鐘）
- Drain MySQL write、等 last LSN propagated to PG
- Application switch connection string → PG
- 解除 maintenance、monitor 24-48 hours

## Phase 5：Cleanup

- MySQL read-only 1-2 週（fallback window）
- 之後 stop replication、decommission MySQL

## Production 故障演練

### Case 1：Auto_increment vs SERIAL 跨 transaction 行為差

**徵兆**：cutover 後某 batch job 跑得比 MySQL 慢 5-10x、PG log 顯示 sequence 競爭。

**根因**：MySQL `AUTO_INCREMENT` 取值受 `innodb_autoinc_lock_mode` 控制（8.0 預設 mode=2 interleaved 可並行、mode=0 才是 table-level lock；詳見 [Lock contention](/backend/01-database/vendors/mysql/lock-contention/)）、PG `SERIAL` 是 *sequence-level non-transactional*；mode=0 場景跟 PG SERIAL 差異最大、mode=2 跟 PG SERIAL 行為較接近（皆可亂號、皆可並行）。

**修法**：

1. **改 UUID v7 / bigserial**：消除 sequence 競爭
2. **bigserial + cache**：`CREATE SEQUENCE ... CACHE 100`、batch 預取 100 個 ID 降 contention
3. **批量 insert 改 COPY**：`COPY t FROM STDIN` 是 PG 對 batch 最快路徑

### Case 2：Charset / collation 跑出 unicode 異常

**徵兆**：cutover 後某些用戶名 / 中文文字 query 對不到結果、`SELECT * WHERE name = '張三'` 返回空。

**根因**：MySQL default `utf8mb3`（3-byte UTF-8、不能存 emoji / 部分 unicode）、PG default `UTF8` 全 unicode；資料遷移時 MySQL 端的 utf8mb3 column 帶到 PG 後 *bytes 不變* 但 *collation rule 變*；string comparison 結果差。

**修法**：

1. **Pre-migration audit**：MySQL 強制 `utf8mb4`、avoid utf8mb3 data
2. **Collation 對位**：MySQL `utf8mb4_unicode_ci` → PG `LC_COLLATE = 'C.utf8'` 或 ICU collation
3. **Application encoding contract**：明示 UTF-8 全範圍、不接受 utf8mb3-only client

### Case 3：Case sensitivity 反轉

**徵兆**：cutover 後 application query `SELECT * FROM users` 報錯 `relation does not exist`；但 `SELECT * FROM "Users"` works。

**根因**：MySQL Linux default *table name case-sensitive*、Windows *case-insensitive*、配置 `lower_case_table_names` 影響；PG *all identifier folded to lowercase unless quoted*。MySQL on macOS 開發環境是 case-insensitive、PG 嚴格 case-sensitive、application code 端可能用 mixed case。

**修法**：

1. **Schema migration 階段強制 lowercase**：所有 table / column name 統一 lowercase
2. **Application code refactor**：grep raw SQL 找 mixed case identifier、改 lowercase
3. **ORM 端設定 `naming_strategy`**：JPA / Hibernate 等明示 lowercase mapping

### Case 4：Replication 行為差、CDC pipeline 失效

**徵兆**：MySQL 端 binlog-based CDC（Debezium MySQL connector）跑得好好的、cutover 後 PG 端要重建 CDC pipeline、初期 1-2 週 message 模式異常。

**根因**：MySQL binlog row format vs PG logical replication slot 完全不同 protocol；Debezium 對兩家連接器是 *獨立* binary、message schema 部分對等但不直通。

**修法**：

1. **Pre-cutover 建 PG 端 CDC**：Debezium PG connector 提前部署、初期跟 MySQL CDC 並存比對
2. **Schema registry 同步**：Avro schema 從 MySQL 端 export、註冊 PG 端 connector 用同 schema
3. **Consumer 端 idempotent**：cutover 期間 dual-source、consumer 必須 idempotent 避免 duplicate

### Case 5：FULLTEXT INDEX 對應 tsvector、application search broken

**徵兆**：cutover 後 application 全文搜尋功能失效、`MATCH(name) AGAINST('xxx')` 不被 PG 認；application 端 raw SQL 對 search 寫死。

**根因**：MySQL `FULLTEXT INDEX` + `MATCH ... AGAINST` syntax PG 不支援；PG 用 `tsvector + ts_rank + to_tsquery`、概念對等但 syntax 完全不同。

**修法**：

1. **Pre-migration**：列 application 用到的 fulltext search 場景、改寫成 tsvector pattern
2. **大型 search 改 Elasticsearch / Meilisearch**：fulltext 是專門 search engine 的本職、不該用 RDBMS 解
3. **降級為 LIKE**：簡單 case `WHERE name ILIKE '%xxx%'`、performance 較差但相容性好

## Capacity / cost

| 維度                      | MySQL                     | PostgreSQL                                    |
| ------------------------- | ------------------------- | --------------------------------------------- |
| Instance cost             | 對等（同 EC2 / RDS spec） | 對等                                          |
| Operational FTE           | 對等                      | 對等                                          |
| Connection pooling        | proxysql / mysql-proxy    | PgBouncer（更成熟）                           |
| Index performance         | 對等                      | 對等                                          |
| JSON performance          | Improving                 | JSONB 領先                                    |
| Replication               | Async binlog              | Async streaming + logical                     |
| Extension ecosystem       | 少                        | 大（PostGIS / TimescaleDB / pgvector）        |
| Migration cost (one-time) | -                         | 2-6 FTE 月 × project length（含 application） |

Migration 主要 cost 在 *application code refactor + dual-write window operational*、不是 DB itself。

## 整合 / 下一步

### 跟 [PostgreSQL → Aurora migration](/backend/01-database/vendors/postgresql/migrate-to-aurora/) 串接

部分組織走 *MySQL → PostgreSQL → Aurora* 兩段：

- 先 MySQL → self-managed PostgreSQL（schema 對位 + application 改）
- 穩定後 self-managed PostgreSQL → Aurora（operational simplification）

不要一次跑 *MySQL → Aurora PostgreSQL compat*、認知負擔太大、failure mode 互相干擾。

### 跟 [Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/) 對位

PG 端 CDC pipeline 在 cutover 完成後立刻可用；可作為 *downstream CDC 重建* 的契機、設計 outbox pattern 更穩。

### 下一步議題

- **MySQL 8 vs PostgreSQL 16 feature gap**：MySQL 8 加了 CTE / window function / generated column；2025+ feature parity 漸高、migration ROI 評估會變
- **Reverse migration**（PG → MySQL）：少見、通常是 application 端 dependency lock-in（用了 MySQL-specific stored procedure）
- **MariaDB → PostgreSQL**：跟 MySQL → PG 類似、MariaDB 部分 syntax 略接近 PG（如 `RETURNING`）

## 相關連結

- Source / target vendor：[MySQL](/backend/01-database/vendors/mysql/) / [PostgreSQL](/backend/01-database/vendors/postgresql/)
- 後續路線：[PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/)
- 平行 migration playbook：[Splunk → Elastic](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/)（同為 Type A 高 schema 差）
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/)（本文驗證 Type A 標準形態）
