---
title: "PostgreSQL Online Schema Change：先用 ALTER 內建特性、不能解才 pg_repack / pg-osc"
date: 2026-05-19
description: "PostgreSQL ALTER TABLE 對多數變更已是 *fast catalog-only*（add column nullable / drop column / 改 default），不必走 ghost table tool。本文走 PG 內建 fast DDL 行為、何時必須走 pg_repack / pg-osc、兩工具機制對比（trigger-based vs WAL-shipping）、配置 step-by-step、5 production 踩雷（lock 升級 / VACUUM FULL 誤用 / pg_repack version mismatch / concurrent index 失敗清理 / generated stored column 不能 online）、跟 MySQL gh-ost / pt-osc sibling 對比"
weight: 13
tags: ["backend", "database", "postgresql", "schema-migration", "online-ddl", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 PG 在 OLTP 譜系的定位、本文聚焦 *online schema change* — 先看 PG ALTER 哪些已 fast catalog-only、再看 pg_repack / pg-osc 何時必要。

---

跟 MySQL 不同：PG 大量 schema change *內建* fast catalog-only 行為、不必走 ghost table tool。MySQL 對應的 gh-ost / pt-online-schema-change 之於 PG 是 *少數場景才需要的 escape hatch*、不是 standard practice。

寫作 OSC 時必須 *先看 PG 自身 ALTER 行為*、確認真的需要再上 pg_repack / pg-osc — 否則徒增複雜度。

## PG ALTER TABLE 的 fast / slow 分類

```sql
-- ALTER TABLE 的操作大致三類
```

### 類 A：Fast catalog-only（< 1 秒、metadata 改）

PG 9.4+ / 11+ 多數 ALTER 已 catalog-only：

- `ADD COLUMN col TYPE NULL DEFAULT NULL` — 直接 metadata、不 rewrite
- `ADD COLUMN col TYPE NOT NULL DEFAULT <constant>`（PG 11+）— optimizer 把 default 存在 metadata、舊 row read 時動態返回 default、不 rewrite
- `DROP COLUMN` — metadata 標 dropped、實際 row 不 rewrite（VACUUM 之後逐步清理）
- `ALTER COLUMN ... SET DEFAULT <constant>` — metadata
- `RENAME COLUMN` / `RENAME TABLE` — metadata
- `ADD CONSTRAINT ... NOT VALID` — 標記 constraint 不 validate、之後 `VALIDATE CONSTRAINT` 才 scan
- `ALTER COLUMN ... TYPE` 同 binary-compat 類型（`VARCHAR(10) → VARCHAR(20)`、`TEXT → VARCHAR` 等）— catalog-only

這類 ALTER *直接跑、不必任何工具*。

### 類 B：Lock heavy（rewrites table、production 慎用）

需要 *rewrite 整張 table*、ACCESS EXCLUSIVE lock 整個 ALTER 期間：

- `ALTER COLUMN ... TYPE` 不相容類型（`INT → BIGINT` PG 12 之前、`TEXT → INT` 永遠）
- `ALTER COLUMN ... SET NOT NULL` 對既有 nullable column（要 scan 整 table）
- `ALTER COLUMN ... DROP IDENTITY`
- `ALTER TABLE ... SET TABLESPACE`

這類 ALTER 對大表 *production 不能直接跑*、要 ghost table tool。

### 類 C：Concurrent index / online operation（無 table lock）

- `CREATE INDEX CONCURRENTLY` — 不 lock 寫入、background build、慢但安全
- `REINDEX INDEX CONCURRENTLY`（PG 12+） — 同上
- `DROP INDEX CONCURRENTLY` — 短 ACCESS EXCLUSIVE lock 只在最後 swap

## 何時需要 ghost table tool

只在以下場景才需要 pg_repack / pg-osc：

1. **Rewrite-required type change**（類 B `ALTER COLUMN TYPE`）對大表
2. **VACUUM FULL 替代**：pg_repack 比 VACUUM FULL 安全（不 lock 整表）
3. **Bloat 重組**：大表 dead tuple 累積、想完整 rewrite

對「add column」「drop column」「create index」等場景 *PG 內建 fast 已夠*、不必 ghost table tool。

## Tool 1：pg_repack — Trigger-based + 雙 table swap

pg_repack 是 PG community 標準 online table rewrite 工具：

```bash
pg_repack -h primary.example.com -p 5432 -d production -U postgres \
  --table=orders --no-superuser-check
```

**Mechanism**：

1. CREATE `repack.table_<oid>` 跟原表同 schema
2. 在原表加 3 個 trigger：INSERT / UPDATE / DELETE → 寫入 log table `repack.log_<oid>`
3. 從原表 `INSERT INTO repack.table_<oid> SELECT * FROM original` 複製 row
4. 邊複製邊 apply log table 紀錄的變更
5. 切換：rename 原表 → original_old、rename repack.table_<oid> → original（atomic）
6. Drop 舊原表跟 trigger / log

**Trade-off**：

- *Trigger overhead*：每個 primary 寫入加 trigger 執行（10-30% 寫吞吐降）
- *FK 處理*：需要 drop & re-create FK referencing original table（pg_repack 自動處理但有 lock window）
- 適用 *PG-version 綁定* — pg_repack 13 不能對 PG 14 cluster 跑

**配置**：

```sql
-- Primary 安裝
CREATE EXTENSION pg_repack;
```

```bash
# Repack orders
pg_repack -d production --table=orders
# 監控 lock：另一 session 跑 SELECT * FROM pg_stat_activity
```

## Tool 2：pg-osc / pg-online-schema-change — WAL-shipping style

[pg-osc](https://github.com/shayonj/pg-osc)（Shayon Mukherjee、2023）是較新的工具、模仿 gh-ost mechanism：

**Mechanism**：

1. 用 logical replication slot 從 primary WAL stream 變更
2. CREATE shadow table + 套 ALTER 變更
3. Stream WAL event 同步 shadow table（不靠 trigger）
4. 完成後 swap

**Trade-off**：

- *Primary 寫入 overhead*：0（WAL 已存在）
- 比 pg_repack 較新（社群驗證度低）
- 適合 *trigger overhead 不可接受* 的高吞吐 production

**配置**：

```bash
# 用 gem install
gem install pg_online_schema_change

# Run
pg-online-schema-change perform \
  --alter-statement="ALTER TABLE orders ADD COLUMN status VARCHAR(20)" \
  --schema=public \
  --dbname=production \
  --host=primary.example.com
```

## 配置 step-by-step（pg_repack 為主）

實務多數 PG OSC 用 pg_repack。pg-osc 是 high-write-throughput escape hatch。

### Step 1：安裝 + 確認版本

```sql
-- 安裝 pg_repack（versioned）
CREATE EXTENSION pg_repack;
SELECT * FROM pg_available_extensions WHERE name = 'pg_repack';
-- 確認 installed_version 跟 PG major version 對齊
```

### Step 2：跑 pg_repack

```bash
pg_repack -h primary -d production -U postgres \
  --table=orders \
  --jobs=4 \                       # 並行 worker
  --wait-timeout=60 \              # 等 lock 超時（秒）
  --no-kill-backend                # 不主動 kill 卡 lock 的 query
```

### Step 3：監控

```sql
-- 看 pg_repack 進度
SELECT pid, query, state, wait_event_type, wait_event
FROM pg_stat_activity
WHERE query LIKE '%repack%';

-- 看 lock 狀態
SELECT * FROM pg_locks WHERE relation IN (
  SELECT oid FROM pg_class WHERE relname IN ('orders', 'repack.table_xxx')
);
```

### Step 4：驗證

```sql
-- 跑完後對比 row count + 抽樣 query
SELECT count(*) FROM orders;
-- 跟 pg_repack 之前 count 對比
```

## 5 個 Production 踩雷

### 1. ALTER 直接跑沒看是不是 fast 變 lock heavy

`ALTER TABLE orders ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending'` — 預期 catalog-only（PG 11+）、但若 PG 10 跑這個就會 rewrite 整表、ACCESS EXCLUSIVE lock 幾小時。

修法：

- 寫 schema migration 前 *確認 PG version*
- 看 [PG ALTER doc](https://www.postgresql.org/docs/current/sql-altertable.html)、each subcommand 標 *Note* 段是否 fast
- Production 跑前 staging 測 + 監控 `pg_stat_activity` lock wait

### 2. VACUUM FULL 誤用 — Production downtime

`VACUUM FULL` 等於「rewrite 整表 + ACCESS EXCLUSIVE lock」。Production 跑 = 表變 unavailable 幾分鐘到幾小時。

修法：

- *永遠用 pg_repack* 取代 VACUUM FULL（除非 maintenance window）
- 對 bloat 議題、定期跑 pg_repack
- autovacuum tuning 第一優先（[autovacuum-tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/) 詳細）

### 3. pg_repack version mismatch

PG cluster 升 14、但 `pg_repack` extension 還是 13 版本。試 ALTER 跑 `pg_repack` 命令、ERROR: `program "pg_repack 14.x" does not match installed extension "pg_repack 13.x"`。

修法：

- 升 PG cluster 後 *立即 ALTER EXTENSION pg_repack UPDATE*
- 若 pg_repack 還沒釋出對應 PG 版本（早期升級）、暫時用 pg-osc 替代或等待
- 升級 runbook 紀錄 pg_repack 是 *必同步升級的 extension*

### 4. CREATE INDEX CONCURRENTLY 失敗清理

`CREATE INDEX CONCURRENTLY` 跑到一半被 cancel（用戶 Ctrl-C / connection drop）、產生 *invalid index*：

```sql
SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;
-- 顯示一個 idx_orders_status_invalid
```

Invalid index 仍佔 disk、但 optimizer 不會用。

修法：

- 跑 `DROP INDEX CONCURRENTLY idx_orders_status_invalid`
- 之後重新 `CREATE INDEX CONCURRENTLY`
- 避免在 connection 不穩的 session 跑長時間 CREATE INDEX CONCURRENTLY、改用 cron 或 deploy pipeline

### 5. Generated stored column 不能 online ADD

`ADD COLUMN total NUMERIC GENERATED ALWAYS AS (price * qty) STORED` — *stored* generated column 必須 rewrite 整表計算 column value、不是 catalog-only。

修法：

- 用 `GENERATED ALWAYS AS (...) VIRTUAL`（PG 18+）— 不存實際 value、catalog-only
- 或 *先加 nullable column + backfill + 加 NOT NULL constraint*：

   ```sql
   ALTER TABLE orders ADD COLUMN total NUMERIC;
   UPDATE orders SET total = price * qty WHERE id BETWEEN ...;  -- chunked
   ALTER TABLE orders ALTER COLUMN total SET NOT NULL;
   -- 之後加 trigger 或 application 層維護 total
   ```

- 或用 pg_repack 跑 rewrite ADD GENERATED STORED

## 容量 / 時間估算

對 100 GB 表、ADD COLUMN 加 index 為例：

| 操作                                              | 時間         | Lock 影響                       |
| ------------------------------------------------- | ------------ | ------------------------------- |
| `ADD COLUMN col TYPE NULL` (PG 11+)               | < 1 秒       | ACCESS EXCLUSIVE（毫秒級）      |
| `ADD COLUMN col TYPE NOT NULL DEFAULT 0` (PG 11+) | < 1 秒       | ACCESS EXCLUSIVE（毫秒級）      |
| `CREATE INDEX CONCURRENTLY`                       | 2-6 小時     | 無 table lock                   |
| `pg_repack table`                                 | 4-8 小時     | 短 ACCESS EXCLUSIVE（swap）     |
| `ALTER COLUMN TYPE` rewrite                       | 4-8 小時     | ACCESS EXCLUSIVE 全程           |
| `VACUUM FULL`                                     | 同 pg_repack | ACCESS EXCLUSIVE 全程（不要跑） |

## 跟 MySQL gh-ost / pt-osc 對照

| 維度                | PG pg_repack        | PG pg-osc           | MySQL gh-ost       | MySQL pt-osc        |
| ------------------- | ------------------- | ------------------- | ------------------ | ------------------- |
| 機制                | Trigger + log table | WAL logical stream  | Binlog stream      | Trigger + log table |
| Primary 寫 overhead | 中（trigger）       | 0（WAL 已存在）     | 0（binlog 已存在） | 中（trigger）       |
| Throttle 支援       | 部分                | 支援                | 強                 | 部分                |
| Pause / Resume      | 不支援              | 不支援              | 支援               | 不支援              |
| 工具成熟度          | 高                  | 中（2023+）         | 高                 | 高                  |
| Use case 比例       | PG 主流（90% case） | 高吞吐 escape hatch | MySQL 主流（dev）  | MySQL legacy + FK   |

PG OSC tool 使用頻率比 MySQL 低 — 因為 PG 內建 fast ALTER 已 cover 90% schema change、ghost table tool 只對 *少數 rewrite-required* 場景。

詳見 [MySQL Online Schema Change Tools](/backend/01-database/vendors/mysql/online-schema-change-tools/) — sibling、不同 use case mix。

## 跟其他模組整合

### 跟 Replication topology

ALTER TABLE / pg_repack / pg-osc 都產生 WAL、會 replicate 到 standby。Standby 上的 long-running query 可能跟 ALTER 衝突、被 `hot_standby_feedback` 影響 primary autovacuum。詳見 [Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)。

### 跟 Autovacuum Tuning

Schema change 後常產生 dead tuple、autovacuum 需要重新 cover。詳見 [Autovacuum Tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)。

### 跟 Logical Replication

logical replication 透過 publication / subscription 同步 — DDL *不會* logical replicate（PG 16 之前）、必須 *在 publisher / subscriber 各自跑 DDL*。詳見 [Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/)。

### 跟 Patroni HA

Patroni promote 新 primary 後、pg_repack extension state（slot / catalog）跟著走、新 primary 仍可繼續 pg_repack。詳見 [Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/)。

## 何時用哪個

| 情境                                          | 選擇                                                              |
| --------------------------------------------- | ----------------------------------------------------------------- |
| ADD COLUMN nullable / DROP COLUMN / RENAME 等 | 直接 ALTER（fast catalog-only）                                   |
| CREATE INDEX 大表                             | `CREATE INDEX CONCURRENTLY`                                       |
| ALTER COLUMN TYPE rewrite（大表）             | pg_repack                                                         |
| Bloat 重組                                    | pg_repack                                                         |
| 高吞吐 + trigger overhead 不可接受            | pg-osc                                                            |
| ADD GENERATED STORED column                   | nullable + backfill + constraint                                  |
| Cluster on Cloud（RDS / Aurora）              | RDS / Aurora 內建 fast DDL 多數已 cover、pg_repack 視 vendor 支援 |

## 相關連結

- [PostgreSQL vendor overview](/backend/01-database/vendors/postgresql/)
- [PG Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)（ALTER 跟 streaming replication 互動）
- [PG Autovacuum Tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)（schema change 後 vacuum 議題）
- [PG Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/)（DDL 不 replicate 議題）
- [PG Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/)（HA 跟 pg_repack 整合）
- [MySQL Online Schema Change Tools](/backend/01-database/vendors/mysql/online-schema-change-tools/)（sibling、tool ecosystem 不同）
- [Expand / Contract 卡片](/backend/knowledge-cards/expand-contract/)（schema migration 設計原則）
- 官方：[ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html) / [pg_repack GitHub](https://github.com/reorg/pg_repack) / [pg-osc GitHub](https://github.com/shayonj/pg-osc)
