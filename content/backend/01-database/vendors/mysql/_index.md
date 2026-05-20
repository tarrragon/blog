---
title: "MySQL"
date: 2026-05-13
description: "高併發網路服務常用關聯式資料庫、Vitess / PlanetScale 分片生態、GitHub / Shopify / Facebook 規模驗證"
weight: 2
tags: ["backend", "database", "vendor", "mysql", "sql"]
---

MySQL 是大型網路服務的常見選擇、簡單 query 效能跟 [database sharding](/backend/knowledge-cards/database-sharding/) 生態（Vitess / PlanetScale）成熟。GitHub、Shopify、Slack、Facebook（YouTube 從 MySQL 起家）等大規模服務的核心 OLTP 多採 MySQL。InnoDB engine 的 row-level lock、clustered index、buffer pool tuning 都被深度驗證。

## 教學路線：高併發 OLTP 與分片生態

MySQL 服務頁的教學目標是把「簡單 SQL 查詢」推進到高併發 OLTP、replication、online schema change 與 [sharding governance](/backend/knowledge-cards/database-sharding/)。讀者讀完後要能判斷 MySQL 何時是成熟預設、何時已經進入 Vitess / PlanetScale 或 application sharding 的討論。

| 學習段        | 核心問題                                                 | 對應段落                   |
| ------------- | -------------------------------------------------------- | -------------------------- |
| OLTP 基線     | MySQL 適合哪種大量簡單查詢與交易路徑                     | 定位、適用場景             |
| Replication   | replica、failover、lag 與 read scaling 如何影響服務      | 容量特性、容量規劃要點     |
| Schema change | online schema change 與 migration 如何保護高流量服務     | 容量規劃要點、預計實作話題 |
| Sharding      | Vitess、PlanetScale 與 application sharding 何時變成主線 | 跟其他 vendor 的取捨       |
| 替代路由      | 何時轉 PostgreSQL、Aurora、DynamoDB 或 distributed SQL   | 不適用場景、下一步路由     |

## 定位：高併發簡單 SQL + 強分片生態

MySQL 跟 PostgreSQL 是 SQL OLTP 兩大主流、但設計取捨明顯不同：

- MySQL 偏 *簡單 query 效能 + 分片生態* — InnoDB clustered index 對 primary key range query 特別快、Vitess 提供超大規模透明 [database sharding](/backend/knowledge-cards/database-sharding/)
- PostgreSQL 偏 *特性深度* — 詳見 [PostgreSQL vendor page](/backend/01-database/vendors/postgresql/)

選 MySQL 的核心訴求：需要超大規模分片（> 100 TB、> 100K WPS）、簡單 query 為主、已用 MySQL 生態工具鏈（gh-ost、pt-online-schema-change）。

## 容量特性

**單一 primary 寫吞吐**：

- 標準 InnoDB：10K-30K WPS（依 row size、commit sync、index 數量）
- 高階 instance + 優化 schema：50K-100K WPS
- 超過此級別 → [Vitess sharding](vitess-sharding/) 或 PlanetScale

**Connection 上限**：

- 預設 max_connections = 151、實務常設 1000-5000
- 每個 connection thread stack ~3 MB + session buffer 累積、active 高峰時 ~8-10 MB（thread + sort/join buffer）
- 仍建議 ProxySQL / connection pool 限制 backend connection 數

**Replication**：

- async / semi-sync / GTID-based
- 跨 AZ async lag 通常 < 100ms
- 跨 region 通常用 chain replication 或 binlog 同步

**Storage 上限**：

- 單一 table 64 TB（InnoDB 設計上限）
- 實務超過 1 TB 表建議分片

## 適用場景

**1. 大規模 OLTP + 分片需求**：

- 流量 > 50K WPS、必須進入 [database sharding](/backend/knowledge-cards/database-sharding/) 設計
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
- Maxwell / Debezium MySQL（[CDC](/backend/knowledge-cards/change-data-capture/)）

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

- MySQL 定位在 OLTP，analytics workload 交給 OLAP 系統
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

**vs DynamoDB（document/KV 替代）**：

- MySQL：SQL、有 transaction、ad-hoc query、connection-based
- DynamoDB：KV、partition 透明、無 connection 限制、5 個 9 SLA
- 選 MySQL：需要 ad-hoc query、複雜 JOIN、SQL transaction
- 選 DynamoDB：access pattern 固定、AWS-only、想避免 connection limit 問題
- 詳見 [1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) 的 connection model 對比

**vs Spanner / CockroachDB / Aurora DSQL（distributed SQL）**：

- MySQL + Vitess：自管 sharding、operational 重、跨雲可用
- Spanner / CockroachDB / Aurora DSQL：分散式 SQL、跨 region 強一致、transparent sharding
- 選 MySQL + Vitess：已有 MySQL 投資、有能力管 Vitess、預算敏感
- 選 distributed SQL：需要 multi-region 強一致、不想自管 sharding
- 詳見 [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)

