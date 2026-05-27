---
title: "從自管 PostgreSQL / MySQL 遷到 Aurora：operational redesign migration playbook"
date: 2026-05-27
description: "PostgreSQL / MySQL → Aurora 的 Type C operational redesign hybrid playbook、6 規格面（Driver / Diff audit / Phase plan / Evidence / Cutover / Cleanup）、Standard Chartered 合規 lead time 模型、Netflix 非 all-purpose store 邊界"
weight: 70
tags: ["backend", "database", "aurora", "migration", "playbook", "postgresql", "mysql", "deep-article"]
---

從自管 PostgreSQL / MySQL 遷到 Aurora 是 *operational redesign hybrid*（Type C migration）— wire protocol 相容、application 不改、但 HA / backup / monitoring / capacity 模型完全不同。本 playbook 走 [migration playbook 6 規格面](/posts/migration-playbook-methodology/)（Driver / Diff audit / Phase plan / Evidence / Cutover / Cleanup）、補三個 Aurora-specific 議題：(1) 合規禁止跨境複製的 no-go condition、(2) 合規驅動遷移的時程模型（市場數 × 平均審查月份）、(3) Aurora 不是 all-purpose store 邊界。

本 playbook 不重複 Aurora overview（請看 [Aurora vendor 頁](/backend/01-database/vendors/aurora/)）— 前置閱讀建議 [Aurora storage architecture](../storage-architecture/)（理解為什麼 operational redesign）、[Aurora cross-AZ failover RTO](../cross-az-failover-rto/)（HA redesign 主項）、[Aurora read replica scaling](../read-replica-scaling/)（fleet 治理 SSoT、含合規 driver）。

## Migration type 判定

本 playbook 是 *Type C：Operational redesign hybrid*：

- PostgreSQL / MySQL → Aurora wire protocol 相容、application 多數不改
- 但 operational model（HA / backup / monitoring / capacity）完全不同、需要 redesign
- 跟 Type A schema translation 差：不需要翻譯 application SQL
- 跟 Type B drop-in 差：HA / backup / monitoring / capacity 模型需要 redesign
- 跟 Type E paradigm shift 差：保留 single-primary SQL 跟 ACID transaction 語意

對照其他 Aurora-related migration playbook：

- [PG → Aurora DSQL](/backend/01-database/vendors/postgresql/migrate-to-aurora-dsql/) 是 Type E paradigm shift（distributed SQL、multi-region active-active）
- [PG → CockroachDB](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/) 是 Type E paradigm shift + cross-cloud

## Driver：為什麼遷

### 主要 driver

- 團隊規模成長、DBA bandwidth 飽和、backup / failover / patch 操作負擔超過產品價值
- Read replica scaling 需求（傳統 streaming replication lag 秒級、Aurora 10-30ms — 詳見 [Aurora read replica scaling](../read-replica-scaling/)）
- Storage growth 痛點（local SSD 上限、resize 要 downtime、Aurora 自動 grow 到 128 TB）

### 次要 driver

- HA model 簡化（Patroni / Orchestrator → Aurora cluster endpoint、見 [cross-AZ failover RTO](../cross-az-failover-rto/)）
- Backup 自動化（pgBackRest / xtrabackup → Aurora automated backup + PITR）
- Multi-region DR 需求（[Aurora Global Database](../global-database-multi-region/)、但合規場景例外）

### No-go condition（嚴格遵守）

| 條件                      | 為什麼是 no-go                                                                                         |
| ------------------------- | ------------------------------------------------------------------------------------------------------ |
| 跨雲 / on-prem 需求       | Aurora AWS-only、wire protocol 相容但 storage 是 AWS 專屬                                              |
| 需要 latest upstream 特性 | Aurora 通常落後 upstream PostgreSQL / MySQL 1-2 major version                                          |
| 預算極敏感                | Aurora 比 self-managed PostgreSQL / MySQL 貴 20-30%                                                    |
| 合規禁止跨境複製          | 受監管市場資料 *不能跨境複製*、Aurora Global Database 在這種場景 *違反合規* — 要改用每市場獨立 cluster |
| 客製化 storage / I/O      | Aurora storage 是 AWS managed、不能客製化（vs self-managed 可以做 cgroup / quota / 自訂 storage 配置） |

