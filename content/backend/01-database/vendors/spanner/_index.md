---
title: "Google Cloud Spanner"
date: 2026-05-13
description: "全球分散式 strong-consistency OLTP、TrueTime API、線性擴展到 10 億 req/sec"
weight: 8
tags: ["backend", "database", "vendor", "spanner", "sql", "global"]
---

Cloud Spanner 是 Google 內部 2007 年起跑、2017 年開放為 GCP 服務的 *全球分散式 SQL OLTP*。內部撐 Google Ads / Play / Search 計費、外部支援 Blockchain.com、Sharechat、ZEE5 等。它的公開案例重點是每秒 10 億請求等級、線性擴展、強一致與 global distribution 可以同時成為 OLTP 設計目標。

## 教學路線：全球強一致與 TrueTime 成本

Spanner 服務頁的教學目標是把 global strong consistency、TrueTime、Paxos、region layout 與 processing unit 連成一條產品決策線。讀者讀完後要能判斷何時需要全球一致 SQL，並理解這種能力的 latency、成本與雲平台邊界。

| 學習段             | 核心問題                                                   | 對應段落                                                                     |
| ------------------ | ---------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Global consistency | 強一致 SQL 為什麼需要時間邊界與 consensus                  | 定位、適用場景、[Linearizability](/backend/knowledge-cards/linearizability/) |
| Region layout      | instance config、leader region、replica 如何影響 latency   | 容量規劃要點、常見陷阱                                                       |
| Capacity unit      | node / processing unit 如何取代傳統 shard 心智模型         | 容量特性、案例對照                                                           |
| Use-case pressure  | billing、subscription、ticketing、金融交易何時需要 Spanner | 適用場景、案例對照                                                           |
| 替代路由           | 何時用 PostgreSQL、CockroachDB、Aurora DSQL、DynamoDB      | 不適用場景、跟其他 vendor 的取捨                                             |

## 定位：TrueTime + Paxos 的全球線性 SQL

Spanner 解決的是跨地理位置同時追求 strong consistency、linear scalability 與 global availability 的 OLTP 問題。

**關鍵設計**：

- **TrueTime API**：用 GPS + 原子鐘提供「全球 unambiguous 時間戳」、誤差 < 7ms
- **External consistency**（線性化）：跨節點交易順序跟 wall clock 一致
- **Paxos-based replication**：跨 zone / region [quorum](/backend/knowledge-cards/quorum/)
- **線性擴展**：2 nodes → 45K reads/sec、4 nodes → 90K reads/sec、依此類推

**容量特性**（引自 [9.C10 Spanner 案例](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)）：

- 內部峰值：> 10 億 requests / sec
- 線性擴展（不像 USL 系統會在某點 plateau）
- 跨 region quorum 延遲：50-200ms（視 region 距離）
- 最小容量單位：100 processing units（PU）≈ 1/10 node、適合小負載

## 適用場景

**1. 金融交易、ticketing inventory、payment ledger**：

- 需要強一致，避免 double-spend、oversell 或帳務順序錯亂
- 全球用戶但需要原子性
- 對應案例：[9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) — Google Ads 計費與 Google Play 訂閱都需要把每次計費事件放進可驗證順序

**2. 全球用戶的 OLTP（不只 read replica）**：

- 跨 region 寫入、各地用戶寫入本地 region 仍維持全球強一致
- 它承擔的是 multi-region write path，而非 single primary + 跨 region read replica
- 對應案例：Blockchain.com（高頻 crypto 交易、強一致）

**3. 想擺脫 sharding 複雜度**：

- 傳統大規模 SQL 常走應用層 sharding（管 shard key、跨 shard query、resharding）
- Spanner 自動 partition，application 主要管理 schema、query shape 與 region layout
- 對應案例：[9.C10 Spanner 案例](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) — 「節點數量是容量單位」，shard placement 由 Spanner 管理

**4. PostgreSQL 相容路徑**：

- 2024 後 Spanner 提供 PostgreSQL dialect interface
- 從 PostgreSQL 應用遷入 Spanner 變得容易
- 跟 CockroachDB / Aurora DSQL 類似的策略

## 不適用場景

**1. 跨洲低延遲（< 50ms）需求**：

- 跨洲 quorum 物理上 100ms+ 不可壓縮
- 替代：single-region OLTP（Aurora、Cloud SQL）+ [eventual consistency](/backend/knowledge-cards/eventual-consistency/) 跨 region 同步

**2. 高 throughput 但容忍 eventual consistency**：

