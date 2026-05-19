---
title: "MySQL 8.0 Modern SQL：CTE / window function / JSON_TABLE 不是「終於跟上 PG」、是進入 SQL 工程深度的入場券"
date: 2026-05-19
description: "MySQL 8.0 在 SQL 特性上 *終於補齊* CTE、window function、lateral derived table、JSON_TABLE、hash join 等現代 SQL 特性。本文走 5 個關鍵特性、各自實際 production 場景、跟 PostgreSQL 對應特性的行為差異（特別是 JSON_TABLE vs PG JSONB / jsonb_path_query）、配置 / migration 注意事項、5 production 踩雷（CTE 不 materialize / window function 大量 sort spill / JSON_TABLE 跟 generated column 取捨 / hash join 預設沒開 / recursive CTE 深度上限）"
weight: 19
tags: ["backend", "database", "mysql", "sql-features", "json", "deep-article"]
---

> 本文是 [MySQL](/backend/01-database/vendors/mysql/) overview 的 implementation-layer deep article。Overview 已說明 MySQL 在 OLTP 譜系的定位、本文聚焦 *8.0 modern SQL 特性* — 5 個關鍵能力 + 跟 PostgreSQL 對應特性的對比。

---

「MySQL 是 SQL 簡單版」是個過時觀念。

這個觀念的來源很合理：MySQL 5.x 時代沒 CTE、window function 要嗑 hack、recursive query 寫不出來、JSON 處理是字串 substring 拼接、複雜分析 query 只能丟去 PostgreSQL 或 Snowflake。整整 10 年 SQL 進階特性 MySQL 全缺、PostgreSQL 全有。

MySQL 8.0（2018 推出）改變這件事。CTE / window function / lateral derived table / JSON_TABLE / hash join / atomic DDL / role-based authentication / common table expression 全部進來。**這不是「終於跟上 PG」、是 MySQL 第一次有資格進入 SQL 工程深度討論**。但有 caveats：每個特性的 *行為實現* 跟 PostgreSQL 對應特性都有 *微妙差異*、不能假設 PG 經驗直接套用。

對從 PostgreSQL 過來評估 MySQL 的讀者：本文是 *特性對等驗證* — 哪些 8.0 特性真的可以 production 用、哪些是 marketing 但實作有 gap。對既有 MySQL 5.7 user：本文是 *upgrade 5.7 → 8.0 的具體 ROI* — 從 SQL feature 角度看升級值不值得。

## 5 個關鍵特性 + PG 對比

### 特性 1：CTE（Common Table Expression）

MySQL 8.0 / PG 8.4+ 都支援。

```sql
-- MySQL 8.0 + PG 都 OK
WITH order_summary AS (
    SELECT user_id, SUM(amount) AS total
    FROM orders
    WHERE created_at > '2026-01-01'
    GROUP BY user_id
)
SELECT u.name, os.total
FROM users u JOIN order_summary os ON u.id = os.user_id
WHERE os.total > 1000;
```

**行為差異**：

- **MySQL 8.0**：CTE *不 materialize 為預設*、optimizer 把 CTE 視為 *inlined subquery*、CTE 引用兩次以上會 *重複計算*
- **PostgreSQL（< 12）**：CTE *fence by default*（materialize barrier）、optimizer 不 push predicate 進 CTE
- **PostgreSQL（12+）**：CTE 行為跟 MySQL 接近、有 `MATERIALIZED` / `NOT MATERIALIZED` keyword 明示

對 PG 12+ user：可以套 MySQL 經驗。對 PG 11 以下 user：CTE 行為跟 MySQL 不一樣、要重看 query plan。

**Recursive CTE**：

```sql
WITH RECURSIVE org_chart AS (
    SELECT id, name, manager_id, 0 AS depth
    FROM employees WHERE manager_id IS NULL
    UNION ALL
    SELECT e.id, e.name, e.manager_id, oc.depth + 1
    FROM employees e JOIN org_chart oc ON e.manager_id = oc.id
)
SELECT * FROM org_chart WHERE depth <= 10;
```

兩家都支援、但 MySQL 8.0 有 *深度上限*（`cte_max_recursion_depth=1000`、預設 1000、PG 預設 unlimited）。複雜 hierarchical query（深度 > 1000）MySQL 需要顯式提高 limit。

