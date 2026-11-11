---
title: "SQLite SQL Dialect and Index Limits"
date: 2026-05-21
description: "SQLite type affinity、NULL / date handling、constraint、index、query planner 與 PostgreSQL / MySQL 差異；SQLite 各構造加入的版本與查實際執行版本的方法、INSERT OR REPLACE 與 ON CONFLICT DO UPDATE、LATERAL／DISTINCT ON／ROLLUP／MERGE 在 SQLite 上的改寫"
tags: ["backend", "database", "sqlite", "sql", "index"]
---

SQLite SQL dialect and index limits 的核心責任是說明 SQLite 和 server SQL 的語意差異。SQLite 可以執行大量 SQL，也支援 transaction、index、trigger、view、window function 與 JSON；但它的 typing、constraint、file-level operation、query planner 與 extension model 會影響測試可信度、migration 成本與 production adapter。

SQLite 測過代表某個 repository contract 在 SQLite 語意下成立，所以本文的範圍是 production target 為 PostgreSQL、MySQL、D1、Turso 或其他 server database 時，type affinity、constraint、transaction 與 index 這幾處 SQLite 語意與 target 的差異；SQLite 與 PostgreSQL 之間的方言對照：SQLite 各構造加入的版本與查實際執行版本的方法、彈性型別對照 PostgreSQL 的型別檢查、拼法不同的寫法、拼法相同或名字相近而結果不同的寫法（含 `INSERT OR REPLACE`）、PostgreSQL 有而 SQLite 不收的查詢構造在同一份資料上的改寫；以及測試與 migration 要為這些差異補上哪些 dialect gap evidence。PostgreSQL 有而 SQLite 沒有、從部署形態推得出來的構造（列鎖、排除約束、建議鎖、角色）各自服務哪一種需求，在 [SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異](/backend/01-database/sql/deployment-shape-and-sql-constructs/)。

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

### 同一組值在 SQLite 一般表與 PostgreSQL 上的結果

SQLite 一般表的欄位型別是傾向而不是限制，這是 SQLite 官方文件寫明的設計選擇（彈性型別，flexible typing）；函式庫同樣是所有寫入的必經之路，`STRICT` 表證明它檢查得了型別。同一組值與運算在 SQLite 3.53.0 與 PostgreSQL 16.2 上的實測：

| 送進去的值或運算            | SQLite（一般表）                     | PostgreSQL                                    |
| --------------------------- | ------------------------------------ | --------------------------------------------- |
| `'abc'` 寫進 `INTEGER` 欄位 | 收下，`typeof` 回 `text`             | 拒絕：`invalid input syntax for type integer` |
| 日期 `'2026-02-30'`         | `date('2026-02-30')` 回 `2026-03-02` | 拒絕：`date/time field value out of range`    |
| `0.1 + 0.2 = 0.3`           | 假（浮點數，`0.30000000000000004`）  | 真（小數常值的型別是 `numeric`）              |

`STRICT` 表同樣寫 `'abc'` 得到 `cannot store TEXT value in INTEGER column`。SQLite 的 `date()` 遇到 29 到 31 日而那個月沒有那一天時往後進位，月份或日期超出格式範圍時（`2026-13-01`、`2026-01-32`）回 `NULL`，兩種都不報錯。PostgreSQL 另有使用者定義型別：`CREATE DOMAIN` 是帶檢查條件的既有型別，`CREATE TYPE … AS ENUM` 是列舉值，陣列與區間是內建型別；SQLite 沒有這幾種語法，限制欄位值改用 `CHECK`，條件要在每一張用到這個格式的表上各寫一次，而 `DOMAIN` 定義一次、各表引用，檢查也作用在型別轉換與函式參數上。SQLite 收下的不合格值複製到 PostgreSQL 時在寫入那一步被拒絕，所以搬遷前先用 `typeof()` 與日期函式掃一次既有資料。

## Constraint Behavior

Constraint behavior 的核心責任是確保資料完整性由 database 和 application 共同維護。SQLite 支援 primary key、unique、check、foreign key 與 deferred constraint，但 foreign key enforcement 需要明確啟用，migration / test runner 也要確認連線設定。

| Constraint  | SQLite 審查點               | 操作判斷標準                                   |
| ----------- | --------------------------- | ---------------------------------------------- |
| Foreign key | `PRAGMA foreign_keys = ON`  | 每個 connection / test setup 都要驗證          |
| Unique      | NULL、collation、expression | 對照 target DB 的 NULL uniqueness 與 collation |
| Check       | type affinity 互動          | 用 domain invalid case 驗證                    |
| Deferred    | transaction boundary        | 用 multi-step workflow 測 commit-time failure  |

Foreign key 是 SQLite fixture 最常漏掉的設定。每個測試連線開啟後應立刻查 `PRAGMA foreign_keys;`，並用一個故意違反 FK 的 fixture case 確認錯誤會出現。

