---
title: "1.11 全球分散式 OLTP"
date: 2026-05-13
description: "Spanner / Aurora DSQL / Cosmos DB multi-region write / CockroachDB / TiDB 的全球一致性取捨"
weight: 11
tags: ["backend", "database", "oltp", "global", "consistency"]
---

## 概念定位

全球分散式 OLTP 解決一個傳統 DB 做不到的問題：跨地理位置 *同時* 維持強一致性、低延遲、高可用性。CAP 定理過往把這視為「三選二」，但近 15 年的工程進展（Google Spanner、AWS Aurora DSQL、CockroachDB、Microsoft Cosmos DB 等）顯示「在投入 *專屬硬體* 或 *特殊演算法* 的條件下、可以同時拿到 strong consistency + global distribution + 可接受 latency」。

本章整理這類系統的工程設計、容量取捨、跟傳統 single-region OLTP 的差異。讀完後讀者能回答：什麼業務需求需要 global OLTP、跨 region quorum 的延遲代價、選 Spanner vs Aurora DSQL vs Cosmos DB 的決策依據。

跟 [1.3 Transaction Boundary](/backend/01-database/transaction-boundary/) 的關係：1.3 處理 single-region OLTP 的 transaction 設計、本章處理 multi-region OLTP 的特殊取捨。

跟 [1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) 的關係：1.10 KV 通常 eventual consistency 全球分散容易、本章處理 *強一致* 全球分散的工程挑戰。

## CAP 跟 PACELC：理論工具

選擇全球 DB 前要先理解兩個理論框架。

**CAP 定理**：分散式系統 *發生分區（network partition）* 時、必須在 Consistency 跟 Availability 二選一。

- CP 系統：強一致、partition 時拒絕服務（Spanner、Cosmos DB strong）
- AP 系統：高可用、partition 時可能回舊資料（Cassandra、DynamoDB Global Tables）

**PACELC（Daniel Abadi 提出）**：擴充 CAP、加上「沒 partition 時」的取捨。

- 沒 partition 時：Latency vs Consistency 二選一
- 結合表示：PA/EL（partition 時選 Availability、平時選 Latency）vs PC/EC（partition 時選 Consistency、平時選 Consistency）

**工程含義**：

- Spanner、Aurora DSQL、Cosmos DB strong：PC/EC — 永遠選一致、付出 latency
- Cassandra、DynamoDB Global Tables：PA/EL — 永遠選快、付出可能不一致
- Cosmos DB session：PA/EL 但對同一 session 內保持 EC — 妥協方案

選 global DB 不是「哪個最好」、是「業務需要哪一邊」。金融交易、ticketing inventory、payment ledger 通常需要 EC；社群 feed、推薦、analytics 通常 EL 夠用。

## Spanner / TrueTime 模型