### 特性 2：Window Function

MySQL 8.0 / PG 8.4+ 都支援、語法同 SQL standard。

```sql
SELECT
    order_id,
    user_id,
    amount,
    SUM(amount) OVER (PARTITION BY user_id ORDER BY created_at) AS running_total,
    RANK() OVER (PARTITION BY user_id ORDER BY amount DESC) AS rank_in_user
FROM orders;
```

**行為差異**：

- **執行 plan**：MySQL 8.0 用 *window iterator*、單 partition 內 sort、外加 in-memory window buffer。PostgreSQL 有更成熟的 *WindowAgg node*、複雜 frame spec 處理更好
- **Frame spec 支援度**：兩家都支援 ROWS / RANGE / GROUPS、但 *GROUPS frame* MySQL 是 8.0.16+ 才補進、PG 11+ 才補
- **大資料量 spill behavior**：MySQL window function 超過 `sort_buffer_size`（預設 256K）會 spill 到 disk、Performance 雪崩。PG 用 `work_mem`（預設 4MB）、寬裕些但也會 spill

對長期用 PG window function 寫複雜 reporting query 的 user：MySQL 8.0 可以做、但 *效能 tune* 工作量大、不是 drop-in。

### 特性 3：JSON_TABLE（PG 主要賣點對比）

這是 user 點到的對比重點。

**MySQL 8.0 的 JSON_TABLE**：

```sql
SELECT t.id, j.name, j.price
FROM products t,
     JSON_TABLE(
         t.metadata,
         '$.variants[*]' COLUMNS (
             name VARCHAR(50) PATH '$.name',
             price DECIMAL(10,2) PATH '$.price'
         )
     ) AS j
WHERE t.category = 'shoes';
```

JSON_TABLE 把 JSON document 內的 array element 展開成 *relational rows*、然後可以 JOIN / WHERE / GROUP BY。SQL:2016 standard 規範。

**PostgreSQL 對應**：

PG 17+ 有 `JSON_TABLE`（SQL:2016 standard、跟 MySQL 同語法）、但歷史上 PG user 用兩條不同路線：

1. **JSONB operator**（PG 9.4+）：

    ```sql
    SELECT id, metadata->'variants' AS variants
    FROM products
    WHERE metadata @> '{"category": "shoes"}';
    ```

2. **jsonb_path_query**（PG 12+）：

    ```sql
    SELECT t.id, v.name, v.price
    FROM products t,
         jsonb_path_query(t.metadata, '$.variants[*]') AS v;
    ```

**核心差異**：

| 維度                    | MySQL JSON_TABLE                                                                    | PG JSONB operator                         | PG jsonb_path_query         |
| ----------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------- | --------------------------- |
| Index                   | 必須對 JSON column 建 *generated column + 一般 index*、不能直接 GIN index JSON path | **GIN index 直接 over JSONB**（業界唯一） | 可以走 GIN expression index |
| Storage                 | JSON column = LONGTEXT 包裝                                                         | JSONB = binary、壓縮、index 友善          | 同左                        |
| Query 效率（複雜 path） | 中等（需要 generated column 加速）                                                  | 高（GIN index 直接）                      | 高                          |
| SQL standard 對齊       | 高（JSON_TABLE 是 standard）                                                        | 低（JSONB operator 是 PG 專有）           | 中（jsonpath 是 standard）  |
| 大 JSON（> 1 MB）       | LONGTEXT 仍可、但 query 慢                                                          | JSONB 壓縮 + 部分 read                    | 同左                        |

**選型結論**：

- **MySQL 是 JSON-storage 角色**（document 順手存進關聯 DB）：JSON_TABLE 夠用、配 generated column + index、production-ready
- **MySQL 是 document-heavy workload**（大量 JSON-driven query / 複雜 path / 高 selectivity）：PG JSONB GIN index 仍是 *clearly winner*、或直接用 MongoDB
- **MySQL 8.0 JSON 不是 PG JSONB 替代**：JSON_TABLE 是 *SQL standard 對齊*、好 portable、但 *index 跟 storage 仍弱*

