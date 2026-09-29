---
title: "MySQL Query Optimization：從 EXPLAIN 看到實際執行、5 條 query 從 5 秒變 50ms 的 anatomy"
date: 2026-05-19
description: "MySQL query 慢的根因不在「SQL 寫法」、在「optimizer 選錯 plan」。本文從 5 個常見 production case 開場（5 秒 → 50ms / 30 秒 → 200ms / 8 秒 → 30ms 等）、走 EXPLAIN / EXPLAIN ANALYZE / optimizer trace 三層分析工具、index hint vs optimizer hint 取捨、cardinality estimation 失效時的修法、5 production 踩雷（statistics 過時 / forced index 用錯 / hash join 沒觸發 / range scan 退化 ALL / derived table materialization）"
weight: 21
tags: ["backend", "database", "mysql", "query-optimization", "explain", "deep-article"]
---

> 這篇涵蓋 MySQL 的 query optimization：EXPLAIN、optimizer trace 與 hint 這幾種工具的用法，以及常見的 production case。

---

## 5 個常見 production case

production 上 query 慢、root cause 幾乎都是 *optimizer 選錯 plan*。從以下 5 個 case 進入 query optimization：

### 5 秒 → 50ms：`customers.region` 缺 index

```sql
-- 慢 (5 秒)：optimizer 選 customers 為 outer table、scan 全 1M row
SELECT o.id, o.amount, c.name
FROM orders o JOIN customers c ON o.customer_id = c.id
WHERE o.created_at > '2026-05-01' AND c.region = 'TW';
```

EXPLAIN 顯示：

```text
+----+-------------+-------+------+---------------+--------+
| id | select_type | table | type | possible_keys | rows   |
+----+-------------+-------+------+---------------+--------+
|  1 | SIMPLE      | c     | ALL  | NULL          | 1000000|
|  1 | SIMPLE      | o     | ref  | idx_cust_id   | 100    |
+----+-------------+-------+------+---------------+--------+
```

`c` table type=ALL（full scan）、rows=1M。問題：`customers` 沒在 `region` 上的 index、optimizer 預估「region=TW filter 沒效率、就 full scan」、但 region=TW 只佔 10% row（100K row）。

修法：

```sql
ALTER TABLE customers ADD INDEX idx_region (region);
ANALYZE TABLE customers;  -- 更新 statistics
```

加 index 後 optimizer 切 plan：先 scan `customers` 用 `idx_region` 篩 100K row、再 join `orders`。從 5 秒降到 50ms。

### 30 秒 → 200ms：Range scan 退化 ALL

```sql
SELECT * FROM events
WHERE created_at BETWEEN '2026-05-01' AND '2026-05-02'
AND user_id = 12345;
```

`events` 有 `idx_user_id` 跟 `idx_created_at` 兩個 index、optimizer 應該選一個 + 二級 filter、但實際 `type=ALL`（full scan）。

EXPLAIN ANALYZE 顯示：

```text
-> Filter: ((events.user_id = 12345) and (events.created_at between ...))  (cost=2M rows=100)
    -> Table scan on events  (cost=2M rows=10000000)  (actual time=0.1..30s ...)
```

問題：optimizer estimated rows=100、實際 *cardinality estimation* 失準（distribution skew）、選了 ALL。

修法：

```sql
-- 用 composite index 直接 cover 兩個條件
ALTER TABLE events ADD INDEX idx_user_created (user_id, created_at);
```

Composite index 讓 optimizer 看到 *單一 index 直接 satisfy 兩個 predicate*、走 range scan + index condition pushdown。30 秒降到 200ms。

### 8 秒 → 30ms：Subquery 沒 unnest

```sql
SELECT * FROM orders
WHERE customer_id IN (
    SELECT id FROM customers WHERE region = 'TW' AND vip_level >= 3
);
```

5.6 之前 MySQL 把 `IN (subquery)` 寫成 *correlated subquery*、外表每 row 都 re-run subquery、極慢。5.6+ 加 subquery unnesting、轉換成 JOIN，但某些情況 unnest 失敗。

EXPLAIN 顯示：

```text
+----+--------------------+-----------+-------+
| id | select_type        | table     | type  |
+----+--------------------+-----------+-------+
|  1 | PRIMARY            | orders    | ALL   |
|  2 | DEPENDENT SUBQUERY | customers | unique_subquery |
+----+--------------------+-----------+-------+
```

