---
title: "MongoDB → Atlas：Atlas 不是 MongoDB + managed、是另一個 product"
date: 2026-05-19
description: "Atlas 號稱「MongoDB managed」但 operational model 完全不同（auto-scaling / VPC peering / IAM-driven access / 內建 backup / billing 模型）；本文採用 Type C operational redesign hybrid 結構、4-phase operational migration + drop-in cutover、5 個 production 踩雷（連線數限制 / IP whitelist / backup retention / IAM token 過期 / billing 暴漲）"
weight: 11
tags: ["backend", "database", "mongodb", "atlas", "managed", "migration", "type-c"]
---

> 本文是跨 vendor [migration](/backend/knowledge-cards/migration/) playbook、cross-link 到 [MongoDB](/backend/01-database/vendors/mongodb/) 跟 MongoDB Atlas。本文是 [Migration playbook methodology](/posts/migration-playbook-methodology/) Type C operational redesign hybrid 的標準形態實證。每階段切換用 [migration gate](/backend/knowledge-cards/migration-gate/) 把關 — 4 phase 之間的驗證條件就是 gate。

## Atlas 不是 MongoDB + managed、是另一個 product

「MongoDB Atlas 是 MongoDB 的 managed 版本」這個 framing 看似合理、實際誤導：

- **Protocol 相容**：MongoDB wire protocol 一致、driver 不改、`mongosh` 連線跟 self-managed 一樣
- **Storage 一致**：WiredTiger storage engine 一樣、document model 一樣
- **API 一致**：Aggregation framework、indexing、change stream 都一樣

但 *operational surface 完全不同*：

| Operational concept | Self-managed MongoDB                              | Atlas                                                 |
| ------------------- | ------------------------------------------------- | ----------------------------------------------------- |
| Cluster bootstrap   | mongod + replica set config + cfgsvr + shard 手動 | UI / API 一鍵建集群、全自動                           |
| HA                  | Replica set 自管 + arbiter + priority             | 自動跨 AZ replica + automatic failover                |
| Backup              | mongodump + S3 archive 自管                       | 內建 cloud backup + PITR（按 region 設）              |
| Network access      | VPC + security group + IP whitelist 自管          | Atlas private endpoint / VPC peering / IP access list |
| Authentication      | mongod 內部 user / x.509 自管                     | Atlas Database User + 整合 LDAP / SSO / AWS IAM       |
| Monitoring          | Self-deploy Prometheus + grafana                  | Atlas Performance Advisor + APM 內建                  |
| Sizing              | Manual instance class + scale                     | Auto-tier scaling + tier-based pricing                |
| Patching            | Manual + outage window                            | Automatic（可配置 maintenance window）                |

Migration 主要工作不在 *資料層* — protocol drop-in 已 cover；是 *operational stack 全換*：SRE runbook、monitoring dashboard、access control、IAM 整合、cost 預估全要重做。「Atlas 是 managed MongoDB」這個 framing 低估了 operational 工作量。

跑 [diff dimension audit](/report/content-structure-by-max-diff-dimension/)：

| 維度                   | 評估                                                   | 等級       |
| ---------------------- | ------------------------------------------------------ | ---------- |
| Schema / API           | MongoDB protocol / API 完全相容                        | Low        |
| Operational model      | HA / backup / monitoring / IAM / network 全換          | **High**   |
| Abstraction / paradigm | 同 document DB                                         | Low        |
| Number of components   | 同 1 個 cluster                                        | Low        |
| Application change     | Connection string / IAM 整合改、application logic 不改 | Low/Medium |

主導維度 Operational = High、Schema / Paradigm 都 Low — 對映 [Type C operational redesign hybrid](/posts/migration-playbook-methodology/)。

## 結構：4-phase operational + drop-in cutover

跟 [PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/) 結構對齊（同 Type C）：

