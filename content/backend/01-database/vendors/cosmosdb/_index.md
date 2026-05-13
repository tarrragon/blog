---
title: "Azure Cosmos DB"
date: 2026-05-13
description: "全球分散式 multi-model DB、5 個 [consistency level](/backend/knowledge-cards/consistency-level/)s、Microsoft 自家 dogfood 證據"
weight: 9
tags: ["backend", "database", "vendor", "cosmosdb", "multi-model", "global"]
---

Azure Cosmos DB 是 Microsoft 全球分散式 multi-model database、提供 SQL / MongoDB / Cassandra / Gremlin / Table 五種 API、五個 consistency levels、自動 multi-region write。Microsoft 自家 Microsoft 365 用它做 analytics、ASOS 在 Black Friday 撐 1.67 億請求 24 小時、Minecraft Earth 測試 1M RU/s — 是 Azure 上 NoSQL / Document 工作負載的旗艦。

## 定位：multi-model + multi-region write

Cosmos DB 跟其他 DB 最大差異是 *multi-model*。一個服務同時支援 5 種 API、每個 API 對應不同資料模型。應用層選擇用哪個 API、底層是同一個分散式 KV store。

**5 個 API**：

- **SQL API**：document（JSON）+ SQL-like query、Cosmos DB native
- **MongoDB API**：wire-protocol 相容 MongoDB
- **Cassandra API**：wire-protocol 相容 Cassandra
- **Gremlin API**：graph database
- **Table API**：簡單 KV（Azure Table Storage 升級版）

**5 個 consistency levels**（從強到弱）：

1. **Strong**：linearizable、跨 region [quorum](/backend/knowledge-cards/quorum/)、最高 latency
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
- 不想管多個 DB vendor
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
- 應用層幾乎不必改、底層改成分散式架構
- 對應案例：[9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — MongoDB → Cosmos DB MongoDB API、planet-scale 分析

**5. 想用 multi-region active-active write**：

- 不像 Spanner / Aurora DSQL 是 PC 系統、Cosmos DB 是 AP 系統
- 用 LWW（Last-Writer-Wins）或 stored procedure 處理 conflict
- 不保證 [linearizability](/backend/knowledge-cards/linearizability/)、可接受 eventual / session consistency

## 不適用場景

**1. 跨雲需求**：

- Cosmos DB only on Azure
- 替代：MongoDB Atlas（cross-cloud）、CockroachDB（自管）

**2. Linearizable 全球 OLTP**：

- Cosmos DB Strong consistency 是 *線性化 within region*、跨 region 不是 linearizable
- 替代：Spanner / Aurora DSQL（真正全球 linearizable）

**3. 預算極敏感的小 workload**：

- 最低 400 RU/s（約 $25/month）
- 小流量場景、Azure SQL Database 更便宜

**4. 純 OLAP 分析**：

- Cosmos DB 是 OLTP / document、不是 OLAP
- 替代：Azure Synapse、BigQuery、Snowflake

**5. 嚴格 ACID 跨 partition transaction**：

- Cosmos DB Transaction 限 same logical partition
- 跨 partition 的 multi-row transaction 不支援
- 替代：Spanner / Aurora DSQL

## 跟其他 vendor 的取捨

**vs DynamoDB（AWS）**：

- Cosmos DB：multi-model（5 API）、5 consistency levels、multi-region write
- DynamoDB：KV only、binary consistency（strong / eventual）、Global Tables（multi-region write 但只是 LWW）
- 選 Cosmos DB：Azure 生態、需要 multi-model、需要 consistency 細粒度控制
- 選 DynamoDB：AWS 生態、純 KV、AWS-native 整合（Lambda、Streams）

**vs Spanner（GCP）**：

- Cosmos DB：AP 系統、5 consistency levels、multi-model
- Spanner：CP 系統、external consistency、SQL only
- 選 Cosmos DB：可接受 eventual / session、需要 multi-model
- 選 Spanner：必須 linearizable、SQL workload

**vs MongoDB Atlas**：

- Cosmos DB MongoDB API：Azure-only、managed、global 強
- MongoDB Atlas：跨雲（AWS / GCP / Azure）、原生 MongoDB 行為
- 選 Cosmos DB：已在 Azure、想要更好 global distribution
- 選 MongoDB Atlas：跨雲、需要 MongoDB 完整功能（aggregation pipeline 等 native 行為）

**vs Cassandra / ScyllaDB**：

- Cosmos DB Cassandra API：managed Azure
- Cassandra / ScyllaDB：自管、跨雲
- 選 Cosmos DB：Azure 生態、想 zero ops
- 選 Cassandra：跨雲、自管、極限 throughput tuning

**vs Azure SQL Hyperscale**：

- Cosmos DB：NoSQL / document、global 分散
- Azure SQL Hyperscale：傳統 SQL OLTP、storage / compute 分離、AWS Aurora 對應
- 選 Cosmos DB：document model、global 分散
- 選 Azure SQL：SQL workload、應用已用 SQL Server
- 對應 [9.C32 Clearent Azure SQL Hyperscale](/backend/09-performance-capacity/cases/clearent-azure-sql-hyperscale-payments/) — SQL 工作負載選 Hyperscale 不是 Cosmos

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
- 適合：流量 unpredictable、不想 manage on-demand 成本

**6. Serverless mode**：

- 完全 on-demand、按 request 計費
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

## 案例對照

| 案例                                                                                              | 規模                                      | 教學重點                                                        |
| ------------------------------------------------------------------------------------------------- | ----------------------------------------- | --------------------------------------------------------------- |
| [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) | 1M RU/s 測試、turnkey global distribution | AR 遊戲全球分散                                                 |
| [9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/)                 | 1.67 億 req / 24h、48ms p99               | 全球零售 Black Friday                                           |
| [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/)  | planet-scale analytics                    | MongoDB → Cosmos DB API-compatible 遷移、Microsoft 自家 dogfood |

## 常見陷阱

- **Strong consistency 用太多**：90% 業務用 session 就夠、不必每個讀都 strong
- **partition key 只用 user_id**：某些業務 user 集中（VIP、bot）會 hot
- **不用 Change Feed**：寫入 + 通知都自己寫、應該 leverage Change Feed
- **MongoDB API behavior 假設**：API compat 不等於行為完全相同、要驗證 aggregation pipeline / index 行為
- **忽略 multi-region 成本乘數**：開 3 region active-active = 3 倍 RU 成本

## 下一步路由

- 平行：[DynamoDB vendor](/backend/01-database/vendors/dynamodb/)、[Spanner vendor](/backend/01-database/vendors/spanner/)、[MongoDB vendor](/backend/01-database/vendors/mongodb/)
- 上游：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) / [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)
- 下游：[1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)（MongoDB → Cosmos 範例）
- 跨模組：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)
- 官方：[Azure Cosmos DB](https://azure.microsoft.com/products/cosmos-db/)、[Cosmos DB consistency levels](https://learn.microsoft.com/azure/cosmos-db/consistency-levels)
