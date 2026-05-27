---
title: "PostgreSQL → Aurora DSQL Migration：PG wire-compatible Distributed SQL 的 Paradigm Shift"
date: 2026-05-19
description: "Aurora DSQL（2024-12 re:Invent preview / 2025-05 GA）是 AWS 推的 PG wire-compatible *active-active distributed SQL*、跟 self-managed PG / Aurora PG 不同 paradigm（OCC + snapshot isolation + multi-region strong consistency）。Migration 結構是 *protocol drop-in + paradigm shift*：app SQL 不太改、但 transaction retry / extension 缺位 / 多 region 一致性需重設計。本文走 DSQL vs Aurora PG vs self-managed PG 三軸對比、為什麼遷的三條 driver（global write / operational zero-touch / region resiliency）、Type E phased plan、5 production 踩雷（transaction retry 沒處理 / extension 缺位 / sequence throughput 限制 / Aurora PG 直升 DSQL 不可行 / region failover semantic）、跟 PG → Aurora 跟 PG → CockroachDB 對比"
weight: 42
tags: ["backend", "database", "postgresql", "aurora-dsql", "migration", "distributed-sql", "cloud-managed"]
---

> 本文是跨 vendor [migration](/backend/knowledge-cards/migration/) playbook、cross-link 到 [PostgreSQL](/backend/01-database/vendors/postgresql/)（source）跟 [Aurora](/backend/01-database/vendors/aurora/)（DSQL 也屬 Aurora family、但 paradigm 不同）。跟 [migrate-to-aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/)（PG → Aurora PG、protocol drop-in + operational redesign）跟 [migrate-to-cockroachdb](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/)（PG → CRDB、Type E paradigm shift）對照、本篇是 *Aurora 內 PG → DSQL 的 paradigm shift*。每階段切換用 [migration gate](/backend/knowledge-cards/migration-gate/) 把關。

> **時間錨點**：Aurora DSQL 在 **2024-12 re:Invent preview**、**2025-05-27 GA**。本文 vendor claim 以 2025-2026 公開狀態為準、實際 migration 前請以 AWS docs 為準（feature 持續演進中）。

## 為什麼遷：Global Write / Operational Zero-touch / Region Resiliency 三條 driver

PG → DSQL 不是「自然演進」、是 *application 需求超出 single-primary 模型* 時的 paradigm 換軌。三條典型 driver 各自對應一種 application 約束、不是「三選一」、而是「至少其中一條剛性、其他兩條是 bonus」：

| Driver                     | 觸發場景                                                                                                     |
| -------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Global write**           | Application 需要多 region active-active write（不是 Aurora PG 的 single-writer + read replica）              |
| **Operational zero-touch** | 不想管 Patroni / PgBouncer / autovacuum / failover / backup retention、Aurora PG 已減一半、DSQL 進一步零接觸 |
| **Region resiliency**      | 整 region 失效時應用無感切換（Aurora PG 是 cross-region replica 異步、DSQL 是 strong consistency 多 region） |

反向 driver（DSQL → Aurora PG）也存在：

- 需要 PG extension（pgvector / TimescaleDB / PostGIS / pg_repack）— DSQL 不支援
- Cost：DSQL 比 Aurora PG 貴 2-5x（依 region 數量）
- Single-region OLTP 不需 distributed transaction 的 overhead

## 結構：Protocol Drop-in + Paradigm Shift

DSQL 是 PG wire-compatible（用 `psql` 連得上）、但內部是 *distributed SQL engine*：

| 維度               | self-managed PG           | Aurora PG                       | Aurora DSQL                                 |
| ------------------ | ------------------------- | ------------------------------- | ------------------------------------------- |
| Wire protocol      | PG                        | PG                              | PG（subset）                                |
| Architecture       | Single primary            | Single primary + shared storage | **Active-active distributed**               |
| Multi-region write | 不支援（async replica）   | 不支援（async replica）         | **Strong consistency 多 region**            |
| Transaction model  | MVCC + snapshot isolation | MVCC + snapshot isolation       | **OCC + strong snapshot isolation**         |
| Extension          | 任意                      | AWS whitelist                   | **無 extension 支援**                       |
| Operational        | 全部自管                  | AWS 管 storage / failover       | AWS 管全部、零接觸                          |
| Failover           | Patroni 15-60s            | Aurora 30s                      | N/A（永遠 active-active、無 failover 概念） |
| Cost model         | Self-managed instance     | Instance hour + storage         | Per-DPU + multi-AZ replication              |

