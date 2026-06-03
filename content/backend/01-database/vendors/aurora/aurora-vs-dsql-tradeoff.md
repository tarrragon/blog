---
title: "Aurora PG/MySQL vs Aurora DSQL 取捨：何時 single-region managed 夠用、何時跨到 distributed"
date: 2026-06-02
description: "Aurora DSQL 不是 Aurora 的升級版而是不同 paradigm；本文聚焦『standard Aurora（single-region managed SQL）什麼時候夠用、什麼時候需要跨到 active-active distributed』的升級門檻決策，切分『怎麼遷』（migrate-to-aurora-dsql）與『DSQL vs Spanner vs CockroachDB 三方選型』（decision-tree）兩個既有 SSoT"
weight: 34
tags: ["backend", "database", "aurora", "aurora-dsql", "distributed-sql", "decision", "deep-article"]
---

> 本文是 Aurora family 內的決策取捨文章。聚焦 *standard Aurora（Aurora PostgreSQL / MySQL，single-region managed SQL）* 跟 *Aurora DSQL（active-active distributed SQL）* 之間的升級門檻判斷。兩個既有 SSoT 不在本篇重複：「PG → DSQL 怎麼遷」見 [migrate-to-aurora-dsql](/backend/01-database/vendors/postgresql/migrate-to-aurora-dsql/)；「DSQL vs Spanner vs CockroachDB 三方 distributed SQL 選型」見 [aurora-dsql-spanner-decision-tree](/backend/01-database/vendors/cockroachdb/aurora-dsql-spanner-decision-tree/)。本篇只回答「standard Aurora 夠不夠、要不要跨過去」。

多數團隊不需要 Aurora DSQL。Aurora PostgreSQL / MySQL 已經是 managed SQL、storage / compute 分離、跨 AZ 高可用、read replica 擴讀——絕大多數 OLTP workload 在這層就解決了。Aurora DSQL 是 2024-12 re:Invent preview、2025-05 GA 的 *不同 paradigm* 產品：PG wire-compatible 但底層是 active-active distributed、OCC + snapshot isolation、multi-region strong consistency。它解的是 standard Aurora *解不了* 的特定問題，代價是放棄一部分 PostgreSQL 相容性與交易自由度。要不要跨過去，看 workload 是否真的撞到 standard Aurora 的結構上限。

> **時間錨點**：Aurora DSQL 2024-12 preview、2025-05 GA。vendor 能力持續演進、實際決策前以 AWS docs 當前狀態為準。

## 核心差異：single-writer vs active-active

兩者的根本差異在寫入架構：

| 維度     | Aurora PG / MySQL（standard）            | Aurora DSQL                                 |
| -------- | ---------------------------------------- | ------------------------------------------- |
| 寫入架構 | single writer（一個 region 一個 writer） | active-active（多 region 同時可寫）         |
| 一致性   | 單 region 強一致、跨 region 非同步       | multi-region strong consistency             |
| SQL 相容 | 完整 PostgreSQL / MySQL                  | PG wire-compatible *子集*、無多數 extension |
| 交易模型 | 標準 PG/MySQL transaction、長交易        | OCC + snapshot isolation、需處理 retry      |
| 寫入擴展 | 受 single writer instance 上限約束       | 水平擴展、無 single writer 瓶頸             |
| 運維     | managed、但仍要管 instance / failover    | serverless、zero-touch、無 instance 概念    |

standard Aurora 的 storage 層雖然分散，*compute 寫入仍是 single writer*——這是它的結構上限。DSQL 把寫入也分散，代價是 SQL 相容性縮窄（PG 子集、extension 缺位）與交易語意改變（OCC，衝突要 application retry）。

## 該跨到 DSQL 的訊號

只有撞到 standard Aurora 結構上限的特定需求，才值得跨 paradigm：

- **global write（多 region 都要低延遲寫入）**：standard Aurora 跨 region 只有非同步副本、寫入要回到單一 writer region；真正需要多 region active-active 寫入 → DSQL
- **single-writer 寫入上限撞牆**：寫入量大到單一 writer instance（即使最大 instance class）撐不住、且無法用 sharding 簡單解 → DSQL 的水平寫入擴展
- **region resiliency（單 region 失效仍要可寫）**：standard Aurora 的跨 region failover 有 RPO/RTO 與寫入中斷；要求單 region 失效時其他 region 仍持續接受寫入 → DSQL active-active
- **operational zero-touch**：不想管 instance / failover / 容量 → DSQL serverless 模型（但這單項不足以跨 paradigm、要搭配上面的結構需求）

## 不該跨的訊號（standard Aurora 夠用）

以下情況跨 DSQL 是過度工程、且會付出相容性代價：