**合規禁止跨境複製 no-go**（[9.C14 Standard Chartered 揭露](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/)）：

受監管市場資料不能跨境複製、Aurora Global Database 在這種場景違反合規。讀者規劃 Aurora migration 時不能假設「Aurora 一定有 Global Database 選項」— 要改用每市場獨立 cluster（fleet 拓樸吸收合規邊界、見 [Aurora read replica scaling](../read-replica-scaling/) fleet SSoT）。

### 替代方案

- **RDS PostgreSQL / MySQL**：更接近 upstream、單 AZ 便宜、不重寫 storage
- **自管 + Patroni HA + pgBackRest**：保留控制、跨雲可用
- **CockroachDB / Aurora DSQL**：multi-region active-active write 需求

### Case anchor

- [9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)：多套 RDBMS 統一到 Aurora、driver 是 *operational consolidation*、不是純效能
- [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)：200 個 cluster、按業務切分（不是一個大 cluster + 200 schema）
- [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/)：受監管場景、合規 lead time 是時程主項

**Netflix scope warning（必引用）**：

- [case「需要警惕」段第 2 點原文](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)：「Netflix 數據層遠不止 Aurora — 還有 Cassandra（playback metadata）、EVCache（cache layer）、Iceberg（data warehouse）。Aurora 主要是『需要 ACID 的 OLTP 工作負載』、不是『all-purpose store』」
- 工程含義：consolidation 是 *ACID OLTP 整合到 Aurora*、不是 *所有 store 整合到 Aurora*
- 讀者規劃整合範圍時要明示什麼 workload 不在範圍（cache、analytics、time-series、search、KV 高峰）
- 「+75% performance improvement 是跨多 workload 的最大改善幅度、不是『每個 workload 都 +75%』。實際每個 workload 改善幅度從 10% 到 75% 不等」（case「需要警惕」段第 1 點）

## Diff audit：6 維 source / target 差異盤點

| 維度        | 差異                                                                                                                                                                                                              | 主導程度   |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| Schema      | PostgreSQL extension 相容性（pg_cron 改 Lambda / Step Functions、pg_partman 改 manual / native partitioning、TimescaleDB 不支援、PostGIS 支援）；MySQL plugin（HandlerSocket 不支援、audit plugin 改 CloudTrail） | 中         |
| Operational | HA model、backup、monitoring、parameter management（postgresql.conf → DB parameter group / cluster parameter group）                                                                                              | 高（主導） |
| Paradigm    | 保留（single-primary SQL、ACID transaction、wire protocol）                                                                                                                                                       | 無變動     |
| Components  | connection pool（PgBouncer → RDS Proxy 或保留 PgBouncer in front of Aurora）、logical replication（pglogical / Debezium → Aurora 原生支援、但有版本限制）                                                         | 中         |
| Application | 保留（connection string 改 endpoint、SSL config 改 RDS CA、driver 不改）                                                                                                                                          | 低         |
| Topology    | 保留（single-region scaling、若要 multi-region 走另一條 playbook to DSQL）；fleet 拓樸決策（拆幾個 cluster）詳見 [read replica scaling](../read-replica-scaling/) fleet SSoT                                      | 中-高      |

**主導差異**：Operational layer（HA / backup / monitoring）、不是 schema 或 application。

### Schema diff 細節

**PostgreSQL → Aurora PostgreSQL**：

| Extension   | Aurora 支援  | Migration 策略                                               |
| ----------- | ------------ | ------------------------------------------------------------ |
| pg_cron     | 不支援       | 改 Lambda 排程 + RDS event 或 Step Functions                 |
| pg_partman  | 不支援       | 改 native declarative partitioning（PostgreSQL 11+）         |
| TimescaleDB | 不支援       | 改 native partition + materialized view、或保留 self-managed |
| PostGIS     | 支援         | 直接遷                                                       |
| pgvector    | 支援（新版） | 確認 Aurora PostgreSQL version、可能需要升級                 |
| pglogical   | 不支援       | 改 Aurora 原生 logical replication（有版本限制）             |

**MySQL → Aurora MySQL**：

