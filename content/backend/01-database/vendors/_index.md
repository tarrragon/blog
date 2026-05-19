---
title: "資料庫 Vendor 清單"
date: 2026-05-01
description: "規劃 SQL、managed SQL、document、KV 與 distributed SQL 的服務頁撰寫順序與教學大綱"
weight: 90
tags: ["backend", "database", "vendor"]
---

資料庫 Vendor 清單的核心責任是把 database 服務名稱放回正式狀態、交易邊界、查詢模型、schema 演進、容量與資料治理的判斷。每個服務頁先說明它承擔的資料責任，再比較適用場景、容量邊界、替代服務、操作成本、案例對照與下一步路由。

資料庫服務頁的共同讀法見 [0.17 後端真實服務討論大綱](/backend/00-service-selection/service-entity-discussion-outline/)。閱讀時先用 PostgreSQL / MySQL 建立 SQL baseline，再看 managed SQL、KV / document 與 global distributed SQL 如何改變團隊責任。

## T1 服務頁大綱

| 服務                                                     | 類型                  | 頁面要回答的核心問題                                                          |
| -------------------------------------------------------- | --------------------- | ----------------------------------------------------------------------------- |
| [PostgreSQL](/backend/01-database/vendors/postgresql/)   | SQL baseline          | transaction、schema、query、extension 與操作成熟度如何成為比較基準            |
| [MySQL](/backend/01-database/vendors/mysql/)             | SQL baseline          | 高併發 OLTP、replication、online schema change 與 sharding 生態如何取捨       |
| [SQLite](/backend/01-database/vendors/sqlite/)           | Embedded SQL          | 單機正式狀態、測試資料、edge / local DB 與低操作成本如何成立                  |
| [MongoDB](/backend/01-database/vendors/mongodb/)         | Document database     | document shape、index、schema flexibility 與 transaction 邊界如何治理         |
| [DynamoDB](/backend/01-database/vendors/dynamodb/)       | Managed KV / document | partition key、access pattern、容量計費與 hot partition 如何設計              |
| [Aurora](/backend/01-database/vendors/aurora/)           | Managed SQL           | storage / compute 分離、failover、replica 與 AWS operation model 如何轉移責任 |
| [Spanner](/backend/01-database/vendors/spanner/)         | Global SQL            | TrueTime、strong consistency、multi-region latency 與成本如何取捨             |
| [Cosmos DB](/backend/01-database/vendors/cosmosdb/)      | Global multi-model    | consistency level、API model、partition 與 Azure 約束如何影響架構             |
| [CockroachDB](/backend/01-database/vendors/cockroachdb/) | Distributed SQL       | SQL 相容、range lease、multi-region 與自管 / managed 邊界如何判斷             |

## 內容覆蓋進度

每個 vendor 服務頁下會擴充兩類文章：deep article（vendor 自身的配置、故障、容量、走 [6-section 模板](/posts/vendor-deep-article-methodology/)）跟 migration playbook（跨 vendor 遷移流程、走 [6-type 結構](/posts/migration-playbook-methodology/)）。「→ X」代表遷移到 X 的 playbook、其他形式代表 same-vendor 的 topology / version / config 變動。

| Vendor                    | Deep article                                                                                                                                                                                                                                                                                                                                      | Migration playbook                                                                                                                                                                                                                                                                       |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [PostgreSQL](postgresql/) | [autovacuum-tuning](postgresql/autovacuum-tuning/) / [declarative-partitioning](postgresql/declarative-partitioning/) / [logical-replication-debezium](postgresql/logical-replication-debezium/) / [patroni-ha](postgresql/patroni-ha/) / [pgbouncer-config](postgresql/pgbouncer-config/) / [pitr-wal-archiving](postgresql/pitr-wal-archiving/) | [major-version-upgrade](postgresql/major-version-upgrade/) / [→ Aurora](postgresql/migrate-to-aurora/) / [→ CockroachDB](postgresql/migrate-to-cockroachdb/) / [multi-region-gdpr-rollout](postgresql/multi-region-gdpr-rollout/) / [partition-redesign](postgresql/partition-redesign/) |
| [MySQL](mysql/)           | —                                                                                                                                                                                                                                                                                                                                                 | [→ PostgreSQL](mysql/migrate-to-postgresql/)                                                                                                                                                                                                                                             |
| [MongoDB](mongodb/)       | —                                                                                                                                                                                                                                                                                                                                                 | [→ Atlas](mongodb/migrate-to-atlas/) / [shard-expansion-multi-dc](mongodb/shard-expansion-multi-dc/)                                                                                                                                                                                     |
| [DynamoDB](dynamodb/)     | [consistency-model-optimization](dynamodb/consistency-model-optimization/)                                                                                                                                                                                                                                                                        | —                                                                                                                                                                                                                                                                                        |

其他 T1 vendor（Aurora / CockroachDB / SQLite / Spanner / Cosmos DB）尚未開始。對應的 backlog 議題見上方「T1 服務頁大綱」段每個服務頁要回答的核心問題、跟各 vendor `_index.md` 的「預計實作話題」段。

## 服務頁標準章節

| 章節                 | 資料庫服務頁要補的內容                                                      |
| -------------------- | --------------------------------------------------------------------------- |
| 服務定位             | 它是正式狀態、embedded store、managed SQL、KV/document 還是 distributed SQL |
| 本章目標             | 讀者能判斷資料形狀、交易需求、查詢邊界、容量與操作責任                      |
| 最短判讀路徑         | 用「資料是否需要 transaction / ad-hoc query / global consistency」快速定位  |
| 日常操作與決策形狀   | schema migration、backup、restore、replica、index、connection、quota        |
| 核心取捨表           | SQL baseline、managed SQL、KV/document、distributed SQL 的機會成本          |
| 進階主題             | sharding、multi-region、online migration、CDC、global consistency           |
| 排錯與失敗快速判讀   | connection exhaustion、slow query、lock、replication lag、hot partition     |
| 何時改走其他服務     | query 變複雜時回 SQL、replay 需求轉 event log、全文搜尋轉 search            |
| 不在本頁內的主題     | ORM 語法、語言 driver 細節、完整 DBA 手冊                                   |
| 案例回寫與下一步路由 | 回到 01 主章、09 capacity case、08 incident decision log                    |

## 後續擴充

| 層級 | 候選服務                                                                     | 補充理由                                                    |
| ---- | ---------------------------------------------------------------------------- | ----------------------------------------------------------- |
| T2   | Oracle Database、Microsoft SQL Server、MariaDB                               | enterprise / commercial SQL 與 MySQL 相鄰生態               |
| T2   | PlanetScale / Vitess、TiDB、YugabyteDB、Neon、Supabase、Azure SQL Hyperscale | sharding、distributed SQL、serverless Postgres、managed SQL |
| T2   | Apache Cassandra、ScyllaDB、Firestore                                        | wide-column、high-write、mobile / serverless document       |
| T2   | OpenSearch / Elasticsearch                                                   | search engine 與 log / document search 邊界                 |
| T3   | ClickHouse、BigQuery、Snowflake                                              | OLAP / analytics，先作相鄰路由                              |
| T3   | CouchDB、Couchbase                                                           | sync / document database 的特殊場景                         |

主流覆蓋檢查的重點是區分 OLTP、search 與 analytics。Oracle、SQL Server、MariaDB 補 enterprise SQL；Cassandra / ScyllaDB 補 wide-column；OpenSearch / Elasticsearch 補 search；ClickHouse、BigQuery、Snowflake 先保留 analytics 路由，避免資料庫服務頁承擔整個數倉教材。