**vs MongoDB（document 替代）**：

- MySQL：SQL + JSON column 補充
- MongoDB：document 為主、aggregation pipeline 強、schema-flexible
- 選 MySQL：主要結構化、少量半結構化
- 選 MongoDB：document 占主要 schema、aggregation 工作負載

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

- innodb_buffer_pool_size：dedicated server 70-75%、shared server 30-50%（詳見 [InnoDB Tuning](innodb-tuning/)）
- innodb_flush_log_at_trx_commit：1（durable）vs 2（faster）vs 0（fastest, 不安全）
- innodb_io_capacity：依 storage 類型調整

## Anti-recommendation 與升級路由

MySQL 的成熟生態容易讓讀者過早引入重工具。這一段補上 deep article audit 提到的 anti-recommendation 缺口：先說何時維持簡單 MySQL 路徑，再說何時升級到 ProxySQL、Orchestrator、gh-ost、Vitess、PlanetScale 或 distributed SQL。

| 機制                 | 維持簡單設計的條件                                            | 升級訊號                                                     | 主要引用路徑                                                                                                                  |
| -------------------- | ------------------------------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| Replication          | 單 primary + 1-2 replica，lag 可被 read routing 容忍          | failover 反覆手動、GTID gap、semi-sync fallback              | [Replication Topology](replication-topology/)、[Orchestrator Failover](orchestrator-failover/)                                |
| Online schema change | 小表、maintenance window 足夠、MySQL 8.0 instant DDL 可 cover | 大表 ALTER 需 hours、metadata lock 影響 production           | [Online Schema Change Tools](online-schema-change-tools/)、[6.11 Migration Safety](/backend/06-reliability/migration-safety/) |
| ProxySQL             | application pool + primary endpoint 已能控制連線              | read/write routing、lag-aware routing、connection storm      | [ProxySQL Config](proxysql-config/)、[Connection Pool](/backend/knowledge-cards/connection-pool/)                             |
| Vitess / sharding    | 單 primary 寫入與資料量仍在可維護範圍                         | > 50K WPS、> 100 TB、shard key 已明確、跨 shard query 可接受 | [Vitess Sharding](vitess-sharding/)、[Database Sharding](/backend/knowledge-cards/database-sharding/)                         |
| PlanetScale          | 團隊已有 DBA / SRE 能力管理 Vitess 或自管 MySQL               | 想把 Vitess ops、schema branch workflow 與 failover 交給平台 | [→ PlanetScale](migrate-to-planetscale/)、[Vitess → PlanetScale](migrate-vitess-to-planetscale/)                              |
| Distributed SQL      | workload 仍是 single-region OLTP 或 Vitess 可解               | multi-region 強一致、cross-shard transaction 是核心需求      | [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)                                                         |

Replication 的簡單路徑是 GTID + async replica + 明確 read routing。當 failover 仍靠人工判斷、replica re-pointing 反覆出錯、或 semi-sync fallback 沒有被監控時，才需要把 Orchestrator、ProxySQL 與 incident runbook 放進同一條 HA 路徑。

Online schema change 的簡單路徑是先判斷 MySQL 8.0 instant / inplace DDL 能否 cover。只有大表 rewrite、長時間 metadata lock、FK / trigger 複雜互動或 maintenance window 不足時，才讓 gh-ost / pt-online-schema-change 成為主線工具。

Sharding 的簡單路徑是延後到資料形狀穩定後再做。Vitess 能把 MySQL 推到超大規模，但它也引入 VTGate、VTTablet、VReplication、VSchema、resharding workflow 與跨 shard transaction 邊界；[shard key](/backend/knowledge-cards/database-sharding/) 還沒穩定時，應先用 schema、index、read replica、partition 與容量治理延長單 primary 壽命。

Managed sharding 的簡單路徑是先確認團隊想轉移哪一層責任。PlanetScale 解的是 Vitess operation、branch-based schema workflow 與 managed failover；FK、cross-shard query、connection pool 與 cost model 仍要在 migration playbook 中驗證。

## Deep article + Migration playbook（已完成）