對「JSON 是 PG 主要賣點」的判斷：JSONB binary storage + GIN index 是 PG 在 JSON workload 的 *結構性優勢*、MySQL 8.0 補了 SQL_TABLE 但 *index 那層沒補*。8.0 後 JSON 議題 *不是 deal-breaker for MySQL*（不像 5.7 時代直接 disqualify）、但仍不是 MySQL 主場。

### 特性 4：Lateral Derived Table

MySQL 8.0.14+ / PG 9.3+ 都支援。

```sql
-- 對每個 user、找他最近 5 個 order
SELECT u.id, recent.*
FROM users u
LEFT JOIN LATERAL (
    SELECT order_id, amount
    FROM orders o
    WHERE o.user_id = u.id
    ORDER BY created_at DESC LIMIT 5
) recent ON true;
```

Lateral 讓 subquery 可以 *引用外部 reference column*（`u.id`）、不可能用 plain subquery 寫出來。

**行為差異**：

- MySQL 8.0：lateral 後加、optimizer plan 仍在演進、複雜 lateral query 可能 plan 次優
- PostgreSQL：lateral 早就成熟、plan 跟 join 直接 fuse、效率高

對 PG-experienced 使用 lateral 寫 reporting query 的 user：MySQL 8.0 可以、但有時候要 hint optimizer 達到最佳 plan。

### 特性 5：Hash Join

MySQL 8.0.18+ / PG 早已有。

**MySQL 8.0 之前**：只有 *nested loop join*、大表 JOIN 完全失控（n × m row scan）。8.0.18 加 hash join、optimizer 在預估 row count 大時自動切。

**注意**：MySQL 8.0 hash join 預設 *不對所有 join 開*、只在 `optimizer_switch='hash_join=on'` 且 join condition 是 *equality on indexed column* 時觸發。常見錯估：複雜 join 條件不觸發 hash join、optimizer fallback nested loop、query 永遠跑不完。

**PG 對應**：PG 一直有 hash join、optimizer 預設 cover 廣、且有 *parallel hash join*（PG 11+）大表 JOIN 並行加速。

MySQL hash join 是 *補洞*、不是 *並肩特性*。複雜 OLAP query MySQL 仍弱於 PG。

## 其他 8.0 特性（一句話帶過）

- **Atomic DDL**：CREATE TABLE / DROP / ALTER 變 transactional、crash recovery 不會留 orphan table（PG 早就 atomic）
- **Role-based authentication**：role 取代 group-level grant、user 可繼承 role（PG 早就 role 系統）
- **CHECK constraint enforcement**：5.7 可寫但不執行、8.0 真的 enforce（PG 一直執行）
- **invisible index**：建 index 但 optimizer 暫不用、適合 staging query plan 測試（PG 沒原生對應）
- **Resource Group**：query 跑時可分配 CPU thread 給特定 user group（PG 沒原生對應）
- **Generated column**：MySQL 5.7 已有、8.0 強化、可作為 JSON path 加速的 workaround

## 配置 step-by-step（從 5.7 → 8.0 SQL feature 升級）

如果已經是 8.0、所有特性都可以用、不必額外配置。如果是 5.7 → 8.0、需要：

1. **`character_set_server=utf8mb4`**：8.0 預設 utf8mb4（5.7 預設 latin1）、character set 不一致導致 query 行為微差
2. **`default_authentication_plugin=mysql_native_password`**：8.0 預設 caching_sha2_password、舊 client 連不上、cluster upgrade 期間用 native_password 保兼容
3. **`optimizer_switch='hash_join=on'`**：確認 hash join 啟用、預設應該已 ON
4. **`cte_max_recursion_depth=10000`**：複雜 recursive CTE 需要時提高
5. **重新 review 所有 ORM-generated SQL**：8.0 keywords 變多（WINDOW、RANK、LATERAL 等變成 reserved word）、5.7 識別碼可能變 syntax error

## 5 個 Production 踩雷

### 1. CTE 引用兩次 = 跑兩次

```sql
WITH expensive AS (SELECT ... heavy aggregation ...)
SELECT * FROM expensive WHERE ...
UNION ALL
SELECT * FROM expensive WHERE other_condition;
```

