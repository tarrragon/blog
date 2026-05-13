---
title: "PostgreSQL"
date: 2026-05-13
description: "多用途 OLTP 主流關聯式資料庫、MVCC、豐富 SQL 特性、是 Aurora / Cosmos DB / Spanner / CockroachDB / Aurora DSQL 的相容目標"
weight: 1
tags: ["backend", "database", "vendor", "postgresql", "sql"]
---

PostgreSQL 是 backend 預設關聯式資料庫的安全選擇。生態完整、SQL 功能豐富、MVCC 跟 transaction 模型穩定、新版本仍積極演進（pg17 加入 JSON_TABLE、平行 vacuum；pg18 加入 io_uring async）。Aurora（AWS managed）、CockroachDB、Aurora DSQL（2024）、Spanner（2024 PostgreSQL dialect）都把 PostgreSQL wire protocol 當作相容標的 — 它是 SQL DB 世界的 lingua franca。

## 定位：OLTP 預設、SQL 工程深度

PostgreSQL 跟 MySQL 是兩大 SQL OLTP 主流、但設計取捨明顯不同：

- PostgreSQL 偏 *特性深度* — JSON、GIS、full-text search、partial index、CTE、window function 都成熟
- MySQL 偏 *簡單 query 效能 + 分片生態* — Vitess / PlanetScale 提供超大規模分片

選 PostgreSQL 的核心訴求：需要進階 SQL 特性、需要長期 schema evolution 彈性、信任 community-driven 演進、想避免單一 vendor lock-in（PostgreSQL 是 open source、可跨雲 / on-prem）。

## 容量特性

PostgreSQL 沒有「vendor 給的容量數字」、要靠 instance 配置 + tuning 推估。但有幾個工程上限要知道：

**單一 primary 寫吞吐**：

- 一般 m5.4xlarge 級 instance：5K-10K WPS（依 schema、index、commit fsync）
- 高階 r6i.16xlarge + io2 storage：30K-50K WPS
- 超過這個級別 → 應用層 sharding 或換 Aurora / Spanner

**Connection 上限**：

- 預設 100 connection、每個 connection ~10MB RAM
- 1000+ connection 必須 pgBouncer / PgCat 共享 pool
- 對應 [9.C29 Lemino case](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) — RDB connection limit 是 surge 場景的隱性 bottleneck

**Read replica**：

- streaming replication：1 個 primary + 多個 standby（async / sync）
- 跨 AZ replication lag 通常 < 100ms、跨 region 可能秒級
- 跟 Aurora 比、自管 PostgreSQL replication lag 較大

**Storage 上限**：

- 單一 table 32 TB（PostgreSQL 設計上限）
- 實務上單表超過 1 TB 開始有 vacuum / index 問題、建議 partition

## 適用場景

**1. 多用途 OLTP、複雜查詢**：

- 複雜 JOIN、CTE、window function、subquery
- 訂單系統、會員系統、訂閱方案、權限 RBAC
- 需要 strong consistency + ACID transaction

**2. JSON / 半結構化資料**：

- JSONB column 支援 indexing、partial query
- 比 MongoDB 適合 *主要結構化 + 部分 JSON* workload
- 不適合主要 document workload（用 MongoDB / Cosmos DB）

**3. 地理 / 全文檢索**：

- PostGIS 是業界標準 GIS extension
- 全文檢索（ts_vector）對中等規模夠用、超大規模用 Elasticsearch

**4. 進階特性需求**：

- partial index（WHERE 條件下才建 index）
- exclusion constraints（避免 booking 重疊）
- range types（時間 / 數字範圍）
- logical decoding / CDC（Debezium、pgcapture）
- foreign data wrapper（query 跨 DB）

**5. 跨雲 / on-prem 部署**：

