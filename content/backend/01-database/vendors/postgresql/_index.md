---
title: "PostgreSQL"
date: 2026-05-13
description: "多用途 OLTP 主流關聯式資料庫、MVCC、豐富 SQL 特性、是 Aurora / Cosmos DB / Spanner / CockroachDB / Aurora DSQL 的相容目標"
weight: 1
tags: ["backend", "database", "vendor", "postgresql", "sql"]
---

PostgreSQL 是 backend 預設關聯式資料庫的安全選擇。生態完整、SQL 功能豐富、MVCC 跟 transaction 模型穩定、新版本仍積極演進（pg17 加入 JSON_TABLE、平行 vacuum；pg18 加入 io_uring async）。Aurora（AWS managed）、CockroachDB、Aurora DSQL（2024-12 preview / 2025-05 GA）、Spanner（2024 PostgreSQL dialect）都把 PostgreSQL wire protocol 當作相容標的 — 它是 SQL DB 世界的 lingua franca。

## 教學路線：SQL baseline 與交易演進

PostgreSQL 服務頁的教學目標是建立 SQL baseline。讀者讀完後要能用 PostgreSQL 理解 transaction、schema evolution、query boundary、connection pressure 與 managed / distributed SQL 的比較基準。

| 學習段       | 核心問題                                                    | 對應段落                         |
| ------------ | ----------------------------------------------------------- | -------------------------------- |
| SQL baseline | PostgreSQL 為什麼常作為 OLTP 預設比較基準                   | 定位、適用場景                   |
| 容量邊界     | connection、write throughput、replica、storage 如何限制服務 | 容量特性、容量規劃要點           |
| 交易與查詢   | 複雜 SQL、JSONB、GIS、全文檢索如何影響資料模型              | 適用場景、跟其他 vendor 的取捨   |
| 演進與維護   | vacuum、partition、index、replication 如何成為長期責任      | 容量規劃要點、常見陷阱           |
| 替代路由     | 何時轉 Aurora、CockroachDB、Spanner、DynamoDB 或 OLAP       | 不適用場景、跟其他 vendor 的取捨 |

## 定位：OLTP 預設、SQL 工程深度

PostgreSQL 跟 MySQL 是兩大 SQL OLTP 主流、但設計取捨明顯不同：

- PostgreSQL 偏 *特性深度* — JSON、GIS、full-text search、partial index、CTE、window function 都成熟
- MySQL 偏 *簡單 query 效能 + 分片生態* — Vitess / PlanetScale 提供超大規模 [database sharding](/backend/knowledge-cards/database-sharding/)

選 PostgreSQL 的核心訴求：需要進階 SQL 特性、需要長期 schema evolution 彈性、信任 community-driven 演進、想避免單一 vendor lock-in（PostgreSQL 是 open source、可跨雲 / on-prem）。

## 容量特性

PostgreSQL 沒有「vendor 給的容量數字」、要靠 instance 配置 + tuning 推估。但有幾個工程上限要知道：

**單一 primary 寫吞吐**：

- 一般 m5.4xlarge 級 instance：5K-10K WPS（依 schema、index、commit fsync）
- 高階 r6i.16xlarge + io2 storage：30K-50K WPS
- 超過這個級別 → 應用層 [database sharding](/backend/knowledge-cards/database-sharding/) 或換 Aurora / Spanner

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

- 必須進入 [database sharding](/backend/knowledge-cards/database-sharding/) 或分散式 SQL
- 替代：CockroachDB、TiDB、Spanner、應用層 sharding

**2. 全球 multi-region active-active write**：

- PostgreSQL 是 single primary、不支援 multi-region active-active
- 替代：Aurora DSQL、Spanner、CockroachDB multi-region

**3. KV 簡單查詢 + sub-10ms p99**：

- PostgreSQL connection 開銷 + parsing + planning 已經 1-3ms
- KV-pattern workload 用 DynamoDB / Redis / Cosmos DB 更便宜更快

**4. 大規模 OLAP**：

- PostgreSQL 定位在 OLTP，analytics workload 交給 OLAP 系統
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

## 安全、DR 與角色分工

