---
title: "Google Cloud Spanner"
date: 2026-05-13
description: "全球分散式 strong-consistency OLTP、TrueTime API、線性擴展到 10 億 req/sec"
weight: 8
tags: ["backend", "database", "vendor", "spanner", "sql", "global"]
---

Cloud Spanner 是 Google 內部 2007 年起跑、2017 年開放為 GCP 服務的 *全球分散式 SQL OLTP*。內部撐 Google Ads / Play / Search 計費、外部支援 Blockchain.com、Sharechat、ZEE5 等。它是 *唯一公開撐每秒 10 億請求* 同時維持線性擴展 + 強一致 + global distribution 的 OLTP 系統。

## 教學路線：全球強一致與 TrueTime 成本

Spanner 服務頁的教學目標是把 global strong consistency、TrueTime、Paxos、region layout 與 processing unit 連成一條產品決策線。讀者讀完後要能判斷何時需要全球一致 SQL，並理解這種能力的 latency、成本與雲平台邊界。

| 學習段             | 核心問題                                                   | 對應段落                         |
| ------------------ | ---------------------------------------------------------- | -------------------------------- |
| Global consistency | 強一致 SQL 為什麼需要時間邊界與 consensus                  | 定位、適用場景                   |
| Region layout      | instance config、leader region、replica 如何影響 latency   | 容量規劃要點、常見陷阱           |
| Capacity unit      | node / processing unit 如何取代傳統 shard 心智模型         | 容量特性、案例對照               |
| Use-case pressure  | billing、subscription、ticketing、金融交易何時需要 Spanner | 適用場景、案例對照               |
| 替代路由           | 何時用 PostgreSQL、CockroachDB、Aurora DSQL、DynamoDB      | 不適用場景、跟其他 vendor 的取捨 |

## 定位：TrueTime + Paxos 的全球線性 SQL

Spanner 解決一個過去 30 年分散式 DB 認為不可能的問題：*跨地理位置* 同時拿到 strong consistency + linear scalability + global availability。

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

- 必須強一致（不能 double-spend、不能 oversell）
- 全球用戶但需要原子性
- 對應案例：[9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) — Google Ads 計費（不能漏一個 click）、Google Play 訂閱

**2. 全球用戶的 OLTP（不只 read replica）**：

- 跨 region 寫入、各地用戶寫入本地 region 仍維持全球強一致
- 不是 single primary + 跨 region read replica
- 對應案例：Blockchain.com（高頻 crypto 交易、強一致）

**3. 想擺脫 sharding 複雜度**：

- 傳統大規模 SQL 必須應用層 sharding（管 shard key、跨 shard query、resharding）
- Spanner 自動 partition、應用層不必管
- 對應案例：[9.C10 Spanner 案例](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) — 「節點數量是容量單位」、不是「shard 數量」

**4. PostgreSQL 相容路徑**：

- 2024 後 Spanner 提供 PostgreSQL dialect interface
- 從 PostgreSQL 應用遷入 Spanner 變得容易
- 跟 CockroachDB / Aurora DSQL 類似的策略

## 不適用場景

**1. 跨洲低延遲（< 50ms）需求**：

- 跨洲 quorum 物理上 100ms+ 不可壓縮
- 替代：single-region OLTP（Aurora、Cloud SQL）+ [eventual consistency](/backend/knowledge-cards/eventual-consistency/) 跨 region 同步

**2. 高 throughput 但容忍 eventual consistency**：

- Spanner 強一致是有溢價的、不需要的話用更便宜
- 替代：Bigtable（wide-column、eventual）、DynamoDB Global Tables（KV、eventual）

**3. 小規模 OLTP**：

- 100 PU 起跳、月費約 $65 起、比 Cloud SQL 貴
- 流量 < 1000 RPS 的場景、Cloud SQL 更划算
- Spanner 主要對 *中大規模 + 全球* workload

**4. 跨雲需求**：

- Spanner GCP-only、無 cross-cloud 部署
- 替代：CockroachDB、TiDB（自管、可跨雲）

**5. 需要 OLAP 分析能力**：

- Spanner 是 OLTP、不是 OLAP
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
- 選 Spanner：不想 ops、需要 Google 規模驗證
- 選 CockroachDB：跨雲 / on-prem、PostgreSQL 相容、自管彈性

**vs TiDB**：

- Spanner：GCP-only、PostgreSQL-like
- TiDB：可自管 + Cloud、MySQL 相容、中國 / 亞洲生態深
- 選 Spanner：英語 / 歐美生態
- 選 TiDB：MySQL 應用、亞洲市場

**vs Aurora（traditional single-region scaling）**：

