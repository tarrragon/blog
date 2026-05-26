---
title: "MongoDB"
date: 2026-05-13
description: "Document database 代表、Atlas managed、跨雲可用、許多大規模平台從 MongoDB 起家"
weight: 3
tags: ["backend", "database", "vendor", "mongodb", "document"]
---

MongoDB 是 document database 的事實標準。schema flexibility、aggregation pipeline、跨雲 managed（Atlas）讓它成為許多 startup 的 default 選擇。Microsoft 365、Disney+ 早期、Uber 等大規模平台都從 MongoDB 起家，後來依 workload 壓力把部分路徑遷移到 KV / 雲商專屬服務（Cosmos DB、DynamoDB）。

## 教學路線：Document shape 與 schema governance

MongoDB 服務頁的教學目標是把 document model、schema flexibility、index、aggregation pipeline 與 sharding 放回資料形狀治理。讀者讀完後要能判斷資料是否適合 aggregate root，並知道 schema governance 如何影響長期維護成本。

| 學習段            | 核心問題                                                 | 對應段落                                                                       |
| ----------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Document shape    | 哪些資料適合 aggregate root 與 nested document           | 定位、適用場景                                                                 |
| Schema governance | schema flexibility 如何搭配 validation、版本與 migration | 容量規劃要點、預計實作話題                                                     |
| Query / index     | index、aggregation pipeline、ad-hoc query 如何影響成本   | 容量特性、常見陷阱                                                             |
| Sharding          | shard key、chunk、balancer 如何把資料形狀變容量問題      | 容量規劃要點、[Database Sharding](/backend/knowledge-cards/database-sharding/) |
| 替代路由          | 何時轉 PostgreSQL、DynamoDB、Cosmos DB 或 search         | 不適用場景、跟其他 vendor 的取捨                                               |

## 定位：JSON document + 跨雲彈性

MongoDB 是以 document model 為主體的 DB。PostgreSQL JSONB 適合「SQL 為主、少量半結構化欄位」；MongoDB 則把 BSON document、aggregation pipeline、[database sharding](/backend/knowledge-cards/database-sharding/) 與 schema governance 放在核心設計裡。近年版本加入 time series、change streams、queryable encryption、CSFLE 等能力。

選 MongoDB 的核心訴求：document model 是主要 use case、需要跨雲 managed（Atlas）、想避免 vendor lock-in（也可自管）。

## 容量特性

**單一 instance 吞吐**：

- 一般 m5.4xlarge：5K-15K WPS（依 doc size、index）
- 高階 instance + tuning：30K-50K WPS
- 超過此級別 → sharding

**Sharding**：

- MongoDB 原生支援 sharded cluster
- mongos router + config servers + shard
- MongoDB sharding 要主動設計 shard key，並和 [Hot Partition](/backend/knowledge-cards/hot-partition/) 風險一起看

**Replication**：

- Replica set（primary + secondary、async）
- 跨 region 通常 async
- 自動 failover < 30 秒（mongod 內建）

**Storage**：

- 單一 collection 沒有官方上限、但 shard key resharding 過去版本是大手術（4.4+ 支援 reshardCollection）

## 適用場景

**1. Document model 主要 workload**：

