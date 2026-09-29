---
title: "PostgreSQL Online Schema Change：先用 ALTER 內建特性、不能解才 pg_repack / pg-osc"
date: 2026-05-19
description: "PostgreSQL ALTER TABLE 對多數變更已是 *fast catalog-only*（add column nullable / drop column / 改 default），不必走 ghost table tool。本文走 PG 內建 fast DDL 行為、何時必須走 pg_repack / pg-osc、兩工具機制對比（trigger-based vs WAL-shipping）、配置 step-by-step、5 production 踩雷（lock 升級 / VACUUM FULL 誤用 / pg_repack version mismatch / concurrent index 失敗清理 / generated stored column 不能 online）、跟 MySQL gh-ost / pt-osc sibling 對比"
weight: 13
tags: ["backend", "database", "postgresql", "schema-migration", "online-ddl", "deep-article"]
---

本文的範圍是 PostgreSQL 的 online schema change：ALTER TABLE 哪些變更只改 catalog、哪些要 rewrite，何時需要 ghost table tool，pg_repack 與 pg-osc 的機制與配置，production 踩雷、容量與時間估算，以及跟 MySQL gh-ost / pt-osc 的對照。

---

做 online schema change 之前，先確認 PG 自己的 ALTER 對這個變更是只改 catalog、還是要 rewrite 或掃描整張 table；確定會 rewrite 大表，才需要 ghost table tool。

## PG ALTER TABLE 的 fast / slow 分類

PG 的 ALTER TABLE 依它對 table 做的事分成三種：只改 catalog、要 rewrite 或掃描整張 table、以及用 CONCURRENTLY 在不擋讀寫的情況下建立或移除 index。

### Fast catalog-only（< 1 秒、只改 metadata）

PG 9.4+ / 11+ 多數 ALTER 已 catalog-only：

- `ADD COLUMN col TYPE NULL DEFAULT NULL` — 直接 metadata、不 rewrite
- `ADD COLUMN col TYPE NOT NULL DEFAULT <constant>`（PG 11+）— PG 把 default 值存進 catalog（`pg_attribute.attmissingval`），舊 row 讀取時補上這個值、不 rewrite
- `DROP COLUMN` — metadata 標 dropped、實際 row 不 rewrite（VACUUM 之後逐步清理）
- `ALTER COLUMN ... SET DEFAULT <constant>` — metadata
- `RENAME COLUMN` / `RENAME TABLE` — metadata
- `ADD CONSTRAINT ... NOT VALID` — 標記 constraint 不 validate、之後 `VALIDATE CONSTRAINT` 才 scan
- `ALTER COLUMN ... TYPE` 同 binary-compat 類型（`VARCHAR(10) → VARCHAR(20)`、`TEXT → VARCHAR`（不帶長度）等）— catalog-only；`TEXT → VARCHAR(n)` 要逐列套長度限制，會 rewrite
- `ALTER COLUMN ... DROP IDENTITY` — catalog-only

這類 ALTER *直接跑、不必任何工具*。

### Rewrite 或全表掃描（lock heavy、production 慎用）

需要 *rewrite 或掃描整張 table*、ACCESS EXCLUSIVE lock 整個 ALTER 期間：

- `ALTER COLUMN ... TYPE` binary 不相容類型（`INT → BIGINT` 永遠 rewrite、`TEXT → INT` 也是）— 雖然語意「擴大」、底層 4-byte 跟 8-byte storage 不同、全表 rewrite + ACCESS EXCLUSIVE 不可省
- `ALTER COLUMN ... SET NOT NULL` 對既有 nullable column：不 rewrite，但持 ACCESS EXCLUSIVE 掃完整張 table 確認沒有 NULL
- `ALTER TABLE ... SET TABLESPACE`

這類 ALTER 對大表 *production 不能直接跑*、要 ghost table tool。

### Concurrent index（不擋讀寫）

- `CREATE INDEX CONCURRENTLY` — 不 lock 寫入、background build、慢但安全
- `REINDEX INDEX CONCURRENTLY`（PG 12+） — 同上
- `DROP INDEX CONCURRENTLY` — 不擋 table 的讀寫：table 與 index 上拿的是 SHARE UPDATE EXCLUSIVE，等既有 transaction 結束之後才移除 index

## 何時需要 ghost table tool

只在以下場景才需要 pg_repack / pg-osc：

1. **Rewrite-required type change**（需要 rewrite 的 `ALTER COLUMN TYPE`）對大表：這一項要用 pg-osc，pg_repack 不改 schema
2. **VACUUM FULL 替代**：pg_repack 比 VACUUM FULL 安全（不 lock 整表）
3. **Bloat 重組**：大表 dead tuple 累積、想完整 rewrite

對「add column」「drop column」「create index」等場景 *PG 內建 fast 已夠*、不必 ghost table tool。