`DEPENDENT SUBQUERY` 是危險訊號。修法：

```sql
-- 手動改寫成 JOIN
SELECT o.* FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE c.region = 'TW' AND c.vip_level >= 3;
```

或用 `EXISTS`（部分 case 比 `IN` plan 好）：

```sql
SELECT * FROM orders o
WHERE EXISTS (
    SELECT 1 FROM customers c
    WHERE c.id = o.customer_id AND c.region = 'TW' AND c.vip_level >= 3
);
```

不同寫法 plan 差異需用 EXPLAIN 驗證、不能假設「JOIN 一定比 IN 快」。

### Derived table 帶 GROUP BY：MySQL materialize 一次，不會每列重算

```sql
SELECT * FROM orders o
JOIN (
    SELECT customer_id, COUNT(*) AS order_count
    FROM orders
    GROUP BY customer_id
) AS counts ON o.customer_id = counts.customer_id
WHERE counts.order_count > 10;
```

MySQL 處理 FROM 裡的子查詢（derived table）有兩種方式：merge 進外層查詢，或 materialize 成一張內部暫存表、整個查詢只算一次。帶 `GROUP BY` 的 derived table 無法 merge，一律 materialize；EXPLAIN 出現 `select_type=DERIVED` 那一列，代表它被 materialize 了。MySQL 8.4 對上面這段查詢的 `EXPLAIN FORMAT=TREE`（orders 兩萬列、兩千個 customer_id）：

```text
-> Nested loop inner join  (cost=70352 rows=194656)
    -> Filter: (counts.customer_id is not null)  (cost=4170..2222 rows=19731)
        -> Table scan on counts  (cost=4170..4198 rows=2000)
            -> Materialize  (cost=4170..4170 rows=2000)                  -- derived table 算一次、存成暫存表
                -> Filter: (count(0) > 10)  (cost=3970 rows=2000)        -- 外層的 order_count > 10 被推進 derived table 裡過濾
                    -> Group aggregate: count(0)  (cost=3970 rows=2000)
                        -> Covering index scan on orders using idx_cust_id  (cost=1997 rows=19731)
    -> Index lookup on o using idx_cust_id (customer_id=counts.customer_id)  (cost=2.47 rows=9.87)  -- 外層每個 customer_id 走 index 回 orders
```

改寫成 CTE 得到同一份計畫，差別只在 materialize 節點的名稱變成 `Materialize CTE counts`：

```sql
WITH counts AS (
    SELECT customer_id, COUNT(*) AS order_count
    FROM orders GROUP BY customer_id
)
SELECT o.* FROM orders o
JOIN counts ON o.customer_id = counts.customer_id
WHERE counts.order_count > 10;
```

這段查詢慢的時候，要看的是 materialize 本身的成本（derived table 掃了多少列）與外層 join 走不走 index，而不是 derived table 有沒有被 materialize。改用 temporary table 做的是同一個 materialize 動作，差別在暫存表由 application 建立與清除，可以在多段查詢之間重用：

```sql
CREATE TEMPORARY TABLE counts AS
SELECT customer_id, COUNT(*) AS order_count FROM orders GROUP BY customer_id;
SELECT o.* FROM orders o JOIN counts ON o.customer_id = counts.customer_id
WHERE counts.order_count > 10;
DROP TEMPORARY TABLE counts;
```

### 10 秒 → 100ms：Optimizer 選 index 不對

```sql
SELECT * FROM users WHERE age > 30 AND active = 1;
```

`users` 有 `idx_active` (selectivity 高) 跟 `idx_age` (selectivity 低)。Optimizer 選 `idx_age`、scan 60% rows、慢。

EXPLAIN：`key: idx_age` — 但 active=1 filter 後 row 量 < 5%。

修法選一：

1. **Index hint 強制**：

    ```sql
    SELECT * FROM users USE INDEX (idx_active)
    WHERE age > 30 AND active = 1;
    ```

2. **Composite index 取代**：

    ```sql
    ALTER TABLE users ADD INDEX idx_active_age (active, age);
    DROP INDEX idx_age ON users;
    ```

3. **Optimizer hint (8.0+)**：

    ```sql
    SELECT /*+ INDEX(users idx_active) */ * FROM users
    WHERE age > 30 AND active = 1;
    ```

Composite index 是最持久解（不依賴 hint）。Index hint 是 quick fix、但對 future schema change 脆弱。

