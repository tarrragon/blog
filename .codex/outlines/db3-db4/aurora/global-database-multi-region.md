# Aurora Global Database：跨 region async replication、< 1 秒 lag 與 DR / read-route 取捨

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。
>
> **Stage 3 校準（case-first）**：anti-recommendation 設計（合規禁止跨境 → 用 fleet 不用 Global Database）正確（F3.6 已支撐）、keep 狀態。可選補：(1) 若 FanDuel 雙峰 case 引用、明示「betting 走 Aurora、streaming 走 CDN」分開（F3.12 scope warning），(2) Fleet 治理 cross-link 到 `read-replica-scaling.md` 邊界段。

## 問題情境（Production pressure）

- 啟動壓力：global SaaS / 跨地理金融服務、需要 region-level DR（us-east-1 整 region 失效時 < 5 分鐘恢復寫入）、或跨地理 read（歐洲用戶查美國 primary 延遲 100ms+ 不可接受）、但又不到「multi-region active-active write」需求
- 讀者徵兆：「Global Database 是 sync 還是 async？lag 多少？」「Secondary region 可以寫嗎？」「Region failover 流程跟 cross-AZ 一樣嗎？」「跟 Aurora DSQL / Spanner 怎麼選？」
- Case anchor：[9.C14 Standard Chartered Aurora banking](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 7 個受監管市場、*合規要求* 跟 Global Database 設計選擇的張力（為什麼選獨立 cluster 而非 Global Database）

## 核心機制（Vendor-specific mechanism）

- Aurora Global Database：跨 region async replication、storage-level（不是 logical / streaming）、< 1 秒 typical lag
- Architecture：primary region 1 個 writer cluster + N read replica、secondary region N 個 reader-only cluster（最多 5 個 secondary region）
- Write path：application 寫 primary region → primary region storage commit → async push to secondary region storage（不等 secondary ack）
- Read path：secondary region 直接從 local storage 讀、不需要跨 region 拉
- DR 切換：手動 promote secondary（managed planned failover < 2 分鐘、unplanned 5-15 分鐘）、不像 cross-AZ failover < 30 秒
- 對應 knowledge card：[stale-read](/backend/knowledge-cards/stale-read/)、[rpo](/backend/knowledge-cards/rpo/)、[rto](/backend/knowledge-cards/rto/)
- 跟通用 cross-region replication 差在哪：Aurora 在 storage layer 複製（不是 logical）、lag 上限更穩定；vs PostgreSQL logical replication lag 受寫速度影響大

## 操作流程（Operations）

- 配置：`aws rds create-global-cluster --global-cluster-identifier myglobal`、`aws rds create-db-cluster --global-cluster-identifier myglobal --engine aurora-postgresql --source-region us-east-1` 加 secondary region
- Application routing：寫永遠去 primary region writer endpoint；read 可走 secondary region reader endpoint
- DR 切換：`aws rds failover-global-cluster --global-cluster-identifier myglobal --target-db-cluster-identifier secondary-cluster-arn`、application 端要 reconfigure connection string（DNS 不自動切跨 region）
- 驗證點：`AuroraGlobalDBReplicationLag` < 1 秒、planned failover RTO 量測、application read 路徑跨 region latency
- Rollback boundary：promote secondary 後原 primary 變 secondary、不會自動 fallback；rollback 要再做一次 failover

## 失敗模式（Failure modes）

- 期待 multi-region active-active write：Global Database secondary 是 *reader-only*、寫只能去 primary region；要 active-active 改 Aurora DSQL / Spanner
- DNS 不跨 region 自動切：cross-AZ failover writer endpoint 自動跟、cross-region 不會、application 要管 region-specific connection string
- 跨 region read 假設 strong consistency：lag < 1 秒不是 zero、read-after-write 場景仍會看到 stale data
- Lag spike during bulk operation：DDL / bulk insert 期間 cross-region lag 可能跳到秒級、不該假設 < 1 秒永遠成立
- 合規邊界誤用 Global Database：Standard Chartered 案例顯示受監管市場資料*不能跨境複製*、Global Database 違反合規、要改用每市場獨立 cluster（fleet 拓樸吸收合規邊界、見 [read-replica-scaling.md](./read-replica-scaling.md) fleet 治理 SSoT）
- Cost trap：cross-region data transfer 收費、heavy write workload 跨 region 月費可能 doubled
- Case 對應根因：Standard Chartered 為什麼選 7 個獨立 cluster 而非 1 個 Global Database、合規邊界比 DR 簡化更重要
- 若引 FanDuel 雙峰 case 對照 multi-region 場景（**scope warning 必明示**）：FanDuel 5-10x 是 *betting 服務的 Aurora 擴容*、streaming 走 CDN 不走 Aurora（[case「判讀」段第 1 點](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/)）；引用時不能壓成「Aurora 撐 5-10x」單一數字、且 betting transaction TPS / concurrent streams 案例自承未公開、不能 over-extrapolate

## 容量與觀測（Capacity & observability）

- CloudWatch metric：`AuroraGlobalDBReplicationLag`（secondary lag）、`AuroraGlobalDBReplicatedWriteIO`（cross-region data transfer）、`AuroraGlobalDBProgressLag`
- 容量上限：1 primary region + 5 secondary region、每 secondary region 16 個 reader 含 1 個 headless（可升 writer）
- Cost signal：CloudWatch `AuroraGlobalDBReplicatedWriteIO` × per-region transfer rate = 月費（write 多時意外高）
- 驗證 DR：planned failover drill 每季一次、量測 RTO / RPO
- 回路徑：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) cross-region cost、[8.x DR playbook](/backend/08-incident-response/) region-level failover decision

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[Aurora storage architecture](./storage-architecture.md)（cross-region replication 是 storage-level 延伸）、[Aurora cross-AZ failover RTO](./cross-az-failover-rto.md)（cross-AZ 跟 cross-region failover RTO 數量級對比）
- Migration playbook：若從 PostgreSQL streaming replication 跨 region 升級走 [PG → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/)
- 何時改 Aurora DSQL / Spanner / CockroachDB：multi-region active-active write、< 100ms write latency requirement、跨 region strong consistency
- 何時不用 Global Database：合規禁止跨境複製（Standard Chartered case）、single-region 已滿足 DR / read、跨 region cost 不划算
- 1.x 章節互引：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) Global Database vs distributed SQL 對比、[1.13 DR / 跨 region 設計](/backend/01-database/disaster-recovery/)（若已建）

## 寫作前置 checklist

- [ ] case anchor 確認：Standard Chartered 為什麼*不用* Global Database 是核心對照、不是直接 endorsement
- [ ] knowledge card 雙引用：[stale-read](/backend/knowledge-cards/stale-read/) + [rpo](/backend/knowledge-cards/rpo/)
- [ ] sibling 對比：跟 Aurora DSQL active-active 的決策樹（連到 cockroachdb decision tree article）
- [ ] 預估寫作長度：220-260 行（架構 + DR 流程 + 合規 anti-recommendation）
- [ ] 寫作難度：中（AWS 文件足、合規邊界由 Standard Chartered case 撐起，新內容是「何時不用」段）
