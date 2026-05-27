# DynamoDB Global Tables 多區複寫與 LWW Conflict Resolution：reconciliation 與 application contract

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。
>
> **Stage 3 校準紀錄**：原 outline 主軸正確、F1.10 / F1.11 / F1.12 / F1.13 / F1.17 充分支撐。本次 keep + 補強：補 *正向* access pattern 段（cross-device sync / global read / DR failover、不只 conflict）、強化 B2B SaaS vs B2C 業務 driver 對比、降溫 9.C26 PayPay 引用（Streams 是通用實作非 case 揭露）、明示 99.999% 是滾動指標 + 99.99% / 99.999% 是 B2B 合約而非 B2C 預設。

## 問題情境（Production pressure）

### 啟動壓力與徵兆

- 啟動壓力：B2B SaaS 跟客戶 SLA 寫 99.99%、單 region 跑了一年遇過兩次 region-level outage、合計 downtime 已逼近 SLA 上限；team 要把核心 table 改 Global Tables active-active；首問是「multi-region write 之後資料還會一致嗎」
- 讀者徵兆：跨 region 同一 record 同時 update、application 端看到欄位「跳回去」、稽核 log 顯示某筆 write 被 LWW 蓋掉、reconciliation job 找到 dual-region inconsistency

### B2B SaaS vs B2C 業務 driver 對比（F1.11 + F1.12、9.C24 Genesys「策略」段第 4 條 + 「判讀」段第 1 條揭露）

Global Tables 不是預設選擇、是 *業務性質* 決定的工程投資。9.C24 Genesys 揭露兩條關鍵 frame：

**業務 driver 對比表**：

| 業務性質     | 典型可用性目標           | 年停機容忍           | Multi-region 投資邏輯                           |
| ------------ | ------------------------ | -------------------- | ----------------------------------------------- |
| B2C 大型網站 | 99.9%                    | 8.76 小時            | 通常單 region + PITR / cross-region backup 划算 |
| B2B SaaS     | 99.95% 或 99.99%（合約） | 4.4 小時 / 52.6 分鐘 | 合約義務、客戶 SLA 違約有金錢損失、ROI 正向     |
| 客服平台類   | 99.999%（合約客戶）      | 5.26 分鐘            | 客戶停線損失極大、15 region 投資合理（Genesys） |

**Scope warning（F1.10）**：99.999% 是「12 個月滾動歷史值、不代表未來持續達成」（9.C24 警惕段第 1 條）、可用性是 *滾動指標、不是恆久承諾*。寫稿引用 Genesys 99.999% 數字時要明示口徑（滾動 / customer-facing）。

**成本對比（9.C24 揭露）**：15 region 成本約 = 1 region 的 15x（base table cost）+ 跨 region replication WCU。對 B2B SaaS 是合理投資（合約義務）、對 B2C 通常不划算。每多一個 9、容量規劃跟運維成本指數成長。

### Case anchor

- **主**：[9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) — 99.999% 跨 15 region、8000+ orgs、active-active write、B2B SaaS 客服平台合約場景。
- **補（正向 access pattern）**：[9.C27 Disney+](/backend/09-performance-capacity/cases/disney-plus-content-metadata/) — watchlist + 播放進度跨裝置同步（F1.17、見下方「正向 access pattern」段）。
- **補（謹慎引用）**：[9.C26 PayPay](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/) — 3 億訊息 / 天、揭露 *需求分層*（通知 vs 訊息）跟 TTL 機制；*未* 揭露用 DynamoDB Streams、本 outline 把 Streams 寫成「通用工程實作」、不是 PayPay case 揭露（對應 F1.13 警示）。

## 核心機制（Vendor-specific mechanism）

- Global Tables：multi-region active-active replica、每 region 都能寫、async replication（typical < 1s but no SLA）
- Conflict resolution：LWW（Last Writer Wins）by wall clock timestamp（attribute `aws:rep:updatetime`）— 不是 logical clock、不是 vector clock、純物理時間
- 跨 region 一致性語意：本 region 寫立即可讀（read-your-write 同 region）、其他 region 看到要等 replication；strong read 只在同 region 內 quorum 內成立
- Capacity 獨立：每個 region 自己的 RCU/WCU、`ReplicatedWriteCapacityUnits` 是跨 region replication 額外 WCU、按 region 數倍計
- 對應 knowledge card：[consistency level](/backend/knowledge-cards/consistency-level/)、[rto](/backend/knowledge-cards/rto/)、[rpo](/backend/knowledge-cards/rpo/)