```text
Phase 0：Pre-migration audit（1-2 週）
  - Workload sizing（IOPS / connection / storage）
  - Application connection pattern audit
  - Compliance requirement audit

Phase 1：Operational infrastructure 準備（2-3 週）
  - Atlas cluster 建立
  - VPC peering / private endpoint
  - IAM role + Atlas Database User
  - Monitoring + alert
  - Backup retention 設定

Phase 2：Data migration（取決於 dataset 大小）
  - mongomirror / Atlas Live Migration tool
  - 或 mongodump → mongorestore（小 DB）

Phase 3：Cutover 跟 verification

Phase 4：Cleanup（self-managed decommission）
```

整體 4-12 週、依 dataset 大小跟 organization 流程複雜度。

## Phase 0：Pre-migration audit

### Workload sizing → Atlas tier

```text
Self-managed observations:
- Peak IOPS: 8000
- P99 read latency: 5ms
- Connection count peak: 1500
- Storage: 800GB
- Cross-region replication needed: yes

Atlas tier mapping:
- M40 (8 vCPU, 16GB RAM): IOPS 3000、不夠
- M60 (16 vCPU, 64GB RAM): IOPS 6000、邊界
- M80 (32 vCPU, 128GB RAM): IOPS 9000、安全（選此）
- Storage: 1TB tier（足夠 800GB + 25% buffer）
- Cross-region replication add-on
```

Atlas 不是 *自由 instance class*、是 *固定 tier*；workload 跨 tier 邊界時要選 *上一級* 而不是 push 下一級。

### Connection pattern audit

```javascript
// Application connection pool config
const client = new MongoClient(uri, {
  maxPoolSize: 100,     // ← Atlas 端 tier-specific connection limit
  minPoolSize: 10,
  maxIdleTimeMS: 60000,
});
```

Atlas tier 對 *single user connection* 有限制（M40 ~1500、M80 ~3000）；多 application instance 跑同帳號連 Atlas 可能撞 limit。預先計算 total connection = `pod_count × maxPoolSize`、對照 tier limit。

### Compliance audit

- **Data residency**：Atlas 部署 region 是否符合 GDPR / 客戶合約
- **Encryption at rest**：Atlas 預設 enable、但 *encryption key 是 Atlas-managed* — 合規嚴格要用 CMK / BYOK
- **Audit log**：Atlas 提供 audit log、export 到 S3 / Splunk

## Phase 1：Operational infrastructure 準備

### Atlas cluster 配置

```yaml
# 用 Terraform mongodbatlas provider
resource "mongodbatlas_cluster" "production" {
  project_id   = var.project_id
  name         = "production-cluster"
  cluster_type = "REPLICASET"

  provider_name         = "AWS"
  provider_region_name  = "US_EAST_1"
  provider_instance_size_name = "M80"

  backup_enabled         = true
  pit_enabled            = true   # PITR
  mongo_db_major_version = "7.0"

  advanced_configuration {
    javascript_enabled                   = false
    minimum_enabled_tls_protocol         = "TLS1_2"
    no_table_scan                        = false
    oplog_size_mb                        = 51200
  }
}

# Backup retention
resource "mongodbatlas_cloud_backup_schedule" "production" {
  project_id   = var.project_id
  cluster_name = mongodbatlas_cluster.production.name

  reference_hour_of_day    = 3
  reference_minute_of_hour = 0
  restore_window_days      = 7

  policy_item_daily {
    frequency_interval = 1
    retention_unit     = "days"
    retention_value    = 7
  }
}
```

### VPC peering / private endpoint

```text
Pattern A: VPC Peering
  AWS VPC <──peering──> Atlas project VPC
  - 跨 region 跑、routing table 對齊
  - 適合中型 / 大型 workload、stable network topology

Pattern B: Private Endpoint (Atlas private link)
  AWS VPC ──private link──> Atlas
  - 不需要 routing table 改
  - 適合 multi-account / multi-region 複雜場景
  - Cost 略高
```

production default 走 Private Endpoint、設定簡單跟 IAM 整合好。

### Atlas Database User 跟 IAM 整合