| 主題                                                 | 文章                                                            | 類型                         |
| ---------------------------------------------------- | --------------------------------------------------------------- | ---------------------------- |
| Replication topology（async / semi-sync / GTID）配置 | [replication-topology](replication-topology/)                   | Deep article                 |
| gh-ost / pt-online-schema-change 對比                | [online-schema-change-tools](online-schema-change-tools/)       | Deep article                 |
| ProxySQL 配置跟 query routing                        | [proxysql-config](proxysql-config/)                             | Deep article                 |
| Orchestrator failover 設計                           | [orchestrator-failover](orchestrator-failover/)                 | Deep article                 |
| InnoDB tuning（buffer pool / log / IO）              | [innodb-tuning](innodb-tuning/)                                 | Deep article                 |
| Binary log + Maxwell / Debezium CDC                  | [binlog-cdc](binlog-cdc/)                                       | Deep article                 |
| Vitess sharding 設計                                 | [vitess-sharding](vitess-sharding/)                             | Deep article                 |
| 8.0 modern SQL（CTE / window / JSON_TABLE）          | [modern-sql-features](modern-sql-features/)                     | Deep article                 |
| Group Replication / InnoDB Cluster 部署              | [group-replication](group-replication/)                         | Deep article                 |
| Query optimization deep dive                         | [query-optimization](query-optimization/)                       | Deep article                 |
| Partitioning（range / list / hash / sub-partition）  | [partitioning](partitioning/)                                   | Deep article                 |
| PITR + Backup strategy                               | [pitr-backup](pitr-backup/)                                     | Deep article                 |
| Lock contention（gap / next-key / deadlock）         | [lock-contention](lock-contention/)                             | Deep article                 |
| 5.7 → 8.0 major version upgrade                      | [major-version-upgrade](major-version-upgrade/)                 | Migration playbook（Type E） |
| 從自管 MySQL 遷到 Aurora MySQL                       | [migrate-to-aurora](migrate-to-aurora/)                         | Migration playbook（Type C） |
| 從自管 MySQL 遷到 PlanetScale                        | [migrate-to-planetscale](migrate-to-planetscale/)               | Migration playbook（Type E） |
| 自管 Vitess 遷到 PlanetScale                         | [migrate-vitess-to-planetscale](migrate-vitess-to-planetscale/) | Migration playbook（Type C） |
| 從 MySQL 遷到 PostgreSQL                             | [migrate-to-postgresql](migrate-to-postgresql/)                 | Migration playbook           |

## 後續擴充候選

當前 deep article + migration playbook 已 cover 17 個主題、涵蓋 ops / schema / failover / tuning / SQL features / sharding / backup / migration 八大維度。未來可考慮深化：

- **Encryption at rest + TLS in transit + key management**：對應 PG TLS-mTLS 議題
- **Audit log + SIEM 整合**：MySQL Enterprise Audit Plugin 跟 Splunk / Elastic Security 整合
- **MySQL Document Store（X-Protocol）**：少用但對特定 use case 有興趣
- **Multi-source replication topology**：1 個 replica 從 N 個 primary 拉、用於 sharded environment 整合
- **HeatWave（MySQL OLAP add-on）**：Oracle 推的 HTAP solution、跟 ClickHouse / Snowflake 對比
- **Cross-buffer memory contention deep dive**：buffer pool / connection thread / temp table / sort buffer 之間的 RAM 競爭、跟 OS swap 互動
- **Metadata lock deep dive**：DDL / long-running SELECT / FK 互動造成的 stalls

上述候選先接既有路由。Encryption / TLS / key management 先接 [TLS / mTLS](/backend/knowledge-cards/tls-mtls/) 與 [Secret Management](/backend/knowledge-cards/secret-management/)；audit log 先接 [Audit Log](/backend/knowledge-cards/audit-log/) 與 07 資安資料保護；Document Store 先接 [MongoDB vendor](/backend/01-database/vendors/mongodb/) 與 [1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)；multi-source replication 先接 [Replication Topology](replication-topology/)；HeatWave 先接 OLAP 替代路由；memory contention 先接 [InnoDB Tuning](innodb-tuning/)；metadata lock 先接 [Lock Contention](lock-contention/) 與 [Online Schema Change Tools](online-schema-change-tools/)。

## 已知 limitation（多輪 audit 結論）

17 篇 batch 跑過 4-reviewer audit（寫作規範 / 跨檔一致性 / 技術準確性 / 結構性質疑）後留下的 limitation：

- *Framework bias*：5 篇 migration playbook 全落在 Type A / C / E、沒一篇 Type B / D / F。這反映 *MySQL 領域 migration 的本質*（多數情境是 schema 差 / operational 轉手 / paradigm shift）、也可能反映 [6 type framework](/posts/migration-playbook-methodology/) 的覆蓋限制
- *Anti-recommendation 已補 overview 路由*：本頁新增「Anti-recommendation 與升級路由」作為總入口；各 deep article 之後仍可逐篇補「何時維持簡單設計」段。
- *Real case anchor 已補 overview 路由*：本頁新增「真實案例 anchor」把 Shopify、Slack、GitHub gh-ost、YouTube / Vitess 與既有 09 case 串回 deep article；各 deep article 後續可把這些 anchor 下沉到對應機制段。
- *PG 對比 narrative*：對比段公允度尚可、但 PG 弱點（vacuum ops 開銷 / connection-per-process model / replication slot 治理）較少在 MySQL 視角展開、單方面對比偶有偏 MySQL 不利

