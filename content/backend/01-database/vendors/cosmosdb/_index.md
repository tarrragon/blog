---
title: "Azure Cosmos DB"
date: 2026-05-13
description: "全球分散式 multi-model DB、5 個 consistency levels、Microsoft 自家 dogfood 證據"
weight: 9
tags: ["backend", "database", "vendor", "cosmosdb", "multi-model", "global"]
---

Azure Cosmos DB 是 Microsoft 全球分散式 multi-model database、提供 SQL / MongoDB / Cassandra / Gremlin / Table 五種 API、五個 consistency levels、自動 multi-region write。Microsoft 自家 Microsoft 365 用它做 analytics、ASOS 在 Black Friday 撐 1.67 億請求 24 小時、Minecraft Earth 測試 1M RU/s — 是 Azure 上 NoSQL / Document 工作負載的旗艦。

## 教學路線：Multi-model API 與全球寫入

Cosmos DB 服務頁的教學目標是把 API model、consistency level、RU/s、logical partition 與 multi-region write 放在同一個 Azure 服務決策中。讀者讀完後要能判斷 Cosmos DB 是遷移相容層、全球 NoSQL 平台，還是特定 Azure workload 的容量抽象。

| 學習段            | 核心問題                                                        | 對應段落                                                                       |
| ----------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| API model         | SQL API、MongoDB API、Cassandra API 各自服務哪種遷移或資料形狀  | 定位、跟其他 vendor 的取捨                                                     |
| Consistency level | session、bounded staleness、strong consistency 如何改變產品語意 | 容量規劃要點、[Consistency Level](/backend/knowledge-cards/consistency-level/) |
| RU/s capacity     | request unit 如何把 query、index、payload 轉成成本與節流        | 容量特性、案例對照                                                             |
| Global write      | multi-region write 何時值得承擔衝突與一致性成本                 | 適用場景、案例對照                                                             |
| 替代路由          | 何時用 MongoDB、DynamoDB、Spanner、PostgreSQL 或 analytics      | 不適用場景、下一步路由                                                         |

## 定位：multi-model + multi-region write

Cosmos DB 跟其他 DB 最大差異是 *multi-model*。一個服務同時支援 5 種 API、每個 API 對應不同資料模型。應用層選擇用哪個 API、底層是同一個分散式 KV store。

**5 個 API**：

- **SQL API**：document（JSON）+ SQL-like query、Cosmos DB native
- **MongoDB API**：wire-protocol 相容 MongoDB
- **Cassandra API**：wire-protocol 相容 Cassandra
- **Gremlin API**：graph database
- **Table API**：簡單 KV（Azure Table Storage 升級版）

**5 個 consistency levels**（從強到弱）：

1. **Strong**：在支援的 account / region 配置內提供最強一致性，通常帶來最高 latency
2. **Bounded staleness**：訂版本 / 時間差異上限
3. **Session**：同 session 內強一致（最常用）
4. **Consistent prefix**：保證寫入順序
5. **Eventual**：最便宜、最終一致

**容量特性**：

- 容量單位：RU/s（Request Unit per second）— 把 read / write / query 統一抽象
- 1 RU = strongly consistent read of 1KB document
- 配置擴容延遲：99 百分位 5 秒內生效
- 每個 logical partition 上限：10,000 RU/s
- 測試最高：1,000,000 RU/s（[Minecraft Earth 案例](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/)）

## 適用場景

**1. Azure 生態的 multi-model 需求**：