## EXPLAIN 三層工具

### EXPLAIN：query plan preview

```sql
EXPLAIN SELECT ...;
```

輸出每個 step 的 *估計* cost / row count / key used。**用於 quick check plan 形狀**。

關鍵欄位：

- `type`：access type（ALL < index < range < ref < eq_ref < const）、ALL / index 是警訊
- `key`：實際選的 index、可能跟 `possible_keys` 不同
- `rows`：估計 scan row 數
- `Extra`：`Using filesort` / `Using temporary` / `Using index condition` 等行為標記

### EXPLAIN ANALYZE：實際執行統計

8.0+ 加的。差別：實際 run query、回實際 row count / time、跟 estimate 對比。

```sql
EXPLAIN ANALYZE SELECT ...;
```

輸出格式（tree format）：

```text
-> Nested loop inner join  (cost=2.4e6 rows=100000) (actual time=0.05..3.2 rows=10000 loops=1)
    -> Index range scan on orders using idx_created (cost=2.4e6 rows=10000) (actual time=0.04..3.0 rows=10000 loops=1)
    -> Single-row index lookup on customers using PRIMARY (cost=1 rows=1) (actual time=0.0001..0.0001 rows=1 loops=10000)
```

關鍵：對比 `cost / rows`（estimate） vs `actual time / rows`。如果 estimate=100K / actual=10M、optimizer 嚴重低估、可能選錯 plan。

### Optimizer Trace：看 optimizer 為何選這個 plan

```sql
SET optimizer_trace='enabled=on';
SELECT ...;
SELECT * FROM information_schema.optimizer_trace;
```

輸出 JSON、列每個 step optimizer 考慮過的 plan + cost estimate + 為什麼選最終 plan。**用於：optimizer 行為跟你預期不符時、debug 為什麼**。

複雜 query 的 optimizer trace 可能 100+ KB、要熟讀 JSON 結構。production debug tool、不是常規 tool。

## Optimizer hint vs Index hint

兩種 hint、語法不同、行為不同：

### Index hint（5.x 就有）

```sql
SELECT ... FROM table USE INDEX (idx_name) WHERE ...;
SELECT ... FROM table FORCE INDEX (idx_name) WHERE ...;
SELECT ... FROM table IGNORE INDEX (idx_name) WHERE ...;
```

- `USE INDEX`：建議 optimizer 用這 index、但 optimizer 仍可拒絕
- `FORCE INDEX`：強制用、optimizer 不能拒絕
- `IGNORE INDEX`：禁止用

**問題**：

- 對 table name 寫死、refactor / partition 時容易斷
- `FORCE` 太強、可能讓 optimizer 跑得比沒 hint 更慢（forced index 不是最佳 plan）

### Optimizer hint（8.0+）

```sql
SELECT /*+ INDEX(table_name idx_name) */ ... FROM table WHERE ...;
SELECT /*+ JOIN_ORDER(t1, t2, t3) */ ... FROM t1, t2, t3 WHERE ...;
SELECT /*+ HASH_JOIN(t1 t2) */ ... FROM t1 JOIN t2 ...;
SELECT /*+ NO_INDEX_MERGE(table) */ ... FROM table WHERE ...;
```

- 更細粒度（join order / join method / index 選擇分開）
- 注入 query comment 內、不污染 SQL syntax
- 比 index hint 安全：optimizer 看 hint 但仍走 plan space search

**推薦**：

- 8.0+ 用 optimizer hint
- 5.7 仍用 index hint、但謹慎 — 觀察 hint 加上去後 *實際 plan* 是否真的好

## 5 個 Production 踩雷

### Statistics 過時：optimizer 估錯 row count

`information_schema.STATISTICS` 紀錄每個 index 的 cardinality。如果 *過 1 個月沒 ANALYZE*、statistics 跟實際資料 distribution 嚴重偏差、optimizer 估計錯。

修法：

- 定期跑 `ANALYZE TABLE`（大表改 nightly cron）
- 8.0+ `innodb_stats_auto_recalc=ON` 預設、但變更超過 10% row 才觸發
- `innodb_stats_persistent=ON`（預設、把 statistics 存 disk）；要提高 sample 精度就把 `innodb_stats_persistent_sample_pages` 調到預設值 20 以上，代價是 `ANALYZE TABLE` 讀的 page 變多、跑得較久

### Forced index 用錯：hint 比沒 hint 還慢