- **single-region 夠用**：寫入集中在一個 region、跨 region 只需要讀副本或 DR → standard Aurora
- **需要 PostgreSQL extension**：依賴 PostGIS / pgvector / 特定 extension → DSQL 子集不支援、留 standard Aurora
- **複雜 / 長交易**：依賴長交易、複雜多語句交易、特定 isolation 行為 → standard Aurora 的完整交易模型
- **寫入量 standard Aurora 撐得住**：single writer 還有餘量 → 不必為「未來可能」預先跨 paradigm

`9.C14 Standard Chartered` 與 `9.C4 DraftKings` 是反向佐證：金融帳本 / 博彩這類高一致性、高關鍵 OLTP workload，在 *standard Aurora* 上就能同時拿到韌性與性能（DraftKings replication lag 降到 10-30ms 級、Standard Chartered 把韌性與性能當單一目標）。它們沒有跨到 distributed SQL——因為 single-region 強一致 + 跨 AZ 高可用已滿足需求。多數金融 OLTP 不需要 active-active multi-region write。

> **Scope warning**：Standard Chartered / DraftKings 的 case 揭露其用 standard Aurora 達成韌性 + 性能（見 [storage-architecture](/backend/01-database/vendors/aurora/storage-architecture/)）；「它們不需要 DSQL」是本文基於其 single-region 強一致需求的推論、非 case 明文比較 DSQL。引用為「standard Aurora 已足夠多數高一致 OLTP」的訊號、不當 DSQL 對比的 case fact。

## 升級門檻決策流程

從需求判讀到路徑選擇的流程：

#### Step 1：確認是不是 global write 需求

寫入是否真的需要多 region 同時低延遲？還是只需要多 region 讀 + 單 region 寫？後者 standard Aurora（+ Global Database 讀副本）就解。

#### Step 2：確認 single-writer 是否真的撞牆

當前寫入量 vs 最大 instance class 上限、是否已嘗試過 read/write 分離、是否能用 application 層 sharding。撞牆才考慮 DSQL；沒撞牆是過早優化。

#### Step 3：檢查相容性代價

清點對 PG extension、長交易、特定 SQL 功能的依賴。依賴重 → DSQL 相容性子集會擋路、留 standard Aurora。

#### Step 4：若決定跨，走既有 SSoT

- 「PG → DSQL 怎麼遷」（protocol drop-in + paradigm shift、transaction retry 處理、extension 缺位）→ [migrate-to-aurora-dsql](/backend/01-database/vendors/postgresql/migrate-to-aurora-dsql/)
- 「DSQL vs Spanner vs CockroachDB 哪個 distributed SQL」→ [aurora-dsql-spanner-decision-tree](/backend/01-database/vendors/cockroachdb/aurora-dsql-spanner-decision-tree/)

**Rollback boundary**：跨 paradigm 是高成本決策——DSQL 子集相容性與 OCC 交易模型改變了 application 契約，回退到 standard Aurora 不是改 connection string 就好。決策前用一個非關鍵 workload 試點、確認相容性與 retry 行為，再擴大。

## 邊界與整合

### 為什麼這是「升級門檻」而非「遷移」

standard Aurora → DSQL 不是版本升級、是 paradigm 切換。Aurora PG/MySQL 用得好好的，不代表「升級到 DSQL 會更好」——多數情況會更差（失去 extension、交易要改、相容性縮窄）。只有 workload 真的需要 active-active multi-region write 或撞到 single-writer 上限，跨過去才划算。這跟「PostgreSQL major version upgrade」（同 paradigm、向後相容）是完全不同性質的決策。

### Sibling 與 cross-link

- [storage-architecture](/backend/01-database/vendors/aurora/storage-architecture/) — standard Aurora 的 storage 分散但 compute single-writer 的結構上限根源
- [global-database-multi-region](/backend/01-database/vendors/aurora/global-database-multi-region/) — standard Aurora 的多 region 方案（非同步副本）、global write 需求前先確認這層夠不夠
- [migrate-to-aurora-dsql](/backend/01-database/vendors/postgresql/migrate-to-aurora-dsql/) — 決定跨之後的遷移 playbook（SSoT）
- [aurora-dsql-spanner-decision-tree](/backend/01-database/vendors/cockroachdb/aurora-dsql-spanner-decision-tree/) — 三方 distributed SQL 選型（SSoT）
- 替代路由：single-region 夠 → 留 standard Aurora；KV access pattern → [DynamoDB](/backend/01-database/vendors/dynamodb/)
- 跟 [Standard Chartered 9.C14](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) / [DraftKings 9.C4](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 互引：高一致 OLTP 在 standard Aurora 已足夠的訊號