| Plugin         | Aurora 支援 | Migration 策略                              |
| -------------- | ----------- | ------------------------------------------- |
| HandlerSocket  | 不支援      | 改 SQL access 或 Aurora-specific KV cache   |
| Vault audit    | 不支援      | 改 AWS CloudTrail + RDS audit log           |
| MyRocks engine | 不支援      | 改 InnoDB（Aurora 預設）、評估 storage 成本 |
| MaxScale       | 不支援      | 改 Aurora reader endpoint 或 RDS Proxy      |

### Operational diff 細節

| 元素              | Self-managed                              | Aurora                                        |
| ----------------- | ----------------------------------------- | --------------------------------------------- |
| HA                | Patroni / Orchestrator + etcd / ZooKeeper | Cluster endpoint + 自動 cross-AZ failover     |
| Backup            | pgBackRest / xtrabackup + S3 lifecycle    | Automated backup + manual snapshot + PITR     |
| Monitoring        | Prometheus exporter + Grafana             | CloudWatch + Performance Insights             |
| Parameter         | postgresql.conf / my.cnf                  | DB parameter group / cluster parameter group  |
| Failover testing  | Patroni `patronictl failover`             | `aws rds failover-db-cluster`                 |
| WAL / binlog 觀測 | `pg_stat_wal` / `SHOW MASTER STATUS`      | CloudWatch + Performance Insights wait events |

### Application diff 細節

```text
# Self-managed PostgreSQL
jdbc:postgresql://primary.internal:5432/mydb?ssl=true&sslmode=verify-full&sslrootcert=/etc/ssl/postgresql.crt

# Aurora PostgreSQL
jdbc:postgresql://my-cluster.cluster-xxx.us-east-1.rds.amazonaws.com:5432/mydb?ssl=true&sslmode=verify-full&sslrootcert=rds-ca.pem
```

Application 改動量小：connection string 換 endpoint、SSL CA 換 RDS CA、driver 不變。

對應 knowledge card：[failover](/backend/knowledge-cards/failover/)、[replication-lag](/backend/knowledge-cards/replication-lag/)。

## Phase plan：階段切換

### Phase 0：Pre-migration audit（2-4 週）

工作：

- Extension audit：`SELECT * FROM pg_extension` / `SHOW PLUGINS`、列出 source 使用的 extension
- Parameter audit：postgresql.conf vs Aurora parameter group、列差異
- Application connection string audit：所有服務的 DB connection 點位
- Benchmark baseline：write QPS / read QPS / p99 latency
- Cost baseline：current self-managed monthly cost vs Aurora estimate

Output：

- Migration feasibility report（含 no-go condition check）
- Aurora cluster sizing 估算
- Extension migration plan（each extension 對應的策略）

### Phase 1：Aurora infra 準備（1-2 週）

工作：

- Aurora cluster 開設（dev / staging / prod）
- Parameter group 對位（從 source postgresql.conf / my.cnf 翻譯到 Aurora parameter group）
- SG / subnet / IAM 設定
- RDS Proxy 配置（如需要）
- CloudWatch dashboard + Performance Insights baseline
- Backup retention 設定（1-35 天）

Output：

- Aurora cluster 待 data load
- Monitoring 已 ready、能對照 source 跟 target

### Phase 2：Data migration（2-8 週、依資料量）

三條 path、依場景選：

#### Path A：AWS DMS full load + CDC

- 適合：< 1 TB、可接受 read-only 短窗口
- 流程：DMS full load → DMS CDC → application cutover
- 優點：managed、validation 工具齊全
- 缺點：CDC lag 受 DMS task config 影響、bulk DDL 不友善

#### Path B：pg_dump / mysqldump + logical replication catch-up

- 適合：> 1 TB、要長 CDC 期、預算敏感
- 流程：snapshot → pg_dump / mysqldump → restore to Aurora → logical replication catch-up → application cutover
- 優點：成本低、可控性高
- 缺點：手動步驟多、要自己管 CDC lag

#### Path C：Snapshot restore

- 適合：已在 RDS PostgreSQL / MySQL
- 流程：RDS snapshot → Aurora restore-from-snapshot → catch-up → application cutover
- 優點：最快、AWS-internal 操作
- 缺點：只適用 RDS source、不適用 self-managed

### Phase 3：Dual-read validation（1-2 週）

工作：

