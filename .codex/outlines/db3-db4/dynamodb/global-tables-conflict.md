# DynamoDB Global Tables 多區複寫與 LWW Conflict Resolution：reconciliation 與 application contract

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：B2B SaaS 跟客戶 SLA 寫 99.99%、單 region 跑了一年遇過兩次 region-level outage、合計 downtime 已逼近 SLA 上限；team 要把核心 table 改 Global Tables active-active；首問是「multi-region write 之後資料還會一致嗎」
- 讀者徵兆：跨 region 同一 record 同時 update、application 端看到欄位「跳回去」、稽核 log 顯示某筆 write 被 LWW 蓋掉、reconciliation job 找到 dual-region inconsistency
- Case anchor: [9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) — 99.999% 跨 15 region、8000+ orgs、active-active write；補充 anchor: [9.C26 PayPay](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/)（3 億訊息 / 天、跨 region 訊息系統 TTL + idempotency）

## 核心機制（Vendor-specific mechanism）

- Global Tables：multi-region active-active replica、每 region 都能寫、async replication（typical < 1s but no SLA）
- Conflict resolution：LWW（Last Writer Wins）by wall clock timestamp（attribute `aws:rep:updatetime`）— 不是 logical clock、不是 vector clock、純物理時間
- 跨 region 一致性語意：本 region 寫立即可讀（read-your-write 同 region）、其他 region 看到要等 replication；strong read 只在同 region 內 quorum 內成立
- Capacity 獨立：每個 region 自己的 RCU/WCU、`ReplicatedWriteCapacityUnits` 是跨 region replication 額外 WCU、按 region 數倍計
- 對應 knowledge card：[consistency level](/backend/knowledge-cards/consistency-level/)、[rto](/backend/knowledge-cards/rto/)、[rpo](/backend/knowledge-cards/rpo/)

## 操作流程（Operations）

- Step 1：access pattern 分類 — region-pinned data（user 主要 region）vs global data（跨 region read）、決定哪些 table 上 Global Tables
- Step 2：啟用 Global Tables — `aws dynamodb update-table --replica-updates`、加 region 後 vendor 自動 backfill；backfill 期間 capacity 雙倍
- Step 3：application 設計 — 寫入策略選 `home region write`（每 user 固定 region 寫、避免 conflict）或 `nearest region write`（latency 優先、conflict 機率高）
- Step 4：idempotency — 每筆 write 加 `request_id` 或 `client_timestamp`、application 端去重；不依賴 DynamoDB 的 LWW
- Step 5：conflict detection — DynamoDB Streams 訂閱、Lambda 比較 `aws:rep:updatetime` 跟 application timestamp、抓出可疑 conflict 進 reconciliation queue
- Step 6：reconciliation pipeline — 把 conflict 進 SQS、人工或 rule-based merge、結果寫回 base table
- 驗證點：DR drill 演 region outage、確認 secondary region 接管後 read / write 都正常；replication lag p99 < 1s
- Rollback boundary：region 可逐個移除、但 active-active 改 active-passive 期間 application 需配合路由切換

## 失敗模式（Failure modes）

- **Case 1：LWW 默默吃掉 write** — 跨 region 同 record concurrent update、後到的 write 因 timestamp 較大蓋過先到的；business 看到「我送出的更新沒了」；修法：critical write 加 `ConditionExpression` 比較 `version` attribute、conflict 時 application 端 retry + merge
- **Case 2：Clock skew 讓 LWW 倒置** — region A 寫入 timestamp 因 NTP skew 比 region B 的後寫快 200ms、結果舊資料贏；修法：依靠 application timestamp + monotonic counter、不依賴 server wall clock
- **Case 3：Replication lag 撞 SLO** — 大 batch write 期間 replication lag 從 1s 變 30s、跨 region read 看到 30s 前資料、application 端 user 操作異常；修法：偵測 `ReplicationLatency` 升高時 application 端切 home region read、避免跨 region eventual read
- **Case 4：DR 切換後 stale data 持續 propagate** — primary region outage 切到 secondary、舊 primary 恢復後仍把 outdated data 推回去；修法：DR runbook 含「舊 primary 恢復後人工 reconciliation 或重建」step、不可全自動 catch-up
- **Case 5：跨 region transaction 失敗** — application 試圖跨 region `TransactWriteItems`、API 不支援跨 region transaction、原子性破裂；修法：transaction 限同 region 內、跨 region 用 saga + idempotent + reconciliation
- Anti-recommendation：single-region availability 已達 99.95% + RTO 可接受 1 小時 + 預算敏感 → 用 PITR + 跨 region backup 而非 Global Tables；Global Tables cost = N × single region cost 不止

## 容量與觀測（Capacity & observability）

- CloudWatch metric：`ReplicationLatency`（p99 通常 < 1s、SLO 設 5s alarm）、`PendingReplicationCount`（積壓量）、`ReplicatedWriteCapacityUnits`（額外 WCU）
- DynamoDB Streams + Lambda：抓 conflict event、寫進獨立 audit table；reconciliation job 從 audit table 跑
- Region-level dashboard：每 region 獨立 capacity / latency / error rate panel；DR drill 看是否能在 RTO 內切換
- Cost monitoring：Global Tables cost ≈ N region × base cost + replication WCU；4 region 成本約 4.5x single region
- 接回 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)、[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[consistency-model-optimization](/backend/01-database/vendors/dynamodb/consistency-model-optimization/)（同 region eventual / strong 取捨）、[on-demand-vs-provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/)（多 region capacity 規劃放大）、[partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/)（hot partition 跨 region 同樣存在）
- 替代路由：global strong consistency 必要 → Spanner / Cosmos DB strong consistency level
- Migration playbook：single-region → Global Tables 屬 topology re-layout、對應 [migration playbook methodology](/posts/migration-playbook-methodology/) Type F
- 跟 [Genesys 9.C24](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) 互引：15 region 5 個 9 可用性的工程實踐
- 跟 [PayPay 9.C26](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/) 互引：idempotency + TTL 在多 region 訊息系統的作用

## 寫作前置 checklist

- [ ] case anchor 確認（Genesys 主、PayPay 補）
- [ ] knowledge card 雙引用（consistency-level + rto + rpo）
- [ ] sibling 對比（consistency-model-optimization 是同 region、global-tables 是跨 region 延伸）
- [ ] 預估寫作長度：260-300 行（含 conflict resolution 流程、reconciliation pipeline、DR runbook、5 case）