- 同一服務多種 use case（document、graph、KV 共存）
- 想把多個 NoSQL 資料模型集中在 Azure 服務邊界內治理
- 對應案例：[9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — Microsoft 自家用 Cosmos DB 撐分析平台

**2. 全球零售 + 季節性高峰**：

- multi-region write 讓全球用戶寫入本地 region
- 對應案例：[9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) — Black Friday 24 小時 1.67 億請求、3500 RPS 峰值、48ms 平均延遲

**3. 全球分散式遊戲後端**：

- AR / 即時遊戲跨地區同步
- session consistency 對遊戲足夠、不需 strong
- 對應案例：[9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) — AR 遊戲玩家位置、跨 region 寫入

**4. MongoDB 應用想要 *managed + 全球分散***：

- Cosmos DB MongoDB API wire protocol compatible
- 應用層主要驗證相容差異，底層改成分散式架構
- 對應案例：[9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — MongoDB → Cosmos DB MongoDB API、planet-scale 分析

**5. 想用 multi-region active-active write**：

- 不像 Spanner / Aurora DSQL 是 PC 系統、Cosmos DB 是 AP 系統
- 用 LWW（Last-Writer-Wins）或 stored procedure 處理 conflict
- 適合可接受 eventual / session consistency 的 multi-region write workload；需要 global SQL linearizability 時轉 Spanner / Aurora DSQL

## 不適用場景

**1. 跨雲需求**：

- Cosmos DB only on Azure
- 替代：MongoDB Atlas（cross-cloud）、CockroachDB（自管）

**2. Linearizable 全球 OLTP**：

- Cosmos DB Strong consistency 的適用範圍要按 account / region 配置判讀；全球 linearizable SQL 需求通常轉 Spanner / Aurora DSQL
- 替代：Spanner / Aurora DSQL（真正全球 linearizable）

**3. 預算極敏感的小 workload**：

- 最低 400 RU/s（約 $25/month）
- 小流量場景、Azure SQL Database 更便宜

**4. 純 OLAP 分析**：

- Cosmos DB 定位在 OLTP / document，analytics workload 交給 Synapse、BigQuery 或 Snowflake
- 替代：Azure Synapse、BigQuery、Snowflake

**5. 嚴格 ACID 跨 partition transaction**：

- Cosmos DB Transaction 限 same logical partition
- 跨 partition 的 multi-row transaction 要改用 workflow、stored procedure 邊界或 distributed SQL
- 替代：Spanner / Aurora DSQL

## 跟其他 vendor 的取捨

**vs DynamoDB（AWS）**：

- Cosmos DB：multi-model（5 API）、5 consistency levels、multi-region write
- DynamoDB：KV 為主、strong / eventual consistency、Global Tables 以 LWW 處理 multi-region conflict
- 選 Cosmos DB：Azure 生態、需要 multi-model、需要 consistency 細粒度控制
- 選 DynamoDB：AWS 生態、純 KV、AWS-native 整合（Lambda、Streams）

**vs Spanner（GCP）**：

- Cosmos DB：AP 系統、5 consistency levels、multi-model
- Spanner：CP 系統、external consistency、SQL only
- 選 Cosmos DB：可接受 eventual / session、需要 multi-model
- 選 Spanner：需要 [linearizability](/backend/knowledge-cards/linearizability/) 與 SQL workload

**vs MongoDB Atlas**：

- Cosmos DB MongoDB API：Azure-only、managed、global 強
- MongoDB Atlas：跨雲（AWS / GCP / Azure）、原生 MongoDB 行為
- 選 Cosmos DB：已在 Azure、想要更好 global distribution
- 選 MongoDB Atlas：跨雲、需要 MongoDB 完整功能（aggregation pipeline 等 native 行為）

**vs Cassandra / ScyllaDB**：

- Cosmos DB Cassandra API：managed Azure
- Cassandra / ScyllaDB：自管、跨雲
- 選 Cosmos DB：Azure 生態、想把 operation 交給 managed service
- 選 Cassandra：跨雲、自管、極限 throughput tuning

**vs Azure SQL Hyperscale**：

- Cosmos DB：NoSQL / document、global 分散
- Azure SQL Hyperscale：傳統 SQL OLTP、storage / compute 分離、AWS Aurora 對應
- 選 Cosmos DB：document model、global 分散
- 選 Azure SQL：SQL workload、應用已用 SQL Server
- 對應 [9.C32 Clearent Azure SQL Hyperscale](/backend/09-performance-capacity/cases/clearent-azure-sql-hyperscale-payments/) — SQL 工作負載選 Hyperscale，document / NoSQL workload 才進 Cosmos DB

**vs PostgreSQL（SQL baseline）**：

- PostgreSQL：SQL、強一致、single-primary、跨雲可用
- Cosmos DB：NoSQL / multi-model、AP 系統、Azure-only、global 分散
- 選 PostgreSQL：SQL workload、跨雲、需要進階 SQL 特性
- 選 Cosmos DB：Azure 生態、document / KV / multi-model、需要 global distribution

**vs Aurora（AWS managed SQL）**：

- Aurora：AWS、SQL（PostgreSQL / MySQL）、single-region scaling
- Cosmos DB：Azure、NoSQL / multi-model、global write
- 兩者分別站在 cloud provider 與 data model 兩個維度；同需求下通常先看既有雲平台（AWS → Aurora、Azure → Cosmos / Azure SQL）

**vs CockroachDB（cross-cloud distributed SQL）**：

- CockroachDB：跨雲、PostgreSQL wire、distributed SQL、強一致
- Cosmos DB：Azure-only、multi-model、5 consistency levels、AP 系統
- 選 CockroachDB：要 SQL + 跨雲 + 強一致
- 選 Cosmos DB：要 NoSQL + Azure 生態 + 細粒度 consistency 選擇

## 容量規劃要點

**1. RU/s 抽象化把 read / write / query 統一**：

- 不像 DynamoDB 拆 RCU / WCU、Cosmos DB 用單一 RU
- 簡化容量規劃、但要算「不同操作各吃多少 RU」
- 1 RU = 1 KB strong read、寫 ~5 RU、複雜 query 數百 RU

**2. partition key 設計跟 DynamoDB 一樣關鍵**：

- 每個 logical partition 上限 10,000 RU/s
- partition key 不均 → hot partition
- 對應 [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) — synthetic partition key 強制分散
- 詳見 [Hot Partition 卡片](/backend/knowledge-cards/hot-partition/)

**3. multi-region 配置**：

- 開啟跨 region 後、容量在每個 region 都 mirror、成本乘以 region 數
- 對應 [9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) — 跟 DynamoDB Global Tables 同類思維、各 region 獨立容量

**4. Consistency level 影響成本**：

- Strong consistency：跨 region quorum、單個 read 約 2x RU
- Session：cost 跟 eventual 接近、但提供同 session 一致
- Eventual：最便宜

**5. Autoscale provisioned throughput**：

- 訂 max RU/s、實際用多少算多少（10% min）
- 適合：流量 unpredictable、想降低 on-demand 成本治理負擔

**6. Serverless mode**：

- 按 request 計費，適合稀疏與小流量 workload
- 適合：dev / test、小流量、稀疏 workload

## 預計實作話題（後續擴充）

- 5 個 consistency levels 的工程選擇邏輯
- partition key 設計（synthetic、composite、hierarchical）
- Multi-region write 跟 conflict resolution
- Change Feed（CDC）整合
- Stored procedure / trigger（JavaScript）
- MongoDB API vs native SQL API trade-off
- 從 MongoDB / Cassandra 遷到 Cosmos DB
- Cosmos DB for PostgreSQL（2022 新增、不同產品）
- 跟 Azure Synapse Link 整合（OLTP / OLAP [federation](/backend/knowledge-cards/federation/)）

## Anti-recommendation 與升級路由

Cosmos DB 的 multi-model 能把遷移阻力降到很低，也會讓 API compatibility、RU/s、partition key 與 consistency level 同時變成設計責任。這一段先說何時維持單一 API model，再說何時升級 multi-region write、Synapse Link、MongoDB Atlas、Spanner 或 Azure SQL。

| 機制 / 路線           | 維持簡單設計的條件                                  | 升級訊號                                                           | 主要引用路徑                                                                                                                   |
| --------------------- | --------------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| 單一 API model        | document / MongoDB / Cassandra / Table 語意清楚分工 | 多 API 共用同一資料語意、相容層行為差異開始影響 production         | [MongoDB vendor](/backend/01-database/vendors/mongodb/)、[Database](/backend/knowledge-cards/database/)                        |
| Session consistency   | user session 內讀寫一致已滿足產品需求               | 金融 / 庫存 / 票務需要更強順序承諾                                 | [Consistency Level](/backend/knowledge-cards/consistency-level/)、[Linearizability](/backend/knowledge-cards/linearizability/) |
| Provisioned RU/s      | 流量可預測、partition key 均勻                      | Black Friday、遊戲上線、全球事件帶來突發尖峰                       | [Hot Partition](/backend/knowledge-cards/hot-partition/)、[Peak Forecast](/backend/knowledge-cards/peak-forecast/)             |
| Multi-region write    | single-region write + global read 已足夠            | regional write latency、region residency、active-active 是產品需求 | [RPO](/backend/knowledge-cards/rpo/)、[RTO](/backend/knowledge-cards/rto/)、[Stale Read](/backend/knowledge-cards/stale-read/) |
| MongoDB Atlas         | Azure global distribution 是主訴求                  | 跨雲、原生 MongoDB 行為、Atlas ecosystem 是主訴求                  | [MongoDB vendor](/backend/01-database/vendors/mongodb/)                                                                        |
| Spanner / CockroachDB | session / eventual consistency 可接受               | global SQL、strong transaction、cross-partition ACID 是核心需求    | [Spanner vendor](/backend/01-database/vendors/spanner/)、[CockroachDB vendor](/backend/01-database/vendors/cockroachdb/)       |
| Azure SQL Hyperscale  | document / NoSQL 是主要資料形狀                     | JOIN-heavy、transaction-heavy、SQL Server 生態是主需求             | [Aurora vendor](/backend/01-database/vendors/aurora/)                                                                          |

Cosmos DB 的簡單路徑是先固定 API model 與 consistency level。每個 API 的相容範圍、index 行為與 query cost 都不同；單純因為「同一服務支援多模型」而混用 API，後續 migration、debug 與容量估算會變複雜。

RU/s 的升級路徑要把 partition key 與 query shape 放在同一張圖。單純提高 RU/s 只能提高名義容量；logical partition 熱點、跨 partition query、index policy 與 payload size 仍會決定真實成本。

## 已知 limitation 與後續路由

Cosmos DB overview 目前完成 Azure global NoSQL 判斷。下一輪 deep article / playbook 應補 consistency level 選擇、RU/s cost model、partition key design、multi-region conflict、Change Feed、MongoDB API migration、Cassandra API migration 與 Synapse Link。

## 案例對照

| 案例                                                                                              | 規模                                      | 教學重點                                                        |
| ------------------------------------------------------------------------------------------------- | ----------------------------------------- | --------------------------------------------------------------- |
| [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) | 1M RU/s 測試、turnkey global distribution | AR 遊戲全球分散                                                 |
| [9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/)                 | 1.67 億 req / 24h、48ms p99               | 全球零售 Black Friday                                           |
| [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/)  | planet-scale analytics                    | MongoDB → Cosmos DB API-compatible 遷移、Microsoft 自家 dogfood |

Cosmos DB case 的讀法是分開看三種壓力：Minecraft Earth 提供 global partition 與 RU/s 訊號，ASOS 提供季節性零售尖峰訊號，Microsoft 365 提供 MongoDB API 相容遷移與 Azure dogfood 訊號。

## 反向 sibling 路由

Cosmos DB 的反向 sibling 路由用來把 Azure global NoSQL、DynamoDB 與 document migration 分開。若讀者從 DynamoDB 過來，先比較 RU/s、partition key、multi-region conflict 與 API model；若讀者從 MongoDB 過來，先把 API compatibility 當 migration hypothesis，再用 aggregation、index、change stream / Change Feed 行為驗證；若需求其實是 SQL strong consistency，轉到 [Spanner vendor](/backend/01-database/vendors/spanner/) 或 [CockroachDB vendor](/backend/01-database/vendors/cockroachdb/)。

這條路由的判準是 API model 是否已固定。Cosmos DB 的 multi-model 是產品入口，不代表同一套資料可以在多個 API 之間自由切換；partition key、index policy、RU/s 與 consistency level 一旦進 production，就會成為 migration 與成本邊界。

## 常見陷阱

- **Strong consistency 用太多**：多數互動式業務用 session consistency 就能滿足讀寫體驗
- **partition key 只用 user_id**：某些業務 user 集中（VIP、bot）會 hot
- **忽略 Change Feed**：寫入後通知、投影與同步流程適合先評估 Change Feed
- **MongoDB API behavior 假設**：API compat 仍要驗證 aggregation pipeline / index 行為
- **忽略 multi-region 成本乘數**：開 3 region active-active = 3 倍 RU 成本

## 下一步路由

- 完整 T1 對照：[01-database vendors index](/backend/01-database/vendors/)
- 平行：[DynamoDB vendor](/backend/01-database/vendors/dynamodb/)、[Spanner vendor](/backend/01-database/vendors/spanner/)、[MongoDB vendor](/backend/01-database/vendors/mongodb/)
- 上游：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) / [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)
- 下游：[1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)（MongoDB → Cosmos 範例）
- 跨模組：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)
- Last reviewed：2026-05-22（API compatibility / consistency / RU model 屬時間敏感 claim）
- 官方：[Azure Cosmos DB](https://azure.microsoft.com/products/cosmos-db/)、[Cosmos DB consistency levels](https://learn.microsoft.com/azure/cosmos-db/consistency-levels)