[Google Cloud Spanner](https://cloud.google.com/spanner) 是目前最成熟的 global strong-consistency OLTP。

**TrueTime API**：用 GPS + 原子鐘提供「全球 *unambiguous* 時間戳」、解決分散式系統最難的問題之一 — 跨節點時序排序。

**External consistency（線性化）**：用 TrueTime 保證「全球任何節點看到的交易順序、跟 wall clock 一致」。比 CAP 的 strong consistency 更強。

**容量特性**（引自 [9.C10 Spanner 案例](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)）：

- 內部峰值 > 10 億 requests / 秒
- 線性擴展：2 nodes → 45K reads/sec、4 nodes → 90K reads/sec
- 跨地區交易延遲 100-200ms（quorum round-trip 不可壓縮）
- multi-region instance 可設定 quorum location（影響哪幾個 region 必須同意）

**容量規劃**：

- 節點數量 = 容量單位（每年 review）
- 跨 region quorum 配置決定 latency baseline
- 不能像 single-region OLTP 那樣短期擴容、需要提前 ramp

**適用場景**：

- 金融交易、ticketing inventory
- 全球客戶但需要強一致
- 不能容忍跨地區 stale read 的業務

**不適用**：

- 跨洲低延遲（沒辦法、TrueTime 也壓不下 100ms 跨洲）
- 高 throughput 但容忍 eventual consistency（Bigtable / Cassandra 更便宜）

## Aurora DSQL：AWS 的全球 strong consistency 答案

AWS 在 2024 re:Invent 推出 Aurora DSQL、是 AWS 對 Spanner 的回應。

**設計特點**（引自 [Aurora DSQL announcement](https://aws.amazon.com/blogs/database/amazon-aurora-dsql-for-global-scale-financial-transactions/)）：

- 跨 region active-active write
- 強一致性（線性化）
- PostgreSQL wire protocol compatible（應用層改動小）
- Serverless（不必管 instance）

**跟 Spanner 的差異**：

- Spanner 用 TrueTime 硬體、Aurora DSQL 用其他協議
- Aurora DSQL 跟 PostgreSQL 相容（容易遷移）、Spanner 是專屬 SQL dialect
- Aurora DSQL 較新（2024）、生態還在成長
- Spanner 服務時間長（內部 2007、外部 2017）、production 案例多

**適用場景**：

- AWS 生態用戶想要 global strong consistency
- 已用 Aurora / PostgreSQL、想擴展到 multi-region
- 應用層想保留 PostgreSQL ORM

## CockroachDB 跟 TiDB：自管選項

如果不想 vendor lock-in、或需要 on-prem 部署、選擇是 *self-managed* distributed SQL。

**CockroachDB**：

- 開源、可自管或用 Cockroach Cloud
- 跟 PostgreSQL wire protocol compatible
- 線性擴展、跨 region 部署、強一致
- 設計理念近 Spanner、但不用 TrueTime（用 HLC + Raft）

**TiDB**：

- 開源（PingCAP）、可自管或用 TiDB Cloud
- 跟 MySQL wire protocol compatible
- TiKV + TiDB 分層架構
- 中國市場大量使用、亞洲生態成熟

**選擇取捨**：

- vendor lock-in 風險 → 選 CockroachDB / TiDB
- 想 managed → 選 Spanner / Aurora DSQL
- 已用 PostgreSQL → 選 CockroachDB / Aurora DSQL（migration 容易）
- 已用 MySQL → 選 TiDB

對應案例：[9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) 從 TiDB 遷出（理由不是 TiDB 不好、是 NewSQL 必須 over-provision、KV NoSQL 對該 workload 更划算）。

## Cosmos DB multi-region write 模式

[Azure Cosmos DB](https://azure.microsoft.com/products/cosmos-db/) 提供 *五個一致性層級*、是 multi-region OLTP 最有彈性的選擇之一。

**五個 consistency level**（從強到弱）：

1. **Strong**：linearizable、跨 region quorum
2. **Bounded staleness**：訂版本 / 時間上限
3. **Session**：同 session 內強一致
4. **Consistent prefix**：保證寫入順序
5. **Eventual**：最便宜、最終一致

**Multi-region write 特色**：

- 每個 region 都能寫、不必所有寫入回主 region
- conflict resolution 用 LWW（Last-Writer-Wins）或自訂 stored procedure
- 跟 Spanner 的 strong consistency 不同 — 是 *AP 系統*、不保證 linearizability

**適用場景**：

- 全球用戶分布、想 *寫入本地 region* 減延遲
- 容忍 eventual consistency（電商商品評論、社群動態）
- 不能容忍跨 region failover 中斷

**對應案例**：

- [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) — AR 玩家位置用 session consistency、跨 region 寫入
- [9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) — Black Friday 全球用戶、Cosmos DB 跨 region 複製
- [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — 分析 platform 用 weakest acceptable consistency、最大 throughput

## 跨地理合規：法規限制下的 global OLTP

部分產業（金融、醫療、政府）有 *資料駐留* 要求 — 特定國家的資料不能離境。這跟全球分散式 OLTP 的設計有 conflict。

**典型法規**：

- 歐盟 GDPR：歐洲用戶資料應留歐
- 中國《網路安全法》、《資料安全法》：中國用戶資料留中國
- 印度資料保護法：印度金融資料留印度
- 美國各州 healthcare（HIPAA）：醫療資料規範
- 金融業：各國央行通常規定本地交易資料留本地

**設計策略**：

- *多個獨立 cluster*、每個合規區一個。不是 single global cluster。
- meta-data 可以 global（用戶 profile 摘要）、transaction 必須 local
- 跨區查詢通過 federated query 或 ETL、不是直接 join

**對應案例**：

- [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) — 7 個受監管市場、各自獨立 Aurora cluster、不能合併
- [9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) — 15 主 region + 5 衛星、按合規區分布
- [9.C32 Clearent](/backend/09-performance-capacity/cases/clearent-azure-sql-hyperscale-payments/) — 美國支付業務、Azure SQL Hyperscale + 美國 region

## 延遲代價：跨 region quorum 不可壓縮

全球 strong consistency 必須付的延遲代價來自物理。光速跑跨大西洋（紐約 ↔ 倫敦 5500 km）大約 27ms one-way、實際網路延遲 70-90ms（含路由 / 處理）。任何 strong consistency 系統都不能比這個快。

**典型跨 region quorum latency**：

- 同 region 跨 AZ：1-3ms
- 同 continent 跨 region（us-east-1 ↔ us-west-2）：50-80ms
- 跨 continent（us ↔ eu）：80-120ms
- 跨地球（us ↔ asia）：150-250ms

**工程含義**：

- SLO 訂 p99 < 50ms 跨 continent strong consistency → 不可能達成
- 必須在 SLO 設計時就接受跨 region 的物理 floor
- 業務不需要 strong consistency 的話、用 session / eventual 換 latency

**對應案例**：

- [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) — sub-ms 需求、無法跨 region、用 single-AZ cluster placement
- [9.C12 Riot Games](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) — 35ms VALORANT 延遲門檻、靠 region cluster 滿足、不靠 global DB

詳見 [Latency Budget 卡片](/backend/knowledge-cards/latency-budget/)。

## 容量規劃：跟 single-region OLTP 完全不同

全球分散式 OLTP 的容量規劃有獨特挑戰。

**容量單位**：

- Spanner：節點數
- Aurora DSQL：serverless 自動（按 ACU 計費）
- Cosmos DB：RU/s（每個 region 獨立配置）
- CockroachDB / TiDB：節點數 + storage

**規劃要點**：

- 每個 region 獨立規劃（跨 region 不能 amortize）
- quorum 配置決定哪些 region 必須同意（影響 failure domain）
- 跨 region replication lag 是 SLO 一部分
- 不能像 single-region 那樣 reactive 擴容、必須 predictive

**對應 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)**：全球 OLTP 是「不可水平擴容服務」的延伸 — 不只「單機極限」、是「跨 region 協調的物理極限」。

## 案例對照

| 案例                                                                                                                  | 教學重點                                          |
| --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)                         | 10 億 req/sec 線性擴展、TrueTime 實作             |
| [9.C11 Minecraft Earth Cosmos DB](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/)           | turnkey global distribution、5 consistency levels |
| [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/)                 | 受監管金融跨市場、必須各自獨立 cluster            |
| [9.C21 ASOS Cosmos DB](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/)                           | 全球零售 multi-region、Black Friday 持續高峰      |
| [9.C24 Genesys 99.999%](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/)                  | 跨 15 region active-active 達 5 個 9 可用性       |
| [9.C32 Clearent Azure SQL Hyperscale](/backend/09-performance-capacity/cases/clearent-azure-sql-hyperscale-payments/) | 美國支付業、storage / compute 分離擴展            |

## 下一步路由

- 上游：[1.3 Transaction Boundary](/backend/01-database/transaction-boundary/)（single-region OLTP）
- 平行：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)（KV 全球分散）
- 下游：[1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)
- 跨模組：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/slo-performance-budget/)、[0.2 State Storage Selection](/backend/00-service-selection/state-storage-selection/)、[7.11 Data Residency](/backend/07-security-data-protection/data-residency-deletion-and-evidence-chain/)

## 既建知識卡片

- [Transaction Boundary](/backend/knowledge-cards/transaction-boundary/)
- [Latency Budget](/backend/knowledge-cards/latency-budget/)
- [Universal Scalability Law](/backend/knowledge-cards/universal-scalability-law/)
- [Saturation Point](/backend/knowledge-cards/saturation-point/)
