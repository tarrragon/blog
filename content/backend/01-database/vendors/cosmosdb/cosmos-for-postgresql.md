---
title: "Cosmos DB for PostgreSQL：基於 Citus 的分散式 PostgreSQL、跟核心 Cosmos DB 是不同產品、何時選它而非核心 Cosmos 或一般 PG"
date: 2026-06-02
description: "Cosmos DB for PostgreSQL（2022、Citus-based distributed PG）的定位釐清：它是分散式 PostgreSQL、不是 NoSQL Cosmos DB；distribution column / coordinator-worker 架構、何時選它而非核心 Cosmos DB、何時夠用一般 Azure Database for PostgreSQL — 命名混淆的選型陷阱"
weight: 74
tags: ["backend", "database", "cosmosdb", "postgresql", "citus", "deep-article"]
---

本文是 [Cosmos DB](/backend/01-database/vendors/cosmosdb/) overview 的 deep article、寫作參照 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。Cosmos DB for PostgreSQL 是 Azure 在 2022 把 Citus（PostgreSQL 的分散式 extension）納入後推出的 *分散式 PostgreSQL* 託管服務 — 它跑真正的 PostgreSQL engine、支援標準 SQL / JOIN / ACID 交易、把單表水平分片到多個 worker node。它跟本 vendor 頁主講的核心 Cosmos DB（NoSQL、multi-model、RU/s 計費）是 *兩個不同產品*、只是共用品牌名稱。本文的主責任是釐清這個定位混淆、再講它的架構與選型判準：何時選它、何時該回核心 Cosmos DB、何時一般 PostgreSQL 就夠。

本文沒有專屬 production case anchor：Cosmos DB for PostgreSQL 的公開 case 覆蓋稀薄、機制以 Azure / Citus vendor 規格與分散式 PostgreSQL 通用工程展開、選型判準用「scale-out PG vs NoSQL vs single-node PG」這個具體決策驅動。

