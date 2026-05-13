---
title: "MySQL"
date: 2026-05-13
description: "高併發網路服務常用關聯式資料庫、Vitess / PlanetScale 分片生態、GitHub / Shopify / Facebook 規模驗證"
weight: 2
tags: ["backend", "database", "vendor", "mysql", "sql"]
---

MySQL 是大型網路服務的常見選擇、簡單 query 效能跟分片生態（Vitess / PlanetScale）成熟。GitHub、Shopify、Slack、Facebook（YouTube 從 MySQL 起家）等大規模服務的核心 OLTP 多採 MySQL。InnoDB engine 的 row-level lock、clustered index、buffer pool tuning 都被深度驗證。

## 定位：高併發簡單 SQL + 強分片生態

MySQL 跟 PostgreSQL 是 SQL OLTP 兩大主流、但設計取捨明顯不同：

- MySQL 偏 *簡單 query 效能 + 分片生態* — InnoDB clustered index 對 primary key range query 特別快、Vitess 提供超大規模透明 sharding
- PostgreSQL 偏 *特性深度* — 詳見 [PostgreSQL vendor page](/backend/01-database/vendors/postgresql/)

選 MySQL 的核心訴求：需要超大規模分片（> 100 TB、> 100K WPS）、簡單 query 為主、已用 MySQL 生態工具鏈（gh-ost、pt-online-schema-change）。

## 容量特性

**單一 primary 寫吞吐**：

- 標準 InnoDB：10K-30K WPS（依 row size、commit sync、index 數量）
- 高階 instance + 優化 schema：50K-100K WPS
- 超過此級別 → Vitess sharding 或 PlanetScale

**Connection 上限**：

- 預設 max_connections = 151、實務常設 1000-5000
- 每個 connection ~3MB RAM（比 PostgreSQL 輕）
- 仍建議 ProxySQL / connection pool

**Replication**：

- async / semi-sync / GTID-based
- 跨 AZ async lag 通常 < 100ms
- 跨 region 通常用 chain replication 或 binlog 同步

**Storage 上限**：

- 單一 table 64 TB（InnoDB 設計上限）
- 實務超過 1 TB 表建議分片

## 適用場景

**1. 大規模 OLTP + 分片需求**：

- 流量 > 50K WPS、必須 sharding
- 用 Vitess / PlanetScale 透明 sharding、應用層幾乎不必改
- 對應產業：超大網路服務（GitHub、Shopify、Slack）

**2. 簡單 query 為主**：

- primary key lookup、簡單 range query
- 不太用 CTE、window function、複雜 JOIN
- InnoDB clustered index 對這類 workload 特別快

**3. 既有 MySQL 生態工具**：

- gh-ost / pt-online-schema-change（online schema migration）
- Orchestrator（HA topology 管理）
- ProxySQL（query routing + connection pool）
- Maxwell / Debezium MySQL（CDC）

**4. 強一致 transaction 但容忍部分 SQL 功能缺失**：

- 不需 partial index、不需 JSONB indexing
- 不需 PostGIS、用 spatial extension 夠

**5. Aurora MySQL（managed 路徑）**：

- 從自管 MySQL 上 AWS、保留 wire protocol
- 詳見 [Aurora vendor page](/backend/01-database/vendors/aurora/)

## 不適用場景

**1. 需要 PostgreSQL 等級的 SQL / JSON 特性**：

- 複雜 CTE、recursive query、window function
- JSON Schema validation、JSONB GIN indexing
- PostGIS 等深度 extension

**2. 全球 multi-region active-active write**：

- MySQL 設計是 single primary、跨 region 是 async
- 替代：Aurora DSQL、Spanner、Vitess multi-cluster

**3. 大規模 OLAP**：

- MySQL 不是 OLAP DB
- 替代：ClickHouse、BigQuery、Snowflake

**4. KV 簡單查詢 + sub-10ms p99**：

- 跟 PostgreSQL 一樣有 parsing / planning 開銷
- 替代：DynamoDB、Redis

## 跟其他 vendor 的取捨

**vs PostgreSQL**：

- 詳見 [PostgreSQL vendor page](/backend/01-database/vendors/postgresql/) 對比段
- 摘要：MySQL 適合超大規模分片、PostgreSQL 適合進階 SQL 特性

**vs Aurora MySQL（同 wire protocol）**：

- MySQL（自管 / RDS）：可跨雲、彈性高
- Aurora MySQL：AWS managed、storage / compute 分離、更多 read replica
- 選自管 MySQL：跨雲需求、預算敏感
- 選 Aurora MySQL：AWS 生態深、需要 storage scaling

**vs PlanetScale（Vitess managed）**：

