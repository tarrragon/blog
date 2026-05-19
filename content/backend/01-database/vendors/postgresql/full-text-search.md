---
title: "PostgreSQL Full-Text Search：tsvector / tsquery / GIN index 跟 pg_trgm fuzzy 三層搜尋"
date: 2026-05-19
description: "PG 內建 full-text search 用 *tsvector / tsquery / GIN index* 三件組、適合中小規模搜尋（< 100M 文件）；pg_trgm 提供 fuzzy match。本文走 FTS 機制（tsvector 是 lexeme + position 的 vector）、3 種 query（match / ranking / weighted）、multi-language support、跟 pg_trgm fuzzy match 互補、5 production 踩雷（dictionary 選錯 / GIN 跟 GiST 取捨 / ranking 評分權重 / multi-language column 處理 / 何時不該用 PG FTS 改 Elasticsearch）"
weight: 27
tags: ["backend", "database", "postgresql", "full-text-search", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 PG 在 OLTP 譜系的定位、本文聚焦 *full-text search* — 內建 tsvector / tsquery + pg_trgm fuzzy match。

---

## PG FTS 機制：tsvector + tsquery + GIN index

PG 內建 full-text search 三件組：

- `tsvector`：document 轉成 *lexeme*（字根 + position）vector、normalized 後存
- `tsquery`：搜尋字串 parse 成 query 形式
- GIN index：對 tsvector 加 inverted index

```sql
-- Document
SELECT to_tsvector('english', 'The quick brown fox jumps over the lazy dog');
-- 結果：'brown':3 'dog':9 'fox':4 'jump':5 'lazi':8 'quick':2
-- The/over 是 stop word 被過濾、jumps/lazy 轉字根、保留 position

-- Query
SELECT to_tsquery('english', 'fox & dog');
-- 結果：'fox' & 'dog'

-- Match
SELECT to_tsvector('english', 'The quick brown fox') @@ to_tsquery('english', 'fox & quick');
-- → true
```

**Index**：

```sql
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    title TEXT,
    body TEXT
);

-- GIN index over tsvector (動態 cast)
CREATE INDEX idx_articles_fts ON articles
USING GIN (to_tsvector('english', title || ' ' || body));

-- Query 用 index
SELECT * FROM articles
WHERE to_tsvector('english', title || ' ' || body) @@ to_tsquery('english', 'postgres & index');
```

跟 [JSONB GIN index](/backend/01-database/vendors/postgresql/jsonb-deep-dive/) 同 GIN access method、不同 indexed expression。

## Generated column 加速

每次 query 都跑 `to_tsvector(...)` 浪費 CPU。用 *generated column* 預存：

```sql
ALTER TABLE articles ADD COLUMN fts tsvector
GENERATED ALWAYS AS (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, ''))) STORED;

CREATE INDEX idx_articles_fts ON articles USING GIN (fts);

-- Query 簡化
SELECT * FROM articles WHERE fts @@ to_tsquery('english', 'postgres');
```

Stored generated column 是 PG 12+、自動跟 row update 同步。

## Ranking + 加權

PG FTS 提供 `ts_rank` / `ts_rank_cd` 給結果排序：

```sql
-- 簡單 ranking
SELECT id, title, ts_rank(fts, query) AS rank
FROM articles, to_tsquery('english', 'postgres & index') AS query
WHERE fts @@ query
ORDER BY rank DESC LIMIT 10;
```

加權（A > B > C > D）：

```sql
-- Title 比 body 重要
UPDATE articles SET fts =
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(body, '')), 'B');

-- Query 用加權 ranking
SELECT id, title,
       ts_rank(fts, query, 32 /* normalize by document length */) AS rank
FROM articles, to_tsquery('english', 'postgres') AS query
WHERE fts @@ query
ORDER BY rank DESC;
```

`ts_rank` 第三 parameter 是 normalization flag：

- 0：no normalization
- 1：divide by document length
- 32：divide by uniqueness（避免短 doc 一律 rank 高）

## Multi-language Support

PG 內建多種語言 dictionary：`english` / `french` / `german` / `spanish` / `simple`（不做 stemming）等。

對 *中文 / 日文 / 韓文*、PG 預設無支援、需要 extension：

- `zhparser`（中文、用 SCWS 分詞）
- `pgroonga`（多語言、支援中日韓）
- `RUM index`（PG 自己 + 可選 dictionary）

```sql
-- 中文用 zhparser
CREATE EXTENSION zhparser;
CREATE TEXT SEARCH CONFIGURATION chinese (PARSER = zhparser);
ALTER TEXT SEARCH CONFIGURATION chinese
ADD MAPPING FOR n,v,a,i,e,l WITH simple;

-- 使用
SELECT to_tsvector('chinese', '我愛 PostgreSQL 資料庫');
```

對 *主要英文 search* 場景 PG built-in 夠用、對 *主要 CJK search* 需要 extension。

## pg_trgm — Fuzzy String Match

PG FTS 對 *精確字根 match* 強、對 *拼錯 / similar string* 弱。`pg_trgm` extension 提供 trigram-based fuzzy match：

```sql
CREATE EXTENSION pg_trgm;

-- 對 column 建 GIN trigram index
CREATE INDEX idx_users_name_trgm ON users USING GIN (name gin_trgm_ops);

-- Fuzzy match（similarity threshold 預設 0.3）
SELECT * FROM users WHERE name % 'jhon';
-- → 找到 'John'、'Johan'、'Johnny' 等 similar string

-- 顯式 similarity score
SELECT name, similarity(name, 'jhon') FROM users
ORDER BY similarity(name, 'jhon') DESC LIMIT 5;
```

用途：

- Autocomplete / typeahead suggestion
- 拼錯容錯（user 輸入 typo）
- ILIKE 加速（`name ILIKE '%jhon%'` 走 GIN trigram index）

跟 FTS 互補：

- FTS：full document search、tokenize / stemming / ranking
- pg_trgm：short string similarity、typo tolerance

## 5 個 Production 踩雷

### 1. Dictionary 選錯 — 中文搜不到

對中文 column 用 `to_tsvector('english', text)`、不分詞、整段當一個 token、搜不到任何結果。

修法：

- 中文用 `zhparser` / `pgroonga`
- 多語言 column 拆 *per-language column* 或用 `simple` dictionary（不 stemming、字元級 match）
- 確認 dictionary 選對：`SELECT to_tsvector('chinese', '...')` 看分詞結果

### 2. GIN vs GiST 取捨選錯

PG FTS 有兩種 index access method：

- *GIN*：read fast、write slow、size 大、適合 *read-heavy*
- *GiST*：read 慢、write fast、size 小、適合 *write-heavy 或 small doc*

預設選 GIN、適合 90% search workload。對 *寫入頻繁 + 文件小* 場景 GiST。

修法：

- 預設 GIN
- 寫吞吐 > 10K WPS 場景考慮 GiST 或 *bulk index*（先 disable index、bulk insert、重建 index）
- GIN 有 `fastupdate` option、buffering 加速寫入（trade-off：read 慢）

### 3. Ranking 評分權重不對齊 business

`ts_rank` 預設不考慮 *field weight*、`ts_rank_cd` 考慮 cover density、兩者結果不同。Application 不知道 *自己 query 對應哪個 rank function*、結果隨機。

修法：

- 顯式選 ranking function：`ts_rank` 一般用、`ts_rank_cd` 對 *proximity 重要* 場景
- 設 *field weight*（A > B > C > D）反映 business priority（title > body > tags）
- 對 *搜尋結果* 用 A/B test 評估 ranking 質量、不靠直覺

### 4. Multi-language column 處理

Application 同表存多語言 row（user-generated content、不同 language）、用單一 `to_tsvector('english', ...)` 對中文 row 搜不到、對 french row 也 stem 錯。

修法：

- 加 `language` column 標每 row 語言
- 用 dynamic dictionary：

   ```sql
   ALTER TABLE articles ADD COLUMN fts tsvector
   GENERATED ALWAYS AS (
       to_tsvector(
           CASE WHEN language = 'zh' THEN 'chinese'::regconfig
                WHEN language = 'fr' THEN 'french'::regconfig
                ELSE 'english'::regconfig END,
           coalesce(title, '') || ' ' || coalesce(body, '')
       )
   ) STORED;
   ```

- Query 時用對應語言 `to_tsquery`

### 5. 何時不該用 PG FTS — 應該換 Elasticsearch / OpenSearch

PG FTS 適合 *中小規模搜尋*、不適合：

- *> 100M document* high-QPS search
- 需要 *complex aggregation*（faceted search）
- 需要 *advanced ranking*（BM25 / learning to rank）
- 需要 *分散式 search*（PG FTS 是 single-node）
- 需要 *near-real-time indexing*（PG GIN update 較慢）

對這些場景、用 Elasticsearch / OpenSearch / Meilisearch / Typesense 等專業 search engine。

PG FTS *優勢* 是 *跟 OLTP data 同 transaction* — 不需要 ETL 同步 search index、application 寫 PG 立即 searchable。對 application data + search 是 *同源* 的場景 PG FTS 比較適合。

## 何時用 PG FTS

| 場景                                             | 選擇                       |
| ------------------------------------------------ | -------------------------- |
| Application internal search（admin / dashboard） | PG FTS                     |
| < 10M document、低 QPS（< 100/s）                | PG FTS                     |
| Search 跟 OLTP data 同 transaction needed        | PG FTS                     |
| Fuzzy / typo tolerance                           | PG FTS + pg_trgm           |
| > 100M document + high QPS                       | Elasticsearch / OpenSearch |
| Faceted aggregation                              | Elasticsearch / OpenSearch |
| Vector similarity（semantic search）             | pgvector（同 PG）          |

PG FTS + pgvector 組合對 *中小規模 hybrid keyword + semantic search* 是強選擇。

## 跟其他模組整合

- [JSONB Deep Dive](/backend/01-database/vendors/postgresql/jsonb-deep-dive.md)：JSONB 跟 FTS 都用 GIN
- [Extension Ecosystem](/backend/01-database/vendors/postgresql/extension-ecosystem.md)：pg_trgm / pgroonga / zhparser 都是 extension
- [Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/)：FTS query 的 EXPLAIN
- [Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)：FTS GIN index 在 standby 自動 replicate

## 相關連結

- [PostgreSQL vendor overview](/backend/01-database/vendors/postgresql/)
- [PG Extension Ecosystem](/backend/01-database/vendors/postgresql/extension-ecosystem.md)（pg_trgm / pgroonga）
- [PG JSONB Deep Dive](/backend/01-database/vendors/postgresql/jsonb-deep-dive.md)（共用 GIN）
- [PG Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/)（FTS query plan）
- 官方：[PG Full-Text Search](https://www.postgresql.org/docs/current/textsearch.html) / [pg_trgm](https://www.postgresql.org/docs/current/pgtrgm.html)