- schema 變化頻繁的早期產品
- nested document 自然表達領域模型（訂單含多個 item、用戶含多個 preference）
- 對應案例：[9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — 從 MongoDB 遷移到 Cosmos DB MongoDB API、保留 document model

**2. Aggregation pipeline 重 workload**：

- 複雜的 $group / $match / $project chain
- 報表、analytics、ETL prep
- 比 RDBMS 寫複雜 query 更直觀（對某些 team）

**3. 跨雲 managed（Atlas）**：

- MongoDB Atlas 跨 AWS / GCP / Azure
- 跟 DynamoDB（AWS only）、Cosmos DB（Azure only）、Spanner（GCP only）相反
- 適合多雲策略、避免單一 vendor lock-in

**4. Time series workload（6.0+）**：

- time series collection 專屬優化
- 不過 InfluxDB / TimescaleDB 仍是更專業選擇

**5. 已有 MongoDB 生態 + 想轉移操作責任**：

- Atlas 提供 backup、failover、monitoring、auto-scale
- 想把 MongoDB DBA / SRE 操作責任交給 Atlas

## 不適用場景

**1. 強 ACID multi-document transaction**：

- MongoDB Transaction 支援多 document、但跨 shard 有性能影響
- 高頻金融交易仍建議 SQL 系統
- 替代：PostgreSQL、Aurora、Spanner

**2. 複雜 JOIN**：

- MongoDB `$lookup` 適合少量相鄰資料，JOIN-heavy workload 應回 SQL 系統
- schema design 階段要把常用讀取路徑 denormalize 成 document shape
- 替代：SQL 系統做 JOIN-heavy workload

**3. 純 KV + sub-ms latency**：

- MongoDB document model 比 KV 多一層 BSON parsing
- 替代：Redis、DynamoDB、Bigtable

**4. 大規模 OLAP**：

- aggregation 對中等資料量還行、TB 級不適合
- 替代：ClickHouse、BigQuery、Spark on Delta Lake

**5. 嚴格資料模型 + schema enforcement**：

- MongoDB schema flexibility 可能導致 production data inconsistency
- 替代：SQL DB（schema 強制）+ JSONB column 處理半結構化

## 跟其他 vendor 的取捨

**vs Cosmos DB MongoDB API**：

- MongoDB Atlas：跨雲、原生 MongoDB 行為
- Cosmos DB MongoDB API：Azure-only、global distribution + 5 [consistency level](/backend/knowledge-cards/consistency-level/)s
- 選 MongoDB Atlas：跨雲、需要原生 MongoDB features
- 選 Cosmos DB：Azure 生態、需要更好 global distribution
- 對應案例：[9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — 從 MongoDB 遷到 Cosmos DB MongoDB API，主要保留 document model

**vs DynamoDB**：

- MongoDB：document model、aggregation 強、跨雲
- DynamoDB：KV / single-table design、AWS 整合、5 個 9 SLA
- 選 MongoDB：document 為主、跨雲
- 選 DynamoDB：KV 為主、AWS 生態
- 詳見 [DynamoDB vendor page](/backend/01-database/vendors/dynamodb/) 對比段

**vs PostgreSQL JSONB**：

- MongoDB：document 為主、schema-less
- PostgreSQL：SQL 為主、JSONB 補充
- 選 MongoDB：document 占主要 schema
- 選 PostgreSQL JSONB：主要結構化、少量半結構化欄位

**vs Couchbase / Couchdb / Firestore**：

- Couchbase：MongoDB 替代、有 N1QL（SQL-like）
- CouchDB：偏小規模、master-master replication
- Firestore：GCP-only、realtime updates
- MongoDB 在這群裡是生態最廣的

**vs Elasticsearch 作為 search 替代**：

- 兩者分屬不同類別：MongoDB 是 OLTP / document、Elasticsearch 是 search + analytics
- 通常搭配用：MongoDB 主、Elasticsearch 處理 full-text search

## 容量規劃要點

**1. Shard key 設計是命脈**：

- 跟 DynamoDB partition key 同樣關鍵
- 不均勻 → hot shard、實際容量達不到名義
- 4.4+ 可以 reshard、但仍是大手術

**2. Replica set 是 HA 基礎**：

- 至少 3 個 member（1 primary + 2 secondary）
- secondary 可 read（read preference）但要注意 lag
- failover 通常 < 30 秒

**3. Atlas managed 服務**：

- 提供 auto-scaling、auto-backup、跨雲部署
- Tier 從 M0（free）到 M700（高階）
- Atlas Online Archive 自動把舊資料移到便宜 storage

**4. Index 限制**：

- 單 collection 最多 64 個 index
- compound index 有順序敏感（{a:1, b:1} 跟 {b:1, a:1} 不同）
- TTL index 自動 expire 過期 document

**5. Change streams（CDC）**：

- 4.0+ 提供原生 change streams
- 對接 Kafka / event bus 做 event sourcing

## Anti-recommendation 與升級路由

MongoDB 的 schema flexibility 會降低早期建模成本，也會把 schema governance 延後到 production。這一段先說何時維持 document model，再說何時升級 Atlas、sharding、Cosmos DB、DynamoDB 或 SQL。

| 機制 / 路線           | 維持簡單設計的條件                                     | 升級訊號                                                              | 主要引用路徑                                                                                                               |
| --------------------- | ------------------------------------------------------ | --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| 單一 replica set      | document size 穩定、working set 可控、primary 寫入足夠 | storage / write / working set 接近上限、failover 演練不足             | [Replication Lag](/backend/knowledge-cards/replication-lag/)、[RPO](/backend/knowledge-cards/rpo/)                         |
| Atlas managed         | 團隊仍能管理 backup、upgrade、monitoring 與 scaling    | DBA / SRE 責任想轉交平台、跨雲部署與 backup 成為主要壓力              | [Audit Log](/backend/knowledge-cards/audit-log/)、[Secret Management](/backend/knowledge-cards/secret-management/)         |
| Sharded cluster       | single replica set 還能承擔容量與維護窗口              | shard key 穩定、tenant / user / region 可分、hot shard 可觀測         | [Database Sharding](/backend/knowledge-cards/database-sharding/)、[Hot Partition](/backend/knowledge-cards/hot-partition/) |
| Cosmos DB MongoDB API | Azure 只是部署選項，原生 MongoDB 行為仍重要            | Azure global distribution、multi-region write 或 RU governance 成主題 | [Cosmos DB vendor](/backend/01-database/vendors/cosmosdb/)                                                                 |
| DynamoDB / KV         | query 仍需要 document traversal 與 aggregation         | access pattern 固定、sub-10ms p99、connection-free scaling 成主題     | [DynamoDB vendor](/backend/01-database/vendors/dynamodb/)                                                                  |
| PostgreSQL            | document 是主要資料形狀                                | JOIN-heavy、transaction-heavy、schema 約束是主要價值                  | [PostgreSQL vendor](/backend/01-database/vendors/postgresql/)                                                              |

MongoDB 的簡單路徑是先把 document boundary 寫清楚。資料可以彈性演進，但 application 仍要知道哪些欄位是正式契約、哪些欄位只是相容期，並用 validation、migration 與 data quality check 管住版本漂移。

Sharding 的升級路徑要等 shard key 與 query shape 足夠穩定。過早切 shard 會把 aggregation、transaction 與 index 成本提前放大；過晚切 shard 則會讓 resharding、chunk migration 與 balancer 壓力進入 production 高峰期。

## 已知 limitation 與後續路由

MongoDB overview 目前先完成 document service 判斷，deep article 仍要補 schema design pattern、shard key 選型、aggregation optimization、change streams、Atlas migration 與 MongoDB → Cosmos DB / DynamoDB 的 migration playbook。

## 預計實作話題（後續擴充）

- Schema design pattern（embedded vs reference、polymorphic）
- Shard key 選型（hashed vs ranged）
- Aggregation pipeline optimization
- Index 設計跟覆蓋
- Replica set topology + read preference
- Change streams + Kafka 整合
- 從自管 MongoDB 遷到 Atlas
- 從 MongoDB 遷到 Cosmos DB MongoDB API（保留 document model）
- 從 MongoDB 遷到 DynamoDB（access pattern 需要重設計）
- Queryable encryption（CSFLE）

## 案例對照

| 案例                                                                                                      | 跟 MongoDB 的關係                                                                   |
| --------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/)          | 從 MongoDB 遷到 Cosmos DB MongoDB API、planet-scale analytics                       |
| [9.C36 Coinbase](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/)              | MongoDB 為主資料層、自建 mongobetween 解決 Ruby 連線爆炸、users 服務 1.5M reads/sec |
| [9.C37 Forbes](/backend/09-performance-capacity/cases/forbes-mongodb-atlas-multi-cloud-migration/)        | 自管 MongoDB → Atlas on GCP、6 個月遷完、build 25→9 分鐘、120M MAU                  |
| [9.C38 Toyota Connected](/backend/09-performance-capacity/cases/toyota-connected-mongodb-telematics-iot/) | Atlas 撐 900 萬車 telematics、月 180 億 transaction、緊急訊號 3 秒內到 agent        |

MongoDB case 的讀法分三組：

- **作為 production 主角持續演進**（Coinbase、Toyota Connected）：document model 撐住核心 OLTP / IoT、配 connection proxy / cache / event-driven 處理擴展周邊。
- **自管 → managed 遷移**（Forbes）：同 document model、換託管模式、ROI 集中在 DBA 責任轉移跟跨雲彈性、不是性能改善。
- **遷出 MongoDB 保留 API**（Microsoft 365）：document model 保留、底層換到 Cosmos DB MongoDB API、換取 Azure global distribution。

讀 case 時要區分 MongoDB 在「主角 / 遷入 / 遷出」三種位置的差異，三種位置揭露的工程議題完全不同。

## 常見陷阱

- **schema 長期 schema-less**：production 出現 data inconsistency、難 query
- **shard key 用 _id（自增）**：寫入全集中在最後一個 shard
- **$lookup 過度使用**：跨 collection JOIN-heavy workload 應在 schema design 時 denormalize 或回 SQL
- **index 太多**：寫吞吐被拖垮、定期 review 未用 index
- **secondary read 不檢查 lag**：用戶讀到 stale data
- **不規劃 Atlas tier upgrade 路徑**：流量上來才發現 tier 跟不上、緊急升級費用高

## 下一步路由

- 完整 T1 對照：[01-database vendors index](/backend/01-database/vendors/)
- 平行：[Cosmos DB vendor](/backend/01-database/vendors/cosmosdb/)（MongoDB API replacement）、[DynamoDB vendor](/backend/01-database/vendors/dynamodb/)（KV alternative）
- 上游：[1.2 schema design](/backend/01-database/schema-design/)、[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)
- 下游：[1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)（MongoDB 遷出範例）
- 跨模組：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)（shard key 跟 hot shard）
- 官方：[MongoDB Manual](https://www.mongodb.com/docs/manual/)、[MongoDB Atlas](https://www.mongodb.com/atlas)