**Paradigm shift 的核心**：

1. **Transaction semantic**：DSQL 用 OCC（Optimistic Concurrency Control）+ strong snapshot isolation、跟 PG 預設 read committed / repeatable read snapshot 不同 — 同 row 有 concurrent write 時、commit 階段才偵測衝突 + abort、application 要 handle `40001` serialization_failure
2. **No extension**：PostGIS / pgvector / TimescaleDB / pg_partman 都不能用、依賴這些 feature 的 application 要拆出去
3. **No connection pool stateful**：DSQL 內建 connection pool、application 不能依賴 session state（temp table / prepared statement / advisory lock）

## Schema gap：PG 對 DSQL 限制

DSQL 是 PG-compatible *subset*、有幾類功能不支援：

| 類別                          | PG 支援 | DSQL 支援                                    |
| ----------------------------- | ------- | -------------------------------------------- |
| Extension                     | 是      | 否（沒 `CREATE EXTENSION`）                  |
| Foreign key constraint        | 是      | 否（application 維護 referential integrity） |
| View / Materialized view      | 是      | View 部分 / Materialized view 否             |
| JSON / JSONB                  | 是      | 部分（無 GIN index 加速）                    |
| Foreign data wrapper          | 是      | 否                                           |
| Stored procedure（PL/pgSQL）  | 是      | 部分（限制多）                               |
| Trigger                       | 是      | 部分                                         |
| LISTEN / NOTIFY               | 是      | 否                                           |
| `SELECT ... FOR UPDATE`       | 是      | 部分（DSQL OCC semantic）                    |
| Sequence（serial / identity） | 是      | 支援、但高吞吐有 coordination overhead       |
| Table partition               | 是      | 部分                                         |
| Logical replication slot      | 是      | 否                                           |

**Migration 必做 schema audit**：

```sql
-- 找所有 extension 依賴
SELECT * FROM pg_extension;

-- 找 materialized view
SELECT schemaname, matviewname FROM pg_matviews;

-- 找 sequence
SELECT * FROM pg_sequences;

-- 找 FDW
SELECT * FROM pg_foreign_server;

-- 找 trigger
SELECT * FROM pg_trigger WHERE NOT tgisinternal;
```

任何項目命中、都是 migration blocker。

## Operational Redesign

跟 self-managed PG 或 Aurora PG 比、DSQL operational model 大幅簡化但語意不同：

| Operational concept   | self-managed PG        | Aurora PG                         | Aurora DSQL                        |
| --------------------- | ---------------------- | --------------------------------- | ---------------------------------- |
| Storage               | Local / EBS            | Shared 6 副本                     | Distributed log + replicated state |
| HA                    | Patroni                | Aurora failover                   | 永遠 HA（無 failover 概念）        |
| Backup                | pgBackRest / WAL-G     | 內建 continuous                   | 內建 continuous（更深整合）        |
| Connection pool       | PgBouncer / PgCat      | RDS Proxy 推薦                    | 內建（無需配置）                   |
| Major version upgrade | 手動 + 停機            | Aurora blue/green                 | 完全 transparent（AWS 升）         |
| Read replica          | Streaming replication  | Reader endpoint                   | 無分（每 region 都讀寫）           |
| Monitoring            | Prometheus / pg_stat_* | CloudWatch + Performance Insights | CloudWatch（簡化）                 |
| 預期 SRE FTE          | 0.5-2                  | 0.2-0.5                           | < 0.1                              |

## Migration 流程：Type E Phased Plan

Type E paradigm shift 的 phased plan、跟 [migrate-to-cockroachdb](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/) 結構類似：