> **Scope warning**：本文涉及的服務命名、node 規格上限、Citus 版本、PostgreSQL major version 支援屬時間敏感、Azure 服務命名歷史上有變動、實作前以 [Cosmos DB for PostgreSQL 官方文件](https://learn.microsoft.com/azure/cosmos-db/postgresql/) cross-verify。

## 問題情境

典型觸發場景：team 在 Azure 上跑 PostgreSQL、單機 primary 撐到上限 — write throughput、資料量、或單表太大導致 index / vacuum / query 變慢。看到「Cosmos DB」以為是要把資料搬進 NoSQL、重寫 application 成 document model；或反過來、看到「Cosmos DB for PostgreSQL」以為它就是核心 Cosmos DB 的一個 PostgreSQL API、結果發現它是完全不同的東西。命名混淆讓選型從一開始就走偏。

讀者徵兆：

- 「單機 PostgreSQL 撐不住、但 application 是 SQL / JOIN / 交易重、不想重寫成 NoSQL」
- 「Cosmos DB for PostgreSQL 跟核心 Cosmos DB 是同一個東西嗎」
- 「它跟一般 Azure Database for PostgreSQL 差在哪、什麼時候才需要它」
- 「跟 CockroachDB / Aurora / Spanner 這些 distributed SQL 怎麼選」

真實壓力：SQL workload 撐到單機上限時、選錯方向的成本是年級的。誤以為要遷 NoSQL 而重寫 application 是浪費；誤以為核心 Cosmos DB 有「PostgreSQL 相容」而選錯產品也是浪費。正確的選型要先把這個服務放回它真正的分類 — *分散式 SQL*、見 [distributed SQL](/backend/knowledge-cards/distributed-sql/)。

## 核心機制：Citus-based coordinator-worker 分散式 PostgreSQL

Cosmos DB for PostgreSQL 的底層是 Citus、把 PostgreSQL 從單機擴展成 coordinator + worker 的分散式叢集。它的關鍵概念有幾個。

它跑 *真正的 PostgreSQL*。不是 wire-compat、不是 PostgreSQL API on top of NoSQL — 是 PostgreSQL engine 加 Citus extension。標準 SQL、JOIN、ACID 交易、PostgreSQL extension 生態（含部分如 PostGIS）都在。這跟核心 Cosmos DB（自己的 query language、SQL-like 但無 JOIN、RU/s 計費）是根本不同的東西。

架構是 coordinator-worker。coordinator node 接 query、根據 distribution column 把 query 路由 / 拆分到 worker node、worker 存實際的 shard。application 連 coordinator、看起來像連一個 PostgreSQL。

distribution column 是核心設計決策、類比核心 Cosmos DB 的 partition key 之於 NoSQL、也類比 [partition-key-design](../partition-key-design/) 講的分散原則。表按 distribution column 的值分片到 worker；同一 distribution column 值的 row 落在同一 shard。JOIN 與交易若在同一 distribution column 值內、可以下推到單一 worker 高效執行（co-location）；跨 distribution column 的 JOIN / 交易要跨 worker 協調、較貴。

表分三種：distributed table（按 distribution column 分片、大表用）、reference table（每個 worker 全複本、小的維度表用、讓 JOIN co-locate）、local table（只在 coordinator）。建模的關鍵是把常一起 JOIN 的大表用 *同一 distribution column* 分片、達成 co-location。

## 選型判準：三方對照

這是本文主判讀段。Cosmos DB for PostgreSQL 的正確位置是「single-node PG 不夠、但 workload 仍是 SQL 範式」的中間地帶。

選 Cosmos DB for PostgreSQL 的條件：

- workload 是 SQL 範式（關聯 schema、JOIN、交易）、不想 / 不能重寫成 NoSQL
- single-node PostgreSQL 已達上限（write throughput / 資料量 / 單表大小）、且資料有好的 distribution column（多租戶的 tenant_id、time-series 的某維度）
- 工作負載偏向多租戶 SaaS 或 real-time analytics over fresh data — Citus 的典型適配場景
- 想留在 PostgreSQL 生態（SQL、extension、既有 tooling）而非進 NoSQL

回核心 Cosmos DB（NoSQL）的條件：

- 資料形狀已是 document / KV、access pattern 固定、不需要 JOIN 與複雜 SQL
- 需要 multi-model（document + graph + KV）、5 個 consistency level、turnkey multi-region active-active write
- RU/s 容量抽象與 serverless 計費更符合 workload — 見 [ru-cost-model-sizing](../ru-cost-model-sizing/)

一般 Azure Database for PostgreSQL（single-node managed PG）就夠的條件：

- single-node 還沒到上限 — 多數 OLTP baseline 用 vertical scaling + read replica 就夠、不需要分散式
- 沒有好的 distribution column — 分散式 PostgreSQL 沒有均勻 distribution column 會 hot worker、好處拿不到、複雜度卻全付
- 不想承擔 distributed SQL 的複雜度（distribution column 設計、co-location 規劃、跨 shard query 成本）

判讀句：先確認 single-node PG 真的到上限、再確認 workload 是 SQL 範式（否則考慮 NoSQL）、最後確認有好的 distribution column。三個都成立、Cosmos DB for PostgreSQL 才是對的；缺任一個、回 single-node PG 或核心 Cosmos DB。

### 跟其他 distributed SQL 的位置

Cosmos DB for PostgreSQL 是 Azure 上、PostgreSQL-native、scale-out（co-location 設計驅動）的 distributed SQL。跟 [Spanner](/backend/01-database/vendors/spanner/)（全球 external consistency、自己的 SQL 方言）、[CockroachDB](/backend/01-database/vendors/cockroachdb/)（跨雲、PostgreSQL wire、自動 range 分散）、Aurora DSQL（AWS、全球 active-active）位置不同：Cosmos DB for PostgreSQL 強在「真 PostgreSQL engine + extension 生態 + co-location 控制」、弱在它的分散需要 distribution column 設計（不像 CockroachDB / Spanner 自動分 range）、且綁 Azure。

## 操作流程

### 建叢集與設定 distribution column

```sql
-- 建 distributed table、按 tenant_id 分片（多租戶 SaaS 典型）
CREATE TABLE events (
    tenant_id   bigint NOT NULL,
    event_id    bigint NOT NULL,
    payload     jsonb,
    created_at  timestamptz DEFAULT now()
);
SELECT create_distributed_table('events', 'tenant_id');

-- 維度小表設 reference table、讓 JOIN co-locate
CREATE TABLE tenants (tenant_id bigint PRIMARY KEY, name text);
SELECT create_reference_table('tenants');
```

驗證：`SELECT * FROM citus_tables;` 看每張表的 distribution column 與 shard 分布；對 distributed table 的查詢若帶 distribution column filter、`EXPLAIN` 顯示下推到單一 shard、不帶則 fan-out 到所有 worker。

### 驗證 co-location

```sql
-- 同 distribution column 的兩張 distributed table JOIN 應 co-located
SELECT colocation_id, count(*)
FROM citus_tables GROUP BY colocation_id;
```

驗證：常一起 JOIN 的大表落在同一 colocation group、JOIN 在 worker 本地完成、不跨 worker shuffle。

### 加 worker 擴容

加 worker node 後 rebalance shard。驗證：rebalance 後 shard 在新舊 worker 間分布均勻、單一 worker 不再是 hot spot。

### Rollback boundary

Cosmos DB for PostgreSQL 是叢集級服務、scale worker 是運維操作、可逆（縮回去）。但 *distribution column 一旦選定、改它要重建表 + 重灌資料* — 跟核心 Cosmos DB 的 partition key 不可改是同一類不可逆設計、見 [partition-key-design](../partition-key-design/)。

## 失敗模式

### 把它跟核心 Cosmos DB 當同一產品選

選型時把「Cosmos DB for PostgreSQL」當成「核心 Cosmos DB 的 PostgreSQL 介面」、規劃用 RU/s、找 consistency level 設定、結果整套 mental model 對不上 — 因為它是分散式 PostgreSQL、用 node 規格計費、用 PostgreSQL 的交易隔離級別。修法是選型第一步就確認「這是分散式 SQL、不是 NoSQL」、規劃按 PostgreSQL + Citus 的模型走、不要套核心 Cosmos DB 的概念。

### 沒有好的 distribution column 硬上分散式

workload 沒有均勻的 distribution column（例如資料天然集中在少數 tenant）、硬分片後變 hot worker、分散式的好處拿不到、複雜度全付。徵兆是少數 worker CPU / IO 飽和、其他 worker 閒置。修法是選型階段就評估 distribution column 的 cardinality 與均勻度；不均勻時、要嘛留 single-node PG（垂直擴 + read replica）、要嘛重新設計 distribution column（如多租戶用 composite 或對 hot tenant 特殊處理）。

### 大量跨 shard query / 非 co-located JOIN

application query 大多不帶 distribution column filter、或常做跨 distribution column 的 JOIN、每個 query fan-out 到所有 worker + shuffle、latency 與成本都差。徵兆是 `EXPLAIN` 顯示 query 打所有 worker、p99 latency 高。修法是重新設計 schema 讓常一起查的表 co-located、把 distribution column 放進熱 query 的 filter；改不動時、這個 workload 可能不適合 scale-out PG、回 single-node 或考慮其他方案。

### 該用 NoSQL 卻選了分散式 PG（或反之）

document / KV、固定 access pattern、不需要 JOIN 的 workload 選了 Cosmos DB for PostgreSQL、付了 SQL / distribution column 設計的複雜度卻沒用到關聯能力 — 這類 workload 核心 Cosmos DB（NoSQL）更自然。反過來、SQL / JOIN / 交易重的 workload 被推去核心 Cosmos DB（NoSQL）要重寫成 document model 也是錯。修法是回到「workload 是 SQL 範式還是 document / KV 範式」的根本判斷、見本文選型判準段與 [mongodb-api-vs-sql-api](../mongodb-api-vs-sql-api/) 的範式判讀。

### Anti-recommendation：single-node PG 沒到上限不要上

分散式 PostgreSQL 帶來 distribution column 設計、co-location 規劃、跨 shard query 成本、rebalance 運維。single-node managed PostgreSQL 加 vertical scaling 與 read replica 能撐的 OLTP baseline 比多數團隊以為的大。沒有觸及 single-node 真實上限（write throughput 飽和、單表大到 maintenance 困難、資料量超出單機）就上分散式、是用複雜度換不存在的容量需求。

## 容量與觀測

- 必看 metric：各 worker node 的 CPU / IO / 連線（找 hot worker）、shard 在 worker 間的分布均勻度、跨 shard query 比例、coordinator 連線數
- 容量單位：node 規格（不是 RU/s）— 規劃是 coordinator + N worker 的 vCPU / memory / storage、跟核心 Cosmos DB 的 RU 思維完全不同、不要混用 [ru-cost-model-sizing](../ru-cost-model-sizing/) 的 RU 模型來估這個服務
- distribution column 均勻度是容量上限的真實決定因素 — 跟 [Hot Partition](/backend/knowledge-cards/hot-partition/) 同模型、hot worker 讓名義叢集容量達不到
- 回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)：scale-out 的有效容量 = node 數 × 單 node 容量 × distribution 均勻度
- Alert：單一 worker 飽和（distribution skew）、跨 shard query 比例上升、rebalance 後仍不均

