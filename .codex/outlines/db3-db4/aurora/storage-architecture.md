# Aurora Storage Architecture：quorum-based 分散式 log 與 4-of-6 write / 3-of-6 read

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：團隊從 RDS / 自管 PostgreSQL 遷到 Aurora、看到「跨 AZ replication lag 從秒級降到毫秒級」、但讀文件「quorum / 4-of-6」訊息密集、不知道哪些設計決定要相信、哪些是 marketing 詞
- 讀者徵兆：「為什麼 Aurora 寫入 latency 比 RDS 還低、不是該因為跨 AZ 而變慢？」「Storage layer 跟 compute layer 分離具體怎麼影響 backup / failover / read replica？」「6 個 storage node 失去 2 個還能寫嗎？失去 3 個呢？」
- Case anchor：[9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) +75% 效能改善的根因要回 storage 設計才能解釋

## 核心機制（Vendor-specific mechanism）

- Aurora 把 storage 從「block device + WAL on local disk」重寫成「跨 AZ 分散式 log service」、compute node 只負責 process query 跟 generate redo log records
- 6-way replication：每個 storage segment 跨 3 AZ × 2 node、共 6 個 storage node
- Write quorum：4-of-6（容忍 1 AZ + 1 node 失效仍能寫）
- Read quorum：3-of-6（讀 quorum 比 write 小、降低 read latency）
- Compute node 寫只送 redo log 到 storage、不送整個 page（vs PostgreSQL primary 寫 WAL + dirty page flush）
- Storage node 自己 apply redo log 重建 page、自己 checkpoint、不靠 compute node
- 對應 knowledge card：[quorum](/backend/knowledge-cards/quorum/)、[replication-lag](/backend/knowledge-cards/replication-lag/)、補連 [WAL](/backend/knowledge-cards/wal/)（若已建卡）
- 跟通用 quorum 概念差在哪：Aurora quorum 是 *storage-level*（不是 application-level Cassandra 風格）、application 看到 single primary SQL

## 操作流程（Operations）

- 配置 segment：Aurora 不暴露 segment-level config、讀者只能透過 instance class、storage type（Standard / I/O-Optimized）跟 backup retention 影響
- CLI / Console：`aws rds describe-db-clusters` 看 `StorageType` / `AllocatedStorage`、CloudWatch 看 `VolumeBytesUsed`、`VolumeReadIOPs`、`VolumeWriteIOPs`
- 驗證點：寫入 latency p99（PostgreSQL primary 1-3ms vs Aurora 3-6ms、read 0.5-1ms 跨 AZ 仍快）、storage autoscale event（128 TB 上限前自動 grow）
- Rollback boundary：Aurora storage 是 cluster-level、無法回滾 storage 設計；only rollback 是切回 RDS / 自管（需走 migration playbook、非配置層 rollback）

## 失敗模式（Failure modes）

- 誤以為 Aurora 寫入比 PostgreSQL primary 一定更快：寫小 row、單筆 commit、跨 AZ network round-trip 仍是 3-5ms、不會比 local SSD primary 快
- AZ-level outage 期間寫入 latency spike：失去 1 AZ 後 quorum 仍成立但只能用 2-of-2 + 1（remaining AZ）、單一 storage node fault 會把寫推到 timeout
- I/O-Optimized 費用誤判：Standard storage 按 I/O 收費、I/O-Optimized 月費高 30% 但無 I/O 收費、write-heavy + scan-heavy 才划算
- Storage autoscale 假設：自動 grow 但不自動 shrink；TRUNCATE / DROP 大表後 storage 帳單不會回落、要走 logical migration
- Replication lag 誤解：read replica lag 10-30ms 是 *typical*、heavy write + slow query 期間可能秒級、不該假設 read-after-write consistency
- Case 對應根因：[9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) +75% 效能根因是 *compute 不再 flush dirty page*、不是 marketing 的「分散式儲存」籠統說法

## 容量與觀測（Capacity & observability）

- CloudWatch metric：`VolumeBytesUsed`（128 TB 接近時要警告）、`VolumeReadIOPs` / `VolumeWriteIOPs`（判斷 I/O-Optimized ROI）、`AuroraVolumeBytesLeftTotal`、`ReadIOPS` / `WriteIOPS`（compute side）
- 對照 Aurora Performance Insights：`db.IO.aurora_redo_log_flush` wait event 是 quorum write 等待訊號
- 容量上限：128 TB / cluster、15 read replica / region、storage 自動 grow per 10GB
- 跨 region：Aurora Global Database lag 用 `AuroraGlobalDBReplicationLag`（< 1 秒 typical）
- 回路徑：[4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 抽 CloudWatch evidence、[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) 判斷 storage-bound vs compute-bound

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[Aurora cross-AZ failover RTO](./cross-az-failover-rto.md)（storage 設計如何加速 failover）、[Aurora read replica scaling](./read-replica-scaling.md)（共享 storage 為什麼能養 15 replica）、[Aurora Global Database](./global-database-multi-region.md)（跨 region storage replication）
- Migration playbook：[PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/) 對照 operational redesign（storage 設計差是 driver 之一）
- 1.x 章節互引：[1.3 Transaction Boundary](/backend/01-database/transaction-boundary/)（quorum 寫入 vs single-primary transaction 邊界）、[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)（Aurora storage 是 single-region scaling、不是 distributed SQL）
- 何時不用本文：single-region OLTP 用 RDS 仍足夠、storage architecture 細節不影響容量規劃時可跳過

## 寫作前置 checklist

- [ ] case anchor 確認：Netflix +75% case 中 storage 設計與 compute 改寫的因果關係
- [ ] knowledge card 雙引用：[quorum](/backend/knowledge-cards/quorum/) + [replication-lag](/backend/knowledge-cards/replication-lag/)
- [ ] sibling 對比：跟 RDS PostgreSQL local-WAL + stream replication 對照表
- [ ] 預估寫作長度：240-280 行（storage 細節密 + Netflix case 展開）
- [ ] 寫作難度：中（AWS 公開 storage paper + 既有 Netflix case 足夠材料）