### Phase 1：Schema / Application Audit

- 跑 schema audit（extension / MV / FDW / sequence / trigger）
- 識別 application 哪些 query / transaction pattern 需重設計
- 估算 *能直接遷的 % vs 需重寫的 %*、典型 60-80% / 20-40%

### Phase 2：Application 改造（不上 DSQL、先在 PG 跑）

- 加 transaction retry middleware（攔截 `40001`、exponential backoff）
- 用 UUID 替代 serial / bigserial
- 移除依賴 LISTEN/NOTIFY 的功能（改 SQS / EventBridge）
- 移除 materialized view（改 application-side cache 或 incremental ETL）
- Stored procedure 改 application code
- 在 PG 上跑 staging、確認新 application code 還對

### Phase 3：DSQL Cluster 建立 + Schema 遷

- DSQL cluster create
- DDL apply（subset of PG schema、無 extension）
- DMS（Database Migration Service）initial load + ongoing replication
- 兩邊跑 shadow traffic、比對 query 結果

### Phase 4：Cutover

- Application 切 connection string 到 DSQL
- 保留 PG read-only 一週、出狀況 rollback
- Monitor `40001` retry rate、scaling event 行為

### Phase 5：多 region 拓展（如適用）

- 加第二 region endpoint
- Application 改 multi-region routing（latency-based）
- Test region failure / network partition 行為

## 5 個 Production 踩雷

### Case 1：Transaction Retry 沒處理

**情境**：PG 上「兩個 transaction 都 update 同 row」走 lock + wait；DSQL 同情境一個會收 `40001 serialization_failure`、application 沒 catch、user 看到 500 error。

修法：

- DAO 層加 retry middleware：catch `40001` + exponential backoff（jitter）
- Retry 上限 3-5 次、超過回 4xx 給 user
- Transaction 內不要做 side effect（API call / message send）、retry 會重做

```python
def with_retry(fn, max_attempts=5):
    for attempt in range(max_attempts):
        try:
            return fn()
        except SerializationError:
            if attempt == max_attempts - 1:
                raise
            time.sleep((2 ** attempt) * 0.05 + random.random() * 0.05)
```

### Case 2：Extension 缺位、Feature 整段掉

**情境**：production PG 用 pgvector 做 RAG search、PostGIS 做 store locator、TimescaleDB 做 metrics — 切 DSQL 後三 feature 全沒。

修法：

- 不要直接遷、評估 *which extension is load-bearing*
- pgvector → 外掛 Pinecone / Weaviate 或保留 PG 跑 vector workload
- PostGIS → 保留 PG 跑 GIS workload
- TimescaleDB → 切 Amazon Timestream 或保留 PG
- DSQL 只放 *不依賴 extension* 的 transactional core

實務常見拓撲：DSQL 跑 transactional core、附 PG（vector） + PG（GIS） + Timestream（metrics）。

### Case 3：Sequence 高吞吐撞 Coordination Overhead

**情境**：`SERIAL` / `GENERATED AS IDENTITY` PK 在 DSQL 用、insert 量 1000+/s 時 sequence nextval 變成 bottleneck、insert latency 從 5ms 跳到 80-100ms+。

DSQL 有支援 sequence、但不是「local atomic counter」、是分散式 counter — 每次 nextval 需跨 region coordination 保證唯一性。低吞吐 OK、高吞吐撞牆。

修法：

- 高吞吐表 PK 換 UUID v7（time-sortable、無 coordination）：`gen_random_uuid()` 或 application-side UUID v7 library
- 或 application-side ULID（time-sortable、12-byte 緊湊）
- 完全避免依賴「連續 integer PK」的 application 邏輯（reporting / paging 改用 `ORDER BY created_at, id`）

```sql
-- 換 UUID PK
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ...
);
```

低吞吐表（settings / config）保留 sequence OK；high-volume transactional 表（orders / events）建議 UUID。

### Case 4：Aurora PG 直升 DSQL 想當 in-place

**情境**：team 以為「Aurora PG 跟 Aurora DSQL 都是 Aurora、應該能直升」、申請 cluster modify、發現完全是兩個 service。