`FORCE INDEX (idx)` 強制 optimizer 用、但 *idx 不是最佳* 時、query 變慢。常見：開發 staging 試出 `FORCE INDEX` 有效、production 資料 distribution 不同、forced index 反而慢。

修法：

- 用 `USE INDEX` 而不是 `FORCE INDEX`（optimizer 仍可換）
- 不依賴 hint、用 composite index / 重寫 query 達到目的
- 已用 hint 的 query 進 *staging review 機制*、確認 plan 仍合理

### Join 條件是 expression：optimizer 選 nested loop 是因為另一側有 index

```sql
SELECT ... FROM a JOIN b ON a.id = b.parent_id + 1;
```

條件的一側是 expression（`b.parent_id + 1`）不妨礙 hash join。optimizer 選 nested loop 的原因在 `a.id` 上有 index：對 b 的每一列算出 `b.parent_id + 1`，再到 a 的 PRIMARY 上做單列 lookup。同樣的條件換成一張 `id` 沒有 index 的表，計畫就變成 hash join。MySQL 8.4 實測（兩表各約兩萬列）：

```text
-- a.id 是 PRIMARY KEY：nested loop，每列一次 PRIMARY lookup
-> Nested loop inner join  (cost=8287 rows=18362)
    -> Table scan on b  (cost=1860 rows=18362)
    -> Filter: (a.id = (b.parent_id + 1))  (cost=0.25 rows=1)
        -> Single-row covering index lookup on a using PRIMARY (id=(b.parent_id + 1))  (cost=0.25 rows=1)

-- a2.id 沒有 index：同一個 expression 條件走 hash join
-> Inner hash join (a2.id = (b.parent_id + 1))  (cost=37.4e+6 rows=37.4e+6)
    -> Table scan on a2  (cost=0.0129 rows=20385)
    -> Hash
        -> Table scan on b  (cost=1860 rows=18362)
```

有 index 的那一份計畫通常就是這段 join 該有的計畫，加 `/*+ HASH_JOIN(a b) */` 也不會改變它（實測計畫相同）。要檢查的是 b 那一側的 table scan 能不能靠 b 上的 WHERE 條件與 index 縮小。

### 大 IN 清單讓 range scan 退化 ALL：cardinality 估計失準

```sql
SELECT ... FROM t WHERE col IN (1, 2, 3, ..., 1000);
```

`IN` 1000 value、optimizer 預估「range scan 太多 lookup、不如 ALL」、選 full table scan。對 *中型表*（1M row）通常 IN 仍快、但 optimizer 估錯。

修法：

- `IN` 拆成 *temp table JOIN*：

    ```sql
    CREATE TEMPORARY TABLE in_values (val INT);
    INSERT INTO in_values VALUES (1), (2), ..., (1000);
    SELECT t.* FROM t JOIN in_values iv ON t.col = iv.val;
    ```

- `IN` 清單的值數達到 `eq_range_index_dive_limit`（預設 200）時，optimizer 不再逐值對 index 做 dive，改用 index statistics 估算列數；估算失準時可以調高這個上限，或先跑 `ANALYZE TABLE` 更新 statistics
- 或大 `IN` 改 application 層拆批 query

### Derived table 被 merge 之後計畫變差

`optimizer_switch='derived_merge=on'`（預設 ON、可以 merge 的 derived table 自動 inline 進外層查詢）某些 query 反而慢（merge 後外層的 join 順序與條件組合變複雜，plan 變差）。這時要讓那個 derived table 改回 materialize、只算一次。

修法：

- 看 EXPLAIN 是否有 `DERIVED` row、確認 materialization 行為
- 可 `optimizer_switch='derived_merge=off'` 強制 materialize（影響整個 connection、謹慎用）
- 大 derived table 改 explicit *temporary table* 完全控制

## 跟 PostgreSQL EXPLAIN 對比

| 工具                    | MySQL                    | PostgreSQL                                      |
| ----------------------- | ------------------------ | ----------------------------------------------- |
| Query plan preview      | `EXPLAIN`                | `EXPLAIN`                                       |
| 實際執行統計            | `EXPLAIN ANALYZE` (8.0+) | `EXPLAIN ANALYZE`                               |
| Optimizer 內部 trace    | optimizer_trace (JSON)   | `auto_explain` extension                        |
| Format                  | TABLE / JSON / TREE      | TEXT / JSON / XML / YAML                        |
| Parallel query plan     | 受限（8.0 限 hash join） | Full（PG 10+ parallel scan / aggregate / join） |
| Index merge             | 有                       | 有 (`bitmap index scan`)                        |
| Genetic Query Optimizer | 無                       | PG 有（適合 > 12 table JOIN）                   |
| Cost estimate accuracy  | 中（histograms 8.0+）    | 高（成熟 statistics）                           |