## 案例對照

MySQL 沒有直接的 09 case（大規模 MySQL 多在 engineering blog、不在 vendor case study）、但作為 baseline / 遷移源 在多處出現：

| 案例                                                                                                              | 跟 MySQL 的關係                             |
| ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| [9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)        | 從多套 RDBMS（含 MySQL）統一到 Aurora MySQL |
| [9.C20 Zomato TiDB → DynamoDB](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)         | TiDB（MySQL 相容）→ DynamoDB 對比           |
| [9.C29 Lemino RDB connection limit](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) | MySQL connection 限制問題（同 PostgreSQL）  |

## 真實案例 anchor

MySQL 真實案例的責任是把大規模 OLTP 的機制壓力放回正文。案例不只證明「某公司使用 MySQL」，而是提供 schema change、CDC、sharding、connection、queue 整合或 managed migration 的壓力來源。

| 案例 / 來源                                                                                                       | 回收的工程訊號                                                                                 | 對應正文路由                                                                                                                                                |
| ----------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Shopify Debezium CDC over sharded MySQL](/backend/03-message-queue/cases/kafka-shopify-debezium-cdc/)            | 100+ shard、~150 Debezium connector、BFCM 100K records/sec、snapshot lock 與 oversized payload | [Binary Log + CDC](binlog-cdc/)、[Database Sharding](/backend/knowledge-cards/database-sharding/)、[Kafka vendor](/backend/03-message-queue/vendors/kafka/) |
| [Slack Job Queue 演進到 Kafka + Redis](/backend/03-message-queue/cases/slack-job-queue-kafka-redis/)              | 成長期把背景工作拆成多條傳遞路徑，揭露單一資料路徑與 queue 路徑分工                            | MySQL 只承擔 OLTP [source of truth](/backend/knowledge-cards/source-of-truth/)；queue / cache 路徑回 [03 Message Queue](/backend/03-message-queue/)         |
| gh-ost / GitHub operation workflow                                                                                | 大表 schema change 需要 throttle、pause / resume、cutover 控制                                 | [Online Schema Change Tools](online-schema-change-tools/)                                                                                                   |
| YouTube / Vitess                                                                                                  | MySQL sharding layer 需要 VTGate、VTTablet、VReplication、VSchema                              | [Vitess Sharding](vitess-sharding/)、[Database Sharding](/backend/knowledge-cards/database-sharding/)、[→ PlanetScale](migrate-to-planetscale/)             |
| [9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)        | 多套 RDBMS 整併到 managed Aurora，揭露 operation transfer driver                               | [→ Aurora](migrate-to-aurora/)、[Aurora vendor](/backend/01-database/vendors/aurora/)                                                                       |
| [9.C29 Lemino RDB connection limit](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) | surge 場景 connection limit 讓 RDB 退到 DynamoDB 類 access pattern                             | [ProxySQL Config](proxysql-config/)、[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)                                  |

案例下沉規則是先放 overview，再進 deep article。當某個案例只支撐服務定位，留在本頁；當案例提供具體操作訊號，例如 Shopify 的 Debezium connector scaling、GitHub 的 gh-ost workflow 或 YouTube 的 Vitess topology，後續再把它下沉到對應 deep article 的 production case 段。

## 常見陷阱

- **直接 ALTER TABLE 大表**：lock 表 hours、production 停擺、必須用 online schema change
- **不用 GTID**：replication topology 變更困難、recover from failure 容易出錯
- **buffer pool 太小**：cache miss 高、IOPS 飆升
- **shard key 選錯**：hot shard 出現、整體吞吐達不到名義
- **connection 沒 pool**：跟 PostgreSQL 同樣問題、用 ProxySQL
- **semi-sync 對高吞吐 workload**：每次 commit 等 ack、寫吞吐降一半

## 下一步路由

- 完整 T1 對照：[01-database vendors index](/backend/01-database/vendors/)
- 平行：[PostgreSQL vendor](/backend/01-database/vendors/postgresql/)、[Aurora vendor](/backend/01-database/vendors/aurora/)（managed MySQL）
- 上游：[1.1 高併發資料存取](/backend/01-database/high-concurrency-access/)、[1.3 Transaction Boundary](/backend/01-database/transaction-boundary/)
- 下游：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)（MySQL 不適用時的替代）
- 跨模組：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) — connection / replication / lock contention 常見 MySQL bottleneck
- 官方：[MySQL Documentation](https://dev.mysql.com/doc/)、[Vitess](https://vitess.io/)、[PlanetScale](https://planetscale.com/)