```text
Pattern A: 傳統 username / password
  - 設 Database User、application 用 SCRAM-SHA-256 連
  - 適合 legacy application

Pattern B: AWS IAM authentication（推薦）
  - Atlas Database User type: "AWS IAM"
  - Application 用 AWS IAM role + Atlas SDK
  - Token 15 分鐘輪換、application 自管 refresh
```

cutover 時間表內加 IAM authentication migration、不要事後補。

## Phase 2：Data migration

### Atlas Live Migration tool（小到中型）

Atlas UI 內建 Live Migration tool：

1. Source cluster URI（self-managed MongoDB）
2. Atlas target cluster
3. tool 自動 full sync + oplog tailing
4. Cutover window 內 final cutover

支援 dataset < 100GB 簡單；100GB-1TB 需要分批 / collection 順序設計。

### mongomirror（大型）

```bash
# Mongomirror: source → atlas
mongomirror \
  --host source-replicaset/host1:27017,host2:27017 \
  --destination atlas-cluster-host:27017 \
  --destinationUsername admin \
  --destinationPassword $ATLAS_PASSWORD \
  --ssl
```

mongomirror 分兩段：

1. Initial sync（full dump + restore）
2. Oplog tailing（continuous CDC）

Cutover 期間 application 切 connection string、mongomirror 跟著 stream 收尾。

## Phase 3：Cutover + verification

```text
1. Application 端設 maintenance mode（block write）
2. Wait mongomirror catch up（oplog gap → 0）
3. 驗證 Atlas 端 collection count + sample query
4. Application connection string 切到 Atlas
5. 解除 maintenance、monitor 24-48 小時
6. Self-managed mongo read-only standby 1-2 週
```

## Production 故障演練

### Case 1：Atlas tier connection limit 撞牆

**徵兆**：cutover 後 application 流量高峰時大量 `Connection refused`、Atlas 端顯示 connection limit reached；self-managed 階段沒有這問題。

**根因**：M80 tier connection limit ~3000、application 100 個 pod × maxPoolSize=50 = 5000 connection；超出 limit。

**修法**：

1. **Pre-migration 計算**：total connection 對照 Atlas tier、超出選上一級 tier
2. **降 maxPoolSize**：100 pod × 30 = 3000、剛好 cap；但 burst 仍可能撞
3. **加 connection proxy**：在 application 跟 Atlas 之間放 connection pooler（如 mongos sharded 或 ProxySQL-style proxy）

### Case 2：IP whitelist 漏 application VPC、cutover 後完全連不上

**徵兆**：cutover 後 application 直接報 `connection timeout`、Atlas dashboard 顯示 zero traffic；troubleshooting 1 小時才發現是 IP access list 漏掉某 application VPC CIDR。

**根因**：Atlas IP access list 預設 deny all、必須明示加 application VPC；Phase 1 設定漏看某個 VPC（如 multi-account organization 內的 staging account）。

**修法**：

1. **Pre-cutover 連線測試**：每個 application VPC 跑 sample MongoDB 連線、確認 ping 通
2. **改 Private Endpoint**：不靠 IP whitelist、用 PrivateLink 自動 routing
3. **Backup access**：保留 bastion host with whitelisted IP、incident 期間能直連

### Case 3：Backup retention 設不夠、compliance audit 抓到

**徵兆**：cutover 3 個月後 SOX audit 發現 backup retention 設 7 天、合規要求 90 天；急忙改 Atlas config 設 90 天、但 *過去 3 個月 backup 已不可恢復*。

**根因**：Atlas backup retention 是 *向前生效*、不能回追加；Phase 1 預設配置漏對合規 review。

**修法**：

1. **Pre-Phase 1 跑 compliance review**：跟 legal / security team 確認 retention / data residency / audit log
2. **預設 retention 設保守值**（30 / 60 天）、之後可降不能升
3. **PITR 跟 backup retention 分開設**：PITR window 7-30 天、full backup 90-365 天

### Case 4：IAM token 過期、application 端 reconnect storm

**徵兆**：production 切到 IAM authentication 後、每 15 分鐘出現一波 connection failure；Atlas log 顯示「auth token expired」。

