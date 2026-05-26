# Aurora Read Replica Scaling：15 replica 上限、lag profile 與 peak workload 容量規劃

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：FanDuel Super Bowl / DraftKings 比賽日、流量 5-10 倍尖峰、read query（用戶查 balance / 投注紀錄 / odds）打爆 primary、需要快速擴 read replica 但又怕 lag 把 stale read 推到 user-facing
- 讀者徵兆：「加 read replica 後 primary CPU 沒降、為什麼？」「Auto-scaling 加 replica 要幾分鐘、來不及接尖峰」「Reader endpoint round-robin 把 query 打到 lag 大的 replica、用戶看到舊 balance」
- Case anchor：[9.C28 FanDuel dual-peak](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) Super Bowl 5-10x peak、直播 + 投注雙工作負載；[9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 200 個 cluster、每集 cluster 用多 read replica

## 核心機制（Vendor-specific mechanism）

- 15 replica 上限：每個 Aurora cluster 最多 15 個 read replica（跨 AZ）、跨 region replica 走 Global Database（不算 15）
- 共享 storage：replica 不靠 logical replication catch-up、直接從共享 storage 讀；lag 來源是 *compute node 的 buffer cache 同步*、不是 WAL replay
- Lag profile：typical 10-30ms（vs PostgreSQL streaming replication 秒級）、heavy write 期間可能 100ms+、不會像 PostgreSQL 那樣 unbounded
- Reader endpoint：DNS-based round-robin、不感知 replica 健康狀態；application 想要 lag-aware routing 要自己實作或用 RDS Proxy
- Auto-scaling policy：CloudWatch metric（CPU / connection）trigger、replica creation 2-5 分鐘、無法用於秒級尖峰
- 對應 knowledge card：[replication-lag](/backend/knowledge-cards/replication-lag/)、[stale-read](/backend/knowledge-cards/stale-read/)、[read-replica](/backend/knowledge-cards/read-replica/)（若已建）
- 跟通用 read replica 差在哪：Aurora replica 不用 catch-up WAL、lag 上限可預測；vs PostgreSQL streaming replication lag 是 unbounded（取決於 primary 寫速度）

## 操作流程（Operations）

- 配置：`aws rds create-db-instance --db-cluster-identifier mycluster --db-instance-class db.r6g.4xlarge`、Auto-scaling policy 用 CloudWatch alarm
- Reader endpoint vs custom endpoint：custom endpoint 可以 group 特定 replica（例：分析 query 走獨立 endpoint、不影響 OLTP）
- 預配 vs auto-scale：peak workload 預知（Super Bowl）用預配（提前 1 小時加 replica）、unpredictable burst 才用 auto-scale
- 驗證點：`AuroraReplicaLag` < 100ms、reader endpoint CPU distribution 均勻、application stale-read error rate < 0.1%
- Rollback boundary：移除 replica 即時生效、無 data loss；但 reader endpoint DNS cache 仍可能短暫 routing 到已移除 replica

## 失敗模式（Failure modes）

- 加 replica 後 primary CPU 沒降：application 沒把 read query routing 到 reader endpoint、所有 query 仍打 primary；要 application 端拆 read / write data source
- Reader endpoint round-robin 推 stale read：read-after-write 場景（用戶下注後立刻查 balance）打到 lagging replica、看到舊 balance、客訴；解法：sticky session 或 application 端做「下注後 N 秒走 primary」
- Auto-scaling 來不及接秒級尖峰：replica creation 2-5 分鐘、Super Bowl 開賽 30 秒尖峰已過；FanDuel 案例靠預配
- 15 replica 上限：超過 15 個 read replica 需求要拆 cluster（DraftKings 200 個獨立 cluster 模式）、不是堆 replica
- Heavy write 期間 replica lag spike：bulk insert / DDL 期間 replica buffer cache invalidate、lag 可能 100-500ms、不該假設 typical 10-30ms 永遠成立
- Case 對應根因：FanDuel 為什麼 Super Bowl 前 1 小時預配而非 auto-scale；DraftKings 為什麼 200 個 cluster 而非 1 個 cluster + 200 replica

## 容量與觀測（Capacity & observability）

- CloudWatch metric：`AuroraReplicaLag`（per replica）、`AuroraReplicaLagMaximum`（cluster max）、`CPUUtilization` per replica、`DatabaseConnections` per replica
- Application metric：read query latency p99 per endpoint（writer vs reader）、stale-read error count
- 容量上限：15 replica / cluster、cross-region 走 Global Database
- 容量公式：read QPS / replica throughput = replica count、加 30% buffer for lag spike
- 回路徑：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) 判斷 read-bound vs write-bound、[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) peak workload 預配 vs auto-scale 決策

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[Aurora storage architecture](./storage-architecture.md)（共享 storage 為什麼能養 15 replica）、[Aurora cross-AZ failover RTO](./cross-az-failover-rto.md)（replica 升 primary 流程）、[Aurora Global Database](./global-database-multi-region.md)（跨 region replica 配置）
- 何時拆 cluster vs 加 replica：> 15 replica 需求、blast radius 隔離、合規邊界 → 拆 cluster
- 1.x 章節互引：[1.4 Replication Lag](/backend/01-database/replication-lag/)（若已建）、[1.10 Read replica 設計](/backend/01-database/read-replica-design/)（若已建）
- RDS Proxy 整合：lag-aware routing、connection pool 共享、Lambda 場景
- 何時不用本文：single replica + cross-AZ failover 已滿足、read traffic 不是 bottleneck

## 寫作前置 checklist

- [ ] case anchor 確認：FanDuel Super Bowl peak 預配時機、DraftKings 200 cluster 設計理由
- [ ] knowledge card 雙引用：[replication-lag](/backend/knowledge-cards/replication-lag/) + [stale-read](/backend/knowledge-cards/stale-read/)
- [ ] sibling 對比：跟 PostgreSQL streaming replication 的 lag profile 對照
- [ ] 預估寫作長度：220-260 行（lag 機制 + auto-scaling 限制 + FanDuel/DraftKings 雙 case 展開）
- [ ] 寫作難度：中（兩個 case 提供 peak workload 訊號、auto-scaling 行為公開）