### 正向 access pattern：不只 conflict 議題（F1.17、9.C27 Disney+「判讀」段第 3 條揭露）

Global Tables 不只是 DR / availability、也是 *正向 access pattern* 的工程方案。原 outline 主軸偏 conflict / LWW、本段補正向用例：

- **Cross-device sync**（Disney+ 揭露）：用戶在手機看到一半、晚上回家用電視繼續、播放進度跨裝置同步。Global Tables 自然解這個 access pattern — 用戶在不同 region 登入同帳號、寫入自動同步。最終一致性可接受場景。
- **Global read（latency 優化）**：跨地域用戶讀取就近 region 副本、latency 從 200ms 降到 < 10ms。read 比 write 多很多倍的 workload（feed / catalog / 設定）受益最大。
- **DR failover**：region-level outage 時、application 切到 secondary region 繼續服務、RTO 通常 < 5 分鐘（DNS / routing 切換時間）。
- **B2C 也可能划算的場景**：cross-device sync 是 *user-facing experience*、不是合規 / 可用性 driver、所以 B2C 大規模平台（Disney+ / Spotify 類）也可能投資 Global Tables。判讀軸是「sync 體驗是否核心 UX」、不只「合約 SLA」。

寫稿時 framing：本段先講「Global Tables 不只是 conflict 痛點、也是正向工程方案」、後續才進 conflict resolution 細節。避免讓讀者誤以為 Global Tables 只是「跨 region 寫入會 conflict、所以痛苦」。

## 操作流程（Operations）

- Step 1：access pattern 分類 — region-pinned data（user 主要 region）vs global data（跨 region read / cross-device sync）、決定哪些 table 上 Global Tables
- Step 2：啟用 Global Tables — `aws dynamodb update-table --replica-updates`、加 region 後 vendor 自動 backfill；backfill 期間 capacity 雙倍
- Step 3：application 設計 — 寫入策略選 `home region write`（每 user 固定 region 寫、避免 conflict）或 `nearest region write`（latency 優先、conflict 機率高）
- Step 4：idempotency — 每筆 write 加 `request_id` 或 `client_timestamp`、application 端去重；不依賴 DynamoDB 的 LWW
  - **Scope warning**：「加 request_id 或 client_timestamp」具體實作屬通用工程知識、9.C26 PayPay case 揭露「通知不可丟失」需求、但 *沒* 揭露具體 idempotency 實作。引用 PayPay 時要降溫成「PayPay 揭露需求分層（通知 vs 訊息）、idempotency 為通用工程實作」、不寫成「PayPay 使用 request_id」
- Step 5：conflict detection — DynamoDB Streams 訂閱、Lambda 比較 `aws:rep:updatetime` 跟 application timestamp、抓出可疑 conflict 進 reconciliation queue
  - **Scope warning**：DynamoDB Streams 用法屬通用工程實作、PayPay case *沒* 明示用 Streams、引用時要分層
- Step 6：reconciliation pipeline — 把 conflict 進 SQS、人工或 rule-based merge、結果寫回 base table
- 驗證點：DR drill 演 region outage、確認 secondary region 接管後 read / write 都正常；replication lag p99 < 1s
- Rollback boundary：region 可逐個移除、但 active-active 改 active-passive 期間 application 需配合路由切換

## 失敗模式（Failure modes）

- **Case 1：LWW 默默吃掉 write** — 跨 region 同 record concurrent update、後到的 write 因 timestamp 較大蓋過先到的；business 看到「我送出的更新沒了」；修法：critical write 加 `ConditionExpression` 比較 `version` attribute、conflict 時 application 端 retry + merge
- **Case 2：Clock skew 讓 LWW 倒置** — region A 寫入 timestamp 因 NTP skew 比 region B 的後寫快 200ms、結果舊資料贏；修法：依靠 application timestamp + monotonic counter、不依賴 server wall clock
  - **Scope warning**：「200ms NTP skew」具體數字屬通用工程估算、case 未揭露
