# Aurora Cross-AZ Failover：RTO 量測、endpoint routing 與 application reconnect 契約

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。
>
> **Stage 3 校準（case-first）**：Standard Chartered anchor 充分（F3.6）、keep 狀態。可選補：明示「Standard Chartered 用每市場獨立 cluster 而非 Global Database 跨 region failover」的合規 driver、Fleet 治理 cross-link 到 `read-replica-scaling.md` 邊界段。

## 問題情境（Production pressure）

- 啟動壓力：DraftKings / Standard Chartered 規模的金融交易服務、AZ-level outage 期間用戶下注不能斷、RTO 預算 < 60 秒、但 application 端看到的 reconnect 行為跟 AWS 文件「< 30 秒 failover」不一致
- 讀者徵兆：「failover trigger 後新 connection 還連到舊 primary、為什麼？」「writer endpoint DNS 切換了、application 還沒重連、什麼時候會」「failover 期間是 in-flight transaction 全 abort 還是部分 commit？」
- Case anchor：[9.C14 Standard Chartered Aurora banking](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 7 個受監管市場、合規要求每市場獨立 cluster 跟 RTO 量測

## 核心機制（Vendor-specific mechanism）

- Failover lifecycle 三段：detection（health check 失敗）→ promotion（read replica 升 primary）→ DNS update（cluster endpoint 指向新 primary）
- 不需要 data sync：storage layer 跨 AZ 共享、replica 升 primary 不需要 catch-up；vs traditional PostgreSQL streaming replication 要等 WAL apply
- Cluster endpoint vs writer endpoint vs reader endpoint：
  - Writer endpoint：跟著 failover 走、DNS 切到新 primary
  - Reader endpoint：load-balance 到所有 replica、replica 升 primary 後不再 serve read
  - Custom endpoint：用戶自定 routing rule、failover 期間行為要驗證
- DNS TTL：Aurora endpoint DNS TTL 5 秒、但 application driver / OS 可能 cache 更久（JVM `networkaddress.cache.ttl` 預設 -1 cache forever）
- 對應 knowledge card：[failover](/backend/knowledge-cards/failover/)、[rto](/backend/knowledge-cards/rto/)、[rpo](/backend/knowledge-cards/rpo/)
- 跟通用 failover 差在哪：Aurora 不需要 data catch-up phase、failover 主要瓶頸是 DNS propagation + application reconnect、不是 promotion 本身

## 操作流程（Operations）

- 配置：Multi-AZ deployment（至少 1 個跨 AZ replica）、replica 升 primary 優先順序（`PromotionTier` 0-15）
- CLI：`aws rds failover-db-cluster --db-cluster-identifier mycluster` 觸發手動 failover、量測 RTO
- Application 端：JVM `networkaddress.cache.ttl = 5`、connection pool 設 `validationQuery`、retry policy（exponential backoff、max 30 秒）
- 驗證點：CloudWatch `DatabaseConnections` 看 reconnect spike、application metric「first successful write after failover」
- Rollback boundary：promotion 不可逆（原 primary 變 replica、不會自動 fallback）、只能下一輪 failover 切回去

## 失敗模式（Failure modes）

- DNS cache 過長：application 看 RTO 是 60 秒而非 AWS 文件 30 秒、根因 JVM DNS cache、不是 Aurora 慢
- Application connection pool 不知道 endpoint 換了：cached connection 全 stale、新查詢 timeout 才觸發 reconnect、p99 spike
- Reader endpoint 假設：failover 期間 reader endpoint 短暫包含 promoted replica（已升 primary）、reader query 打到 primary、寫鎖競爭
- In-flight transaction 全 abort：failover 不保留 transaction 狀態、application 沒做 retry 會丟失 commit
- PromotionTier 配置忽略：cross-region replica 設 tier 0 會優先升、跨 region 升 primary 後 application latency 暴漲
- Case 對應根因：[9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) 用每市場獨立 cluster 而非 Global Database 跨 region failover、跟「合規要求 + RTO 預算」綁定 — 合規 driver 揭露：受監管市場資料 *不能跨境複製*、Global Database 在這種場景違反合規（case「判讀」段第 1 點）、每市場用獨立 cluster 的 cross-AZ failover 吸收 RTO 預算、不是用跨 region failover。Fleet 拓樸（7 個合規 cluster）詳見 [Aurora read replica scaling](./read-replica-scaling.md) fleet 治理 SSoT 邊界段。

## 容量與觀測（Capacity & observability）

- CloudWatch metric：`FailoverEvent`（counter）、`DatabaseConnections`（reconnect spike）、`AuroraReplicaLag`（failover 前 replica 是否 caught up）
- Application metric：first successful write latency after failover trigger、connection pool error rate、retry count
- 量測 RTO：`aws rds failover-db-cluster` + application heartbeat 寫入時間戳、計算 gap
- Alert：`FailoverEvent > 0` 立即通知、`DatabaseConnections` 5-min drop > 50% 警告 stale connection
- 回路徑：[8.x incident response](/backend/08-incident-response/) failover playbook、[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) 判斷 reconnect-bound vs query-bound

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[Aurora storage architecture](./storage-architecture.md)（為什麼不需要 data catch-up）、[Aurora Global Database](./global-database-multi-region.md)（跨 region failover 不同 RTO 數量級）
- Migration playbook：[PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/) 的 HA redesign 段
- 1.x 章節互引：[1.7 HA / replication topology](/backend/01-database/ha-replication-topology/)（若已建）、[8.x incident response](/backend/08-incident-response/) failover decision log
- 何時不用本文：non-critical workload、RTO 預算 > 5 分鐘、Multi-AZ 預設配置足夠

## 寫作前置 checklist

- [ ] case anchor 確認：Standard Chartered 為什麼選獨立 cluster 而非 Global Database failover
- [ ] knowledge card 雙引用：[failover](/backend/knowledge-cards/failover/) + [rto](/backend/knowledge-cards/rto/)
- [ ] sibling 對比：跟 Patroni HA 的 promotion 流程差（要等 data catch-up）
- [ ] 預估寫作長度：220-260 行（failover lifecycle + application 契約 + 量測流程）
- [ ] 寫作難度：中（AWS 文件 + application reconnect 模式公開、量測 RTO 是核心新內容）
