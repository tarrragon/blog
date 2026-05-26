# DynamoDB On-Demand vs Provisioned：capacity mode 對比、auto-scaling 邊界與 cost 模型

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：團隊 quarterly review 看 DynamoDB bill 突然漲 80%、原因是 dev team 把所有 table 切 on-demand「省 capacity 管理」；finance 反問「於是省了多少 SRE 工時、又多花多少 cost」、團隊答不出來
- 反向情境：Black Friday 前一週、provisioned table auto-scaling 上限是日常 5 倍、但開賣瞬間流量是 50 倍、auto-scaling 反應週期 5 分鐘、前 10 分鐘大量 throttle
- 讀者徵兆：cost / throughput ratio 在不同 table 差 3-5 倍、auto-scaling alarm 頻繁但 utilization 仍低於 70%、on-demand table 出現 latency spike（單 partition 被打爆但 throttling 隱藏在 latency 裡）
- Case anchor: [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — TiDB over-provision 壓力轉 DynamoDB on-demand pay-per-use、成本下降 50%、4x 吞吐 + 90% latency 降；補充 anchor: [9.C18 Zoom](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/)（COVID 30x DAU surge、on-demand 吸收 spike）

## 核心機制（Vendor-specific mechanism）

- Provisioned mode：預先買 RCU/WCU、auto-scaling 動態調整（target utilization、min / max）；throttle 立即可見、cost 可預測
- On-demand mode：按 request 計費、自動 scale 但仍受單 partition 1000 WCU / 3000 RCU 上限；cost 通常 6-7x provisioned base rate
- Cost cross-over：on-demand 在「peak / average > 5x」時划算、sustained workload provisioned + auto-scaling 便宜
- Auto-scaling 內部機制：CloudWatch alarm 觸發 → scaling activity → 1-5 分鐘調整 capacity；連續 surge 仍可能 throttle
- 對應 knowledge card：[peak forecast](/backend/knowledge-cards/peak-forecast/)、[cost per request](/backend/knowledge-cards/cost-per-request/)、[scheduled scaling](/backend/knowledge-cards/scheduled-scaling/)

## 操作流程（Operations）

- Step 1：workload profiling — 用 CloudWatch 過去 30 天 RCU/WCU、算 p50 / p95 / p99 peak、求 peak/avg ratio
- Step 2：決策樹 — peak/avg > 5x → on-demand；穩定 + 已知大事件 → provisioned baseline + scheduled scale-up；探索期或 spiky 不穩 → on-demand 過渡、穩定後切 provisioned
- Step 3：provisioned 配 auto-scaling — target utilization 70%、min = baseline、max = baseline × 預期 surge multiplier；alarm 設 5 分鐘觀察窗
- Step 4：scheduled scaling — 已知大事件（黑五、開票）前 30-60 分鐘預先提升 min capacity、事件後 60 分鐘回原值
- Step 5：mode switch — `aws dynamodb update-table --billing-mode-summary`；每張 table 24 小時內只能切一次、要計畫 maintenance window
- 驗證點：切換後第一週對比 cost + throttle metric、確認方向正確
- Rollback boundary：on-demand → provisioned 隨時可切、但 baseline 要先 sized 好；切錯方向第一個月可逆、長期累積 cost 不可逆

## 失敗模式（Failure modes）

- **Case 1：on-demand 後 cost 翻 3 倍** — dev team 切 on-demand「不用管 capacity」、但 workload 是 sustained constant、on-demand 6-7x base rate 全付出來；修法：穩定 workload 用 provisioned + auto-scaling
- **Case 2：auto-scaling 跟不上 spike** — 流量在 1 分鐘內 10x、auto-scaling alarm 5 分鐘才觸發、前 4 分鐘全 throttle；修法：peak/avg > 5x 改 on-demand、或 scheduled scaling 預先升配
- **Case 3：on-demand hot partition 隱藏** — on-demand 不顯示 throttle、latency 從 5ms 變 50ms、application timeout retry 加劇問題；修法：on-demand 仍要看 partition-level metric（Contributor Insights）、不能假設 mode 解決設計問題
- **Case 4：provisioned target utilization 設太高** — target = 90% 看似省、實際每次 spike 都先 throttle 再 scale；建議 70% buffer 給 scale latency
- **Case 5：頻繁切 mode 撞 24h 限制** — team 想「白天 provisioned 晚上 on-demand」省 cost、但 mode 切換 24h 一次、計畫破產；修法：白天 provisioned + 晚上把 capacity 設低、不切 mode
- Anti-recommendation：流量 < 100 RPS、cost < $50/月 的小 table 不用糾結 mode、on-demand 簡單；workload 穩定且 cost 高才值得做 provisioned + auto-scaling 的工程投入

## 容量與觀測（Capacity & observability）

- CloudWatch metric：`ConsumedRead/WriteCapacityUnits` / `Provisioned*` / `ThrottledRequests` / `SuccessfulRequestLatency`（p99 是 on-demand hot partition 訊號）
- AWS Cost Explorer：按 table + mode 切 cost trend、月對比；DynamoDB cost 分 read / write / storage / DAX / Streams / replication
- Auto-scaling activity log：CloudWatch alarm history + scaling activity，觀察 scaling 是否頻繁但 utilization 低
- 接回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)
- Cost gate：每月 finance review 把 DynamoDB cost 對齊 access pattern volume、不只看絕對數字

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/)（capacity mode 不解 hot partition）、[single-table-design-pattern](/backend/01-database/vendors/dynamodb/single-table-design-pattern/)（access pattern 影響 peak/avg ratio）
- Migration playbook：跨 vendor cost optimization（如 [Zomato TiDB → DynamoDB](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)）對應 type C operational hybrid
- 替代路由：cost 極度敏感 + 流量穩定 → 自管 PostgreSQL / MySQL 可能更便宜（回 [PostgreSQL vendor](/backend/01-database/vendors/postgresql/)）
- 跟 [Zoom 9.C18](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) 互引：30x surge 是 on-demand 教科書 case

## 寫作前置 checklist

- [ ] case anchor 確認（Zomato 主、Zoom 補）
- [ ] knowledge card 雙引用（peak-forecast + cost-per-request、補 scheduled-scaling）
- [ ] sibling 對比（partition-key-antipatterns + single-table 互引）
- [ ] 預估寫作長度：240-280 行（含 mode 對照表、決策樹、cost 模型、5 case）