預期 CTE 跑一次、實際 MySQL 跑兩次。Query 時間 doubled。

修法：

- 把 CTE 結果先 INSERT 進 *temporary table*、SELECT 兩次走 temp table（手動 materialize）
- 或 PG 用 `MATERIALIZED` keyword（MySQL 沒對應 hint、要手動 temp table）

### 2. Window function 大 partition spill 到 disk

```sql
SELECT order_id,
       SUM(amount) OVER (PARTITION BY user_id ORDER BY created_at)
FROM orders;  -- 1 億 row
```

`sort_buffer_size=256K` 預設、單 partition > 256K row 開始 spill disk、執行從秒級變分鐘級。

修法：

- 提高 `sort_buffer_size`（per-connection、不要設太大、connection × buffer 會吃 RAM）
- 加 INDEX 包含 `user_id, created_at`、optimizer 可直接用 sorted index、不必額外 sort

### 3. JSON_TABLE 跟 generated column 取捨錯誤

直接 JSON_TABLE on every query：

```sql
SELECT * FROM products,
JSON_TABLE(metadata, '$.variants[*]' COLUMNS (...));
```

每次 query 跑 JSON parse、無 index 加速、大表 query 慢。

修法：

- 對 *常 query 的 JSON path* 建 generated column：

    ```sql
    ALTER TABLE products
    ADD COLUMN category VARCHAR(50)
    GENERATED ALWAYS AS (JSON_UNQUOTE(metadata->'$.category')) STORED,
    ADD INDEX idx_category (category);
    ```

- JSON_TABLE 用於 *ad-hoc query*、不要當熱 path
- 跟 PG JSONB GIN 對比：PG 不必預先建 generated column、GIN index 直接 over JSONB

### 4. Hash join 沒觸發 — Optimizer 預估錯 row count

JOIN 大表預期 hash join、實際 MySQL 跑 nested loop、query 跑不完。常見原因：

- Table statistics 過時（沒跑 `ANALYZE TABLE`）
- Join condition 不是 pure equality（`a.id = b.id + 1` 等）
- 一邊有 LIMIT、optimizer 估 small set、選 nested loop

修法：

- 跑 `ANALYZE TABLE` 更新 statistics
- 用 `EXPLAIN ANALYZE` 看實際 row count vs 估計
- 用 `optimizer_hint`（如 `/*+ HASH_JOIN(t1 t2) */`）強制

### 5. Recursive CTE 深度上限 — Production query 突然 fail

`cte_max_recursion_depth=1000` 預設、organization hierarchy / tree query 超過 1000 層直接 fail（`ER_CTE_MAX_RECURSION_DEPTH_EXCEEDED`）。

修法：

- 評估真實 hierarchy 深度、設 `cte_max_recursion_depth=10000` 或更高
- 或 query 加 `WHERE depth < N` 提前停（不依賴 implicit limit）
- 對極大 hierarchy（社群 follow graph 等）改用 *graph DB*（Neo4j）— MySQL recursive CTE 不是 graph workload 主場

## MySQL 8.0 vs PG SQL 特性 cross-reference

| 特性                 | MySQL 8.0           | PostgreSQL           | 差異                                                         |
| -------------------- | ------------------- | -------------------- | ------------------------------------------------------------ |
| CTE                  | 8.0+                | 8.4+                 | PG 2009 即支援、MySQL 2018 才支援、約晚 9 年                 |
| Recursive CTE        | 8.0+（depth 限）    | 8.4+（unlimited）    | PG 無深度上限                                                |
| Window function      | 8.0+                | 8.4+                 | Frame spec 兩家略不同（GROUPS frame 推出時點）               |
| Lateral              | 8.0.14+             | 9.3+                 | PG plan 較成熟                                               |
| JSON_TABLE           | 8.0+                | 17+                  | MySQL 早 6 年（SQL:2016 standard）                           |
| JSONB index          | 無原生              | GIN index over JSONB | **PG 結構優勢**                                              |
| Hash join            | 8.0.18+             | 早                   | PG parallel hash join                                        |
| Atomic DDL           | 8.0+                | 早                   | PG 一直 atomic                                               |
| Common keyword       | 補齊                | 完整                 | -                                                            |
| Role-based auth      | 8.0+                | 早                   | -                                                            |
| Materialized view    | 無原生              | 9.3+                 | **PG 結構優勢**（MySQL 用 trigger / scheduled refresh 模擬） |
| Partial index        | 無                  | 早                   | **PG 結構優勢**                                              |
| Expression index     | 8.0.13+             | 早                   | MySQL 後加                                                   |
| Full-text search     | 內建（InnoDB 5.6+） | 內建（tsvector）     | PG full-text 更成熟                                          |
| Foreign data wrapper | 無原生              | 早（FDW）            | **PG 結構優勢**                                              |

