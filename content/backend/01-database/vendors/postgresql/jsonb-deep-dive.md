---
title: "PostgreSQL JSONB Deep Dive：Binary Storage + GIN Index 為什麼是結構性優勢"
date: 2026-05-19
description: "PG JSONB（9.4+）是 *binary 儲存的 JSON*、可直接 GIN index、是 PG 在 JSON workload 的結構性優勢、跟 MongoDB / MySQL 8.0 JSON_TABLE 比仍領先。本文走 JSON vs JSONB 差異、GIN index 機制（jsonb_ops vs jsonb_path_ops）、operator + path query、partial JSONB indexing、5 production 踩雷（大 JSONB 跟 TOAST / nested update / index 選錯 op class / jsonb_path_query 跟 jsonb_path_exists 行為差 / partial index 條件搞錯）、何時用 JSONB vs 拆 column"
weight: 25
tags: ["backend", "database", "postgresql", "jsonb", "json", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 PG 在 OLTP 譜系的定位、本文聚焦 *JSONB deep dive* — binary storage + GIN index 的結構性優勢。

---

## JSON vs JSONB：選 JSONB

PG 9.2 加 `JSON` type、9.4 加 `JSONB`。99% 場景用 JSONB：

| 維度          | JSON                        | JSONB                           |
| ------------- | --------------------------- | ------------------------------- |
| 儲存          | 純文字（原樣保存）          | Binary decomposed format        |
| Parse cost    | 每次 query parse            | Insert 時 parse 一次            |
| Index 支援    | Limited（functional index） | GIN / functional / partial 都行 |
| Operator 支援 | 有限（→ / →>）              | 完整（@> / ? / @? / ? 等）      |
| Duplicate key | 保留（原樣）                | 只保留最後一個（normalize）     |
| Key order     | 保留                        | 不保留                          |
| Whitespace    | 保留                        | 不保留                          |

JSONB 唯一缺點是 *binary 儲存（不保留 key order / whitespace / duplicate）*。99% application 不在意這些。

從 *application semantics* 視角、JSONB 是 PG JSON 的 *the right type*、JSON 是 *legacy / niche*。

## JSONB GIN Index：核心結構性優勢

PG GIN（Generalized Inverted Index）可以對 JSONB 內所有 key/value pair 建 inverted index：

```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    metadata JSONB
);

-- GIN index
CREATE INDEX idx_products_metadata ON products USING GIN (metadata);
```

加完後、JSONB query 用 GIN index 加速：

```sql
-- @> (contains) 用 GIN
SELECT * FROM products WHERE metadata @> '{"category": "shoes"}';

-- ? (has key) 用 GIN
SELECT * FROM products WHERE metadata ? 'discount';

-- ?| (has any of these keys) 用 GIN
SELECT * FROM products WHERE metadata ?| array['discount', 'promotion'];
```

跟 MongoDB index 對比、PG 不必 *預先 define* JSON path index、`USING GIN (metadata)` 對 *整個 JSONB document 任意 path* 都有效。

### `jsonb_ops` vs `jsonb_path_ops`

PG GIN 對 JSONB 有兩種 *operator class*：

| 維度          | `jsonb_ops`（預設） | `jsonb_path_ops`         |
| ------------- | ------------------- | ------------------------ |
| 索引內容      | Key + value 都索引  | 只索引 path → value pair |
| Index size    | 大                  | 小（約一半）             |
| 支援 operator | `@> / ? / ?\| / ?&` | 只 `@>` (containment)    |
| 適用          | 多種 query pattern  | 只用 `@>` 的場景         |

```sql
-- jsonb_ops（預設）
CREATE INDEX idx_meta_default ON products USING GIN (metadata);

-- jsonb_path_ops（小、快、但只支援 @>）
CREATE INDEX idx_meta_path ON products USING GIN (metadata jsonb_path_ops);
```

**選擇**：

- 只跑 `@>` containment query → `jsonb_path_ops`（index 小、快）
- 跑 `?` / `?|` / `?&` key existence query → `jsonb_ops`（預設）

## Operator + Path Query

JSONB 提供豐富 operator + jsonpath：

### Operator

```sql
-- Extract value（returns jsonb）
SELECT metadata -> 'name' FROM products;

-- Extract text（returns text）
SELECT metadata ->> 'name' FROM products;

-- Path extract
SELECT metadata #> '{variants, 0, price}' FROM products;
SELECT metadata #>> '{variants, 0, price}' FROM products;  -- 返回 text

-- Containment（用 GIN index）
SELECT * FROM products WHERE metadata @> '{"category": "shoes", "active": true}';

-- Reverse containment
SELECT * FROM products WHERE '{"sub": "value"}' <@ metadata;

-- Key existence
SELECT * FROM products WHERE metadata ? 'discount';
SELECT * FROM products WHERE metadata ?| array['a', 'b'];  -- 任一 key
SELECT * FROM products WHERE metadata ?& array['a', 'b'];  -- 全部 key
```

### jsonpath（PG 12+）

SQL/JSON jsonpath 是 SQL standard、PG 12+ 支援：

```sql
-- jsonb_path_query：展開 path 結果
SELECT jsonb_path_query(metadata, '$.variants[*].price')
FROM products WHERE id = 1;

-- jsonb_path_exists：返 boolean
SELECT * FROM products
WHERE jsonb_path_exists(metadata, '$.variants[*] ? (@.price > 100)');

-- jsonb_path_query_array：返 array of result
SELECT jsonb_path_query_array(metadata, '$.tags[*]')
FROM products;
```

jsonpath 比 PG-specific operator 標準化、跨 vendor portable。

## Partial JSONB Index

對 *只 query subset row* 的場景、建 partial index：

```sql
-- 只對 active product 建 metadata index
CREATE INDEX idx_active_products_metadata
ON products USING GIN (metadata)
WHERE status = 'active';

-- Query active products + JSONB filter
SELECT * FROM products
WHERE status = 'active' AND metadata @> '{"category": "shoes"}';
-- → planner 用 partial GIN index
```

Partial index 比 full GIN 小很多、write cost 低、index hit rate 高。

## 5 個 Production 踩雷

### 1. 大 JSONB + TOAST — 性能崩潰

JSONB > 2 KB 自動進 TOAST（PG 內外部 storage）、每次 query read 該 row 都要 *de-TOAST*（拉外部 storage 再合併）。大 JSONB（> 50 KB）每次 query 慢 10-100x。

修法：

- 把 *大 attribute 拆獨立 column*（如 `description TEXT` 不放 metadata）
- 用 *JSON path index* 對 hot path 加速、不必每次讀整個 JSONB
- 用 `pg_column_size(metadata)` 監控 JSONB size 分布、找 outlier
- 對 truly 大 document（> 1 MB）考慮 separate table 或 object storage

### 2. Nested update — 整個 JSONB 重寫

PG 沒 *atomic partial update*。修改 nested key 必須讀整個 JSONB → 修改 → 寫回：

```sql
UPDATE products
SET metadata = jsonb_set(metadata, '{discount}', '0.2'::jsonb)
WHERE id = 100;
-- 等同於：讀 metadata、改 discount、寫回整個 metadata
```

對 *大 JSONB + 高頻 update* 場景、寫吞吐受限。跟 MongoDB `$set` operator 對應 *partial document update* 不同。

修法：

- 對 *high-update nested key* 拆獨立 column
- Application 層 batch update（攢一批一次 update）
- 接受 PG JSONB *是 immutable-replace* 心智模型、不是 *mutable in-place*

### 3. Index 選錯 op class — `?` query 走 full scan

對 `jsonb_path_ops` index、`?` key existence query 走 *full scan*（不用 index）。Application 看 query 慢、查 EXPLAIN 才發現 index 沒用。

修法：

- 設計階段確認 *application query pattern*：只用 `@>` 還是會用 `?`
- 多 query pattern → `jsonb_ops`（預設）
- 純 containment → `jsonb_path_ops`（省 index size）
- 不確定先用預設、production 觀察後再優化

### 4. `jsonb_path_query` 跟 `jsonb_path_exists` 行為差

- `jsonb_path_query(metadata, '$.variants[*].price')` — 展開、每個 match return 一 row
- `jsonb_path_exists(metadata, '$.variants[*]')` — return boolean（true if any match）

Application 想要「過濾 row」用前者寫成：

```sql
-- 錯：返多 row 給每個 product、結果 row count 暴增
SELECT id, jsonb_path_query(metadata, '$.variants[*].price') FROM products;
```

應該：

```sql
-- 對：只過濾 product
SELECT * FROM products WHERE jsonb_path_exists(metadata, '$.variants[*] ? (@.price > 100)');
```

修法：

- 區分 *exists 過濾 row* vs *query 展開 row*
- 過濾用 `jsonb_path_exists` 或 `@>` operator
- 展開用 `jsonb_path_query` + 配合 `LATERAL` 或 subquery

### 5. Partial index 條件不對齊 query

```sql
CREATE INDEX idx_active_metadata ON products USING GIN (metadata) WHERE status = 'active';

-- Application query 但 status 沒 explicit
SELECT * FROM products WHERE metadata @> '{"category": "shoes"}';
-- → 不用 partial index（planner 不知道 status='active' 條件）
```

修法：

- Application query *必須包含 partial index 的 WHERE 條件*：

   ```sql
   SELECT * FROM products WHERE status = 'active' AND metadata @> '...';
   ```

- 確認 planner 用 partial index：`EXPLAIN` 看 `Index Scan using idx_active_metadata`
- 不對齊 query pattern 的 partial index = waste

## 何時用 JSONB vs 拆 column

| 場景                                                     | 選擇                         |
| -------------------------------------------------------- | ---------------------------- |
| 不規則 schema（user-generated metadata / customization） | JSONB                        |
| 半結構化 + 5-10 個常 query key                           | JSONB + GIN partial index    |
| 規則 schema、column 數量穩定                             | 拆 column（更快 / index 易） |
| Nested 結構 + 經常需要展開 query                         | JSONB + jsonb_path_query     |
| 大 document（> 1 KB）+ 高頻 update                       | 拆 column 或 separate table  |
| 完全 schemaless workload                                 | 考慮 MongoDB 而非 PG         |

JSONB 是 *PG 適合 semi-structured data* 的工具、不是 *MongoDB 替代品*。對 *主要結構化 + 少量 JSON* 場景 JSONB 完美；對 *主要 JSON / 複雜 nested aggregation* 場景 MongoDB 仍是專業選擇。

## 跟其他模組整合

### 跟 Query Optimization

JSONB query 的 planner 行為：

- `@>` containment 對 jsonb_ops / jsonb_path_ops 都用 GIN
- `?` 只對 jsonb_ops 用 GIN
- jsonb_path_exists 用 *functional index*（不是 GIN）
- 看 EXPLAIN 確認用對 index、詳見 [Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/)

### 跟 SQL Features Baseline

JSONB 是 PG 結構性領先特性之一、詳見 [SQL Features Baseline](/backend/01-database/vendors/postgresql/sql-features-baseline/)。

### 跟 MVCC + Lock Model

JSONB UPDATE 整個 column 重寫、每次 update 創新 tuple、跟 row update 相同 MVCC behavior。詳見 [MVCC + Lock Model](/backend/01-database/vendors/postgresql/mvcc-lock-model/)。

### 跟 MySQL JSON_TABLE

MySQL 8.0 JSON_TABLE 跟 PG jsonpath 類似（都 SQL standard）、但 *index 機制* 完全不同：

- PG：JSONB + GIN index over 整個 column
- MySQL：JSON column + generated column + index over generated

PG JSONB GIN 是 *結構性領先*、MySQL 短期內難對應。詳見 [MySQL Modern SQL Features](/backend/01-database/vendors/mysql/modern-sql-features/)。

## 觀測 metric

- `pg_column_size(metadata)` — 每 row JSONB size 分布
- `pg_relation_size('idx_name')` — JSONB GIN index 大小
- `pg_stat_user_indexes.idx_scan` — JSONB index 使用次數
- TOAST table size：`SELECT pg_relation_size(reltoastrelid) FROM pg_class WHERE relname='products'`

## 相關連結

- [PostgreSQL vendor overview](/backend/01-database/vendors/postgresql/)
- [PG SQL Features Baseline](/backend/01-database/vendors/postgresql/sql-features-baseline/)（JSONB 是 PG 結構領先之一）
- [PG Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/)（JSONB index 用對）
- [PG MVCC + Lock Model](/backend/01-database/vendors/postgresql/mvcc-lock-model/)（JSONB update 跟 MVCC）
- [MySQL Modern SQL Features](/backend/01-database/vendors/mysql/modern-sql-features/)（JSON_TABLE vs JSONB 對比）
- [MongoDB vendor](/backend/01-database/vendors/mongodb/)（純 document workload 替代）
- 官方：[PG JSON Functions](https://www.postgresql.org/docs/current/functions-json.html) / [JSONB Indexing](https://www.postgresql.org/docs/current/datatype-json.html#JSON-INDEXING)