- Spanner 強一致有溢價，eventual consistency workload 通常有更低成本選項
- 替代：Bigtable（wide-column、eventual）、DynamoDB Global Tables（KV、eventual）

**3. 小規模 OLTP**：

- 100 PU 起跳、月費約 $65 起、比 Cloud SQL 貴
- 流量 < 1000 RPS 的場景、Cloud SQL 更划算
- Spanner 主要對 *中大規模 + 全球* workload

**4. 跨雲需求**：

- Spanner 是 GCP managed service，cross-cloud / on-prem 需求要看 CockroachDB、TiDB 或其他自管路線
- 替代：CockroachDB、TiDB（自管、可跨雲）

**5. 需要 OLAP 分析能力**：

- Spanner 定位在 OLTP，analytics workload 交給 BigQuery 或其他 OLAP 系統
- 替代：跟 BigQuery 整合做 ETL、或用 Spanner Graph（2024 推出）

## 跟其他 vendor 的取捨

**vs Aurora DSQL（AWS 2024 推出、概念對標 Spanner）**：

- Spanner：用 TrueTime hardware、生產驗證 17 年（Google 內部）+ 7 年（公開）
- Aurora DSQL：新（2024）、PostgreSQL 相容、serverless
- 選 Spanner：GCP 生態、需要極致成熟度
- 選 Aurora DSQL：AWS 生態、需要 PostgreSQL ORM 相容

**vs CockroachDB**：

- Spanner：managed、TrueTime hardware、GCP 限定
- CockroachDB：自管、HLC + Raft（不靠 TrueTime）、跨雲
- 選 Spanner：想把 operation 交給 GCP managed service，並需要 Google 規模驗證
- 選 CockroachDB：跨雲 / on-prem、PostgreSQL 相容、自管彈性

**vs TiDB**：

- Spanner：GCP-only、PostgreSQL-like
- TiDB：可自管 + Cloud、MySQL 相容、中國 / 亞洲生態深
- 選 Spanner：英語 / 歐美生態
- 選 TiDB：MySQL 應用、亞洲市場

**vs Aurora（traditional single-region scaling）**：

- Spanner：全球分散式
- Aurora：single-region scaling
- 選 Spanner：流量明確跨 region + 需要強一致
- 選 Aurora：流量集中一個 region（多數情況）

**vs Cosmos DB（multi-region write）**：

- Spanner：strong consistency 跨 region
- Cosmos DB：5 個 [consistency level](/backend/knowledge-cards/consistency-level/)s、AP 系統（含 strong 但語義不同）
- 選 Spanner：需要 linearizable（金融、ticketing）
- 選 Cosmos DB：可接受 session / eventual、Azure 生態、需要 multi-model

**vs Bigtable**：

- Spanner：SQL、強一致、OLTP
- Bigtable：wide-column、eventual replication、時序 / IoT / 大資料
- 兩者互補：Bigtable 承擔大資料 / wide-column，Spanner 承擔強一致 OLTP

**vs PostgreSQL（baseline）**：

- PostgreSQL：single-primary、跨 region async replication、90% 場景夠用
- Spanner：全球線性化、強一致跨 region、需要 GCP + 接受 latency / 成本
- 從 PostgreSQL 升級 Spanner 的判準：流量明確跨 region，且跨 region 一致性是 product requirement
- 詳見 [PostgreSQL vendor page](/backend/01-database/vendors/postgresql/) 取捨段 + [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)

## 容量規劃要點

從 09 案例庫 + Spanner 文件提煉：

**1. 節點數量 = 容量單位**：

- 節點配置通常用較長週期 review，並在事件高峰前預先調整
- 線性擴展讓 forecast 簡單（2x 流量 → 2x 節點）
- 對應 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 的「不可水平擴容服務」反向 — Spanner 是 *可水平擴容* 但需要 *提前 provision*

**2. 跨 region quorum 配置**：

- multi-region instance 可選擇哪些 region 是 voting member
- voting region 數量決定 failure domain
- 跨大洲 voting 延遲高、跨大陸內可接受

**3. 100 PU 起跳的 granular sizing**：

- 早期 Spanner 最小單位 1 node（約 $1000+/month）、中小負載難用
- 後來推出 100 PU（1/10 node、約 $65/month）、讓小負載也能 evaluate

**4. 跨環境與新產品能力要查官方文件**：

- Spanner 的跨環境、graph、PostgreSQL dialect 與 change streams 能力持續演進
- 實作前要用官方文件確認可用 region、版本、限制與 pricing

**5. TrueTime 是 Spanner 價值之一**：