8.0 補了 *語法層* 大部分缺漏、*storage / index / extensibility 層* 仍是 PG 結構優勢。對「先選 SQL 工程深度」的 org、PG 仍領先；對「先選 ecosystem / replication / sharding」的 org、MySQL 已不是 disqualifier。

## 跟其他模組整合

### 跟 InnoDB Tuning

JSON column 在 InnoDB 是 LONGTEXT 包裝、大 JSON 進 off-page storage（`innodb_default_row_format=DYNAMIC` 才行、Antelope format 不支援）。Buffer pool 對 LONGTEXT 較不友善、大 JSON workload 可能要更大 buffer pool。詳見 [InnoDB Tuning](/backend/01-database/vendors/mysql/innodb-tuning/)。

### 跟 Query Optimization

8.0 新 hash join + lateral derived 讓 *EXPLAIN ANALYZE* 結果更複雜。優化複雜 query 需要熟 *新 plan node 類型*。詳見 *Query Optimization deep dive* 篇（待寫）。

### 跟 Online Schema Change

JSON column 跟 generated column 的 schema change 走 gh-ost / pt-osc 沒問題、但 JSON 大表 ALTER 速度比一般 column 慢（每 row 重 serialize）。詳見 [Online Schema Change Tools](/backend/01-database/vendors/mysql/online-schema-change-tools/)。

### 跟 Replication

Window function / CTE / JSON_TABLE 的 query *結果* replicate（row-level binlog 紀錄結果）、不 replicate *query 本身*。所以 replica apply 不會重新跑 window function、效率 OK。詳見 [Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)。

## 何時 SQL 特性是 MySQL 選型 driver

- **想要 SQL standard 對齊跨 vendor portable**：MySQL 8.0 JSON_TABLE / window 都對齊 standard、PG 部分能力（JSONB operator）是 PG-only、portability MySQL 略好
- **JSON workload < 20% query**：MySQL 8.0 + generated column 夠用、不必為 JSON 換 PG
- **JSON workload > 50% query + 複雜 path / aggregation**：PG JSONB GIN 仍 winner、考慮 PG 或 MongoDB
- **需要 materialized view / FDW / partial index**：PG 仍領先、不要因為 SQL feature parity 假設 MySQL 全 cover
- **既有 MySQL 投資 + SQL 工程深度上升**：升 8.0 + 訓練團隊用新特性、不是換 vendor

## 相關連結

- [MySQL vendor overview](/backend/01-database/vendors/mysql/)
- [InnoDB Tuning](/backend/01-database/vendors/mysql/innodb-tuning/)（JSON column 對 buffer pool 影響）
- [Online Schema Change Tools](/backend/01-database/vendors/mysql/online-schema-change-tools/)（JSON column 大表 ALTER）
- [Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)（ROW-format binlog 對 window function）
- [PostgreSQL SQL Features Baseline](/backend/01-database/vendors/postgresql/sql-features-baseline/)（PG 反向視角、哪些特性 PG 早 5-15 年、MySQL 8.0 補齊後 PG 仍領先）
- [PostgreSQL JSONB Deep Dive](/backend/01-database/vendors/postgresql/jsonb-deep-dive/)（PG sibling、binary storage + GIN index 跟 MySQL JSON_TABLE 對比）
- [PostgreSQL vendor page](/backend/01-database/vendors/postgresql/)（JSON / SQL feature 對比 source）
- [MongoDB vendor page](/backend/01-database/vendors/mongodb/)（document-heavy workload 替代）
- 官方：[MySQL 8.0 What's New](https://dev.mysql.com/doc/refman/8.0/en/mysql-nutshell.html)