- Application read 50/50 split source / target
- 比對 query 結果（per-table checksum + sampling）
- 量測 latency（Aurora p99 ≤ source × 1.2）
- 確認 stale read 比例 < 0.01%

Output：

- Validation report：query 結果差異、latency 對照
- Go/no-go decision for cutover

### Phase 4：Cutover（< 1 小時 window）

工作：

- Source set read-only
- CDC catch-up final（lag → 0）
- Application switch endpoint（DNS / service discovery / config flag）
- Smoke test（critical path query + write）
- Monitor error rate + latency 1 小時

Output：

- Cutover complete
- Source 切到 read-only、保留作為 rollback 餘地

### Phase 5：Cleanup（4-8 週）

工作：

- Source 保留 1 個月 read-only（rollback window）
- 確認穩定後 snapshot → S3 archive → decommission
- 舊 monitoring / backup / runbook archive

Output：

- Source decommissioned
- 新 runbook + monitoring 為 SSoT

### 本 phase plan 適用範圍

**Non-regulated workload**（一般 SaaS / e-commerce / 內部系統）。受監管場景（銀行 / 保險 / 醫療）請見下方「合規驅動遷移的時程模型」段、技術 phase 不變但 lead time 完全不同。

## 合規驅動遷移的時程模型

受監管產業遷移的關鍵時程是 *合規審查 lead time*、不是技術遷移時間 — 本段是補充給銀行 / 保險 / 醫療讀者、避免照本 playbook 走嚴重低估時程。

### Standard Chartered 揭露的時程模型