- Spanner 還有 schema migration without downtime、change streams、interleaved tables
- 評估 Spanner 要同時看跨 region 強一致與整體 SQL 工程能力

## Deep article（已完成）

本批 4 篇 deep article 已完成、覆蓋 Spanner 從 TrueTime 到 Cloud SQL 遷移的核心 production 議題：

| 主題                                                                  | 文章                                                                        | 對應 production 議題                                                                                     |
| --------------------------------------------------------------------- | --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| TrueTime 是手段、line-rate scaling 才是設計目的、commit wait 數學     | [truetime-api-depth](truetime-api-depth/)                                   | 9.C10 Google internal dogfood 線性擴展模式、ε 暴衝失敗模式、cross-region voting latency 影響             |
| external consistency / serializability / linearizability 精確定義差異 | [consistency-models-comparison](consistency-models-comparison/)             | PG SSI / CockroachDB / Spanner / Aurora DSQL line-rate scaling 對照、9.C10 cross-region quorum 100-200ms |
| Schema migration without downtime + interleaved tables 物理 layout    | [schema-migration-interleaved-tables](schema-migration-interleaved-tables/) | TrueTime version timestamp、5 production 踩雷、跟 PostgreSQL online schema change 對照                   |
| Cloud SQL for PostgreSQL → Spanner（Type E paradigm shift）playbook   | [migrate-from-cloud-sql-pg](migrate-from-cloud-sql-pg/)                     | sizing barrier（100 pu 起跳）+ < 50ms write latency no-go、cost crossover 報告、9.C10 dogfood 邊界       |
| Change Streams (CDC)：data change record、watch partition、下游整合   | [change-streams-cdc](change-streams-cdc/)                                   | OLTP 變更餵搜尋 / 快取 / 分析、child partition 接力、retention 失敗、跟 DynamoDB Streams 對照            |
| PostgreSQL dialect vs GoogleSQL、相容子集邊界、dialect 不可逆         | [postgresql-dialect](postgresql-dialect/)                                   | PostgreSQL 生態遷入、相容性 audit、dialect 鎖定的高代價回退、何時選 PG dialect                           |
| Spanner Graph (2024)：property graph、跟 relational 共存、GQL         | [spanner-graph](spanner-graph/)                                             | 多跳關係查詢、edge table layout 不可逆設計代價、super node 扇出、何時用專用 graph DB                     |
| Spanner ↔ BigQuery federation：OLTP/OLAP 分工、Data Boost             | [bigquery-federation](bigquery-federation/)                                 | 分析查詢拖垮 OLTP、Data Boost workload 隔離、federation vs change-stream 落地、何時分出去                |

DB4 cross-vendor entry：先看 [CockroachDB / Aurora DSQL / Spanner 決策樹](../cockroachdb/aurora-dsql-spanner-decision-tree/) 識別 driver path、再進本 vendor 深度。

## 後續擴充（仍待補）

- Spanner Graph 進階查詢 lab（GQL pattern、super node 處理、遍歷效能調校）
- Data Boost 容量規劃與成本模型 deep dive
- Change Streams → Dataflow hands-on lab（建 stream、部署 pipeline、驗證 end-to-end）
- Spanner regional → multi-region topology 升級 playbook

## Anti-recommendation 與升級路由

Spanner 的 global strong consistency 是高價值能力，也會把 latency、region layout 與 GCP lock-in 帶進核心架構。這一段先說何時維持 Cloud SQL / Aurora，再說何時升級 Spanner、CockroachDB、Aurora DSQL 或 Bigtable / DynamoDB。

| 機制 / 路線          | 維持簡單設計的條件                                         | 升級訊號                                                      | 主要引用路徑                                                                                                       |
| -------------------- | ---------------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Cloud SQL / Aurora   | single-region primary 足夠、跨 region 只需 async DR / read | 跨 region 寫入順序是產品契約、double-spend / oversell 代價高  | [Aurora vendor](/backend/01-database/vendors/aurora/)、[RPO](/backend/knowledge-cards/rpo/)                        |
| Spanner regional     | 單 region 強一致與水平擴容已足夠                           | 需要 multi-region availability、regional failure survival     | [Quorum](/backend/knowledge-cards/quorum/)、[External Consistency](/backend/knowledge-cards/external-consistency/) |
| Spanner multi-region | GCP 生態、SQL workload、global consistency 是核心需求      | 跨洲 p99 目標過低、成本或 GCP lock-in 成為主要風險            | [Latency Budget](/backend/knowledge-cards/latency-budget/)、[Global OLTP](/backend/knowledge-cards/global-oltp/)   |
| CockroachDB          | GCP-only managed 服務可接受                                | 跨雲、on-prem、自管或 PostgreSQL wire 相容是硬需求            | [CockroachDB vendor](/backend/01-database/vendors/cockroachdb/)                                                    |
| Aurora DSQL          | 團隊已在 GCP 或需要 Spanner 成熟度                         | AWS 生態、serverless distributed SQL、PostgreSQL 相容是主訴求 | [PG → Aurora DSQL Migration](/backend/01-database/vendors/postgresql/migrate-to-aurora-dsql/)                      |
| Bigtable / DynamoDB  | workload 可接受 eventual consistency 或 KV / wide-column   | 強一致 SQL 的協調成本高於產品收益                             | [DynamoDB vendor](/backend/01-database/vendors/dynamodb/)                                                          |