PG optimizer 整體更成熟、複雜 OLAP-style query plan 更穩定。MySQL 8.0 補了不少（histograms、hash join、derived table merge）、簡單 OLTP query 已 OK、複雜 query 仍弱。

## 跟其他模組整合

### 跟 Modern SQL Features

CTE / window function / lateral / hash join 都改變 query plan space、optimizer 跟著要識別新 pattern。8.0 optimizer 對新 SQL feature plan 仍有改進空間。詳見 [Modern SQL Features](/backend/01-database/vendors/mysql/modern-sql-features/)。

### 跟 InnoDB Tuning

Query plan 受 *buffer pool hit rate* 影響 — optimizer 假設 random IO cost、實際資料在 buffer pool 內讀取快。Buffer pool 不夠時 plan estimate 失真。詳見 [InnoDB Tuning](/backend/01-database/vendors/mysql/innodb-tuning/)。

### 跟 ProxySQL

ProxySQL query rule 不影響 optimizer plan、但可以 *rewrite query*（rule engine 的 `replace_pattern`）— 用於把 application 寫不好的 query 改成 optimizer-friendly 形式、application 不必改。詳見 [ProxySQL 配置](/backend/01-database/vendors/mysql/proxysql-config/)。

### 跟 Lock Contention

Slow query 持有 lock 久、其他 query wait、整個 cluster lock contention 爆。Query optimization 不只是 latency 問題、也是 *lock 影響範圍* 問題。lock 怎麼被持有、deadlock 怎麼判讀，見 [MySQL Lock Contention](/backend/01-database/vendors/mysql/lock-contention/)。

### 跟 Partitioning

Partition pruning 是 optimizer 決定的，`EXPLAIN` 輸出的 `partitions` 欄列出查詢命中的 partition（`EXPLAIN PARTITIONS` 這個寫法在 8.0 已移除，8.4 執行會回語法錯誤）。partition + index 組合可能比 single big table + index 慢（cross-partition query overhead）。partition 怎麼切、pruning 什麼時候失效，見 [MySQL Partitioning](/backend/01-database/vendors/mysql/partitioning/)。

## 觀測 metric

Production 持續 monitor：

- `Performance_schema.events_statements_summary_by_digest`：每個 query digest 的累計 time / row examined / row sent
- `slow_query_log`：slow query 進 log 檔（`long_query_time=1`）
- `sys.statements_with_full_table_scans`：列 query 用 full scan 的歷史
- `sys.schema_unused_indexes`：列從未用過的 index、可以 drop 省 write cost

把這些丟進 Datadog / Percona Monitoring & Management 做 trend analysis。

## 相關連結

- [MySQL vendor overview](/backend/01-database/vendors/mysql/)
- [MySQL Modern SQL Features](/backend/01-database/vendors/mysql/modern-sql-features/)（hash join / window / CTE 的 plan 議題）
- [MySQL InnoDB Tuning](/backend/01-database/vendors/mysql/innodb-tuning/)（buffer pool 對 plan estimate）
- [MySQL ProxySQL 配置](/backend/01-database/vendors/mysql/proxysql-config/)（query rewrite 整合）
- [MySQL Online Schema Change Tools](/backend/01-database/vendors/mysql/online-schema-change-tools/)（add index 走 OSC）
- [PostgreSQL Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/)（PG sibling、EXPLAIN ANALYZE / pg_hint_plan / auto_explain 三層工具）
- [PostgreSQL Index Selection](/backend/01-database/vendors/postgresql/index-selection/)（B-tree / GIN / GiST / BRIN 決策樹 vs MySQL B-tree only）
- [PostgreSQL vendor page](/backend/01-database/vendors/postgresql/)（EXPLAIN ANALYZE 對比）
- 官方：[MySQL Optimization](https://dev.mysql.com/doc/refman/8.0/en/optimization.html) / [Optimizer Hints](https://dev.mysql.com/doc/refman/8.0/en/optimizer-hints.html)