PostgreSQL 的 production 完整性不只來自 SQL 特性，也來自資料存取、備份復原、升級責任與事故證據的分工。這一段補上 PG baseline 原本留在 limitation 的三個缺口：Security / RLS / audit logging、cross-region DR、application developer vs DBA / SRE 視角。

| 責任面                | PostgreSQL 要回答的問題                                                          | 主要引用路徑                                                                                                                                                                                                         |
| --------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Access control / RLS  | table、row、function、extension 與 service account 權限如何切                    | [Security / RLS / Audit Logging](security-rls-audit-logging/)、[7.4 Data Protection](/backend/07-security-data-protection/data-protection-and-masking-governance/)、[Audit Log](/backend/knowledge-cards/audit-log/) |
| TLS / credential      | application 連線、DB user、憑證與 secret rotation 如何治理                       | [TLS / mTLS](/backend/knowledge-cards/tls-mtls/)、[Credential](/backend/knowledge-cards/credential/)、[Secret Management](/backend/knowledge-cards/secret-management/)                                               |
| Cross-region DR       | region 失效時要 async replica、PITR、Aurora Global Database 還是 distributed SQL | [Cross-region DR](cross-region-dr/)、[RPO](/backend/knowledge-cards/rpo/)、[RTO](/backend/knowledge-cards/rto/)、[Failover](/backend/knowledge-cards/failover/)、[PITR + WAL Archiving](pitr-wal-archiving/)         |
| Developer / DBA split | application schema、migration、query、index 與 rollback 誰負責                   | [Developer / DBA Responsibility Split](developer-dba-responsibility-split/)、[1.2 Schema Design](/backend/01-database/schema-design/)、[1.6 Migration Playbook](/backend/01-database/database-migration-playbook/)   |
| Incident evidence     | 資料事故中要留下哪些 query、timeline、restore 與 decision evidence               | [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)、[8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)                                 |

Access control / RLS 的判讀重點是把資料責任放在資料層與 application 層之間分工。PostgreSQL 支援 role、grant、schema、function security 與 row-level security；但 RLS 會把授權邏輯拉進 database，適合 multi-tenant row isolation、資料平台或共享 reporting schema，日常 OLTP 仍要保留 application authorization 與 audit trail。

TLS / credential 的判讀重點是連線安全與憑證生命週期。Self-managed PostgreSQL 要處理 server cert、client cert、DB user rotation 與 [connection pool](/backend/knowledge-cards/connection-pool/) 重連；managed PostgreSQL 常把 certificate、IAM auth 或 secret integration 交給平台，但 application pool、migration tool 與 read replica 仍要一起更新。

Cross-region DR 的判讀重點是 [RPO](/backend/knowledge-cards/rpo/) / [RTO](/backend/knowledge-cards/rto/) 與資料一致性。自管 PostgreSQL 可用 streaming replication、WAL archiving、PITR 與 Patroni 做 region [failover](/backend/knowledge-cards/failover/)；Aurora 把 backup、PITR 與 Global Database 交給 AWS；真正 active-active 或 global strong consistency 需求要回到 CockroachDB、Spanner 或 Aurora DSQL，single-primary PostgreSQL 保留為 region failover 與 async DR 路線。

Developer / DBA split 的判讀重點是把日常責任寫進流程。Application developer 擁有 query shape、transaction boundary、repository adapter 與 migration contract；DBA / SRE 擁有 backup、replication、pooler、extension、vacuum、index maintenance 與 DR drill；release gate 需要把兩邊 evidence 合在同一份 decision log。

## Managed PG 與相容變體路由

PostgreSQL wire protocol 已成為 managed SQL 與 distributed SQL 的相容目標。選型時要區分「PostgreSQL 本體」、「managed PostgreSQL」、「PostgreSQL-compatible distributed SQL」與「PostgreSQL extension ecosystem」四種不同責任。

