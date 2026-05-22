---
title: "SQLite SQL Dialect and Index Limits"
date: 2026-05-21
description: "SQLite type affinity、NULL / date handling、constraint、index、query planner 與 PostgreSQL / MySQL 差異"
tags: ["backend", "database", "sqlite", "sql", "index"]
---

SQLite SQL dialect and index limits 的核心責任是說明 SQLite 和 server SQL 的語意差異。SQLite 可以執行大量 SQL，也支援 transaction、index、trigger、view、window function 與 JSON；但它的 typing、constraint、file-level operation、query planner 與 extension model 會影響測試可信度、migration 成本與 production adapter。

本文的判讀錨點是：SQLite 測過代表某個 repository contract 在 SQLite 語意下成立。當 production target 是 PostgreSQL、MySQL、D1、Turso 或其他 server database 時，測試與 migration 要補上 dialect gap evidence。

## Type Affinity

[Type affinity](/backend/knowledge-cards/type-affinity/) 的核心責任是定義資料寫入時如何被保存與比較。SQLite 官方 [Datatypes](https://www.sqlite.org/datatype3.html) 文件說明 SQLite 使用 dynamic typing，型別關聯在 value 層與 column affinity 層共同作用；[STRICT tables](https://www.sqlite.org/stricttables.html) 則提供較嚴格的型別檢查。

| 議題      | SQLite 行為重點                   | Production 影響                             |
| --------- | --------------------------------- | ------------------------------------------- |
| Integer   | value type 可依寫入內容變化       | test fixture 可能放過錯誤型別               |
| Text      | collation 與比較語意需明確設定    | 排序、大小寫、unique 判斷要對照 target DB   |
| Date/time | 常以 TEXT / REAL / INTEGER 表示   | timezone、range query、serialization 要一致 |
| Boolean   | 常以 integer convention 表示      | adapter 要定義 true / false encoding        |
| STRICT    | 提供更接近 server DB 的型別 guard | 適合作為 fixture 預設，仍需 production test |

Type affinity 的教學重點是把資料合約放在 application boundary。若 domain 說 `created_at` 是 timestamp，就要定義 storage format、timezone、precision、comparison query 與 serialization，而非只讓 SQLite 接受任意 value。

```sql
CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  created_at TEXT NOT NULL,
  total_cents INTEGER NOT NULL CHECK (total_cents >= 0)
) STRICT;
```

這段 schema 用 `STRICT`、`NOT NULL` 與 `CHECK` 讓 fixture 更接近正式資料合約。Production target 仍要跑 PostgreSQL / MySQL container test，確認 timestamp、integer range 與 constraint error mapping。

## Constraint Behavior

Constraint behavior 的核心責任是確保資料完整性由 database 和 application 共同維護。SQLite 支援 primary key、unique、check、foreign key 與 deferred constraint，但 foreign key enforcement 需要明確啟用，migration / test runner 也要確認連線設定。

| Constraint  | SQLite 審查點               | 操作判準                                       |
| ----------- | --------------------------- | ---------------------------------------------- |
| Foreign key | `PRAGMA foreign_keys = ON`  | 每個 connection / test setup 都要驗證          |
| Unique      | NULL、collation、expression | 對照 target DB 的 NULL uniqueness 與 collation |
| Check       | type affinity 互動          | 用 domain invalid case 驗證                    |
| Deferred    | transaction boundary        | 用 multi-step workflow 測 commit-time failure  |

Foreign key 是 SQLite fixture 最常漏掉的設定。每個測試連線開啟後應立刻查 `PRAGMA foreign_keys;`，並用一個故意違反 FK 的 fixture case 確認錯誤會出現。

```sql
PRAGMA foreign_keys = ON;
SELECT foreign_keys FROM pragma_foreign_keys;
```

Constraint error 要在 repository adapter 層被歸類。若 production target 會把 duplicate key、foreign key、check violation 映射成不同 error code，SQLite fixture 也要至少保留 domain-level classification test。

## Transaction Behavior

Transaction behavior 的核心責任是定義讀寫隔離、savepoint、nested workflow 與 retry。SQLite 官方 [isolation](https://www.sqlite.org/isolation.html) 文件說明 connection 之間的隔離語意；WAL mode 下 reader / writer behavior 也會影響 concurrent test。

| 行為          | SQLite 判讀                        | 測試影響                               |
| ------------- | ---------------------------------- | -------------------------------------- |
| Single writer | 同一時間只有一個 writer 取得寫鎖   | concurrent writer test 要顯式設計      |
| Snapshot read | WAL mode 下 reader 可讀舊 snapshot | freshness 與 read-after-write 要分開測 |
| Savepoint     | 適合 nested workflow               | repository transaction helper 要支援   |
| Busy timeout  | lock wait policy                   | integration test 要設定固定 timeout    |

Savepoint 可以讓 application 實作可組合的 transaction helper。若上層 workflow 已在 transaction 內，內層 repository 可以使用 savepoint 承接局部 rollback，而非開另一個 database transaction。

```sql
SAVEPOINT create_order;
INSERT INTO orders(id, created_at, total_cents) VALUES (1, '2026-05-21T00:00:00Z', 1200);
RELEASE create_order;
```

Busy timeout 是測試穩定性的關鍵設定。若 fixture 會平行跑測試，應每個 temp DB 獨立，或在專門 concurrency lab 裡測 `SQLITE_BUSY`；一般 contract test 要追求 deterministic result。

## Index Model

Index model 的核心責任是把查詢形狀與資料量變成可觀測的計畫。SQLite 支援 B-tree index、covering index、partial index、expression index 與 query planner；但 planner choice、統計資訊與 function support 會和 target DB 不同。

| Index 類型       | 適用情境                           | 審查問題                                 |
| ---------------- | ---------------------------------- | ---------------------------------------- |
| Composite index  | 多欄位 equality / range query      | 欄位順序是否符合主要 query pattern       |
| Partial index    | active / pending / soft-delete row | predicate 是否穩定、target DB 是否支援   |
| Expression index | normalized email、date bucket      | function deterministic 與 migration 支援 |
| Covering index   | read-mostly list page              | index size 與 write overhead             |

Index review 要從 query pattern 開始，而非從「常用欄位」開始。SQLite 可以用 `EXPLAIN QUERY PLAN` 檢查是否掃 index；production target 要用自己的 explain 工具重跑。

```sql
EXPLAIN QUERY PLAN
SELECT id, total_cents
FROM orders
WHERE created_at >= '2026-05-01T00:00:00Z'
ORDER BY created_at DESC
LIMIT 50;
```

Index drift 是 migration 的常見風險。SQLite fixture 裡的 index 可以讓測試變快，但若 production schema 缺少同等 index，正式服務會在資料量成長後出現 latency spike；因此 index 要進入 schema diff audit。

## Dialect Gap

Dialect gap 的核心責任是把 SQLite 與 target database 的差異寫成 matrix。這份 matrix 應跟 repository adapter、migration plan 與 CI test suite 綁定。

| 面向             | SQLite 審查點                        | 對照路由                                                                                          |
| ---------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------- |
| ALTER TABLE      | 支援範圍、table rebuild              | [Schema migration / versioning](/backend/01-database/vendors/sqlite/schema-migration-versioning/) |
| JSON             | function availability、index support | production container test                                                                         |
| Generated column | expression、storage、index           | migration dry run                                                                                 |
| Window function  | target DB 支援與 planner             | query compatibility suite                                                                         |
| Extension        | FTS、vector、custom function         | vendor extension policy                                                                           |

Dialect matrix 要以 query contract 為單位。每個 repository method 至少列出 SQL feature、SQLite behavior、production behavior、test layer 與 fallback strategy。

```text
Contract: Search active documents by tenant and prefix
SQLite: FTS5 virtual table in fixture
PostgreSQL: tsvector + GIN index
Risk: ranking / tokenizer / collation differ
Evidence: golden result set + production container explain
```

這種寫法讓測試負責驗證 domain contract，避免把兩個 SQL engine 的搜尋語意視為完全一致。

## Test / Migration Impact

Test / migration impact 的核心責任是決定哪些東西可以用 SQLite 快速驗證，哪些東西要交給 production-like database。SQLite 很適合 repository contract、migration fixture、local development 與 file lifecycle drill；涉及 planner、extension、collation、locking、permission、role 與 HA 時，需要追加 target DB evidence。

| 測試層            | SQLite 適合度 | 必補 evidence                              |
| ----------------- | ------------- | ------------------------------------------ |
| Domain repository | 高            | invalid data、constraint、transaction case |
| Migration syntax  | 中            | target DB dry run                          |
| Query performance | 中            | target DB explain + realistic data volume  |
| Permission / role | 低            | server DB integration test                 |
| HA / failover     | 低            | vendor-specific drill                      |

SQLite fixture 的價值在於快、穩、便宜。它應承擔「資料合約是否被 repository 保護」；production container 或 staging database 承擔「正式 engine 是否用同樣方式執行」。

## 下一步路由

SQL dialect and index limits 完成後，下一步要把 gap 接到實作層。測試設計讀 [Test Fixture Best Practice](/backend/01-database/vendors/sqlite/test-fixture-best-practice/)；migration 實作讀 [Schema migration / versioning](/backend/01-database/vendors/sqlite/schema-migration-versioning/)；要升級到 PostgreSQL，讀 [SQLite to PostgreSQL migration](/backend/01-database/vendors/sqlite/migrate-to-postgresql/)。