- Spanner：全球分散式
- Aurora：single-region scaling
- 選 Spanner：流量真的跨 region + 需要強一致
- 選 Aurora：流量集中一個 region（多數情況）

**vs Cosmos DB（multi-region write）**：

- Spanner：strong consistency 跨 region
- Cosmos DB：5 個 [consistency level](/backend/knowledge-cards/consistency-level/)s、AP 系統（含 strong 但語義不同）
- 選 Spanner：必須 linearizable（金融、ticketing）
- 選 Cosmos DB：可接受 session / eventual、Azure 生態、需要 multi-model

**vs Bigtable**：

- Spanner：SQL、強一致、OLTP
- Bigtable：wide-column、eventual replication、時序 / IoT / 大資料
- 兩者不是替代、是互補（Bigtable 大資料、Spanner OLTP）

**vs PostgreSQL（baseline）**：

- PostgreSQL：single-primary、跨 region async replication、90% 場景夠用
- Spanner：全球線性化、強一致跨 region、需要 GCP + 接受 latency / 成本
- 從 PostgreSQL 升級 Spanner 的判準：流量真的跨 region + 跨 region 一致性是 product requirement（不是 nice-to-have）
- 詳見 [PostgreSQL vendor page](/backend/01-database/vendors/postgresql/) 取捨段 + [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)

## 容量規劃要點

從 09 案例庫 + Spanner 文件提煉：

**1. 節點數量 = 容量單位**：

- 每年 review 節點配置、不是每個月
- 線性擴展讓 forecast 簡單（2x 流量 → 2x 節點）
- 對應 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 的「不可水平擴容服務」反向 — Spanner 是 *可水平擴容* 但需要 *提前 provision*

**2. 跨 region quorum 配置**：

- multi-region instance 可選擇哪些 region 是 voting member
- voting region 數量決定 failure domain
- 跨大洲 voting 延遲高、跨大陸內可接受

**3. 100 PU 起跳的 granular sizing**：

- 早期 Spanner 最小單位 1 node（約 $1000+/month）、中小負載難用
- 後來推出 100 PU（1/10 node、約 $65/month）、讓小負載也能 evaluate

**4. Spanner Omni（2026）**：

- 跨地區峰值：數百萬 QPS、PB 級資料
- 仍維持線性擴展特性

**5. TrueTime 不是 Spanner 唯一價值**：

- Spanner 還有 schema migration without downtime、change streams、interleaved tables
- 評估 Spanner 不要只看「跨 region 強一致」、要看整體 SQL 工程能力

## 預計實作話題（後續擴充）

- TrueTime API 深度（為什麼 GPS + 原子鐘）
- External consistency vs serializability vs [linearizability](/backend/knowledge-cards/linearizability/)
- Schema migration 跟 interleaved tables
- Change streams（CDC）
- Spanner PostgreSQL dialect
- Spanner Graph（2024）
- 從 Cloud SQL / PostgreSQL 遷到 Spanner
- 跟 BigQuery 整合（OLTP / OLAP [federation](/backend/knowledge-cards/federation/)）

## 案例對照

| 案例                                                                                                | 規模                      | 教學重點             |
| --------------------------------------------------------------------------------------------------- | ------------------------- | -------------------- |
| [9.C10 Cloud Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) | > 10 億 req/sec、線性擴展 | 全球強一致 OLTP 標竿 |

## 常見陷阱

- **誤以為跨 region 強一致沒延遲代價**：跨洲 quorum 100-200ms、無法避免
- **設計 schema 像傳統 PostgreSQL**：Spanner 有 interleaved tables、適當用能加速查詢
- **不用 [stale read](/backend/knowledge-cards/stale-read/)**：read-only transaction 可選 bounded staleness、便宜很多、適合 reporting
- **單 region 用 Spanner**：浪費、Cloud SQL / Aurora 更便宜
- **不評估 100 PU 起跳**：早年 1 node minimum、現在 100 PU 起、small workload 也可以 POC

## 下一步路由

- 完整 T1 對照：[01-database vendors index](/backend/01-database/vendors/)
- 平行：[Aurora vendor](/backend/01-database/vendors/aurora/)、[DynamoDB vendor](/backend/01-database/vendors/dynamodb/)、[CockroachDB vendor](/backend/01-database/vendors/cockroachdb/)
- 上游：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)
- 跨模組：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) — 全球 OLTP 的容量規劃特殊性
- 官方：[Cloud Spanner](https://cloud.google.com/spanner)、[TrueTime: Time Distributed in Spanner](https://cloud.google.com/spanner/docs/true-time-external-consistency)