| 變體                           | 適合情境                                                    | 主要代價 / 檢查點                                     | 下一步路由                                                                                                                                                            |
| ------------------------------ | ----------------------------------------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| RDS / self-managed PG          | 想接近 upstream、保留跨雲與 extension 彈性                  | 團隊承擔 HA、backup、upgrade、vacuum 與 pooler        | [Patroni HA](patroni-ha/)、[PITR + WAL Archiving](pitr-wal-archiving/)                                                                                                |
| Aurora PostgreSQL              | AWS 內 production OLTP、想轉移 HA / storage ops             | extension whitelist、cost model、cluster endpoint     | [→ Aurora](migrate-to-aurora/)、[Aurora vendor](/backend/01-database/vendors/aurora/)                                                                                 |
| Cloud SQL / AlloyDB            | GCP 內 managed PostgreSQL 與 Google operation model         | extension / version matrix、IAM / backup / cost model | [Managed PG Comparison](managed-pg-comparison/)                                                                                                                       |
| Azure Cosmos DB for PostgreSQL | Citus-based distributed PostgreSQL、tenant / shard workload | coordinator / worker topology、Citus 語意             | [Citus distributed](citus-distributed/)、[Database Sharding](/backend/knowledge-cards/database-sharding/)、[Cosmos DB vendor](/backend/01-database/vendors/cosmosdb/) |
| Neon / serverless PG           | preview、branch、稀疏 workload、dev environment             | cold start、connection、production sustained workload | 本頁 vs Neon 段、後續 serverless PG comparison                                                                                                                        |
| Aurora DSQL / CockroachDB      | global write、distributed SQL、region resiliency            | transaction retry、extension gap、latency / cost      | [→ Aurora DSQL](migrate-to-aurora-dsql/)、[→ CockroachDB](migrate-to-cockroachdb/)                                                                                    |

Managed PG 變體的引用規則是先查 compatibility，再談 migration。Extension whitelist、backup / restore API、logical replication 支援、connection endpoint 行為與 pricing 都是時間敏感 claim；實作前要回到官方文件確認版本，並把確認日期留在 migration plan 或 decision log。

## Deep article + Migration playbook（已完成）

| 主題                                                  | 文章                                                          | 類型                                                                        |
| ----------------------------------------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Streaming replication topology + LSN + slot           | [replication-topology](replication-topology/)                 | Deep article                                                                |
| pg_repack / pg-osc 跟 PG 內建 ALTER 行為              | [online-schema-change](online-schema-change/)                 | Deep article                                                                |
| Process-per-connection model + pooler 必要性          | [connection-scaling](connection-scaling/)                     | Deep article                                                                |
| pgBouncer + PgCat connection pool                     | [pgbouncer-config](pgbouncer-config/)                         | Deep article                                                                |
| Patroni HA + DCS-based failover                       | [patroni-ha](patroni-ha/)                                     | Deep article                                                                |
| Autovacuum tuning + bloat 治理                        | [autovacuum-tuning](autovacuum-tuning/)                       | Deep article                                                                |
| Logical replication + Debezium CDC                    | [logical-replication-debezium](logical-replication-debezium/) | Deep article                                                                |
| Citus distributed extension                           | [citus-distributed](citus-distributed/)                       | Deep article                                                                |
| BDR / pgEdge / Bucardo multi-master                   | [bdr-multi-master](bdr-multi-master/)                         | Deep article                                                                |
| MVCC + lock model（PG 並行控制核心）                  | [mvcc-lock-model](mvcc-lock-model/)                           | Deep article                                                                |
| EXPLAIN / auto_explain / pg_hint_plan                 | [query-optimization](query-optimization/)                     | Deep article                                                                |
| Index method 選型決策樹（B-tree / GIN / GiST / BRIN） | [index-selection](index-selection/)                           | Deep article                                                                |
| Declarative partitioning + pg_partman                 | [declarative-partitioning](declarative-partitioning/)         | Deep article                                                                |
| JSONB binary storage + GIN index                      | [jsonb-deep-dive](jsonb-deep-dive/)                           | Deep article                                                                |
| Full-text search（tsvector + pg_trgm）                | [full-text-search](full-text-search/)                         | Deep article                                                                |
| Extension ecosystem（pgvector / TimescaleDB 等）      | [extension-ecosystem](extension-ecosystem/)                   | Deep article                                                                |
| TimescaleDB hypertable + CAGG + compression           | [timescaledb-deep-dive](timescaledb-deep-dive/)               | Deep article                                                                |
| pgvector HNSW / IVFFlat ANN search                    | [pgvector-deep-dive](pgvector-deep-dive/)                     | Deep article                                                                |
| PostGIS geometry / geography + GiST                   | [postgis-deep-dive](postgis-deep-dive/)                       | Deep article                                                                |
| PITR + WAL archiving                                  | [pitr-wal-archiving](pitr-wal-archiving/)                     | Deep article                                                                |
| Replication slot management（含 PG 17 failover slot） | [replication-slot-management](replication-slot-management/)   | Deep article                                                                |
| SQL features baseline + MySQL 對比                    | [sql-features-baseline](sql-features-baseline/)               | Deep article                                                                |
| Hands-on 操作路線                                     | [hands-on](hands-on/)                                         | 操作型章節群                                                                |
| Major version upgrade（N → N+1 pg_upgrade）           | [major-version-upgrade](major-version-upgrade/)               | Migration playbook（5-type 漏類 / 接近 Type B 但需 upgrade-specific audit） |
| → Aurora PostgreSQL                                   | [migrate-to-aurora](migrate-to-aurora/)                       | Migration playbook（Type C）                                                |
| → Aurora DSQL（PG wire-compat distributed）           | [migrate-to-aurora-dsql](migrate-to-aurora-dsql/)             | Migration playbook（Type E）                                                |
| → CockroachDB                                         | [migrate-to-cockroachdb](migrate-to-cockroachdb/)             | Migration playbook（Type E）                                                |
| Multi-region + GDPR rollout                           | [multi-region-gdpr-rollout](multi-region-gdpr-rollout/)       | Migration playbook（Type F）                                                |
| Partition redesign                                    | [partition-redesign](partition-redesign/)                     | Migration playbook（Type F）                                                |