- **Case 3：Replication lag 撞 SLO** — 大 batch write 期間 replication lag 從 1s 變 30s、跨 region read 看到 30s 前資料、application 端 user 操作異常；修法：偵測 `ReplicationLatency` 升高時 application 端切 home region read、避免跨 region eventual read
- **Case 4：DR 切換後 stale data 持續 propagate** — primary region outage 切到 secondary、舊 primary 恢復後仍把 outdated data 推回去；修法：DR runbook 含「舊 primary 恢復後人工 reconciliation 或重建」step、不可全自動 catch-up
- **Case 5：跨 region transaction 失敗** — application 試圖跨 region `TransactWriteItems`、API 不支援跨 region transaction、原子性破裂；修法：transaction 限同 region 內、跨 region 用 saga + idempotent + reconciliation
- Anti-recommendation：single-region availability 已達 99.95% + RTO 可接受 1 小時 + 預算敏感（特別 B2C 場景）→ 用 PITR + 跨 region backup 而非 Global Tables；Global Tables cost = N × single region cost 不止（對應 B2B vs B2C driver 對比）

## 容量與觀測（Capacity & observability）

- CloudWatch metric：`ReplicationLatency`（p99 通常 < 1s、SLO 設 5s alarm）、`PendingReplicationCount`（積壓量）、`ReplicatedWriteCapacityUnits`（額外 WCU）
- DynamoDB Streams + Lambda：抓 conflict event、寫進獨立 audit table；reconciliation job 從 audit table 跑
- Region-level dashboard：每 region 獨立 capacity / latency / error rate panel；DR drill 看是否能在 RTO 內切換
- Cost monitoring：Global Tables cost ≈ N region × base cost + replication WCU；4 region 成本約 4.5x single region；15 region（Genesys 規模）約 15x
- 接回 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)、[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)
- **指標口徑紀律**（Frame 7、F1.10）：99.99% / 99.999% SLA 是 *滾動指標 + 歷史值*、不是永久承諾；引用 Genesys 99.999% 時明示「12 個月滾動 / customer-facing」

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[consistency-model-optimization](/backend/01-database/vendors/dynamodb/consistency-model-optimization/)（同 region eventual / strong 取捨）、[on-demand-vs-provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/)（多 region capacity 規劃放大）、[partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/)（hot partition 跨 region 同樣存在）
- 替代路由：global strong consistency 必要 → Spanner / Cosmos DB strong consistency level
- Migration playbook：single-region → Global Tables 屬 topology re-layout、對應 [migration playbook methodology](/posts/migration-playbook-methodology/) Type F
- 跟 [Genesys 9.C24](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) 互引：15 region 5 個 9 可用性的工程實踐 + B2B SaaS 業務 driver
- 跟 [Disney+ 9.C27](/backend/09-performance-capacity/cases/disney-plus-content-metadata/) 互引：cross-device sync 作為 *正向* access pattern
- 跟 [PayPay 9.C26](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/) 互引：揭露需求分層（通知 vs 訊息）、idempotency / Streams 為通用工程實作、PayPay *未* 公開揭露具體實作（陷阱 4 注意）

## 寫作前置 checklist

- [ ] case anchor 確認（Genesys 9.C24 主、Disney+ 9.C27 補正向 access pattern、PayPay 9.C26 補需求分層但降溫引用）
- [ ] knowledge card 雙引用（consistency-level + rto + rpo）
- [ ] sibling 對比（consistency-model-optimization 是同 region、global-tables 是跨 region 延伸）
- [ ] **Scope warning 明示**：99.999% 是「12 個月滾動」非永久承諾、idempotency / DynamoDB Streams 屬通用工程實作 PayPay 沒揭露具體實作、「200ms NTP skew」屬通用估算
- [ ] B2B vs B2C 業務 driver 段明示「業務性質決定可用性目標、不是越高越好、每多一個 9 cost 指數成長」
- [ ] 正向 access pattern 段（cross-device sync / global read / DR failover）在 conflict 議題之前、避免讀者誤以為 Global Tables 只是 conflict 痛點
- [ ] 引用 case 數字時標口徑（Genesys 99.999% 滾動 + customer-facing、Disney+ 跨裝置 sync 屬 access pattern frame）
- [ ] 預估寫作長度：280-320 行（含 B2B/B2C driver 表 + 正向 access pattern 段 + conflict resolution 流程 + reconciliation pipeline + DR runbook + 5 case）