## pg_repack — Trigger-based + 雙 table swap

pg_repack 是 PG community 標準 online table rewrite 工具，用來清 bloat、依 clustered index 重排或搬 tablespace，不改 schema：

```bash
pg_repack -h primary.example.com -p 5432 -d production -U postgres \
  --table=orders --no-superuser-check
```

**Mechanism**：

1. 建 log table `repack.log_<oid>`，記錄原表之後的變更
2. 在原表加一個 trigger，把 INSERT / UPDATE / DELETE 寫進 log table
3. 建新表 `repack.table_<oid>`，把原表所有 row 複製進去
4. 在新表上建 index
5. 把 log table 累積的變更套到新表
6. 切換：透過 system catalog 交換新舊兩張表（含 index 與 toast table）
7. Drop 舊的那份資料與 trigger / log table

**Trade-off**：

- *Trigger overhead*：每個 primary 寫入加 trigger 執行（10-30% 寫吞吐降）
- *FK 處理*：需要 drop & re-create FK referencing original table（pg_repack 自動處理但有 lock window）
- *版本綁定*：client 端的 `pg_repack` 程式、server 端的 library 與 extension 版本要一致，不一致時 pg_repack 直接報錯（見〈pg_repack version mismatch〉）

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

## pg-osc / pg-online-schema-change — Trigger + audit table + shadow table