## 補充正文路由

當前 deep article、migration playbook、補充正文與 hands-on 已 cover replication / HA / OSC / connection / CDC / sharding / multi-master / MVCC / query opt / index / partitioning / JSONB / FTS / extension（含 TimescaleDB / pgvector / PostGIS）/ backup / slot / SQL features / upgrade / migration / security / DR / managed variant 等維度。下列補充正文用來承接 overview 中提到的延伸議題：

- **[Logical decoding plugins deep dive](logical-decoding-plugins/)**：wal2json / pgoutput / decoderbufs 對位、CDC pipeline 整合
- **[pg_partman advanced](pg-partman-advanced/)**：retention 跟 child partition 自動 management
- **[Connection pooler comparison](connection-pooler-comparison/)**：PgBouncer vs Pgcat vs Odyssey 細部對比
- **[Aurora I/O-Optimized vs standard](aurora-io-optimized-cost/)**：cost model 取捨
- **[AlloyDB / Cloud SQL 比較](managed-pg-comparison/)**：GCP managed PG 選型

上述補充篇已完成正文，並保留既有引用路徑。Logical decoding 接 [Logical Replication + Debezium](logical-replication-debezium/) 與 [Replication Slot Management](replication-slot-management/)；pg_partman advanced 接 [Declarative Partitioning](declarative-partitioning/)；pooler comparison 接 [Connection Scaling](connection-scaling/) 與 [pgBouncer Config](pgbouncer-config/)；Aurora cost 接 [→ Aurora](migrate-to-aurora/)；AlloyDB / Cloud SQL 接 [Managed PG Comparison](managed-pg-comparison/)。

## 案例對照

PostgreSQL 沒有直接的 09 case（多數 09 case 用 managed vendor）、但作為 *baseline 跟遷移源頭* 在許多 case 出現：

| 案例                                                                                                                  | 跟 PostgreSQL 的關係                       |
| --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| [9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)            | 從多套 RDBMS（含 PostgreSQL）統一到 Aurora |
| [9.C32 Clearent Azure SQL Hyperscale](/backend/09-performance-capacity/cases/clearent-azure-sql-hyperscale-payments/) | Azure 生態替代 PostgreSQL 的選擇           |
| [9.C29 Lemino RDB connection limit](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/)     | PostgreSQL/MySQL 都有的 connection 限制    |

## 已知 Limitation 與 Audit 紀錄