[9.C14 Standard Chartered case](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 「判讀」段第 3 點 + 「策略」段第 3 點原文：「每個受監管市場的審查可能 3-12 個月、合計遷移時程是『市場數 × 平均審查月份』、不是『技術遷移月份』」。

工程含義：

- 技術 phase plan 假設 2-8 週 data migration + < 1 小時 cutover
- 合規 lead time 是 *獨立軸*、可能比技術時程長一個數量級
- 不同市場合規進度不同步、可能要分批上線

### 合規時程組合

| 軸                   | 時程估算                                                  | 不可壓縮原因                                                |
| -------------------- | --------------------------------------------------------- | ----------------------------------------------------------- |
| 技術遷移             | 2-8 週 data migration + < 1 小時 cutover                  | 工程可控                                                    |
| 單市場合規審查       | 3-12 個月（Standard Chartered case 揭露）                 | 監管機構 lead time、不是技術問題                            |
| 多市場合規 lead time | 市場數 × 平均審查月份（7 市場 × 6 個月 ≈ 3.5 年最壞情況） | 各市場各自審、平行度受監管機構文化影響                      |
| 跨境複製禁令審查     | 包含在合規審查內、可能讓 Global Database 從候選變反指標   | 監管要求 data residency、無 cross-region replication option |

### 讀者判讀

- 受監管場景 *不能* 用本 playbook 的「2-8 週 data migration + < 1 小時 cutover」估時程交付給管理層 — 合規 lead time 是時程主項
- 受監管場景 *不能* 假設 Aurora Global Database 是 multi-region DR 選項 — 合規禁止跨境複製場景下 Global Database 違反合規（見 [global-database-multi-region](../global-database-multi-region/)），要改用每市場獨立 cluster
- 合規場景的 phase plan 要把每市場當成獨立 mini-migration、用 *市場批次* 推進、不是一次 big bang

**scope warning（必明示、case 自承）**：Standard Chartered case 未公開是 PostgreSQL 還是 MySQL、未公開具體 cost 數字 — 引用時不能擴寫「Standard Chartered 用 Aurora PostgreSQL」這類細節（case 用「相關 case study」匿名標明）。

**合規時程 scope 警示**：「3-12 個月、7 市場 × 6 個月 ≈ 3.5 年」是 Standard Chartered case 揭露範圍。實際合規 lead time 隨產業（銀行 / 保險 / 醫療）跟國家（東南亞 / 歐盟 / 北美 / 中東）差異大、不是恆定數字。讀者要把自家對應監管框架的實際 lead time 算進來、不是直接套 Standard Chartered 數字。

## Evidence：每階段驗證資料

| Phase   | Evidence                                                                                      |
| ------- | --------------------------------------------------------------------------------------------- |
| Phase 0 | extension list、parameter diff、application SQL 抽樣 test on Aurora dev cluster               |
| Phase 1 | Aurora cluster ready、monitoring dashboard 跟 source 對照                                     |
| Phase 2 | DMS row count match、checksum（per-table MD5）、CDC replication lag < 5 秒                    |
| Phase 3 | query result diff < 0.01%、p99 latency Aurora ≤ source × 1.2、application error rate baseline |
| Phase 4 | cutover 完成後 1 小時內 error rate < baseline × 2、write success rate 100%                    |
| Phase 5 | 30 天無 rollback trigger、cost 月帳對齊預估                                                   |

**受監管追加 evidence**：

- 每市場合規 sign-off 文件（central bank / 金融監管機關）
- 跨境複製禁令審查記錄
- Data residency 驗證測試（資料未流出受監管市場 boundary）
- Audit log 連續性驗證（source / target audit log 銜接）

**回路徑**：[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 抽 CDC / latency evidence。

## Cutover：切流決策

**Cutover window**：

- 建議 4 AM local time（lowest traffic）
- 預留 4 小時 buffer
- 受監管場景可能要在合規規定的 maintenance window（例如某些央行規定週日凌晨）

**Rollback condition**：

- error rate > baseline × 5
- write latency p99 > baseline × 3 持續 10 分鐘
- data corruption signal（checksum mismatch、unexpected row count drop）

**Rollback path**：

- Application connection string 切回 source
- Source 仍 read-write（cutover 前留 read-write 路徑、若已 read-only 要先解凍）
- CDC 反向同步（Aurora → source）catch-up

**Decision owner**：

- DBA lead + service owner + on-call SRE 三方 sign-off
- 受監管場景追加 compliance officer sign-off
- Cutover decision log 記錄（[rollback window](/backend/knowledge-cards/rollback-window/) / [rollback condition](/backend/knowledge-cards/rollback-condition/) 文件化）

對應 knowledge card：[rollback-window](/backend/knowledge-cards/rollback-window/)、[rollback-condition](/backend/knowledge-cards/rollback-condition/)。

## Cleanup：雙軌退役

| 元素             | Cleanup 策略                                                                               |
| ---------------- | ------------------------------------------------------------------------------------------ |
| Source database  | read-only 1 個月、確認穩定後 snapshot → S3 archive → decommission                          |
| 舊 monitoring    | Prometheus exporter 拆、Grafana dashboard archive、CloudWatch dashboard 為 SSoT            |
| 舊 backup chain  | pgBackRest / xtrabackup retention 保留至合規邊界（金融 7 年、一般 90 天）                  |
| 舊 runbook       | Patroni / Orchestrator runbook archive、新 runbook 對 Aurora cluster endpoint              |
| 舊 CDC connector | DMS task 留 7 天觀察期 → delete；自管 Debezium / pglogical 在 source decommission 同時退役 |

**不可逆 cleanup 邊界**：

- Source decommission 後資料只能從 backup restore
- 確保 backup 可用性測試通過再 decommission
- 受監管場景要保留 source backup 到合規 retention（金融 7 年、可能更長）

## 案例對照

### Netflix Aurora consolidation：operational consolidation 的價值

[9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 多套 RDBMS（PostgreSQL / MySQL / Oracle）→ Aurora、+75% 效能 / -28% 成本。

**驗證的 driver**：

- DB 種類太多本身是規模化的成本（每多一種 DB 多一套 DBA 知識 / backup / monitoring）
- 整合到 Aurora 釋放工程資源、不是純效能改善

**case 自帶警示（必引用）**：

- 「+75% 是跨多 workload 最大改善幅度、不是每 workload 都 +75%」（case「需要警惕」段第 1 點）
- **Aurora 非 all-purpose store 邊界**：「Netflix 數據層遠不止 Aurora — 還有 Cassandra（playback metadata）、EVCache（cache layer）、Iceberg（data warehouse）。Aurora 主要是『需要 ACID 的 OLTP 工作負載』」（case「需要警惕」段第 2 點）

工程含義：consolidation 是「ACID OLTP 整合到 Aurora」、不是「所有 store 整合到 Aurora」。讀者規劃整合範圍時要明示什麼 workload 不在範圍：

| Workload          | 是否在 Aurora consolidation 範圍 | 替代                                |
| ----------------- | -------------------------------- | ----------------------------------- |
| ACID OLTP         | 是                               | -                                   |
| Playback metadata | 否（Netflix 用 Cassandra）       | Cassandra / ScyllaDB                |
| Cache layer       | 否（Netflix 用 EVCache）         | EVCache / Redis / Memcached         |
| Data warehouse    | 否（Netflix 用 Iceberg）         | Iceberg / Snowflake / Redshift      |
| Time-series       | 否（性能不適合）                 | InfluxDB / TimescaleDB self-managed |
| Search            | 否（無 inverted index 優化）     | Elasticsearch / OpenSearch          |

### DraftKings：fleet 拓樸 redesign

[9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 200 個獨立 Aurora cluster、按業務切分（不是一個大 cluster + 200 schema）。

**驗證的 driver**：

- Migration 不只是技術切換、也是 cluster 拓樸 redesign
- 業務本身可切分（每體育類別 / 每地理 / 每產品線）就在 migration 時順便拆 cluster
- Blast radius 隔離跟容量規劃分散一起獲得

**Fleet 拓樸決策**：詳見 [Aurora read replica scaling](../read-replica-scaling/) 邊界段 SSoT。本 playbook 提醒 *migration 是拆 cluster 的好時機*、不展開拓樸決策本身。

### Standard Chartered：合規 lead time + 跨境複製禁令

[9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 受監管場景揭露：

- 合規 lead time 是時程主項（3-12 個月 / 市場）
- 跨境複製禁止讓 Global Database 變反指標
- 每市場獨立 cluster + cross-AZ failover 是合規場景的標準解

### 反例：Aurora 不適合的場景

- Multi-region active-active write：見 [PG → Aurora DSQL Migration](/backend/01-database/vendors/postgresql/migrate-to-aurora-dsql/)
- 跨雲：見 [PG → CockroachDB Migration](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/)
- 極端寫入吞吐（> 100K WPS）：考慮 sharding、CockroachDB、或 DynamoDB

## 邊界與整合 / 下一步

**Sibling playbook**：

- [PG → Aurora DSQL](/backend/01-database/vendors/postgresql/migrate-to-aurora-dsql/) — paradigm shift、Type E、multi-region active-active
- [PG → CockroachDB](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/) — cross-cloud、paradigm shift
- [PG → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/) — 既有 PG-specific playbook、可對照本 playbook 的 vendor-neutral 版本

**Sibling deep article**：

- [Aurora storage architecture](../storage-architecture/) — 理解 storage 設計才知道為什麼 operational redesign
- [Aurora cross-AZ failover RTO](../cross-az-failover-rto/) — HA redesign 主項
- [Aurora read replica scaling](../read-replica-scaling/) — fleet 治理 SSoT、含合規 driver
- [Aurora Global Database](../global-database-multi-region/) — 合規禁止跨境複製的 anti-recommendation

**1.x 章節互引**：

- [1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/) — migration 上游 framework

**何時不用本 playbook**：

- 從 Aurora 遷到別處（反向、走對應的反向 playbook）
- 從 RDS PostgreSQL 升 Aurora PostgreSQL 是 in-place upgrade、用 RDS console「Convert to Aurora」即可、不需要這套 playbook
- 跨雲遷移：本 playbook 不涵蓋 GCP / Azure SQL → Aurora 流程

## 相關連結

- [Aurora vendor overview](/backend/01-database/vendors/aurora/) — 服務定位、適用 / 不適用場景
- [Failover 卡片](/backend/knowledge-cards/failover/) — 概念基底
- [Replication Lag 卡片](/backend/knowledge-cards/replication-lag/) — operational diff 主軸
- [Rollback Window 卡片](/backend/knowledge-cards/rollback-window/) — cutover decision
- [Rollback Condition 卡片](/backend/knowledge-cards/rollback-condition/) — rollback trigger
- [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — operational consolidation 跟 Aurora 非 all-purpose store 邊界
- [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) — fleet 拓樸 redesign
- [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) — 合規 lead time + 跨境複製禁令
- [Migration Playbook 寫作方法論](/posts/migration-playbook-methodology/) — 本文遵循的 6 規格面寫作模板
- 官方：[Aurora migration documentation](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Migrating.html)
