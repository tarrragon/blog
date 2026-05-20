---
title: "PostgreSQL Citus Distributed：用 extension 把 PG 變成 sharded cluster"
date: 2026-05-19
description: "Citus 是 PG extension、把單機 PG 變成 *coordinator + worker* sharded cluster、保留 PG SQL + 加 distributed table + reference table + columnar storage。本文走 Citus 架構（coordinator / worker / distribution column）、3 種 table type（distributed / reference / local）、配置 step-by-step、5 production 踩雷（distribution column 選錯 / cross-shard transaction / reference table 過大 / colocate 不對齊 / worker failover）、跟 MySQL Vitess sharding sibling 對比"
weight: 18
tags: ["backend", "database", "postgresql", "citus", "sharding", "distributed", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 PG 在 OLTP 譜系的定位、本文聚焦 *Citus distributed extension* — 把 PG 變成 sharded cluster 的方式。

---

當 PG single-primary 寫吞吐撞上單機極限（50K-100K WPS）、選項三條：

1. **Application 層 sharding**：應用層自管 shard routing
2. **Citus**：PG extension、自動 routing + cross-shard query
3. **Distributed SQL**（CockroachDB / Aurora DSQL / Spanner）：不同 engine

選 Citus 的核心 driver：*保留 PG SQL syntax + extension 生態*。但「應用層幾乎不必改」是樂觀說法 — 實際上 application 必須圍繞 distribution column 重設計（query 加 filter / transaction 限定同 shard / reference table 量控制）、跟 Vitess 比 cross-shard query 自動化弱。代價是 *coordinator / worker 部署複雜度 + cross-shard query 限制 + application schema 改造工作量*。

閱讀本文前可先對齊 [Database Sharding](/backend/knowledge-cards/database-sharding/) 的 shard key、routing、resharding 與 cross-shard query 語意；容量失衡時再接 [Hot Partition](/backend/knowledge-cards/hot-partition/)。

跟 [MySQL Vitess sharding](/backend/01-database/vendors/mysql/vitess-sharding/) 的核心差異：Citus 是 *PG extension*（PG 自己跑）、Vitess 是 *獨立 proxy + tablet 系統*（包 MySQL）。Citus 用 PG 原生機制（FDW / extension hook）、Vitess 是 *外部包裝*。

## Citus 架構：Coordinator + Worker

```text
                ┌─────────────────┐
   Application  │   Coordinator   │  ← 對外 PG wire protocol、planner、routing
                │   (Citus + PG)  │
                └────┬─────┬──────┘
                     │     │
              ┌──────┘     └──────┐
              ▼                   ▼
        ┌──────────┐         ┌──────────┐
        │ Worker 1 │         │ Worker 2 │  ← 各跑 PG + Citus extension
        │  (PG)    │         │  (PG)    │
        │ shard 1,3│         │ shard 2,4│
        └──────────┘         └──────────┘
```

**Coordinator**：

- 對 application 看起來像 PG（同 port / 同 wire protocol）
- 接 SQL → Citus planner 把 query 分解 + route 給 worker
- 不存 data（distributed table 的 shard 在 worker 上）
- 存 *metadata*（哪個 shard 在哪個 worker）

**Worker**：

- 標準 PG instance + Citus extension
- 各存若干 shard
- 接 coordinator 來的 query、跑 local execute、回結果

**Shard**：

- Distributed table 拆成 N 個 shard（預設 32）
- 每 shard 是 worker 上的 *physical PG table*（含 `_<shardid>` 後綴）
- 行為跟一般 PG table 一樣、可以直接連 worker 用 PG 工具 access

## 3 種 Table Type

### Distributed table — 跨 shard 切分

```sql
-- 建一般 PG table
CREATE TABLE orders (
    id BIGSERIAL,
    user_id BIGINT NOT NULL,
    amount DECIMAL(10,2),
    created_at TIMESTAMP,
    PRIMARY KEY (user_id, id)  -- PK 必須含 distribution column
);

-- 用 Citus 把它變 distributed
SELECT create_distributed_table('orders', 'user_id');
```

`user_id` 是 *distribution column* — Citus 用它的 hash 決定 row 屬哪個 shard。`PK 必須含 distribution column`（跟 MySQL partitioning 同要求）。

跟 Vitess Vindex 對比：

- Citus：hash distribution column → shard（單一 hash function、不可選 algorithm）
- Vitess：Vindex 可選多種（hash / lookup_hash / xxhash / null）

### Reference table — 全 shard 共有

```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    price DECIMAL
);

SELECT create_reference_table('products');
```

`products` 在 *每個 worker 都有完整 copy*、寫入 coordinator 廣播給所有 worker。

用途：

- 小 lookup table（country code / product category 等）
- 跨 distributed table JOIN 時、reference table 在每 worker 上、不必 cross-shard
- 寫入頻率低（廣播 cost 跟 worker 數 linear）

### Local table — Coordinator 上的 PG table

```sql
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    event JSONB
);
-- 不調用 Citus function、預設留在 coordinator
```

行為跟一般 PG table 一樣。用於 *不需 distribute* 的 table（如 admin metadata）。

## Colocation：跨 distributed table 同 shard 對齊

當兩個 distributed table 都用 *同 distribution column*（例如 `user_id`）+ 同 shard count、Citus 自動 colocate：

```sql
SELECT create_distributed_table('orders', 'user_id');
SELECT create_distributed_table('user_addresses', 'user_id', colocate_with => 'orders');
```

Colocate 後：

- `user_id = 100` 的 orders 跟 user_addresses 在 *同一 worker shard*
- JOIN 不跨 worker、效率高
- 可用 PG 原生 FK constraint（cross-table 但同 shard）

Colocate 是 Citus 設計的核心 *跨 table 一致性* 機制。沒 colocate 的 cross-table query 變 cross-worker、效率大降。

## 配置 step-by-step（local cluster）

Production 用 Citus Cloud（Microsoft 託管）或 Azure Cosmos DB for PostgreSQL（同 engine）。Self-hosted：

### Step 1：Coordinator + worker 都裝 PG + Citus

```bash
# 在每個 node（coordinator + 2 worker）
apt install postgresql-14
apt install postgresql-14-citus-12.0

# postgresql.conf
shared_preload_libraries = 'citus'

systemctl restart postgresql
```

```sql
-- 在每個 node 跑
CREATE EXTENSION citus;
```

### Step 2：Coordinator 註冊 worker

```sql
-- 在 coordinator 跑
SELECT citus_add_node('worker1.example.com', 5432);
SELECT citus_add_node('worker2.example.com', 5432);

-- 確認
SELECT * FROM citus_get_active_worker_nodes();
```

### Step 3：建 distributed table

```sql
CREATE TABLE orders (
    id BIGSERIAL,
    user_id BIGINT NOT NULL,
    amount DECIMAL(10,2),
    created_at TIMESTAMP,
    PRIMARY KEY (user_id, id)
);

SELECT create_distributed_table('orders', 'user_id');
```

Citus 自動把 `orders` 拆成 32 個 shard（`orders_102008` 等）、分配到 worker。

### Step 4：Application 連 coordinator

Application connection string 連 coordinator IP / port（不必知道 worker 存在）。

```sql
-- 從 application 跑 query、Citus 透明 route
INSERT INTO orders (user_id, amount) VALUES (12345, 50);
-- → Citus 看 user_id=12345 hash 屬 shard 17、route 給對應 worker

SELECT * FROM orders WHERE user_id = 12345;
-- → Single-shard query、極快

SELECT count(*) FROM orders;
-- → Cross-shard aggregation、Citus 並行跑、合併結果
```

## 5 個 Production 踩雷

### 1. Distribution column 選錯 — Cross-shard query 變主流

選 `created_at` 或 `id`（auto increment）作 distribution column、看起來均勻、實際 *application query 多以 user_id 為主*、變成 *每個 query 都 cross-shard*、performance 雪崩。

修法：

- *Distribution column 選 application 最常 filter / join 的 column*（通常是 `tenant_id` / `user_id`）
- Audit application top query、確認 distribution column 對齊 query pattern
- 改 distribution column 要 *rewrite 所有 shard*、像 resharding、大工程

### 2. Cross-shard transaction 限制

跨多 shard 的 transaction（如：UPDATE 兩個 user_id 不同的 row）Citus 用 *2PC*（two-phase commit）但有限制：

- Multi-statement transaction 跨 shard 需明確開 `SET citus.multi_shard_modify_mode = 'sequential'`
- 部分 isolation level 不保證 serializable across shards
- DDL 跨 shard 是 sequential

修法：

- Schema design 避免 cross-shard transaction（同 colocation group 內 transaction 沒問題）
- 必要 cross-shard 場景明確設 multi-shard mode
- 對 *strict cross-shard consistency*、考慮 distributed SQL（CockroachDB / Aurora DSQL）

### 3. Reference table 過大 — 寫入廣播 cost 爆

Reference table 在每 worker 都有 copy、寫入 *廣播給所有 worker*。Reference table 100K row + 高頻寫入 → 寫一次寫 N worker、cost N x。

修法：

- Reference table 限 *小 + 寫入頻率低* 的 lookup data
- 超大表不該是 reference table、考慮 distributed
- 監控 reference table 寫入 rate、超 threshold 重新評估

### 4. Colocate 沒對齊 — 隱性 cross-shard JOIN

```sql
-- 看似可以、實際 cross-shard 慢
SELECT * FROM orders o JOIN user_addresses ua ON o.user_id = ua.user_id;
```

若 `user_addresses` 沒 `colocate_with => 'orders'`、兩表 shard 分配獨立、JOIN 跨 worker。

修法：

- 建相關 table 時 `colocate_with` 對齊
- 用 `SELECT * FROM citus_tables` 看 colocation_id、確認對齊
- 跨非 colocate table 的 JOIN 用 *materialized view* 或 application 層拆 query 避開

### 5. Worker failover — Coordinator 必須知道

Worker 故障、Citus 預設 *coordinator 看到 query 失敗、不自動 failover*。

修法（Citus 11+）：

- 用 *shard replication*（`citus.shard_replication_factor = 2`）— 每 shard 在 2 個 worker 有 copy
- 配 PG streaming replication 在 worker 層、外加 Patroni 管 failover
- Coordinator 失敗 → 整個 cluster 失能、coordinator 也要 HA（Patroni）

跟 Vitess 對比 Citus 的 HA story 較弱、production 必須認真規劃。

## 何時用 Citus

| 條件                                                  | 建議                                        |
| ----------------------------------------------------- | ------------------------------------------- |
| Multi-tenant SaaS、tenant_id 為自然 distribution      | 是                                          |
| 寫吞吐 > 50K WPS、單 PG 撐不住                        | 是                                          |
| 需要保留 PG SQL + extension（pgvector / TimescaleDB） | 是                                          |
| 應用 query pattern 80% 都用同一 distribution column   | 是                                          |
| 應用大量 ad-hoc cross-tenant aggregation              | 否（cross-shard 慢）                        |
| 強 cross-shard consistency 需求                       | 否（用 CockroachDB）                        |
| 想 zero-ops managed                                   | Azure Cosmos DB for PostgreSQL（同 engine） |

## 容量規劃

- Coordinator: 中等 CPU + RAM、metadata 不大、不存 data
- Worker: per-worker spec 同 single PG production
- Shard count: 預設 32、實務常設 worker count × 4-8
- Replication factor: production 至少 2

## 跟其他模組整合

### 跟 Replication topology

Coordinator + worker 各跑 PG streaming replication、Citus 不取代 PG replication。Worker failover 用 Patroni / streaming replication。詳見 [Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)。

### 跟 PG Extensions

Citus 跟其他 PG extension 多數兼容（pgvector / TimescaleDB / pg_stat_statements）— 它維持 *extension* 形態，保留 PostgreSQL 生態接點。詳見 *PG Extension Ecosystem* 篇（待寫）。

### 跟 MySQL Vitess

| 維度             | Citus                             | Vitess                            |
| ---------------- | --------------------------------- | --------------------------------- |
| 部署模型         | PG extension                      | 獨立 proxy + tablet               |
| 主要場景         | Multi-tenant SaaS                 | 超大規模分片                      |
| Cross-shard JOIN | colocate 對齊 + reference table   | VTGate 自動 split + aggregate     |
| FK               | 同 colocation 內可用              | Vitess 18+ 支援、cross-shard 限制 |
| HA               | 依賴 Patroni + replication factor | VTOrc + replication               |
| 學習曲線         | 中（PG ops 經驗夠）               | 高（4 component）                 |

Citus 對 *PG-native* 場景更平順、Vitess 對 *MySQL-native* 場景更平順、不直接競爭。詳見 [MySQL Vitess Sharding](/backend/01-database/vendors/mysql/vitess-sharding/)。

## 相關連結

- [PostgreSQL vendor overview](/backend/01-database/vendors/postgresql/)
- [PG Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)（per-worker replication）
- [PG MVCC + Lock Model](/backend/01-database/vendors/postgresql/mvcc-lock-model/)（cross-shard transaction lock 行為）
- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)（Citus vs CockroachDB vs Spanner）
- [MySQL Vitess Sharding](/backend/01-database/vendors/mysql/vitess-sharding/)（sibling、不同實作）
- [Cosmos DB vendor](/backend/01-database/vendors/cosmosdb/)（Azure Cosmos DB for PostgreSQL = managed Citus）
- 官方：[Citus Documentation](https://docs.citusdata.com/) / [Citus on GitHub](https://github.com/citusdata/citus)