- MySQL（自管 + Vitess）：完全控制、可自管分片
- PlanetScale：managed Vitess、branch-based schema migration
- 選 MySQL + Vitess：team 有能力管 Vitess、預算敏感
- 選 PlanetScale：想 zero ops、branch-based workflow

**vs TiDB**：

- MySQL：single-primary、傳統分片靠 Vitess
- TiDB：MySQL wire protocol 相容、HTAP（OLTP + OLAP 同庫）、跨 region 強一致
- 選 MySQL：已有 MySQL 投資、不想換引擎
- 選 TiDB：需要跨 region 強一致 + OLAP 同庫

**vs Vitess（self-managed sharding layer）**：

- Vitess 本質是 MySQL 上層的 sharding layer
- 由 YouTube 設計、捐贈 CNCF
- 適合超大規模 MySQL 集群、需要透明 sharding

## 容量規劃要點

**1. Sharding 是 MySQL 大規模的核心**：

- 單一 MySQL primary 寫吞吐有上限
- Vitess / PlanetScale 用 keyspace + shard 切分
- shard key 設計類似 DynamoDB partition key — 必須均勻
- 大規模案例：Shopify（多 shard 分散）、Slack（per-team sharding）

**2. Online schema change 是必備**：

- ALTER TABLE 直接跑會 lock 整個 table
- gh-ost（GitHub）/ pt-online-schema-change（Percona）/ Vitess online DDL 用 ghost table 漸進 migrate
- 大表 schema change 可能跑 hours / days、要排程

**3. Replication 跟 GTID**：

- GTID-based replication 比 binlog position 容易管 topology
- semi-sync replication 保證至少一個 standby ack 才 commit
- async replication 高吞吐但 lag 較大

**4. Connection management**：

- ProxySQL 是 MySQL 生態的 connection pool 標準
- 提供 query routing（讀 → replica、寫 → primary）
- 對應 [9.C29 Lemino case](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) — RDB connection limit 議題對 MySQL 同樣適用

**5. InnoDB tuning**：

- innodb_buffer_pool_size：通常設 system RAM 70%
- innodb_flush_log_at_trx_commit：1（durable）vs 2（faster）vs 0（fastest, 不安全）
- innodb_io_capacity：依 storage 類型調整

## 預計實作話題（後續擴充）

- Replication topology（async / semi-sync / GTID）配置
- gh-ost / pt-online-schema-change 對比
- Vitess sharding 設計
- ProxySQL 配置跟 query routing
- Orchestrator failover 設計
- 從自管 MySQL 遷到 Aurora MySQL / PlanetScale
- InnoDB tuning（buffer pool、log、IO）
- Binary log + Maxwell / Debezium CDC

## 案例對照

MySQL 沒有直接的 09 case（大規模 MySQL 多在 engineering blog、不在 vendor case study）、但作為 baseline / 遷移源 在多處出現：

| 案例                                                                                                              | 跟 MySQL 的關係                             |
| ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| [9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)        | 從多套 RDBMS（含 MySQL）統一到 Aurora MySQL |
| [9.C20 Zomato TiDB → DynamoDB](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)         | TiDB（MySQL 相容）→ DynamoDB 對比           |
| [9.C29 Lemino RDB connection limit](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) | MySQL connection 限制問題（同 PostgreSQL）  |

業界 large MySQL 規模案例（engineering blog 來源）：

- GitHub：完全 MySQL OLTP、gh-ost 是他們開源工具
- Shopify：pod-based MySQL sharding、BFCM peak
- Slack：per-team MySQL sharding
- YouTube：Vitess 起源、超大 MySQL 集群

## 常見陷阱

- **直接 ALTER TABLE 大表**：lock 表 hours、production 停擺、必須用 online schema change
- **不用 GTID**：replication topology 變更困難、recover from failure 容易出錯
- **buffer pool 太小**：cache miss 高、IOPS 飆升
- **shard key 選錯**：hot shard 出現、整體吞吐達不到名義
- **connection 沒 pool**：跟 PostgreSQL 同樣問題、用 ProxySQL
- **semi-sync 對高吞吐 workload**：每次 commit 等 ack、寫吞吐降一半

## 下一步路由

- 平行：[PostgreSQL vendor](/backend/01-database/vendors/postgresql/)、[Aurora vendor](/backend/01-database/vendors/aurora/)（managed MySQL）
- 上游：[1.1 高併發資料存取](/backend/01-database/high-concurrency-access/)、[1.3 Transaction Boundary](/backend/01-database/transaction-boundary/)
- 下游：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)（MySQL 不適用時的替代）
- 跨模組：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) — connection / replication / lock contention 常見 MySQL bottleneck
- 官方：[MySQL Documentation](https://dev.mysql.com/doc/)、[Vitess](https://vitess.io/)、[PlanetScale](https://planetscale.com/)
