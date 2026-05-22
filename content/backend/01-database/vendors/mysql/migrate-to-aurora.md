---
title: "MySQL → Aurora MySQL：storage layer 轉手到 AWS、replication / HA / backup 全部 outsource"
date: 2026-05-19
description: "自管 MySQL → Aurora MySQL 是 Type C operational hybrid migration — wire protocol 一致、ops 責任轉到 AWS。本文走 6 維 audit（Operational High）、Aurora storage architecture 衝擊、4-phase migration、5 production 踩雷、何時維持原路線。"
weight: 26
tags: ["backend", "database", "mysql", "vendor", "migration", "type-c", "operational-hybrid", "aurora"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [MySQL](/backend/01-database/vendors/mysql/) 跟 [Aurora](/backend/01-database/vendors/aurora/)。走 [Migration playbook methodology](/posts/migration-playbook-methodology/) Type C operational hybrid 結構。

| Ops 責任          | 自管 MySQL                        | Aurora MySQL                                      |
| ----------------- | --------------------------------- | ------------------------------------------------- |
| Storage           | EBS / local SSD、自己選 + 監控    | Aurora distributed storage（自動 6 份跨 3 AZ）    |
| Replication setup | binlog + semi-sync 自己配         | Storage layer 自動、無 binlog replication         |
| Failover          | Orchestrator + VIP + fence script | Aurora 內建、< 30 秒 RTO                          |
| Backup            | mysqldump / Percona XtraBackup    | 自動 continuous backup、PITR                      |
| Parameter tuning  | my.cnf 自己改                     | Parameter group（部分 knob 鎖）                   |
| Connection limit  | max_connections 自己設            | 看 instance class、有上限                         |
| Auto scaling      | 不適用                            | Aurora Serverless v2 + read replica auto-scaling  |
| Multi-region      | 自己配 chained replication        | Aurora Global Database                            |
| Per-month cost    | EC2 + EBS + 自己管 ops            | Higher per-GB / per-IOPS、但 ops headcount saving |

從 *MySQL 角度* 看 Aurora MySQL：wire protocol 一致、SQL 一致、ORM 不必改、application 連 endpoint 字串以外幾乎不必動。從 *Ops 角度* 看 Aurora MySQL：所有 storage / replication / failover knob 都 *看不到也改不了*、整個 ops 心智模型重寫。

這是 Type C operational hybrid 的典型 signature — *schema / paradigm 接近、operational 完全不同*。

## 為什麼是 Type C（operational 為主）

跑 [6 維 diff dimension audit](/posts/migration-playbook-methodology/#寫前的-diff-dimension-audit)：

| 維度        | 評         | 說明                                                         |
| ----------- | ---------- | ------------------------------------------------------------ |
| Schema      | Low        | MySQL wire protocol + SQL 完全一致                           |
| Operational | High       | storage / replication / failover / backup ops 全部轉到 AWS   |
| Paradigm    | Low        | 同 OLTP relational paradigm                                  |
| Components  | Medium     | Aurora 加 storage layer / cluster endpoint / reader endpoint |
| App change  | Low        | 主要 connection string + connection pool 設定                |
| Topology    | Low-Medium | single-region scaling、跨 region 走 Global Database          |

Operational = High（其他 Low） → **Type C operational hybrid**。Migration 路徑用 *4-phase drop-in cutover* + *operational re-onboarding*。

## Driver：TCO + Multi-AZ HA + AWS integration

從自管 MySQL 遷到 Aurora MySQL 的核心 driver：

- **TCO**：自管 MySQL 真實 cost = EC2 + EBS + ops headcount（1-3 個 FTE 撐大 MySQL deployment）。Aurora per-GB / per-IOPS 比 EC2+EBS 貴 30-50%、但省 ops headcount、總帳通常 break-even 或更便宜
- **Multi-AZ HA**：Aurora storage 自動 6 份跨 3 AZ、failover < 30 秒、不需要自管 Orchestrator + VIP + fence script
- **AWS ecosystem integration**：跟 Lambda / SAM / CloudFormation / IAM / Secrets Manager 整合、給 cloud-native architecture 加分
- **Read scaling**：Aurora 最多 15 個 read replica、storage layer 共享（不 replicate data、僅 replicate page cache）、read latency < 10ms inter-replica

不適合 *已用 Percona Server fork* 或 *需要 cross-cloud portability* 的 org — Aurora MySQL 是 AWS-only、且 fork 自 MySQL 5.7/8.0、跟 Percona 特性不完全一致。

## 4-phase migration

### Phase 1：Aurora cluster 起來作為 read replica

最低風險入口：建 Aurora cluster、用 MySQL binlog 把 production 資料 stream 進 Aurora。Application 仍寫自管 MySQL primary、Aurora 作為 *external read replica*。

```bash
# 1. 在 AWS 建 Aurora MySQL cluster
aws rds create-db-cluster \
  --db-cluster-identifier prod-aurora \
  --engine aurora-mysql \
  --engine-version 8.0.mysql_aurora.3.04.0 \
  --master-username admin \
  --master-user-password ... \
  --database-name production \
  --vpc-security-group-ids sg-xxx \
  --db-subnet-group-name prod-subnet

# 2. 用 mysqldump 或 Percona XtraBackup 拿 baseline
mysqldump --single-transaction --master-data=2 --triggers --routines --events \
  --all-databases > baseline.sql

# 3. Restore 到 Aurora
mysql -h prod-aurora.cluster-xxx.us-east-1.rds.amazonaws.com -u admin -p < baseline.sql

# 4. 設定 Aurora 從自管 MySQL 接 binlog
CALL mysql.rds_set_external_master(
  'self-managed-primary.example.com', 3306,
  'replication_user', 'password',
  'mysql-bin.000123', 12345, 0
);
CALL mysql.rds_start_replication;
```

完成標準：Aurora replica lag < 1 秒、跟 production primary 同步。

### Phase 2：Application read 切到 Aurora reader endpoint

Application 仍寫自管 primary、但讀 query 切到 Aurora reader endpoint：

- Aurora reader endpoint：`prod-aurora.cluster-ro-xxx.us-east-1.rds.amazonaws.com`
- 自動 round-robin 多個 read replica
- ProxySQL 或 application config 改 read connection string

跑 1-2 週、確認：

- Aurora read latency 跟自管 replica latency 接近（通常 Aurora 略好）
- Aurora replication lag 穩定 < 1 秒
- Aurora query 結果跟自管 primary 一致（spot-check critical query）

完成標準：所有 read traffic 都進 Aurora、no application bug。

### Phase 3：Cutover — promote Aurora primary

Cutover window 內：

```bash
# 1. 停 application 寫入（feature flag / scheduled maintenance）

# 2. 等自管 primary 跟 Aurora 同步完成（檢查 Aurora replica lag = 0）

# 3. 把 Aurora 從 external replica 提升為獨立 primary
CALL mysql.rds_stop_replication;
CALL mysql.rds_reset_external_master;

# 4. Application 寫 connection string 切到 Aurora writer endpoint
# prod-aurora.cluster-xxx.us-east-1.rds.amazonaws.com

# 5. 開始 application traffic
```

完成標準：寫入流量 100% 進 Aurora、自管 primary 變 idle。Cutover 通常需要 30-60 分鐘 maintenance window。

### Phase 4：Decommission 自管 MySQL

跑 1-2 週確認 Aurora 穩定後 *慢慢退役自管*：

- 自管 primary 保留作 *cold backup*（1-3 個月）、不接 traffic、可隨時 rollback
- Replica 一個一個關掉
- 監控 Aurora cost vs 預估、確認 break-even

完成標準：自管 EC2 instance terminate、EBS volume snapshot 後 delete、cost 對比驗證符合預期。

## 5 個 Production 踩雷

### 1. Parameter group 沒對齊 — `innodb_flush_log_at_trx_commit` 等行為差

Aurora 的 *parameter group* 取代 my.cnf。預設 parameter group 不一定跟自管 MySQL 一致：

- `innodb_flush_log_at_trx_commit`：自管常設 1（zero loss）、Aurora 預設仍 1 但走 *Aurora storage durability*（行為等價但不同 mechanism）
- `sync_binlog`：自管 1、Aurora *沒有 binlog 寫 disk* 概念（Aurora 不用 binlog 做 replication、binlog 是 *optional output*）
- `time_zone`：Aurora 預設 UTC、自管常設 local time、TIMESTAMP query 行為可能不同
- `character_set_*`：自管常設 utf8mb4、Aurora 預設可能是 latin1（看 cluster create 命令）

修法：

- Phase 1 完成後 *逐 row 對比 parameter group*：

   ```sql
   SELECT @@global.variable_name FROM ...
   ```

- 建 *custom DB cluster parameter group*、匹配自管設定
- 重啟 Aurora primary 套 parameter group 改變（部分 parameter 需要重啟）

### 2. IAM authentication — application 沒準備

Aurora 提供 *IAM authentication*（不用 password、用 AWS IAM role + temporary token）。Application 用 IAM auth 不必管 password rotation、但程式碼必須 *call AWS SDK 取 token、放 connection 設定*。

如果 Phase 2-3 期間沒 reverse engineer application connection logic、cutover 後 application 仍試用 password auth、Aurora 拒絕、production down。

修法：

- 評估是否啟用 IAM auth — *簡單情況保留 password*、整合 AWS Secrets Manager 自動 rotation
- 啟用 IAM 必須 application code 改：
   - Java：`com.amazonaws.services.rds.auth.RdsIamAuthTokenGenerator`
   - Python：`boto3.client('rds').generate_db_auth_token(...)`
   - Go：`aws-sdk-go-v2/feature/rds/auth`
- Phase 2 期間 application 對 Aurora 用 IAM token、self-managed 仍 password — 雙 path code

### 3. Aurora-only feature 寫進 application、rollback 成本升高

Migration 過程開發發現 Aurora 有 *Aurora-only feature*（Backtrack、Performance Insights、Aurora Global Database）、誘惑使用。一旦 application 用了 Aurora-only feature、要 rollback 自管 MySQL 變不可能（feature 不存在、query 失敗）。

常見 Aurora-only feature：

- *Backtrack*：72 小時內 in-place rollback 整個 DB（不同於 PITR）
- *Aurora ML*：SQL function 內接 SageMaker / Comprehend
- *Aurora Parallel Query*：analytical query 跨 storage node 並行
- *Aurora Auto Scaling*：read replica 數量按 CPU 自動加減

修法：

- *Phase 1-3 期間禁用 Aurora-only feature*、保留 rollback option
- *Phase 4 完成後* 才開始 evaluate Aurora-only feature、加進來時 *明確記錄不可 rollback decision*
- 把 Aurora-only feature 跟 *Aurora 特定 cluster* 綁定，避免 application 邏輯依賴 Aurora-only

### 4. Read replica endpoint behavior — Application 不知道 reader endpoint round-robin

Aurora reader endpoint（`prod-aurora.cluster-ro-xxx`）是 *DNS-based load balancer*、每次 DNS query 給不同 replica IP。Application connection pool 連續開 10 個 connection、可能全部連同一個 replica（DNS cache）、不均勻。

修法：

- Application connection pool 強制 *DNS re-resolve*（避免長時間 cache）
- 或用 *RDS Proxy*（managed connection pool）放在前面、不直接連 reader endpoint
- 或用 *Route 53 latency-based routing* 配 Aurora reader endpoint per AZ、application 連最近 AZ

### 5. Region failover — Aurora Global Database vs 自管 chained replication

自管 cross-region replication 是 *chained replication*（primary → region2 replica → region2 cascading replica）。Aurora Global Database 是 *storage-level replication*（storage page 直接 ship，而非 binlog）、跨 region < 1 秒 lag、failover < 1 分鐘。

但 Aurora Global Database 是 *active-passive*（primary region 可寫、secondary region 只讀）。如果原本自管已經 cross-region active-active write（用 multi-master 或應用層 sharding）、Aurora Global Database 的寫入模型會成為限制。

修法：

- 評估 cross-region 是 *DR* 用途還是 *active write* 用途
- 純 DR + read scaling：Aurora Global Database 直接 cover
- Active-active write：要 *Aurora DSQL*（2024 新推出、跟 Aurora 不同 product）或 distributed SQL（CockroachDB / Spanner）

## Capability gap：自管 MySQL 有但 Aurora 沒有

| 能力                   | 自管 MySQL             | Aurora MySQL                         |
| ---------------------- | ---------------------- | ------------------------------------ |
| Plugin 自己裝          | 任意                   | 受限（Aurora 只允許官方支援）        |
| OS-level access        | 完整 SSH access        | managed service，無 SSH access       |
| MySQL 8.0 latest patch | 你決定                 | 跟 Aurora major version 對應、有滯後 |
| InnoDB log_file_size   | 自己改                 | Aurora 內建 storage path             |
| Custom storage engine  | 可（MyRocks / TokuDB） | 只 InnoDB（Aurora optimized）        |
| Cross-cloud DR         | 自配 binlog ship       | Aurora-only (AWS region)             |

評估時必須確認 *當前自管功能* 沒用到 Aurora 不支援的能力。如果在用 MyRocks 等 storage engine、Aurora migration 不可行。

## 容量與成本對照

對 100 GB DB、5K WPS、20 個 application instance 的 deployment：

| 項目                 | 自管 MySQL（EC2）                | Aurora MySQL                                  |
| -------------------- | -------------------------------- | --------------------------------------------- |
| Primary instance     | r5.2xlarge（$0.50/hr）           | db.r6g.2xlarge（$0.83/hr）                    |
| EBS / Aurora storage | io2 100 GB + 5000 IOPS = ~$70/mo | Aurora storage 100 GB = ~$10/mo + I/O $0.20/M |
| Replica × 3          | 3 × r5.2xlarge = $1080/mo        | 3 × db.r6g.large = $540/mo                    |
| Backup storage       | S3 + 自己 cron mysqldump ~$50/mo | Aurora backup 100 GB 免費 + 額外 $0.021/GB    |
| Ops headcount        | 1-2 FTE × $150K = $300-500K/yr   | < 0.5 FTE × $150K = $75K/yr                   |
| **Total infra**      | ~$1500/mo + 大 ops cost          | ~$2000-3000/mo + 小 ops cost                  |

Pure infra cost Aurora 貴 30-50%、但 *ops cost 降幅大過 infra increase* — 200 人 eng team 養 1.5 FTE DBA 是 $300K-400K/yr、Aurora 換成 0.3 FTE 是 $60K-100K/yr、差距 $200K+ 抵 infra increase。

小團隊 / 小 deployment Aurora 不一定划算 — 50 人 eng team 沒有 dedicated DBA、自管 MySQL 也只佔某人 20% 時間、Aurora migration 的 ops saving 不存在。

## Production case：Netflix Aurora consolidation

MySQL → Aurora migration 的 production 責任是把自管 database operation 轉移成 managed SQL 的契約，而非只搬 schema 與資料。[9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 提供的工程訊號是多套 RDBMS 整併到 Aurora 後，效能、成本與操作責任一起改變。

這個案例要回收到三個操作判準。第一，migration driver 應寫成 operation transfer，例如 backup、failover、storage growth、patching 與 observability 由誰承擔。第二，效能與成本要一起看，因為 Aurora 的 storage / compute / I/O 計費會把原本藏在 DBA 操作裡的成本攤開。第三，整併多套 RDBMS 時要先做 feature inventory，確認 plugin、storage engine、charset、replication topology 與 SQL mode 都能落到 Aurora MySQL 支援範圍。

Netflix case 的 sibling 路由是 [Aurora vendor page](/backend/01-database/vendors/aurora/) 與 [PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/)。若 migration 目標從 managed SQL 變成 multi-region active-active write，應改接 [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)。

## 何時維持原路線

- **Cross-cloud portability 是 requirement**：Aurora AWS-only、要 cross-cloud 用 PlanetScale 或 自管
- **用 Percona Server fork / MyRocks 等非標準 engine**：Aurora 不支援
- **需要 OS-level customization**：Aurora 完全 managed、無 SSH
- **規模太小**：< 100 GB / < 1K WPS、自管 MySQL EC2 spot instance 已經夠便宜
- **規模太大**：> 50 TB single DB / > 100K WPS、Aurora single-instance 仍是 ceiling、考慮 Vitess 或 Aurora DSQL

## 相關連結

- 平行 batch：→ PlanetScale migration playbook（同 MySQL backlog、不同 target paradigm）
- 上游：[MySQL vendor overview](/backend/01-database/vendors/mysql/) / [Aurora vendor page](/backend/01-database/vendors/aurora/)
- 跨章節：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) — Aurora cost forecast
- 既有 case：[9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — Netflix 從多套 RDBMS 統一到 Aurora 的 migration evidence
- 方法論：[Migration Playbook Methodology](/posts/migration-playbook-methodology/)（Type C operational hybrid 結構說明）
- 官方：[Aurora MySQL Migration Guide](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Migrating.html)