Spanner 的簡單路徑是先證明跨 region 一致性是產品需求。若只是想要全球 read latency，read replica、cache、edge KV 或 eventual consistency pipeline 可能更划算；Spanner 適合把「全球寫入順序正確」視為產品承諾的資料。

Region layout 的升級路徑要先定義 leader、voting replica 與使用者地理分布。跨洲 quorum 會把物理延遲放進 transaction path，因此 latency budget、降級策略與 read staleness policy 要一起寫進設計。

## 已知 limitation 與後續路由

Spanner overview 目前完成 global SQL 判斷。下一輪 deep article / playbook 應補 TrueTime、external consistency、PostgreSQL dialect、interleaved tables、change streams、Cloud SQL / PostgreSQL → Spanner migration 與 Spanner / BigQuery federation。

## 案例對照

| 案例                                                                                                | 規模                      | 教學重點             |
| --------------------------------------------------------------------------------------------------- | ------------------------- | -------------------- |
| [9.C10 Cloud Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) | > 10 億 req/sec、線性擴展 | 全球強一致 OLTP 標竿 |

Spanner case 的讀法是先看一致性需求，再看容量數字。10 億 req/sec 證明它能水平擴展，但讀者真正要回收的是「計費、訂閱、庫存、交易順序」這類需要 global external consistency 的產品壓力。

## 反向 sibling 路由

Spanner 的反向 sibling 路由用來把 global strong consistency 和雲端代管責任一起判讀。若讀者從 PostgreSQL / MySQL 過來，先確認是否具產品契約等級的 external consistency 需求；若只是 managed SQL 與 replica scaling，回 [Aurora vendor](/backend/01-database/vendors/aurora/)；若要 PostgreSQL-like distributed SQL 且需要自管或多雲彈性，對照 [CockroachDB vendor](/backend/01-database/vendors/cockroachdb/)；若 access pattern 是固定 KV / document，先看 [DynamoDB vendor](/backend/01-database/vendors/dynamodb/) 或 [Cosmos DB vendor](/backend/01-database/vendors/cosmosdb/)。

這條路由的判準是交易順序是否跨 region 影響產品正確性。Spanner 的價值在 external consistency、schema 與 SQL 能力、全球 deployment 與 Google Cloud operation model 的組合；若產品只需要 eventual / session consistency，較輕的 NoSQL 或 managed SQL 常有更低成本。

## 常見陷阱

- **誤以為跨 region 強一致沒有延遲代價**：跨洲 quorum 100-200ms 是物理成本
- **設計 schema 像傳統 PostgreSQL**：Spanner 有 interleaved tables、適當用能加速查詢
- **所有讀取都用強一致**：read-only transaction 可選 bounded staleness，reporting 類路徑常能用 [stale read](/backend/knowledge-cards/stale-read/) 換較低成本
- **單 region 用 Spanner**：浪費、Cloud SQL / Aurora 更便宜
- **不評估 100 PU 起跳**：早年 1 node minimum、現在 100 PU 起、small workload 也可以 POC

## 下一步路由

- 完整 T1 對照：[01-database vendors index](/backend/01-database/vendors/)
- 平行：[Aurora vendor](/backend/01-database/vendors/aurora/)、[DynamoDB vendor](/backend/01-database/vendors/dynamodb/)、[CockroachDB vendor](/backend/01-database/vendors/cockroachdb/)
- 上游：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)
- 跨模組：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) — 全球 OLTP 的容量規劃特殊性
- Last reviewed：2026-05-22（processing units / PostgreSQL interface / TrueTime 文件屬時間敏感 claim）
- 官方：[Cloud Spanner](https://cloud.google.com/spanner)、[TrueTime: Time Distributed in Spanner](https://cloud.google.com/spanner/docs/true-time-external-consistency)
