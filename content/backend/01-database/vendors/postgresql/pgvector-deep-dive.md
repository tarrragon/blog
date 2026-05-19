---
title: "pgvector Deep Dive：HNSW / IVFFlat 取捨跟跟專業 Vector DB 對比"
date: 2026-05-19
description: "pgvector 是 PG extension、加 *vector* type 跟兩種 ANN index（IVFFlat / HNSW）、把 PG 變成可用 vector DB。本文走 vector type + distance operator、IVFFlat vs HNSW 取捨（build time / recall / memory）、quantization 跟 dimension reduction、5 production 踩雷（dimension 超 2000 限制 / HNSW build 太慢 / IVFFlat 不重建 recall 漂移 / hybrid search 設計 / memory budget）、跟 Pinecone / Weaviate / Milvus 對比的決策框架"
weight: 30
tags: ["backend", "database", "postgresql", "pgvector", "vector-search", "embedding", "extension", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 PG 在 OLTP 譜系的定位、本文聚焦 *pgvector extension* — 用 PG 解 vector search workload 的路徑、是 [extension-ecosystem](/backend/01-database/vendors/postgresql/extension-ecosystem/) 內最受關注的 extension。

---

## pgvector 是 PG 變 Vector DB 的最短路徑

pgvector 加兩件事：

```sql
CREATE EXTENSION vector;

-- 加 vector column（dimension 必須事先決定）
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding vector(1536)  -- OpenAI ada-002 維度
);

-- 三種 distance operator
SELECT * FROM documents ORDER BY embedding <-> '[0.1, 0.2, ...]' LIMIT 10;  -- L2
SELECT * FROM documents ORDER BY embedding <#> '[0.1, 0.2, ...]' LIMIT 10;  -- inner product
SELECT * FROM documents ORDER BY embedding <=> '[0.1, 0.2, ...]' LIMIT 10;  -- cosine
```

Operator 對應：

| Operator | 意義                   | 適用                           |
| -------- | ---------------------- | ------------------------------ |
| `<->`    | L2 distance            | 通用、空間距離                 |
| `<#>`    | Negative inner product | normalized vector、cosine 等價 |
| `<=>`    | Cosine distance        | embedding 比較最常用           |

對 OpenAI / Cohere / sentence-transformers embedding、通常用 `<=>`（cosine）— embedding model 訓練時是 cosine objective。

## ANN Index 是 Vector Search 的核心

不加 index 的 `ORDER BY embedding <=> ?` 是 *full scan*：

- 100K row、1536 dim、每 query ~2-5s（不可用）
- 1M row 直接超時

pgvector 提供兩種 *Approximate Nearest Neighbor*（ANN）index：

| Index   | Build 時間   | Query 時間     | Recall@10 | Memory cost      | Update 行為                  |
| ------- | ------------ | -------------- | --------- | ---------------- | ---------------------------- |
| IVFFlat | 快（分鐘級） | 中（10-100ms） | 90-95%    | 中（lists 數量） | Insert OK、需重建保持 recall |
| HNSW    | 慢（小時級） | 快（1-10ms）   | 95-99%    | 高（2-4x 資料）  | Insert OK、graph 漸進維護    |

**選 IVFFlat 的場景**：

- Embedding 量 < 1M
- Build 時間敏感（CI / batch 環境）
- Memory 緊
- 接受重建 cost（每月 / 每季）

**選 HNSW 的場景**：

- Embedding 量 1M-100M
- Query latency < 50ms 要求
- Memory 充足
- Insert 量穩定（不會爆炸性增長）

## IVFFlat：分 Cluster 找鄰居

IVFFlat 機制：

1. **Build**：跑 k-means 把所有 vector 分 `lists` 個 cluster
2. **Query**：先找最近的 `probes` 個 cluster、再在這些 cluster 內找 nearest neighbor

```sql
-- Build（lists 數量重要）
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Query 時調 probes 換 recall vs latency
SET ivfflat.probes = 10;
SELECT * FROM documents ORDER BY embedding <=> ? LIMIT 10;
```

**Lists 跟 probes sizing 規則**（pgvector 官方建議）：

| Row count | lists 建議    | probes 建議   |
| --------- | ------------- | ------------- |
| < 1M      | `rows / 1000` | `sqrt(lists)` |
| > 1M      | `sqrt(rows)`  | `sqrt(lists)` |

實務：100K row → lists=100 / probes=10、1M row → lists=1000 / probes=32。

**IVFFlat 的 recall drift**：cluster 是 build 時固定的、新 insert 的 vector 進入「最近 cluster」、但隨資料分布改變、cluster center 可能不再代表性、recall 隨時間下降。

修法：定期 `REINDEX INDEX CONCURRENTLY ...`（每月 / 每 100K 新 row）。

## HNSW：Multi-level Graph 找鄰居

HNSW（Hierarchical Navigable Small World）機制：

1. 多層 graph、上層稀疏、下層密集
2. Query 從上層 entry point 開始、逐層找近鄰、最後在底層精細搜尋
3. Insert 漸進維護 graph、不必重建

```sql
-- Build（兩個關鍵參數）
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Query 時調 ef_search
SET hnsw.ef_search = 100;
SELECT * FROM documents ORDER BY embedding <=> ? LIMIT 10;
```

**參數含義**：

| 參數              | 含義                    | 預設 | Trade-off                   |
| ----------------- | ----------------------- | ---- | --------------------------- |
| `m`               | 每 node 最多鄰居數      | 16   | 大 → recall 高、memory 多   |
| `ef_construction` | Build 時 graph 質量參數 | 64   | 大 → build 慢、graph 質量好 |
| `ef_search`       | Query 時搜尋範圍        | 40   | 大 → recall 高、latency 高  |

**Build cost 真實量級**（1M vector × 1536 dim）：

| 配置                      | Build 時間 | Memory | Recall@10 |
| ------------------------- | ---------- | ------ | --------- |
| m=8, ef_construction=32   | 30 min     | 4GB    | 92%       |
| m=16, ef_construction=64  | 2 hour     | 8GB    | 96%       |
| m=32, ef_construction=200 | 8 hour     | 16GB   | 98%       |

Production 多數選中間 `m=16, ef_construction=64`、recall / cost 平衡。

## Hybrid Search：Vector + Filter 一起

Vector search 加 SQL filter 是 pgvector 比專業 vector DB 強的場景：

```sql
-- Vector + metadata filter
SELECT * FROM documents
WHERE category = 'tech' AND created_at > '2025-01-01'
ORDER BY embedding <=> '[0.1, 0.2, ...]'
LIMIT 10;
```

但這裡有個 *pgvector 的踩雷*：filter 跟 ANN index 互動有兩種模式：

1. **Pre-filter**（planner 選）：先 filter 出符合條件的 row、再對 subset 跑 vector ordering → 不用 ANN index、可能慢
2. **Post-filter**：用 ANN index 找 top-N、再 filter、可能 N 不夠補

pgvector 0.8+（2024-10 release）加入 *iterative index scan*：HNSW / IVFFlat 一邊掃 graph 一邊 filter、效能比 pre-filter 好 5-10x。0.7+（2024-07）加 halfvec / binary quantization / parallel HNSW build。

實務：filter selectivity 高（< 10%）時、考慮對 filter column 加 index 走 pre-filter；selectivity 低（> 50%）走 iterative scan。

## Quantization 跟 Dimension Reduction

1536 dim float32 vector 一筆 6KB、1M row 6GB、加 HNSW index 後 ~20GB。Memory 緊時的省法：

### Half-precision（pgvector 0.7+）

```sql
CREATE TABLE documents (
    embedding halfvec(1536)
);
```

`halfvec` 是 float16、storage 減半、recall 損失通常 < 1%。

### Binary quantization

```sql
-- 把每維壓成 1 bit
CREATE INDEX ON documents USING hnsw (embedding bit_hamming_ops);
```

Recall 下降明顯（85-90%）、但 storage 1/32、適合「先粗篩再 rerank」hybrid pipeline。

### Dimension reduction

訓練 PCA / Matryoshka model 把 1536 dim 降到 256-512 dim、recall 通常損失 < 3%、storage 1/3-1/6。

## 5 個 Production 踩雷

### Case 1：Dimension 超 2000 限制

**情境**：要用 OpenAI text-embedding-3-large（3072 dim）、`CREATE TABLE ... embedding vector(3072)` 報錯。

pgvector `vector` type 上限 2000 dim（IVFFlat / HNSW index 限制）。

修法：

- 改用 `halfvec`（pgvector 0.7+ 支援 4000 dim）
- 用 Matryoshka 截斷到 2000 dim 以下
- 換 embedding model（OpenAI text-embedding-3-small 1536 dim / 可截斷到 256-1024）

### Case 2：HNSW build 太慢

**情境**：1M row build HNSW、跑 8 小時、blocking production。

修法：

```sql
-- 用 CONCURRENTLY 不 block
CREATE INDEX CONCURRENTLY ON documents USING hnsw (...);

-- 開 maintenance_work_mem
SET maintenance_work_mem = '8GB';

-- 開 parallel
SET max_parallel_maintenance_workers = 7;
```

仍慢的話、考慮：

- 切分 batch insert + index（適合 read-heavy）
- 用 IVFFlat 短期上線、之後再切 HNSW
- 改用 cloud managed pgvector（提供更大 instance）

### Case 3：IVFFlat 不重建 recall 漂移

**情境**：IVFFlat build 時資料 100K、現在 500K、新資料 recall 從 92% 降到 75%、user 抱怨「找不到相關文件」。

修法：

- Monitor recall：定期跑 ground-truth eval（brute-force 對比）
- 設定 reindex policy：每 100K 新 row 或每月 reindex
- 換 HNSW：insert 漸進維護、不需 reindex（trade-off：build 更慢）

### Case 4：Hybrid search filter selectivity 沒設計

**情境**：query `WHERE user_id = ? ORDER BY embedding <=> ?`、user_id 高選擇性（1/1M）、planner 選 vector index scan、掃到 top-K 全不符 user_id、補抓無止盡。

修法：

- `EXPLAIN` 看 planner 選 pre-filter 還是 vector-first
- 對 `user_id` 加 B-tree index、強 planner pre-filter（hint 不容易、用 statistics）
- pgvector 0.8+ 用 iterative scan、自動處理
- 設計 schema：高選擇性 filter（user_id）建議走 pre-filter；低選擇性（category）走 iterative

### Case 5：Memory budget 沒抓

**情境**：1M vector × 1536 dim × HNSW（m=16）= ~12GB index、shared_buffers 8GB、index 不在 cache、每 query disk IO、latency 100ms+。

修法：

- 算 vector + index memory：`row × dim × 4 bytes × (1 + index_overhead)`
- `shared_buffers` 至少能放 hot index portion
- 不行就降 dim（halfvec）/ 升 instance / 拆 sharded

## 跟專業 Vector DB 對比

| 維度             | pgvector                 | Pinecone              | Weaviate       | Milvus         |
| ---------------- | ------------------------ | --------------------- | -------------- | -------------- |
| Query 介面       | SQL                      | REST/gRPC API         | GraphQL / REST | gRPC           |
| Recall           | 95-99%（HNSW）           | 95-99%                | 95-99%         | 95-99%         |
| Throughput       | 中（PG 限制）            | 高                    | 高             | 高             |
| Hybrid search    | 強（完整 SQL）           | 中（metadata filter） | 中             | 中             |
| 跟既有 PG 整合   | 完美（同 DB join）       | 需 sync               | 需 sync        | 需 sync        |
| Multi-tenant     | row-level（PG 一致）     | 內建                  | 內建           | partition      |
| Open source      | 是                       | 否                    | 是             | 是             |
| Operational cost | 跟 PG 一樣（管 PG 即可） | Managed-only          | 需自管或 cloud | 需自管或 cloud |
| Scale 上限       | 10M-100M vector          | 10B+                  | 1B+            | 10B+           |

**選 pgvector 的場景**：

- Application 已用 PG、不想多管系統
- Vector 量 < 100M
- 需要 join vector + relational
- Team SQL 熟、不想學 API SDK
- Cost 敏感（managed Pinecone 1M vector 月 ~$70+）

**選專業 vector DB 的場景**：

- Vector 量 > 5-20M（依 dim / QPS / recall 要求、pgvector 在這個級別 + 高 QPS 已開始痛、不必撐到 100M 才換）
- 純 vector workload（沒 relational integration）
- 需要 multi-tenant SaaS
- Throughput 要求極高（> 10K QPS）
- 不想自管 HNSW build / memory budget / recall drift（managed Pinecone 把這層 ops 轉嫁、cost 換 ops 時間）
- 需要 dim > 2000（pgvector vector type 限制、halfvec 可到 4000、再大需 dimension reduction）

## 相關連結

- [extension-ecosystem](/backend/01-database/vendors/postgresql/extension-ecosystem/)：其他 PG extension
- [jsonb-deep-dive](/backend/01-database/vendors/postgresql/jsonb-deep-dive/)：embedding 通常配 metadata JSONB
- [index-selection](/backend/01-database/vendors/postgresql/index-selection/)：B-tree / GIN / HNSW 整體比較
- [query-optimization](/backend/01-database/vendors/postgresql/query-optimization/)：vector query 的 EXPLAIN

## 下一步

- 看 [extension-ecosystem](/backend/01-database/vendors/postgresql/extension-ecosystem/) 探索其他 PG 擴展可能
- 回 [PostgreSQL overview](/backend/01-database/vendors/postgresql/) 看全圖