**根因**：AWS IAM token 15 分鐘輪換、application 用舊 token 重連失敗；token refresh 邏輯沒寫對。

**修法**：

```javascript
// 用 Atlas SDK + AWS SDK 整合、自動 token refresh
const { MongoClient } = require('mongodb');
const { fromIni } = require('@aws-sdk/credential-providers');

const credentials = fromIni({ profile: 'production' });
const client = new MongoClient(uri, {
  authMechanism: 'MONGODB-AWS',
  // SDK 自動 refresh token
});
```

不要自管 token rotation、用 vendor SDK 抽象掉。

### Case 5：Billing 暴漲、IOPS 跟 backup storage 超預估

**徵兆**：第一個月 Atlas 帳單 $15K USD、預估 $8K；Atlas dashboard 顯示 backup storage 跟 IOPS 各超 1.5-2x 預估。

**根因**：

- Atlas backup 預設 *跨 region replicated*、storage cost 2x
- IOPS-heavy workload 在 M tier 內可能撞 burst credit、auto-tier-up 暫時觸發更貴 tier
- Data transfer 跨 region / 跨 cloud 計費沒算

**修法**：

1. **Pre-migration cost estimate**：用 self-managed metrics 估 IOPS / bandwidth、套 Atlas pricing
2. **Backup region 設單一**：若不要跨 region DR、設 same-region backup 省 50%
3. **Reserved Instance**：穩定 workload 預付 1-3 年、省 30-40%
4. **Performance Advisor 早用**：第一週就跑、找 inefficient query 降 IOPS

## Capacity / cost

| 維度                 | Self-managed MongoDB             | Atlas                             |
| -------------------- | -------------------------------- | --------------------------------- |
| Cluster cost (M80)   | EC2 r6g.4xlarge × 3 ≈ $1.5K / mo | M80 + storage + backup ≈ $3K / mo |
| Operational FTE      | 0.5-1.5 FTE                      | 0.1-0.3 FTE                       |
| Backup cost          | S3 + tooling 自管                | 內建 + tiered storage             |
| Cross-region DR cost | Manual + 2x infrastructure       | 1-click + 1.5-2x billing          |
| Time to value        | 1-3 個月（HA + ops setup）       | 1-2 週（cluster ready + IAM）     |
| Migration cost       | -                                | 1-3 FTE × 2-3 個月                |

**Break-even**：~200GB / 中型 workload、Atlas operational savings 平攤 1-2 年後比 self-managed cheaper；TB+ 大型 workload self-managed 仍可能便宜、但需要 ops team。

## 整合 / 下一步

### 跟 [PostgreSQL → Aurora migration](/backend/01-database/vendors/postgresql/migrate-to-aurora/) 對照

兩篇都是 Type C operational redesign hybrid、模板共用、細節差：

- Aurora 端 RDS Proxy 是推薦做法、Atlas 端 Private Endpoint 更標準
- Aurora 端 IAM authentication 是 *optional best practice*、Atlas IAM 是 *推薦預設*
- 兩家 cost model 都複雜、I/O cost 是 surprise 主要來源

### 跟 [Application 端 IAM token rotation](/backend/07-security-data-protection/vendors/hashicorp-vault/dynamic-credential/) 整合

Vault dynamic credential 可 issue Atlas Database User credential、lease lifecycle 對齊 application；對 high-stakes workload 是好做法、但 setup 複雜。

### 下一步議題

- **Atlas Data Federation**：跨 Atlas 集群 query S3 / 跨 region；如果走 multi-region 評估這 feature
- **Atlas Online Archive**：cold data 自動 archive 到 S3、查 query 透明；對 retention 重的 workload 省 storage cost
- **Atlas Serverless**：burst workload 適合、steady 不划算

## 相關連結

- Source vendor：[MongoDB](/backend/01-database/vendors/mongodb/)
- 平行 migration playbook (Type C)：[PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/)
- 平行 migration playbook：[Splunk → Elastic](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/)（Type A schema 差） / [Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/)（Type E paradigm shift）
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/)（本文驗證 Type C 標準形態）
