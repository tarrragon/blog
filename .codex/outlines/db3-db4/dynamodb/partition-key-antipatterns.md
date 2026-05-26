# DynamoDB Partition Key 反模式與 Write Sharding：從 hot partition 到 composite key 修復

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：售票網站開賣前一小時加開 DynamoDB capacity 到 5000 WCU、開賣瞬間還是看到 throttling event；CloudWatch 顯示總 capacity 才用 1500 WCU、partition-level metric 顯示某 partition 已達 1000 WCU 上限
- 讀者徵兆：`ThrottledRequests` 在低總 utilization 下出現、CloudWatch `WriteThrottleEvents` 不為零、application 端看到 `ProvisionedThroughputExceededException`；on-demand 模式則是 latency 突然從 5ms 跳到 50ms+
- Case anchor: [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — 演唱會 event_id 一個熱門場次、原本 PK = event_id 集中打單 partition；改 composite key `event_id#shard_id`（shard_id = 1-100 隨機）分散到 100 個 partition、IOPS 從 20 衝到 135K
- 補充 anchor: [9.C29 Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/)（5M MAU / 3 月、PK 設計決定 connection-free 後 partition 行為）

## 核心機制（Vendor-specific mechanism）

- DynamoDB partition 的單 partition 上限：3000 RCU、1000 WCU、10GB storage；超過任一個都觸發 partition split
- Adaptive Capacity 會 *跨 partition* 重新分配閒置容量、但 *單 partition* 仍硬上限；不解 single-key 集中
- Partition split 由 vendor 自動觸發、但 *splitting on heat* 有延遲（分鐘級）、突發流量來不及 split 就先 throttle
- Composite key 概念：把高基數 suffix 加進 PK，讓邏輯上同 key 物理上散布；讀取時 fan-out 到所有 shard
- 對應 knowledge card：[hot partition](/backend/knowledge-cards/hot-partition/)、[write sharding](/backend/knowledge-cards/database-sharding/)

## 操作流程（Operations）

- Step 1：access pattern audit、辨識 *寫入集中* key（單一 event / single user / bot user / time-based bucket）
- Step 2：選 shard 數 — 一般 10-100、根據預期單 logical key 的峰值 WCU 除以 800（留 20% buffer）
- Step 3：composite key 設計 — `logical_key#random(0, N)` 寫入、讀取時 N 個 query 平行 fan-out 再 application 端合併
- Step 4：alternative — calculated shard（`hash(user_id) % N`）讓同 user 仍可預測讀取、避免完全 random 的讀取 fan-out
- Step 5：驗證點 — Contributor Insights 看 top-N PK 訪問是否平均分布；CloudWatch partition-level throttle = 0
- Rollback boundary：composite key 寫入端可雙寫舊 + 新 key 一段時間、application read 端 fallback；不可逆動作只在「移除舊 key」階段

## 失敗模式（Failure modes）

- **Case 1：時間序 PK 集中**（`PK = date`、`PK = hour`）— 寫入永遠打當下 partition、舊 partition 閒置；修法：`date#shard` 或改用 event-stream pattern
- **Case 2：bot user 集中**（PK = user_id、某 bot 帳號每秒寫 1000 次）— 單 user_id 達 1000 WCU；修法：偵測高頻 user 後動態加 shard suffix、或改用 rate limit
- **Case 3：composite key 但 read 端忘記 fan-out** — 寫入分散到 100 shard、讀取只 query 一個 shard、結果不完整；修法：讀取必須 N 次 query 並合併，或建反向 GSI
- **Case 4：shard 數選太多 read 端 latency 爆** — N=1000 時讀取 fan-out latency 從 5ms 變 200ms；修法：shard 數依「單 logical key 預期峰值 / 800」估算、不是越多越好
- **Case 5：on-demand 模式以為不會 hot partition** — on-demand 仍受單 partition 1000 WCU 限制、只是 throttling 表現為 latency spike 而非 exception；修法：on-demand 不是 partition key 設計的逃避路徑
- Anti-recommendation：access pattern 寫入分散自然均勻（如 UUID 為 PK、無 logical hot key）、不要預先 sharding；增加 read 複雜度沒帶來收益

## 容量與觀測（Capacity & observability）

- CloudWatch metric：`WriteThrottleEvents` / `ReadThrottleEvents` 按 table 跟 GSI 分；partition-level 透過 Contributor Insights 看
- Contributor Insights：必開、show top-N partition key by access frequency；每月 cost ~$0.02 per million event、值得
- DynamoDB Streams：可用來抓 hot key debugging、寫入事件落 Lambda 後統計
- 跟 capacity mode 互動：provisioned 模式 throttle 立刻可見；on-demand 模式 hot partition 表現為 latency 上升、要看 `SuccessfulRequestLatency` p99
- 接回 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 的 partition 章節

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[single-table-design-pattern](/backend/01-database/vendors/dynamodb/single-table-design-pattern/)（PK 設計上游）、[on-demand-vs-provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/)（capacity mode 對 hot partition 表現的影響）
- Migration playbook：composite key migration 屬「topology re-layout」、寫入需雙軌；對應 [migration playbook methodology](/posts/migration-playbook-methodology/)
- 跟 [Tixcraft 9.C15](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 的互引：售票模式的 6750x 擴展細節
- 跟 [Lemino 9.C29](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) 的互引：connection-free scale 的另一面是 partition 設計責任

## 寫作前置 checklist

- [ ] case anchor 確認（Tixcraft 主、Lemino 補）
- [ ] knowledge card 雙引用（hot partition + database-sharding）
- [ ] sibling 對比（single-table + on-demand-vs-provisioned）
- [ ] 預估寫作長度：240-280 行（含 partition 上限表、composite key 範例、5 case）