## 邊界與整合

- 定位釐清：本服務是 *分散式 PostgreSQL*、不是核心 Cosmos DB（NoSQL）— 共用品牌名稱、產品不同、選型不要混淆
- 跟核心 Cosmos DB 的分界：SQL / JOIN / 交易 + 到單機上限 → 本服務；document / KV / multi-model / multi-region active-active → 核心 Cosmos DB、見 [mongodb-api-vs-sql-api](../mongodb-api-vs-sql-api/)
- 跟 PostgreSQL vendor 的分界：single-node 沒到上限 → [Azure Database for PostgreSQL / 一般 PG](/backend/01-database/vendors/postgresql/)；PostgreSQL 既有的 [Specialized PostgreSQL Variants](/backend/01-database/vendors/postgresql/specialized-pg-variants/) 段已把 Cosmos DB for PostgreSQL 列為 Citus-based 變體之一
- 跟其他 distributed SQL：[Spanner](/backend/01-database/vendors/spanner/)（全球強一致）、[CockroachDB](/backend/01-database/vendors/cockroachdb/)（跨雲、自動 range）— 本服務強在真 PostgreSQL engine + co-location 控制、弱在需 distribution column 設計 + 綁 Azure
- distribution column 不可改：跟 [partition-key-design](../partition-key-design/) 的 partition key 不可改是同類不可逆設計
- Knowledge card：[distributed SQL](/backend/knowledge-cards/distributed-sql/) / [Hot Partition](/backend/knowledge-cards/hot-partition/)

