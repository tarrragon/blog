---
title: "PostgreSQL Index Selection：B-tree / GIN / GiST / BRIN / Hash 對應 workload 的決策樹"
date: 2026-05-19
description: "PG 有 6 種 index method（B-tree / Hash / GIN / GiST / SP-GiST / BRIN）跟 partial / expression / covering 三種變體、不是「都用 B-tree 就好」。每種 index 有自己的 query pattern、儲存代價、write amplification 跟 maintenance 成本。本文走 6 種 index 的適用 workload 對照、決策樹、partial / expression / covering / multi-column 變體、5 production 踩雷（過度 index / partial 條件不對 / B-tree 對 JSON 無效 / BRIN 對非 correlated 資料無效 / multi-column 順序錯）、跟 query-optimization 的 EXPLAIN 互補"
weight: 15
tags: ["backend", "database", "postgresql", "index", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 PG 在 OLTP 譜系的定位、本文聚焦 *index 選型* — 何時用哪種 index、跟 [query-optimization](/backend/01-database/vendors/postgresql/query-optimization/) 的「為什麼這個 plan 慢」互補。

---

## 6 種 Index Method 對應 Workload

PG 有 6 種 index access method、各有自己擅長的 query pattern：

| Index method | 適用 query pattern                                         | 典型 column type              | 儲存成本                 |                |
| ------------ | ---------------------------------------------------------- | ----------------------------- | ------------------------ | -------------- |
| B-tree       | `=` / `<` / `>` / `BETWEEN` / `IS NULL` / `LIKE 'prefix%'` | 任何 scalar、最常用           | 中                       |                |
| Hash         | 純 `=` 比對                                                | scalar、不常用                | 低                       |                |
| GIN          | `@>` / `?` / `?                                            | ` / FTS / array 包含          | JSONB / tsvector / array | 高（write 慢） |
| GiST         | 範圍 / 空間 / 自訂 operator                                | geometry / tsvector / range   | 中                       |                |
| SP-GiST      | Non-balanced 樹結構                                        | IP / phone prefix / quad-tree | 中                       |                |
| BRIN         | 大表的 range scan、physical order 跟 logical order 相關    | timestamp / id（append-only） | 極低                     |                |

選錯 index 的代價：

- **Write workload**：每 write 都更新所有相關 index、5 個 unused index = 5x write 放大
- **Storage**：JSONB 加 GIN 可能比表本身還大
- **Plan misjudge**：planner 看到 index 不一定用、`EXPLAIN` 才確認

## B-tree：預設選擇、95% workload 適用

B-tree 是 PG 預設 index、CREATE INDEX 不指定 method 就是 B-tree：

```sql
CREATE INDEX idx_orders_user_id ON orders (user_id);
CREATE INDEX idx_orders_created_at ON orders (created_at);
```

B-tree 擅長的 query：

```sql
-- 等值
SELECT * FROM orders WHERE user_id = 42;

-- 範圍
SELECT * FROM orders WHERE created_at BETWEEN '2025-01-01' AND '2025-01-31';

-- IS NULL
SELECT * FROM orders WHERE shipped_at IS NULL;

-- Prefix LIKE
SELECT * FROM products WHERE sku LIKE 'ABC%';
```

B-tree 不擅長：

- `LIKE '%suffix'`（前綴 wildcard）→ 改 trigram + GIN
- `column @> array`（包含）→ 改 GIN
- JSON 內部 path query → 改 GIN on JSONB

**Multi-column B-tree** 的順序很重要：

```sql
-- 假設常 query: WHERE user_id = ? AND status = ?
CREATE INDEX idx_orders_user_status ON orders (user_id, status);  -- 對
CREATE INDEX idx_orders_status_user ON orders (status, user_id);  -- 錯（status 選擇性低）
```

順序原則：

1. **等值 column 在前**（高選擇性）
2. **範圍 column 在後**（B-tree leftmost 規則）
3. **selectivity 高的在前**（filter 更多 row）

## GIN：JSONB / FTS / Array 的標配

GIN（Generalized Inverted Index）對「一個 value 內含多個 sub-element」的 column 高效：

```sql
-- JSONB
CREATE INDEX idx_products_metadata ON products USING GIN (metadata);

-- Array
CREATE INDEX idx_articles_tags ON articles USING GIN (tags);

-- Full-text search
CREATE INDEX idx_articles_content ON articles USING GIN (to_tsvector('english', content));

-- Trigram（fuzzy match）
CREATE EXTENSION pg_trgm;
CREATE INDEX idx_products_name_trgm ON products USING GIN (name gin_trgm_ops);
```

GIN 代價：

- **Write 慢 2-10x**：每個 sub-element 都要更新 inverted index
- **Storage 大**：可能比表還大
- **Vacuum 沉重**：bloat 累積快

**Operator class** 選擇影響大：

| Op class            | 適用                | 索引大小 | 支援 operator   |          |
| ------------------- | ------------------- | -------- | --------------- | -------- |
| `jsonb_ops`（預設） | 通用                | 大       | `@>` / `?` / `? | ` / `?&` |
| `jsonb_path_ops`    | 只 `@>` containment | 1/3-1/2  | 只 `@>`         |          |

只用 `@>` query 時、`jsonb_path_ops` 救大量 storage。

## GiST：範圍 / 空間 / 自訂

GiST（Generalized Search Tree）擅長範圍跟空間：

```sql
-- 範圍 type（PostgreSQL 內建 int4range / tsrange 等）
CREATE INDEX idx_bookings_period ON bookings USING GiST (period);

-- 空間（PostGIS）
CREATE INDEX idx_locations_geom ON locations USING GiST (geom);

-- Exclusion constraint（範圍不重疊）
ALTER TABLE bookings ADD CONSTRAINT no_overlap
EXCLUDE USING GiST (room_id WITH =, period WITH &&);
```

GiST vs GIN 對 FTS 的選擇：

| 維度        | GIN            | GiST                   |
| ----------- | -------------- | ---------------------- |
| Lookup 速度 | 快 3x          | 慢                     |
| Update 速度 | 慢 3x          | 快                     |
| 索引大小    | 大             | 小                     |
| 適合場景    | Read-heavy FTS | Write-heavy / 即時更新 |

多數 FTS workload 選 GIN — read 占多、index size 換 query latency 划算。

## BRIN：大表 + Physical Order Correlated

BRIN（Block Range Index）對 *physical 儲存順序跟 logical 順序強相關* 的 column 高效：

```sql
-- timestamp column（append-only insert、physical 順序 = 時間順序）
CREATE INDEX idx_events_created_at ON events USING BRIN (created_at);
```

BRIN 機制：每個 block range（預設 128 page）記 min/max、query 時跳過 range 外的 block。

適用場景：

- **append-only 表**：log、metrics、events
- **大表**（10GB+）：B-tree 太貴、BRIN 1/1000 大小
- **column physical order 跟 query 一致**：時間欄、自增 id

**BRIN 失效情境**：

- UPDATE 破壞 physical order（row 被 vacuum 移到別 block）→ BRIN 失效
- 隨機 insert（uuid / hash id）→ BRIN range 完全沒選擇性

**何時不該用 BRIN**：表 < 1GB（沒省 storage 收益）、column 沒 physical order correlation（CLUSTER 後可能改善）。

## Partial Index：條件式 index 救 storage

對 *只 query 部分 row* 的 column、partial index 救大量 storage：

```sql
-- 只 index unshipped order
CREATE INDEX idx_orders_unshipped ON orders (created_at)
WHERE shipped_at IS NULL;

-- 只 index active user
CREATE INDEX idx_users_active ON users (email)
WHERE status = 'active';

-- 只 index 高金額 transaction
CREATE INDEX idx_orders_high_value ON orders (user_id)
WHERE total > 1000;
```

Partial index 的 query 要 *完全匹配 WHERE 條件* 才用得到：

```sql
-- 用得到 partial index
SELECT * FROM orders WHERE shipped_at IS NULL AND created_at > '2025-01-01';

-- 用不到（planner 不 prove WHERE 包含 partial 條件）
SELECT * FROM orders WHERE created_at > '2025-01-01';
```

實務 size 救法：unshipped order 只 1% 總量、partial index 1/100 大小。

## Expression Index：對函式結果 index

```sql
-- 對 lowercased email index（case-insensitive search）
CREATE INDEX idx_users_email_lower ON users (lower(email));
SELECT * FROM users WHERE lower(email) = lower('USER@example.com');

-- 對 JSONB 內部欄位
CREATE INDEX idx_products_category ON products ((metadata->>'category'));
SELECT * FROM products WHERE metadata->>'category' = 'shoes';

-- 對日期截斷
CREATE INDEX idx_orders_day ON orders (date_trunc('day', created_at));
```

Expression 必須 IMMUTABLE — `now()` / `random()` 不能用、`timezone('UTC', ts)` 可以。

## Covering Index（INCLUDE）：避免回表

PG 11+ 支援 INCLUDE column：

```sql
-- 只 index user_id、但 query 常要 email
CREATE INDEX idx_users_user_id_covering ON users (user_id) INCLUDE (email);

-- Index-only scan：不用回表
SELECT email FROM users WHERE user_id = 42;
```

INCLUDE column 不參與 sorting / equality、只放 leaf node、救 IO。

## Index 選擇決策樹

```text
Query pattern 是什麼？

├─ 等值 / 範圍 / prefix LIKE / IS NULL
│  └─ B-tree（90% 場景）
│     ├─ 只 query 部分 row？→ Partial B-tree
│     ├─ 對函式結果？→ Expression B-tree
│     └─ 需要回表更多 column？→ Covering（INCLUDE）
│
├─ JSONB 內部 query / array 包含 / FTS
│  └─ GIN
│     ├─ 只用 @>？→ jsonb_path_ops 救 storage
│     └─ FTS write-heavy？→ 改 GiST
│
├─ 範圍 type（int4range / tsrange）/ 空間
│  └─ GiST
│
├─ 大表 + append-only + physical order correlated
│  └─ BRIN
│
├─ 純 equality + 簡單 column
│  └─ Hash（很少用、B-tree 通常更好）
│
└─ Non-balanced 樹（IP prefix / quad-tree）
   └─ SP-GiST（罕見）
```

## 5 個 Production 踩雷

### Case 1：過度 index（write 放大）

**情境**：team「為了 query 快」對 20 個 column 各建 index、寫入量大時 INSERT 慢 10x。

每個 INSERT 要更新 20 個 index、WAL volume 也跟著放大、replication lag 拉長。

修法：

- 用 `pg_stat_user_indexes` 找 *idx_scan = 0* 的 index、可能根本沒用
- 用 `pg_stat_statements` 找實際被執行的 query、反推真正需要的 index
- 同 column 多 index（user_id 單欄 + (user_id, status) 多欄）通常可拆掉單欄

### Case 2：Partial index 條件跟 query 不匹配

**情境**：建 `WHERE status = 'active'` partial index、application query 寫 `WHERE status IN ('active')`、planner 不 prove 等價、不用 index。

修法：

- Partial 條件用最 generic form（避免 IN / OR 跟 = 的差異）
- 寫完用 `EXPLAIN` 驗證 query 真的用到 partial index
- Application 統一 query 寫法、不要混 `=` 跟 `IN` 跟 `ANY`

### Case 3：B-tree 對 JSONB 內部欄位無效

**情境**：對 `metadata` JSONB column 建 B-tree、query `metadata->>'category' = 'shoes'` 不用 index。

B-tree 對 *整個 JSONB* 排序、但 path query 不是整個 JSONB 的比對。

修法：

- 對固定 path 建 expression index：`CREATE INDEX ... ON products ((metadata->>'category'))`
- 對動態 path 建 GIN index：`CREATE INDEX ... USING GIN (metadata)`
- 兩者並存可、`EXPLAIN` 看 planner 選哪個

### Case 4：BRIN 對非 correlated 資料無效

**情境**：對 `user_id` 建 BRIN index（user_id 是隨機 UUID）、query 完全跑 seq scan。

UUID 沒 physical order correlation、每個 block range 的 min/max 涵蓋整個 ID space、BRIN 完全沒 prune 效果。

修法：

- BRIN 只用 `timestamp` / 自增 `id` / 其他自然 correlate 的 column
- 用 `pg_stats` 看 `correlation` value、< 0.1 就不適合 BRIN
- 真要對 random column 加 index、回 B-tree

### Case 5：Multi-column index 順序錯

**情境**：常見 query `WHERE status = 'pending' AND user_id = 42`、建 index `(status, user_id)`、效能差。

`status` 只 5 個 distinct value、選擇性 1/5；`user_id` 1M distinct、選擇性 1/1M。Index leftmost 是 status、scan range 太大。

修法：

```sql
-- 拆兩個或調順序
CREATE INDEX idx_user_status ON orders (user_id, status);

-- 或加 partial 限定低選擇性 column
CREATE INDEX idx_orders_pending ON orders (user_id) WHERE status = 'pending';
```

## 跟 MySQL Index 差異

| 維度             | PostgreSQL                                          | MySQL                             |
| ---------------- | --------------------------------------------------- | --------------------------------- |
| Index method     | 6 種（B-tree / Hash / GIN / GiST / SP-GiST / BRIN） | 主要 B-tree、空間另算 R-tree      |
| 預設             | B-tree                                              | B-tree（InnoDB clustered）        |
| Clustered index  | 沒有原生（CLUSTER 一次性）                          | InnoDB primary key 永遠 clustered |
| Covering         | INCLUDE（PG 11+）                                   | 自然支援（secondary index 帶 PK） |
| JSON index       | GIN on JSONB（強）                                  | functional index on JSON（弱）    |
| Partial index    | 原生支援                                            | 8.0+ 支援（受限）                 |
| Expression index | 原生支援                                            | 5.7+ functional index             |
| BRIN-like        | 原生                                                | 沒有                              |
| Spatial          | GiST / PostGIS                                      | R-tree（基本）                    |

PG index 系統比 MySQL 表達力高、但代價是 *選對 index method 是 application 責任*、MySQL 預設 B-tree 多數場景夠用。

## 相關連結

- [query-optimization](/backend/01-database/vendors/postgresql/query-optimization/)：EXPLAIN 看 index 用沒用
- [jsonb-deep-dive](/backend/01-database/vendors/postgresql/jsonb-deep-dive/)：JSONB + GIN 細節
- [full-text-search](/backend/01-database/vendors/postgresql/full-text-search/)：FTS + GIN
- [autovacuum-tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)：index bloat
- [online-schema-change](/backend/01-database/vendors/postgresql/online-schema-change/)：CREATE INDEX CONCURRENTLY

## 下一步

- 看 [query-optimization](/backend/01-database/vendors/postgresql/query-optimization/) 驗證 index 有沒有被 plan 用到
- 回 [PostgreSQL overview](/backend/01-database/vendors/postgresql/) 看全圖