修法：

- 不是 in-place upgrade、是 full migration（DMS + cutover）
- 把 DSQL 當完全新的 cluster type、走 Phase 1-4 完整流程
- Aurora PG → Aurora DSQL 不比 PG → CRDB 容易、wire-compatible 只解 application connect 問題、不解 schema / paradigm 差異

### Case 5：Region Failover Semantic

**情境**：team 以為「DSQL multi-region 等於高可用」、設計時假設「整 region 掛還是能寫」、實測發現「網絡分割時 DSQL 走 quorum、可能 reject write」。

DSQL 是 strong consistency 多 region、CAP 取 CP（不是 AP）—  network partition 時部分 region 會拒絕 write、不是「永遠可寫」。

修法：

- 設計 application 要 handle write reject（partition recovery 後 retry）
- 不要把 DSQL 當「永遠可寫」的 cache 或 queue 用
- 真要 AP 行為、用 DynamoDB（global table）

## Capacity 規劃

DSQL 計費跟 Aurora PG 差很多：

| 計費項目     | Aurora PG                    | Aurora DSQL              |
| ------------ | ---------------------------- | ------------------------ |
| Instance     | Per-instance hour            | 無（serverless）         |
| Storage      | Per-GB-month                 | Per-GB-month（多副本價） |
| IO           | Per-million IO               | 每 transaction 計費      |
| Backup       | Per-GB-month                 | 內建（無額外）           |
| Multi-region | Cross-region replica（額外） | 每 region 全費 × N       |

實務 cost：Aurora PG db.r6g.4xlarge multi-AZ 月 ~$2000 → DSQL 同 workload ~$5000-10000（依 region 數）。

何時 DSQL cost 划算：

- 多 region active-active 需求剛性（不是 nice-to-have）
- Operational FTE 節省超過 cost 差
- Burst workload（DSQL 自動 scale、Aurora PG 預配置 idle 期浪費）

## 跟既有 Migration Playbook 對比

| Migration                                                                        | Type | 主結構                                      |
| -------------------------------------------------------------------------------- | ---- | ------------------------------------------- |
| [→ Aurora PG](/backend/01-database/vendors/postgresql/migrate-to-aurora/)        | C    | Protocol drop-in + operational redesign     |
| [→ CockroachDB](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/) | E    | Paradigm shift（distributed SQL）           |
| → Aurora DSQL（本篇）                                                            | E    | Paradigm shift（PG-compatible distributed） |

**Aurora DSQL vs CockroachDB 選擇**：

| 維度              | Aurora DSQL             | CockroachDB                       |
| ----------------- | ----------------------- | --------------------------------- |
| PG compatibility  | Wire-compatible 較完整  | 高、但有差異                      |
| Vendor lock-in    | AWS only                | 跨雲 / on-prem                    |
| Cost              | AWS pricing             | 自管或 CockroachDB Cloud          |
| Multi-region 模型 | Strong consistency 內建 | 可配置（regional / global table） |
| Extension         | 完全沒                  | 部分（CDC / changefeed）          |
| Operational       | Zero-touch              | 自管或 managed                    |

選 DSQL：已綁 AWS、不想管基礎設施、需 PG semantic。
選 CRDB：跨雲、有自管 SRE、需要 fine-grained control。

## 相關連結

- [migrate-to-aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/)：Aurora PG 對比（Type C）
- [migrate-to-cockroachdb](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/)：CRDB 對比（Type E）
- [extension-ecosystem](/backend/01-database/vendors/postgresql/extension-ecosystem/)：DSQL 不支援的 extension
- [connection-scaling](/backend/01-database/vendors/postgresql/connection-scaling/)：DSQL 內建 pool 跟 PgBouncer 對比

## 下一步

- 看 [Aurora overview](/backend/01-database/vendors/aurora/) 認識 Aurora family
- 看 [migrate-to-cockroachdb](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/) 對比另一個 Type E migration
- 回 [PostgreSQL overview](/backend/01-database/vendors/postgresql/) 看全圖
