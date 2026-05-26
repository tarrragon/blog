# 從自管 PostgreSQL / MySQL 遷到 Aurora：operational redesign migration playbook

> **Status**: L5 outline skeleton（planning artifact、非 published article）。**這是 migration playbook、走 6 規格面（Driver / Diff audit / Phase plan / Evidence / Cutover / Cleanup）**、不是 deep article 結構。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 的「Migration Playbook 規格」段 與 [migration playbook methodology](/posts/migration-playbook-methodology/)。

## Migration type 判定

- **Type C：Operational redesign hybrid**（PostgreSQL / MySQL → Aurora wire protocol 相容、application 不改、但 operational model 完全不同）
- 跟 Type A schema translation 差：不需要翻譯 application SQL
- 跟 Type B drop-in 差：HA / backup / monitoring / capacity 模型需要 redesign

## Driver（為什麼遷）

- 主要 driver：團隊規模成長、DBA bandwidth 飽和、backup / failover / patch 操作負擔超過產品價值
- 次要 driver：read replica scaling（傳統 streaming replication lag 秒級、Aurora 10-30ms）、storage growth 痛點（local SSD 上限、resize 要 downtime）
- No-go condition：跨雲 / on-prem 需求（Aurora AWS-only）、需要 latest upstream PostgreSQL / MySQL 特性（Aurora 落後 1-2 major version）、預算極敏感（Aurora 比 self-managed 貴 20-30%）、合規禁止跨境複製
- 替代方案：RDS PostgreSQL / MySQL（更接近 upstream、單 AZ 便宜）、自管 + Patroni HA + pgBackRest（保留控制）、CockroachDB / Aurora DSQL（multi-region 需求）
- Case anchor：[9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 多套 RDBMS 統一到 Aurora 的 driver 是 *operational consolidation*、不是效能

## Diff audit（source / target 差異盤點）

- 6 維 diff audit：
  - **Schema**：PostgreSQL extension 相容性（pg_cron 改 Lambda / Step Functions、pg_partman 改 manual / native partitioning、TimescaleDB 不支援、PostGIS 支援）、MySQL plugin（HandlerSocket 不支援、Vault audit plugin 改 AWS CloudTrail）
  - **Operational**：HA 模型（Patroni / Orchestrator → Aurora cluster endpoint）、backup（pgBackRest / xtrabackup → Aurora automated backup + manual snapshot）、monitoring（Prometheus exporter → CloudWatch + Performance Insights）、parameter management（postgresql.conf → DB parameter group / cluster parameter group）
  - **Paradigm**：保留（single-primary SQL、ACID transaction、wire protocol）
  - **Components**：connection pool（PgBouncer → RDS Proxy 或保留 PgBouncer in front of Aurora）、logical replication（pglogical / Debezium → Aurora 原生支援、但有版本限制）
  - **Application**：保留（connection string 改 endpoint、SSL config 改 RDS CA、driver 不改）
  - **Topology**：保留（single-region scaling、若要 multi-region 走另一條 playbook to DSQL）
- 主導差異：Operational layer（HA / backup / monitoring）、不是 schema 或 application
- 對應 knowledge card：[failover](/backend/knowledge-cards/failover/)、[backup-strategy](/backend/knowledge-cards/backup-strategy/)（若已建）、[replication-lag](/backend/knowledge-cards/replication-lag/)

## Phase plan（階段切換）

- **Phase 0：Pre-migration audit**（2-4 週）：extension audit、parameter audit、application connection string audit、benchmark baseline（write QPS / read QPS / p99 latency）
- **Phase 1：Aurora infra 準備**（1-2 週）：cluster 開設、parameter group 對位、SG / subnet / IAM、RDS Proxy（如需要）、CloudWatch dashboard
- **Phase 2：Data migration**（2-8 週、依資料量）：
  - Path A：AWS DMS full load + CDC（適合 < 1 TB、可接受 read-only 短窗口）
  - Path B：pg_dump / mysqldump + logical replication catch-up（適合 > 1 TB、要長 CDC 期）
  - Path C：snapshot restore（Aurora 從 RDS snapshot 直接 restore、適合已在 RDS）
- **Phase 3：Dual-read validation**（1-2 週）：application read 50/50 split source / target、比對 query 結果、量測 latency
- **Phase 4：Cutover**（< 1 小時 window）：source read-only → catch-up final → application switch endpoint → smoke test
- **Phase 5：Cleanup**（4-8 週）：保留 source 1 個月 read-only 作為 rollback 餘地、確認穩定後 decommission

## Evidence（每階段驗證資料）

- Phase 0：extension list（`SELECT * FROM pg_extension`）、parameter diff（postgresql.conf vs Aurora parameter group）、application SQL 抽樣 test on Aurora dev cluster
- Phase 2：DMS row count match、checksum（per-table MD5）、CDC replication lag < 5 秒
- Phase 3：query result diff < 0.01%、p99 latency Aurora ≤ source × 1.2
- Phase 4：cutover 完成後 1 小時內 error rate < baseline × 2、write success rate 100%
- Phase 5：30 天無 rollback trigger、cost 月帳對齊預估
- 回路徑：[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 抽 CDC / latency evidence

## Cutover（切流決策）

- Cutover window：建議 4 AM local time（lowest traffic）、預留 4 小時 buffer
- Rollback condition：error rate > baseline × 5、write latency p99 > baseline × 3 持續 10 分鐘、data corruption signal（checksum mismatch）
- Rollback path：application connection string 切回 source、source 仍 read-write（cutover 前留 read-write 路徑、若已 read-only 要先解凍）
- Decision owner：DBA lead + service owner + on-call SRE 三方 sign-off
- 對應 knowledge card：[rollback-window](/backend/knowledge-cards/rollback-window/)、[rollback-condition](/backend/knowledge-cards/rollback-condition/)

## Cleanup（雙軌退役）

- Source database：read-only 1 個月、確認穩定後 snapshot → S3 archive → decommission
- 舊 monitoring：Prometheus exporter 拆、Grafana dashboard archive
- 舊 backup chain：pgBackRest / xtrabackup retention 保留至合規邊界（金融 7 年、一般 90 天）
- 舊 runbook：Patroni / Orchestrator runbook archive、新 runbook 對 Aurora cluster endpoint
- 不可逆 cleanup 邊界：source decommission 後資料只能從 backup restore；確保 backup 可用性測試通過再 decommission

## 案例對照

- [9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)：多套 RDBMS（PostgreSQL / MySQL / Oracle）→ Aurora、+75% 效能 / -28% 成本；驗證 operational consolidation 的價值
- [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)：200 個獨立 Aurora cluster、按業務切分（不是一個大 cluster + 200 schema）；提醒 migration 不只是技術切換、也是 cluster 拓樸 redesign
- 反例：Aurora 不適合的場景見 [PG → Aurora DSQL Migration](/backend/01-database/vendors/postgresql/migrate-to-aurora-dsql/)（multi-region active-active）

## 邊界與整合

- Sibling playbook：[PG → Aurora DSQL](/backend/01-database/vendors/postgresql/migrate-to-aurora-dsql/)（paradigm shift、Type E）、[PG → CockroachDB](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/)（cross-cloud、paradigm shift）
- Sibling deep article：[Aurora storage architecture](./storage-architecture.md)（理解 storage 設計才知道為什麼 operational redesign）、[Aurora cross-AZ failover RTO](./cross-az-failover-rto.md)（HA redesign 主項）
- 1.x 章節互引：[1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/) 上游、[1.7 HA / replication topology](/backend/01-database/ha-replication-topology/)（若已建）

## 寫作前置 checklist

- [ ] case anchor 確認：Netflix 統一 RDBMS 的 operational driver、DraftKings 多 cluster 拓樸 redesign
- [ ] knowledge card 雙引用：[failover](/backend/knowledge-cards/failover/) + [replication-lag](/backend/knowledge-cards/replication-lag/) + [rollback-window](/backend/knowledge-cards/rollback-window/)
- [ ] sibling playbook 對比：跟 PG → Aurora DSQL（Type E）跟 Type B drop-in 對照、明示本篇 Type C
- [ ] 預估寫作長度：280-340 行（6 規格面 + operational diff audit 密度高）
- [ ] 寫作難度：中高（DMS / parameter group / RDS Proxy 三條 path 都要展開、AWS 文件 + Netflix case 提供基底）