```sql
PRAGMA foreign_keys = ON;
SELECT foreign_keys FROM pragma_foreign_keys;
-- 1：這個 connection 已啟用 FK；回 0 代表 test setup 沒有執行到上一行

-- 故意違反 FK 的 fixture case：payments.order_id 參照 orders(id)，999 不存在
CREATE TABLE payments (
  id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL REFERENCES orders(id)
) STRICT;
INSERT INTO payments (id, order_id) VALUES (1, 999);
-- Runtime error: FOREIGN KEY constraint failed
-- 這一行沒有報錯，就代表這個 connection 的 FK enforcement 沒有生效
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
-- 上方 schema 沒有 created_at 的 index：
-- |--SCAN orders
-- `--USE TEMP B-TREE FOR ORDER BY

CREATE INDEX orders_created_at ON orders(created_at);
-- 同一段查詢再跑一次 EXPLAIN QUERY PLAN：
-- `--SEARCH orders USING INDEX orders_created_at (created_at>?)
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

### SQLite 與 PostgreSQL 的寫法對照：拼法不同而結果相同、拼法相同而結果不同

搬遷時最大量的改動是拼法不同的寫法，改寫之後結果相同，測試套件跑得出改漏的地方。下表在 SQLite 3.53.0 與 PostgreSQL 16.2 上各執行過一次：

| 用途           | SQLite                                | PostgreSQL                                    | 兩家都收的寫法                  |
| -------------- | ------------------------------------- | --------------------------------------------- | ------------------------------- |
| 參數佔位       | `?`、`?1`、`:name`                    | `$1`（驅動程式可能另外轉換）                  | 由驅動程式決定                  |
| 自動遞增的主鍵 | `INTEGER PRIMARY KEY [AUTOINCREMENT]` | `GENERATED ALWAYS AS IDENTITY`                | 無，各寫各的                    |
| 型別轉換       | `CAST(x AS INTEGER)`                  | `x::int` 或 `CAST`                            | `CAST`                          |
| 空值替代       | `IFNULL(a, b)`                        | `COALESCE(a, b)`                              | `COALESCE`                      |
| 字串串接聚合   | `group_concat(x, ',')`                | `string_agg(x, ',')`                          | `string_agg`（SQLite 3.44 起）  |
| 取月初         | `strftime('%Y-%m-01', t)`             | `date_trunc('month', t)`                      | 無                              |
| 現在時間       | `datetime('now')`                     | `now()`                                       | `CURRENT_TIMESTAMP`，見下一張表 |
| 取前幾列       | `LIMIT n OFFSET m`                    | `LIMIT n OFFSET m`、`FETCH FIRST n ROWS ONLY` | `LIMIT … OFFSET`                |

拼法相同而結果不同的寫法沒有報錯，要靠比對兩家的輸出才找得到：

| 寫法                | SQLite                           | PostgreSQL                                      |
| ------------------- | -------------------------------- | ----------------------------------------------- |
| `'a' LIKE 'A'`      | 真：ASCII 字母預設不分大小寫     | 假；不分大小寫要寫 `ILIKE`，SQLite 不收 `ILIKE` |
| `SELECT TRUE`       | `1`：布林值就是整數              | `true`：獨立的 `boolean` 型別                   |
| `CURRENT_TIMESTAMP` | UTC 的文字 `2026-11-11 20:19:52` | 帶時區的 `timestamptz`，依連線的時區顯示        |

名字相近而語意不同的一組是 SQLite 的 `INSERT OR REPLACE` 與兩家都有的 `ON CONFLICT DO UPDATE`（SQLite 3.24 起）。`INSERT OR REPLACE` 是 SQLite 在有 `ON CONFLICT` 之前處理唯一鍵衝突的寫法，遇到衝突時刪掉衝突的那一列、再插入一列新的；`ON CONFLICT DO UPDATE` 就地更新原列，PostgreSQL 只收後者。在空表上依序執行：

```sql
CREATE TABLE punch (id INTEGER PRIMARY KEY, emp_id INT, day TEXT, at TEXT, note TEXT DEFAULT '');
CREATE UNIQUE INDEX one_per_day ON punch (emp_id, day);
INSERT INTO punch (emp_id, day, at, note) VALUES (1, '2026-11-10', '09:01', 'a');     -- id 1
INSERT INTO punch (emp_id, day, at, note) VALUES (1, '2026-11-11', '08:55', '補登');  -- id 2