## 相關連結

- [Cosmos DB vendor overview](/backend/01-database/vendors/cosmosdb/) — 本文是該頁尾 Cosmos DB for PostgreSQL backlog 的深度展開
- [mongodb-api-vs-sql-api](../mongodb-api-vs-sql-api/) — SQL 範式 vs document / KV 範式的根本判讀
- [PostgreSQL vendor](/backend/01-database/vendors/postgresql/) / [Specialized PostgreSQL Variants](/backend/01-database/vendors/postgresql/specialized-pg-variants/) — single-node PG 與 Citus 變體定位
- [Spanner vendor](/backend/01-database/vendors/spanner/) / [CockroachDB vendor](/backend/01-database/vendors/cockroachdb/) — 其他 distributed SQL 對照
- [partition-key-design](../partition-key-design/) — distribution column 不可改的同類設計
- [Distributed SQL 卡片](/backend/knowledge-cards/distributed-sql/) / [Hot Partition 卡片](/backend/knowledge-cards/hot-partition/) — 概念基底
- 官方：[Azure Cosmos DB for PostgreSQL](https://learn.microsoft.com/azure/cosmos-db/postgresql/) / [Citus distributed tables](https://learn.microsoft.com/azure/cosmos-db/postgresql/concepts-distributed-data)