[pg-osc](https://github.com/shayonj/pg-osc)（Shayon Mukherjee、2023）是較新的工具，把 ALTER 套在 shadow table 上再切換：

**Mechanism**：

1. 建 audit table，記錄原表之後的變更
2. 短暫拿 ACCESS EXCLUSIVE lock，在原表加 trigger，把 INSERT / UPDATE / DELETE 寫進 audit table
3. 建 shadow table，在 shadow table 上跑 ALTER
4. 複製原表所有 row，在 shadow table 上建 index
5. 把 audit table 累積的變更 replay 到 shadow table
6. 拿 lock 交換表名、更新 foreign key 參照，之後 ANALYZE 新表

**Trade-off**：

- *Primary 寫入 overhead*：跟 pg_repack 同一類，每筆寫入多跑一次 trigger
- 比 pg_repack 較新（社群驗證度低）
- 適合 PG 內建 ALTER 會 rewrite 整張大表的 schema 變更，這一類 pg_repack 做不到

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

pg_repack 管 bloat 重組與 tablespace 搬移，pg-osc 管會 rewrite 的 schema 變更；以下以 pg_repack 為例。

### 安裝 + 確認版本

```sql
-- 安裝 pg_repack（versioned）
CREATE EXTENSION pg_repack;
SELECT * FROM pg_available_extensions WHERE name = 'pg_repack';
-- installed_version 是 extension 自己的版本號（1.x），要跟 client 端 pg_repack 程式的版本一致
```

### 跑 pg_repack

```bash
# --jobs=4：並行 worker
# --wait-timeout=60：等 lock 超時（秒）
# --no-kill-backend：不主動 kill 卡 lock 的 query
pg_repack -h primary -d production -U postgres \
  --table=orders \
  --jobs=4 \
  --wait-timeout=60 \
  --no-kill-backend
```

### 監控

```sql
-- 看 pg_repack 進度
SELECT pid, query, state, wait_event_type, wait_event
FROM pg_stat_activity
WHERE query LIKE '%repack%';

-- 看 lock 狀態：orders 本身，以及 repack schema 裡 pg_repack 建的暫存表
SELECT l.pid, n.nspname, c.relname, l.mode, l.granted
FROM pg_locks l
JOIN pg_class c ON c.oid = l.relation
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE (n.nspname = 'public' AND c.relname = 'orders')
   OR n.nspname = 'repack';
```

### 驗證

```sql
-- 跑完後對比 row count + 抽樣 query
SELECT count(*) FROM orders;
-- 跟 pg_repack 之前 count 對比
```

## Production 踩雷

### ALTER 直接跑沒看是不是 fast 變 lock heavy

`ALTER TABLE orders ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending'` — 預期 catalog-only（PG 11+）、但若 PG 10 跑這個就會 rewrite 整表、ACCESS EXCLUSIVE lock 幾小時。

修法：

- 寫 schema migration 前 *確認 PG version*
- 看 [PG ALTER doc](https://www.postgresql.org/docs/current/sql-altertable.html)、each subcommand 標 *Note* 段是否 fast
- Production 跑前 staging 測 + 監控 `pg_stat_activity` lock wait

### VACUUM FULL 誤用 — Production downtime

`VACUUM FULL` 等於「rewrite 整表 + ACCESS EXCLUSIVE lock」。Production 跑 = 表變 unavailable 幾分鐘到幾小時。

修法：

- *永遠用 pg_repack* 取代 VACUUM FULL（除非 maintenance window）
- 對 bloat 議題、定期跑 pg_repack
- autovacuum tuning 第一優先（[autovacuum-tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/) 詳細）

### pg_repack version mismatch

PG cluster 升級之後、`pg_repack` extension 還停在舊版本，而 client 端已經換成新版的 `pg_repack`，一跑就報錯：`program 'pg_repack V1' does not match database library 'pg_repack V2'`（程式與 server library 不一致），或 `extension 'pg_repack V1' required, found 'pg_repack V2'`（程式與 extension 不一致）。

修法：

- 升 PG cluster 後 *立即 ALTER EXTENSION pg_repack UPDATE*
- 若 pg_repack 還沒釋出對應 PG 版本（早期升級）、暫時用 pg-osc 替代或等待
- 升級 runbook 紀錄 pg_repack 是 *必同步升級的 extension*

### CREATE INDEX CONCURRENTLY 失敗清理

`CREATE INDEX CONCURRENTLY` 跑到一半被 cancel（用戶 Ctrl-C / connection drop）、產生 *invalid index*：

```sql
SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;
-- 回傳被中斷的那個 index，名字沿用 CREATE INDEX CONCURRENTLY 當初給的名字（例：idx_orders_status）
```

Invalid index 仍佔 disk、寫入時仍要維護它，但 optimizer 不會用。

修法：

- 跑 `DROP INDEX CONCURRENTLY idx_orders_status`
- 之後重新 `CREATE INDEX CONCURRENTLY`
- 避免在 connection 不穩的 session 跑長時間 CREATE INDEX CONCURRENTLY、改用 cron 或 deploy pipeline

### Generated stored column 不能 online ADD

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

- 或用 pg-osc：把 ADD GENERATED STORED 套在 shadow table 上，rewrite 發生在 shadow table

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

| 維度                | PG pg_repack        | PG pg-osc              | MySQL gh-ost       | MySQL pt-osc           |
| ------------------- | ------------------- | ---------------------- | ------------------ | ---------------------- |
| 機制                | Trigger + log table | Trigger + audit table  | Binlog stream      | Trigger + log table    |
| Primary 寫 overhead | 中（trigger）       | 中（trigger）          | 0（binlog 已存在） | 中（trigger）          |
| Throttle 支援       | 部分                | 支援                   | 強                 | 支援（`--max-lag`）    |
| Pause / Resume      | 不支援              | 不支援                 | 支援               | 支援（`--pause-file`） |
| 工具成熟度          | 高                  | 中（2023+）            | 高                 | 高                     |
| Use case 比例       | PG 主流（90% case） | rewrite 型 schema 變更 | MySQL 主流（dev）  | MySQL legacy + FK      |

PG OSC tool 使用頻率比 MySQL 低 — 因為 PG 內建 fast ALTER 已 cover 90% schema change、ghost table tool 只對 *少數 rewrite-required* 場景。

詳見 [MySQL Online Schema Change Tools](/backend/01-database/vendors/mysql/online-schema-change-tools/) ：MySQL 端 gh-ost 與 pt-osc 的機制、throttle 與 cutover。

## 跟其他模組整合

### 跟 Replication topology

ALTER TABLE / pg_repack / pg-osc 都產生 WAL、會 replicate 到 standby。Standby 上的 long-running query 可能跟 ALTER 衝突、被 `hot_standby_feedback` 影響 primary autovacuum。詳見 [Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)。

### 跟 Autovacuum Tuning

Schema change 後常產生 dead tuple、autovacuum 需要重新 cover。詳見 [Autovacuum Tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)。

### 跟 Logical Replication

logical replication 透過 publication / subscription 同步 — DDL *不會* 經 logical replication 同步（官方文件 logical replication 的限制段列在第一條，目前的 PG 18 文件仍是如此）、必須 *在 publisher / subscriber 各自跑 DDL*。詳見 [Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/)。

### 跟 Patroni HA

Patroni promote 新 primary 之後，pg_repack extension 已經隨 streaming replication 存在於新 primary，在新 primary 上重跑 pg_repack 即可；failover 時正在跑的那一次被中斷，留下的 trigger 與暫存表要先清掉，官方文件的做法是 `DROP EXTENSION pg_repack CASCADE` 再 `CREATE EXTENSION pg_repack`。詳見 [Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/)。

## 何時用哪個

| 情境                                          | 選擇                                                              |
| --------------------------------------------- | ----------------------------------------------------------------- |
| ADD COLUMN nullable / DROP COLUMN / RENAME 等 | 直接 ALTER（fast catalog-only）                                   |
| CREATE INDEX 大表                             | `CREATE INDEX CONCURRENTLY`                                       |
| ALTER COLUMN TYPE rewrite（大表）             | pg-osc                                                            |
| Bloat 重組                                    | pg_repack                                                         |
| Tablespace 搬移                               | pg_repack（`--tablespace`）                                       |
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