INSERT OR REPLACE INTO punch (emp_id, day, at) VALUES (1, '2026-11-11', '10:00') RETURNING id;
-- 回 3；表裡剩 (1, …, 'a') 與 (3, 1, '2026-11-11', '10:00', '')：id 2 那一列被刪掉，note 回到預設值
```

衝突出在主鍵以外的唯一鍵（這裡是 `(emp_id, day)`）而語句沒有給主鍵時，主鍵換成新配的值；不論衝突在哪個鍵上，語句沒寫到的欄位都回到預設值。有別的表以外鍵指向被刪的那一列時，結果看外鍵檢查有沒有開：`PRAGMA foreign_keys` 開著，整句以外鍵錯誤失敗、原列保留；關著，替換成功，子表那一列仍然指著已經不存在的 `id`。

`LIKE` 的大小寫規則與 collation 的關係在 [SQL.15 字串比較與 collation：相等、排序、LIKE 與索引可用性](/backend/01-database/sql/string-comparison-and-collation/)。

### SQLite 各構造的加入版本與實際執行版本的查法

SQLite 的 SQL 構造隨版本增加，所以某個構造能不能用，要看實際執行的那一份 SQLite 是哪一版。下表的版本號取自 SQLite 的版本紀錄（release log）；這裡只在 3.53.0 上確認這些構造都能執行，沒有在各版本的邊界上測：

| 構造                                          | SQLite 加入的版本 |
| --------------------------------------------- | ----------------- |
| `INSERT … ON CONFLICT DO NOTHING / DO UPDATE` | 3.24              |
| 視窗函數（`OVER (PARTITION BY …)`）           | 3.25              |
| 生成欄位（`GENERATED ALWAYS AS … STORED`）    | 3.31              |
| `UPDATE … FROM`                               | 3.33              |
| `RETURNING`、`ALTER TABLE … DROP COLUMN`      | 3.35              |
| `STRICT` 表                                   | 3.37              |
| `RIGHT JOIN`、`FULL JOIN`                     | 3.39              |
| `string_agg`                                  | 3.44              |
| JSONB（`jsonb()` 與二進位 JSON 儲存）         | 3.45              |

版本號要在使用它的那個程式裡查：`SELECT sqlite_version();`。同一台機器上可能有好幾份 SQLite——作業系統附的 `sqlite3` 命令列工具、程式語言自帶的、驅動程式靜態連結的——版本各不相同。撰寫時同一台 macOS 上的 `sqlite3` 命令列工具是 3.43.2，Python 3 自帶的是 3.53.0：在命令列工具上試 `string_agg` 得到 `no such function`，Python 程式裡同一句可以執行。

### PostgreSQL 有而 SQLite 不收的查詢構造：同一份資料上的改寫與代價

下面這些構造兩家都算得出同一個結果，PostgreSQL 多提供了一種寫法。SQLite 3.53.0 對它們都回錯誤（`ROLLUP` 是 `no such function`，其餘是語法錯誤），對應的改寫在同一份資料上跑得出相同的列；資料是上面那張打卡表 `punch` 加一張員工表 `emp (id, name, dept)`：

- **每位員工最近一次打卡**：PostgreSQL 可以寫 `DISTINCT ON (emp_id) … ORDER BY emp_id, day DESC`，或用 `CROSS JOIN LATERAL` 讓子查詢引用外層的員工、每位各取一筆（寫成 `LEFT JOIN LATERAL … ON true` 時，沒有打卡的員工也會留下一列）。SQLite 用視窗函數 `row_number() OVER (PARTITION BY emp_id ORDER BY day DESC)` 再取等於 1 的列。排序鍵有同值時（例如打卡表沒有 `one_per_day` 這個唯一索引、同一位員工同一天有兩筆），這幾種寫法挑出的列可能不同，要在 `ORDER BY` 補上分得出先後的欄位（`at`）。SQLite 另有一個自己的寫法：`SELECT emp_id, max(day), at FROM punch GROUP BY emp_id` 會讓 `at` 取自 `max(day)` 那一列，條件是同一個 `SELECT` 裡只有一個 `min()` 或 `max()`；PostgreSQL 拒絕這段查詢，這個特例的邊界在 [SQL.2 子句的求值順序：每一步可用的欄位、語意模型擋下的寫法與各家引擎放寬的寫法](/backend/01-database/sql/clause-evaluation-order/)。
- **各部門人數加上總計**：PostgreSQL 寫 `GROUP BY ROLLUP(dept)` 或 `GROUPING SETS`，在同一段查詢裡產出各組與總計。SQLite 用 `UNION ALL` 接一段不分組的查詢，結果相同，同一張表在兩段查詢裡各讀一次。
- **依來源資料新增、更新或刪除**：PostgreSQL 15 起有 `MERGE`。「來源沒有的就刪除」要 PostgreSQL 17 起的 `WHEN NOT MATCHED BY SOURCE`，16.2 回語法錯誤，所以在 15、16 上與 SQLite 一樣要另寫一段 `DELETE`。SQLite 的 `INSERT … ON CONFLICT DO UPDATE` 涵蓋「有就更新、沒有就新增」：它要求衝突的欄位上有唯一約束或唯一索引，`DELETE` 要跟它放在同一個交易裡才一次完成；這是資料模型與交易設計的改動，不只改查詢文字（這一項的改寫沒有實跑）。

改寫之後的代價差異（多讀一次表、多一層子查詢）要在目標引擎上看執行計畫才知道，原因在 [SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/)。

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