本 vendor 頁的 22 篇 deep article + 6 篇 migration playbook 經過 4-reviewer audit（A 寫作規範 / B 跨檔一致性 / C 技術準確性 / D 框架偏誤）、Phase 1-3 修法完成。承認以下 limitation：

- **PG narrative bias**：pgvector / TimescaleDB / extension-ecosystem / Citus 四篇對「PG 取代專業 DB」描述偏 PG-favoring；對手 vendor（Pinecone / InfluxDB / Vitess）的優勢段相對簡短。讀者選型時、請以 cost / ops / scale 三軸綜合判斷、不依本 vendor 頁單一視角。
- **Anti-recommendation 深度不一**：bdr-multi-master / extension-ecosystem 有「99% 不需要」明確邊界、其他篇章邊界較柔（如「Vector 量 > 5-20M」是粗略門檻）。實際 production 決策請參考多 vendor 對照 + 自家 workload 量測。
- **Sibling cross-link 狀態**：MySQL ↔ PG sibling、PG 既有 ↔ 新章節 cross-link 已補（refer [#136 卡](/report/sibling-vendor-cross-link-bidirectionality-audit/)）；本輪同步補 Aurora / CockroachDB / Spanner / Cosmos DB / DynamoDB vendor 頁的反向 sibling 路由，剩餘精修可在各 migration playbook 補更細的 step-by-step 對照。
- **時間敏感 vendor claim**：Aurora DSQL（2024-12 preview / 2025-05 GA）/ pgvector（0.8 iterative scan）/ TimescaleDB version matrix / DSQL extension 支援範圍持續演進、本 vendor 頁以 2025-2026 公開狀態為準、實作前請以 vendor 官方 docs 為準（refer [#137 卡](/report/vendor-feature-time-sensitivity-claim-verification/)）。
- **補充維度已正文化**：[Security / RLS / audit logging](security-rls-audit-logging/)、[cross-region DR](cross-region-dr/)、[application developer vs DBA 視角分工](developer-dba-responsibility-split/)、[YugabyteDB / TiDB migration playbook](migrate-to-yugabytedb-tidb/)、[specialized PG variants](specialized-pg-variants/) 已補成正文。本輪也補上跨 vendor 反向連結與時間敏感 claim 路由；下一輪可集中在 migration playbook 的操作步驟與 lab 化。

詳細 audit findings 跟修法見 [#136 Sibling Vendor Cross-Link Bidirectionality](/report/sibling-vendor-cross-link-bidirectionality-audit/) / [#137 Vendor Feature 時間敏感性](/report/vendor-feature-time-sensitivity-claim-verification/) / [#138 Cross-Reviewer Convergence](/report/cross-reviewer-convergence-priority-weighting/)。

## 常見陷阱

- **connection 沒 pool 直接連**：1000 application instance × 30 connection = 30K connection、PostgreSQL 撐不住
- **沒 vacuum 治理**：dead tuple 累積、table bloat、query 變慢
- **大表沒 partition**：> 1 TB 單表的 vacuum / index rebuild 變成事故
- **index 不 review**：寫吞吐被舊 index 拖垮
- **跨 AZ sync replication 給寫入吞吐高的 workload**：每次 commit 等 standby ack、寫吞吐減半
- **logical replication 拖太多 publication**：可能造成 primary WAL 堆積、disk 爆

## 下一步路由

- 完整 T1 對照：[01-database vendors index](/backend/01-database/vendors/)
- 平行：[MySQL vendor](/backend/01-database/vendors/mysql/)、[Aurora vendor](/backend/01-database/vendors/aurora/)（managed PostgreSQL）
- 操作：[PostgreSQL Hands-on](/backend/01-database/vendors/postgresql/hands-on/)（local lab、pool、PITR、migration evidence、HA drill）
- 上游：[1.1 高併發資料存取](/backend/01-database/high-concurrency-access/)、[1.3 Transaction Boundary](/backend/01-database/transaction-boundary/)
- 下游：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)（PostgreSQL 不適用時的替代）/ [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)（PostgreSQL 不夠用時的升級路徑）
- 跨模組：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) — connection / replication lag / vacuum 都是 PostgreSQL 常見 bottleneck 源
- 官方：[PostgreSQL Documentation](https://www.postgresql.org/docs/)