- 不想 vendor lock-in
- 可用 Patroni / Stolon / pg_auto_failover 做 HA
- 對應 [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 的 CockroachDB / Aurora DSQL 比較段

**6. 中小規模高峰場景**：

- 流量 < 10K WPS 級別、PostgreSQL 自管或 RDS 通常夠
- 流量更高、考慮 Aurora（同 wire protocol、storage 升級）

## 不適用場景

**1. 極高寫入吞吐（單機 > 50K WPS）**：

- 必須 sharding 或換分散式 SQL
- 替代：CockroachDB、TiDB、Spanner、應用層 sharding

**2. 全球 multi-region active-active write**：

- PostgreSQL 是 single primary、不支援 multi-region active-active
- 替代：Aurora DSQL、Spanner、CockroachDB multi-region

**3. KV 簡單查詢 + sub-10ms p99**：

- PostgreSQL connection 開銷 + parsing + planning 已經 1-3ms
- KV-pattern workload 用 DynamoDB / Redis / Cosmos DB 更便宜更快

**4. 大規模 OLAP**：

- PostgreSQL 是 OLTP、不是 OLAP
- 大數據分析用 ClickHouse / BigQuery / Snowflake / Redshift / Synapse

**5. 連線量極大 SaaS（每個用戶一個 connection）**：

- 即使有 pgBouncer、超大連線量仍是 PostgreSQL 結構性限制
- 對應 [9.C29 Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) 案例 — 流量上升 connection 爆是換 DynamoDB 的主因

## 跟其他 vendor 的取捨

**vs MySQL**：

- PostgreSQL：SQL 特性深、JSON / GIS / window 完整、replication 較簡單但 lag 較大
- MySQL：簡單 query 效能好、replication 機制成熟、Vitess 分片生態強
- 選 PostgreSQL：需要進階 SQL、複雜 query、JSON workload
- 選 MySQL：高併發簡單 query、需要 sharding、已用 MySQL 生態

**vs Aurora（同 PostgreSQL wire protocol）**：

- PostgreSQL：自管 / RDS、特性接近 upstream、跨雲可用
- Aurora：AWS managed、storage / compute 分離、更多 read replica
- 選 PostgreSQL：跨雲、想最新特性、預算敏感
- 選 Aurora：AWS 生態、需要更快 failover + 更多 read replica
- 詳見 [Aurora vendor page](/backend/01-database/vendors/aurora/)

**vs CockroachDB（PostgreSQL wire protocol 相容）**：

- PostgreSQL：single-primary OLTP、SQL 特性完整
- CockroachDB：multi-region 強一致 SQL、PostgreSQL wire 相容但部分特性缺
- 選 PostgreSQL：single-region 或 read replica 跨 region 夠
- 選 CockroachDB：必須 multi-region active-active write
- 詳見 [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)

**vs Spanner / Aurora DSQL（全球分散式 SQL）**：

- PostgreSQL：傳統設計、跨 region 是 async replication
- Spanner / Aurora DSQL：全球線性化、跨 region 強一致
- 選 PostgreSQL：90% 場景夠用、便宜、容易
- 選 Spanner / Aurora DSQL：金融交易、ticketing inventory、必須全球強一致

**vs DynamoDB**：

- 詳見 [1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) 的 connection model 對比段

**vs Neon（PostgreSQL serverless）**：

- PostgreSQL：standard、自管或 RDS
- Neon：branch-based、scale-to-zero、適合 dev / preview environment
- 選 Neon：dev / preview、稀疏 workload、CI 用
- 選 PostgreSQL：production sustained workload

## 容量規劃要點

**1. Connection pool 必須有**：

- 直接連 1000+ connection 會壓垮 PostgreSQL
- pgBouncer（最簡單、transaction pooling）
- PgCat（rust 寫的進階替代、支援 sharding）
- application 層 pool（HikariCP、SQLAlchemy pool）
- 通常組合使用：application pool 30-50 connection × 多 instance → pgBouncer 共享 → PostgreSQL 200 connection
- 對應 [Connection Pool 卡片](/backend/knowledge-cards/connection-pool/)

**2. Replication 配置**：

- streaming replication：async / sync / [quorum](/backend/knowledge-cards/quorum/)
- 跨 AZ async：lag 通常 < 100ms、failover 1-2 分鐘
- 跨 AZ sync：lag 接近 0、但寫入要等 standby ack、會降寫吞吐
- 跨 region 通常 async
- HA 工具：Patroni（最常見）、pg_auto_failover、Stolon

**3. Vacuum 跟 bloat 治理**：

- PostgreSQL MVCC 會留下 dead tuples、必須 vacuum
- autovacuum 配置：throttle 大表、避免在 peak 跑
- bloat 監控：pg_stat_user_tables 看 dead_tup ratio
- 大表 vacuum 可能要 hours、影響 maintenance window

**4. 大表 partitioning**：

- 單表 > 1 TB 建議 partition（按時間、按 tenant）
- partition pruning 讓 query 只掃需要的 partition
- partition 限制：cross-partition unique constraint、跨 partition join 較慢

**5. Index 策略**：

- 預設 B-tree、適合大多數 query
- partial index 對 boolean / status column 特別有用
- GIN / GiST 對 JSON / full-text / GIS
- index 太多會拖累寫入、定期 review 未用 index（pg_stat_user_indexes）

## 預計實作話題（後續擴充）

- pgBouncer / PgCat 配置 best practice
- streaming replication + Patroni HA 部署
- Logical decoding 跟 Debezium CDC
- 從 PostgreSQL 升級到 Aurora 的遷移流程
- Schema migration 工具對比（Flyway / Liquibase / golang-migrate / Atlas）
- Index 選型決策樹
- Vacuum / autovacuum tuning
- Partitioning 設計（range / list / hash）
- Foreign data wrapper（query 跨 DB）

## 案例對照

PostgreSQL 沒有直接的 09 case（多數 09 case 用 managed vendor）、但作為 *baseline 跟遷移源頭* 在許多 case 出現：

| 案例                                                                                                                  | 跟 PostgreSQL 的關係                       |
| --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| [9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)            | 從多套 RDBMS（含 PostgreSQL）統一到 Aurora |
| [9.C32 Clearent Azure SQL Hyperscale](/backend/09-performance-capacity/cases/clearent-azure-sql-hyperscale-payments/) | Azure 生態替代 PostgreSQL 的選擇           |
| [9.C29 Lemino RDB connection limit](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/)     | PostgreSQL/MySQL 都有的 connection 限制    |

## 常見陷阱

- **connection 沒 pool 直接連**：1000 application instance × 30 connection = 30K connection、PostgreSQL 撐不住
- **沒 vacuum 治理**：dead tuple 累積、table bloat、query 變慢
- **大表沒 partition**：> 1 TB 單表的 vacuum / index rebuild 變成事故
- **index 不 review**：寫吞吐被舊 index 拖垮
- **跨 AZ sync replication 給寫入吞吐高的 workload**：每次 commit 等 standby ack、寫吞吐減半
- **logical replication 拖太多 publication**：可能造成 primary WAL 堆積、disk 爆

## 下一步路由

- 平行：[MySQL vendor](/backend/01-database/vendors/mysql/)、[Aurora vendor](/backend/01-database/vendors/aurora/)（managed PostgreSQL）
- 上游：[1.1 高併發資料存取](/backend/01-database/high-concurrency-access/)、[1.3 Transaction Boundary](/backend/01-database/transaction-boundary/)
- 下游：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)（PostgreSQL 不適用時的替代）/ [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)（PostgreSQL 不夠用時的升級路徑）
- 跨模組：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) — connection / replication lag / vacuum 都是 PostgreSQL 常見 bottleneck 源
- 官方：[PostgreSQL Documentation](https://www.postgresql.org/docs/)
