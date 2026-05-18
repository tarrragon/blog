---
title: "PostgreSQL → Aurora Migration：protocol 相容、operational 重設計"
date: 2026-05-19
description: "Aurora 號稱 PostgreSQL-compatible 但 operational model 不同（storage decouple / cluster endpoint / instance class / 自家備份）；遷移流程是混合（protocol drop-in + operational phased）、5 個 production 踩雷（extension 不支援 / replication slot 不直通 / autovacuum 行為差 / IAM 認證強制 / cost model 換算）、跟 Patroni / read replica / DR 對位"
weight: 13
tags: ["backend", "database", "postgresql", "aurora", "migration", "cloud-managed"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [PostgreSQL](/backend/01-database/vendors/postgresql/)（self-managed source）跟 [Aurora](/backend/01-database/vendors/aurora/)（cloud-managed target）。跟前兩篇 migration（[Splunk → Elastic](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/) 高 schema 差 / [Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/) drop-in）對照、本篇是 *middle ground*：wire protocol drop-in、但 operational model 重設計。

## 為什麼遷：operational cost / HA / DR 三條 driver

| Driver               | 觸發場景                                                                            |
| -------------------- | ----------------------------------------------------------------------------------- |
| **Operational cost** | self-managed PostgreSQL + Patroni HA + pgBackRest backup + monitoring 需 0.5-2 FTE；Aurora 把這層責任轉嫁 AWS、SRE 專注 application |
| **HA reliability**   | Patroni split-brain / DCS quorum 偶爾踩雷、production failover 4-15s；Aurora 自動 multi-AZ failover < 30s、shared storage 不丟資料 |
| **DR / backup**     | 自管 PITR + cross-region replication 複雜；Aurora 內建 PITR + global database + backup retention 簡化 |

反向 driver（Aurora → self-managed）也存在 — 主要是 *cost 在 10TB+ 規模時 Aurora 反而更貴*、或 *需要 PostgreSQL extension Aurora 不支援*（pg_partman / pg_repack / TimescaleDB 等）。

## 結構：protocol 相容 + operational phased 的混合

跟前兩篇對照、Aurora migration 結構是 *protocol drop-in*（application 不改 SQL）+ *operational redesign*（HA / backup / monitoring 全換）：

| 維度                | Splunk → Elastic（高 schema 差）| Redis → DragonflyDB（drop-in）| PostgreSQL → Aurora（middle）|
| ------------------- | -------------------------------- | ----------------------------- | ---------------------------- |
| Wire protocol       | 完全不同（SPL vs KQL）          | 完全相同（RESP）              | 完全相同（PostgreSQL wire） |
| Schema / data model | 高差異（CIM vs ECS）            | 完全相同                      | 完全相同                     |
| Application code    | 必改                            | 不改                          | 不改                         |
| Operational model   | 不同                            | 相似                          | **大差**                     |
| HA / replication    | 不同                            | 相似                          | **完全重設計**               |
| Backup model        | 不同                            | 簡化                          | **完全換 AWS-native**        |
| Migration 週期      | 4-9 個月                        | 1-4 週                        | 6-12 週                      |
| Phased 結構需要     | 6-phase 明顯                    | 不需要                        | **混合**（3 operational phase + drop-in cutover）|

**Hypothesis 驗證**：migration playbook 結構由 *最大差異維度* 決定 — Splunk → Elastic 是 schema 差導向 phased、Aurora migration 是 operational 差導向局部 phased。

## Operational redesign 對位

跟 self-managed PostgreSQL 比、Aurora 的 operational 模型差異：

| Operational concept            | Self-managed PostgreSQL                | Aurora                                            |
| ------------------------------ | -------------------------------------- | ------------------------------------------------- |
| Storage                        | Local disk / EBS、跟 compute 一體     | Shared storage 跨 AZ 6 副本、跟 compute 解耦      |
| HA                             | Patroni + DCS quorum + watchdog        | Aurora 自家 failover、shared storage 不重 promote |
| Read replica                   | Streaming replication + Patroni 管理   | Aurora reader endpoint、cluster 自動 routing      |
| Backup                         | pgBackRest / WAL-G + S3                | 自動 continuous backup + PITR（內建）             |
| Failover time                  | 15-60s（Patroni）                      | < 30s（同 AZ）/ 1-2 min（跨 AZ）                  |
| Connection management         | PgBouncer 必裝                          | RDS Proxy 推薦、Aurora 自家 connection pool      |
| Major version upgrade          | 手動 + 停機                            | Aurora 自家 blue/green deployment                |
| Monitoring                     | Prometheus + grafana-postgresql        | CloudWatch + Performance Insights                |
| Extension support              | 自由安裝                                | **白名單**、限 AWS 認可 extension                |
| Custom config                  | postgresql.conf 全控                    | Parameter Group（限制）                           |
| OS / kernel access             | 完全控                                  | **無**（fully managed）                           |

每一條 operational concept 都需要 migration plan、application code 不變但 *運維知識體系全換*。

## Migration 流程：3 phase operational + drop-in cutover

### Phase 0：Pre-migration audit（1-2 週）

1. **Extension 清單對位**：
```sql
SELECT extname, extversion FROM pg_extension;
-- 對照 Aurora supported extensions list
-- 不支援的（pg_repack / pg_partman 部分 / TimescaleDB / Citus）需替代方案
```

2. **Custom config 清單**：
```sql
SELECT name, setting FROM pg_settings WHERE source != 'default';
-- 對照 Aurora Parameter Group 可調項目
```

3. **Capacity 評估**：
- 當前 IOPS / connection / storage / WAL rate
- 對應 Aurora instance class（db.r6g.large to db.r6g.32xlarge）
- 估算 cost（vCPU + IOPS + storage + backup retention）

4. **Application connection pool audit**：
- PgBouncer 配置是否能直接搬到 RDS Proxy
- Connection string + IAM 認證準備

### Phase 1：Operational infrastructure 準備（2-3 週）

1. 建 Aurora cluster（Terraform / CloudFormation）
2. 設 Parameter Group、對位 self-managed 配置
3. 設 Security Group + IAM role
4. 設 RDS Proxy（推薦、connection 集中管理）
5. CloudWatch alert + Performance Insights baseline
6. Backup retention + PITR window 設定

### Phase 2：Data migration（取決於 dataset 大小）

兩條路：

#### 路線 A：AWS DMS（推薦中等規模 < 5TB）

```text
self-managed Postgres ──(DMS)──→ Aurora
                         |
                  full load + CDC continuous
```
- DMS task 設 `Full Load + Ongoing Replication`
- 跑 full load 估算（100GB ~ 1-3 小時依 instance class）
- CDC 持續直到 cutover

#### 路線 B：Logical replication（推薦 5TB+ 或要精準控制）
```sql
-- Source：建 publication
CREATE PUBLICATION migrate_pub FOR ALL TABLES;

-- Aurora：建 subscription
CREATE SUBSCRIPTION migrate_sub
  CONNECTION 'host=<source> dbname=<db> user=<replicator>'
  PUBLICATION migrate_pub;
```
- Initial COPY 跑完後 streaming
- 詳見 [Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/)

### Phase 3：Cutover 跟 verification

```text
1. Application 端設 maintenance mode（block writes）
2. 等 replication lag → 0
3. 確認 Aurora 端 row count + checksum 對齊
4. Application connection string 切到 Aurora endpoint
5. 解除 maintenance mode
6. Self-managed 端 read-only 保留 1-2 週 standby
```

Cutover window 視 dataset 大小：

- < 100GB：1-2 小時
- 100GB - 1TB：2-4 小時
- 1TB+：考慮 *zero-downtime cutover* via blue-green deployment

## Production 故障演練

### Case 1：Extension 不支援、application 直接壞

**徵兆**：cutover 後 application 某些 query 報 `extension "pg_repack" not available`、batch job 壞。

**根因**：Phase 0 audit 漏掉 application 用 pg_repack 做 maintenance；Aurora 不支援、self-managed 端的 cron job 改不過去。

**修法**：

1. **Pre-migration audit 必做**：`SELECT extname FROM pg_extension` 對照 [Aurora extension whitelist](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraPostgreSQL.Extensions.html)
2. **替代方案**：
   - pg_repack → Aurora 自家 vacuum + storage auto-resize
   - TimescaleDB → 改 declarative partitioning 或換 Timestream
   - Citus → 評估保留 self-managed 或重設計 schema
3. **退役策略**：Extension 是 application 必要的、評估暫不遷或選 alternative cloud（如 AlloyDB / Citus on Azure）

### Case 2：Replication slot 不直通

**徵兆**：self-managed 端有 Debezium CDC 接 application 事件、cutover 後 CDC pipeline 直接壞、Kafka 端訊息斷流。

**根因**：Aurora 對 logical replication slot 有限制 — 不直接支援 external consumer（如 Debezium）讀 slot；要走 *RDS Database Events* 或 *DMS CDC*。

**修法**：

1. **Pre-migration audit**：列所有 logical consumer（Debezium / Kafka Connect / 自家 CDC）
2. **替代方案**：
   - DMS CDC 取代 Debezium（Aurora 原生支援）
   - 評估 RDS Database Activity Streams（newer feature）
   - 重設計 CDC：application 寫 outbox 表、Aurora trigger 發 SNS → Lambda → Kafka
3. **接受代價**：CDC pipeline 重建是 2-4 週工作、納入 migration scope

### Case 3：Autovacuum 行為跟 self-managed 不同

**徵兆**：cutover 後幾天、特定 hot table 的 bloat 數據異常、application 端 query latency p99 漲；CloudWatch Performance Insights 顯示 autovacuum 跑頻率比 self-managed 端高 3 倍。

**根因**：Aurora 預設 Parameter Group 的 autovacuum 配置跟 self-managed 不同 — `autovacuum_vacuum_cost_limit` 預設更低、`vacuum_scale_factor` 更激進；shared storage 上 vacuum 行為不一樣。

**修法**：

1. **Parameter Group 對位**：把 self-managed [autovacuum tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/) 配置複製到 Aurora Parameter Group
2. **per-table tuning**：hot table 的 `ALTER TABLE SET (autovacuum_*)` 可遷過去
3. **接受差異**：Aurora storage 設計讓 vacuum 不一定要跟 self-managed 同 cadence、SRE 心智模型要調

### Case 4：IAM 認證強制、application 端改 connection logic

**徵兆**：production 切到 Aurora 後、application 仍用 password authentication、SOC team 要求改 IAM 認證（compliance）；application 連線 logic 大改、token rotation 邏輯也要加。

**根因**：self-managed 端用固定 username/password、Aurora 推薦（部分情境強制）IAM authentication；token 15 分鐘輪換、application 必須改連線 SDK。

**修法**：

1. **Migration scope 內包含**：authentication migration 是必要工作、不能事後補
2. **SDK 整合**：用 AWS SDK + RDS Proxy 抽象 token rotation、application 不直接管 token
3. **Hybrid 期間**：保留 password auth 直到 application 全切 IAM、再 disable password auth

### Case 5：Cost model 預估錯、月底帳單炸

**徵兆**：第一個月 Aurora 帳單比預估高 50-80%；IOPS / backup storage / I/O cost 都比預期多。

**根因**：Aurora pricing 三層（compute instance / storage / I/O）—

- Storage：actual data + backup × retention
- I/O：每個 read / write block 都計費（self-managed 不算）
- Backup：超過 backup retention 部分 charged as snapshot storage

self-managed 端習慣 *fixed EC2 + EBS* cost、Aurora I/O-based 計費對 high-IOPS workload 衝擊大。

**修法**：

1. **Pre-migration cost estimate**：用 self-managed `pg_stat_database` 估 I/O 量、套 Aurora pricing calc
2. **I/O optimization**：開 Aurora I/O-Optimized storage class（fixed monthly + 不算 I/O）、適合 high-IOPS workload
3. **Backup retention 控制**：不要 default 35 天、依 compliance 調整（7-14 天通常夠）
4. **Reserved Instance**：穩定 workload 預付 1-3 年、省 30-40%

## Capacity / cost 對照

| 維度                | Self-managed PostgreSQL（EC2 + EBS）| Aurora                                            |
| ------------------- | ---------------------------------- | ------------------------------------------------- |
| Instance cost       | EC2 + EBS（compute + storage 自管）| Aurora instance class + storage + I/O            |
| HA cost             | Patroni 跨 3 AZ + EBS 3 副本       | Aurora 跨 3 AZ shared storage（內建）            |
| Backup cost         | pgBackRest + S3 archive           | Aurora 自動 continuous backup（內建）             |
| Operational FTE     | 0.5-2 FTE（HA / backup / patching）| 0.1-0.3 FTE（application 端 + Parameter Group）  |
| 1TB / month cost    | $400-800（含 HA）                  | $700-1500（含 HA）                                |
| 10TB / month cost   | $2K-4K                             | $4K-8K（I/O cost 顯著）                          |
| 50TB+ cost          | $10K-20K                           | $30K+（cost 反轉、self-managed 更便宜）           |

**判讀**：< 10TB workload Aurora 平攤 operational cost 後仍便宜；50TB+ workload Aurora cost 顯著高、要 reserved + I/O-Optimized 才有競爭力。

## 整合 / 下一步

### 跟 [Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/) 對位

Patroni 在 Aurora migration 後 *退役* — Aurora 自家 failover 取代；但 SRE 心智模型要調：

- Patroni 的 `pg_rewind` 概念不存在（shared storage）
- Patroni 的 `synchronous_commit` 行為 Aurora 隱藏在 storage layer
- Aurora 跨 region 用 *Global Database*、不是 Patroni cross-region setup

### 跟 [PITR](/backend/01-database/vendors/postgresql/pitr-wal-archiving/) 對位

self-managed PITR rebuild 工作量大、Aurora PITR 是 native API call：

```bash
aws rds restore-db-cluster-to-point-in-time \
  --source-db-cluster-identifier myapp-prod \
  --db-cluster-identifier myapp-prod-restored \
  --restore-to-time 2026-05-19T14:30:00Z
```

完全不需要 base backup + WAL replay 思維、storage layer 自動處理。

### 跟 [PgBouncer](/backend/01-database/vendors/postgresql/pgbouncer-config/) → RDS Proxy

PgBouncer 多數情境可換 RDS Proxy：

- transaction pooling 等效
- IAM authentication 整合
- Connection pinning（Lambda / serverless workload）
- **限制**：RDS Proxy 對某些 PG 14+ feature 仍 catching up、prepared statements 行為差異

### 下一步議題

- **Aurora Serverless v2 評估**：variable workload 適合、steady workload 反而貴
- **Babelfish 評估**：跑 SQL Server protocol on Aurora（多 source 遷移到 Aurora）
- **Cross-region DR**：Aurora Global Database vs self-managed cross-region streaming + Patroni

## 相關連結

- Source vendor：[PostgreSQL](/backend/01-database/vendors/postgresql/)
- Target vendor：[Aurora](/backend/01-database/vendors/aurora/)
- 平行 migration playbook：[Splunk → Elastic Security](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/) / [Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/)
- 平行 deep article：[Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/) / [PITR + WAL Archiving](/backend/01-database/vendors/postgresql/pitr-wal-archiving/) / [Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/)
- Methodology：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)
