# DynamoDB On-Demand vs Provisioned：capacity mode 對比、auto-scaling 邊界與 cost 模型

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。
>
> **Stage 3 校準紀錄**：原 outline 用「peak/avg ratio > 5x → on-demand」單軸決策樹。F1.4 / F1.5 / F1.16 / F1.18 / F1.19 揭露 mode 選擇之上還有更多軸 — 讀寫比 trend 變化、surge 永久 baseline 上移、predictable-peak vs flash-sale、DBA 工時釋放、vendor vs 自管 cost crossover。本次 rewrite 把單軸擴成 6 軸決策、補「DynamoDB vs 自管 cluster cost crossover」段。原 outline 多處自生數字（5x 閾值 / 30-60 分鐘 scheduled / idempotency 加 request_id）已標 fact vs derive 分層。

## 問題情境（Production pressure）

- 啟動壓力：團隊 quarterly review 看 DynamoDB bill 突然漲 80%、原因是 dev team 把所有 table 切 on-demand「省 capacity 管理」；finance 反問「於是省了多少 SRE 工時、又多花多少 cost」、團隊答不出來
- 反向情境：Black Friday 前一週、provisioned table auto-scaling 上限是日常 5 倍、但開賣瞬間流量是 50 倍、auto-scaling 反應週期 5 分鐘、前 10 分鐘大量 throttle
- 讀者徵兆：cost / throughput ratio 在不同 table 差 3-5 倍、auto-scaling alarm 頻繁但 utilization 仍低於 70%、on-demand table 出現 latency spike（單 partition 被打爆但 throttling 隱藏在 latency 裡）
- Case anchor: [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — TiDB over-provision 壓力轉 DynamoDB on-demand pay-per-use、成本下降 50%、4x 吞吐 + 90% latency 降；補充 anchor: [9.C18 Zoom](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/)（COVID 30x DAU surge、surge 後 baseline 永久上移）+ [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)（sustained workload 應 provisioned + auto-scaling）+ [9.C19 Capcom](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/) / [9.C29 Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/)（DBA 工時釋放）

## 核心機制（Vendor-specific mechanism）

- Provisioned mode：預先買 RCU/WCU、auto-scaling 動態調整（target utilization、min / max）；throttle 立即可見、cost 可預測
- On-demand mode：按 request 計費、自動 scale 但仍受單 partition 1000 WCU / 3000 RCU 上限；cost 通常 6-7x provisioned base rate
- Cost cross-over：on-demand 在「peak / average ratio 高」時划算、sustained workload provisioned + auto-scaling 便宜
  - **Scope warning**：原 outline 寫的「peak/avg > 5x」具體閾值是 LLM 自生 / 通用工程估算、9.C5 / 9.C20 都沒給具體 ratio 數字。寫稿時要明示「5x 為經驗值、case 沒明示 threshold、實際 crossover 點隨 region pricing + workload shape 變動」
- Auto-scaling 內部機制：CloudWatch alarm 觸發 → scaling activity → 1-5 分鐘調整 capacity；連續 surge 仍可能 throttle
- 對應 knowledge card：[peak forecast](/backend/knowledge-cards/peak-forecast/)、[cost per request](/backend/knowledge-cards/cost-per-request/)、[scheduled scaling](/backend/knowledge-cards/scheduled-scaling/)

## 操作流程（Operations）

### Step 1：6 軸決策（rewrite、從單軸 peak/avg 擴成多軸）

mode 選擇不是只看 peak/avg ratio。以下 6 軸合成判讀才能避免單軸誤判：

**軸 1：peak / average 流量 ratio**（原 outline 主軸、屬通用工程估算）

- 高 ratio（spiky / flash-sale）傾向 on-demand
- 穩定 ratio（sustained / 平緩）傾向 provisioned + auto-scaling
- **Scope warning**：「> 5x」具體閾值是經驗值、case 未揭露

**軸 2：讀寫比 trend 變化**（F1.4、9.C5 Amazon Ads「策略」段第 2 條揭露）

- 不是看絕對讀寫比（C5 是 18:1、C27 推估 5:1）、是看 *變化*
- 業務邏輯改變（新增即時報表 / 新增推播）會讓讀寫比跳一個量級、要持續觀測 trend 而非單次量測
- 觀測上加 metric：read / write ratio 7-day rolling average、超過 ±30% 偏移觸發 review

**軸 3：surge 是 *暫時* 還是 *永久 baseline 上移***（F1.5、9.C18 Zoom「策略」段第 3 條揭露）

- Zoom COVID 30x DAU surge 後 baseline 永久上移、不會回去
- 暫時 surge（單日活動 / 季節高峰）on-demand 划算
- 永久上移後、原 on-demand 設計會持續燒錢、要重新算 cross-over、考慮切回 provisioned
- Tripwire：surge 結束後 4-8 週仍維持 surge 期間 baseline 的 70%+、判定為「永久 baseline 上移」、重評 mode

**軸 4：predictable-peak vs flash-sale**（F1.16、9.C27 Disney+ vs 9.C15 Tixcraft 對比合成）

- **predictable-peak**（Disney+ 新片發布、Marvel / Star Wars 首日、metadata 流量 3-5 倍持續時段較長）：可以 *提前* 1-2 天 pre-scale、scheduled scaling 合適
- **flash-sale**（拓元 6750x in seconds、t=0 起跳 / t=300 結束）：scheduled scaling 太慢、必須事前 pre-provision baseline 拉到極高、或用 on-demand + composite partition key 雙保險
- 兩者都不是「peak/avg > 5x → on-demand」單軸決策能解
- **Scope warning**：原 outline 寫的「scheduled scaling 30-60 分鐘前」具體時間是經驗值、case 未揭露具體 lead time

**軸 5：DBA / SRE 工時釋放**（F1.18、9.C19 Capcom「判讀」段第 3 條 + 9.C29 Lemino「判讀」段第 3 條揭露）

- 9.C19 Capcom 揭露：30% 成本下降的本質是「工程資源從 DB 運維轉到遊戲品質」、Capcom 是遊戲公司不是 IT 公司
- 9.C29 Lemino 揭露：90% 工程工時下降（DBA + connection management + capacity planning 統包）
- 評估公式：總成本 = direct cost（monthly bill）+ 工程工時機會成本（DBA 從 patch / replication / backup 釋放出來做的事）
- on-demand 的 6-7x base rate 在 DBA 工時釋放下、實質 ROI 可能仍正向（特別在小團隊 / 非 IT 主業公司）

**軸 6：DynamoDB vs 自管 cluster cost crossover**（F1.19、9.C20 Zomato 警惕段第 1 條揭露）

- 9.C20 Zomato 警示：成本降 50% 是 *當下流量* 的對照、未來流量繼續成長後、DynamoDB cost-per-request 成長率比 TiDB 自管 cluster 高、某流量規模後 crossover、自管 cluster 反而便宜
- mode 選擇之上還有 *vendor 選擇*：不是只在 on-demand vs provisioned 之間挑、是要算「未來 12-24 個月在預期流量下、DynamoDB（不論 mode）vs 自管 cluster 的成本曲線」
- 對小 / 中流量 startup：DynamoDB on-demand 簡單划算
- 對大流量、流量可預測：自管 cluster crossover 點可能在「峰值穩定 + DBA 團隊已存在」的場景下成立
- 寫稿時要分層：本軸是 mode 選擇之上的更上層決策、不是每篇都要展開、但要在 outline 邊界段提醒讀者

### Step 2-5：操作步驟（原 outline 保留 + 軸對應）

- Step 2：workload profiling — 用 CloudWatch 過去 30 天 RCU/WCU、算 p50 / p95 / p99 peak、求 peak/avg ratio（軸 1 輸入）+ read/write ratio rolling avg（軸 2 輸入）
- Step 3：surge 性質判讀 — 是暫時還是永久 baseline 上移（軸 3）、是 predictable-peak 還是 flash-sale（軸 4）
- Step 4：6 軸合成決策樹 — provisioned + auto-scaling / on-demand / scheduled scaling 三選一
- Step 5：provisioned 配 auto-scaling — target utilization 70%、min = baseline、max = baseline × 預期 surge multiplier；alarm 設 5 分鐘觀察窗
- Step 6：scheduled scaling — 已知大事件（黑五、開票、新片發布）前預先提升 min capacity、事件後回原值（時間 lead 依事件性質決定、非固定 30-60 分鐘）
- Step 7：mode switch — `aws dynamodb update-table --billing-mode-summary`；每張 table 24 小時內只能切一次、要計畫 maintenance window
- Step 8：總成本評估公式（軸 5 + 軸 6）— direct cost + 工程工時機會成本、再對照自管 cluster 的 cost crossover 曲線

### 驗證點與 rollback

- 驗證點：切換後第一週對比 cost + throttle metric、確認方向正確
- Rollback boundary：on-demand → provisioned 隨時可切、但 baseline 要先 sized 好；切錯方向第一個月可逆、長期累積 cost 不可逆

## 失敗模式（Failure modes）

- **Case 1：on-demand 後 cost 翻 3 倍** — dev team 切 on-demand「不用管 capacity」、但 workload 是 sustained constant、on-demand 6-7x base rate 全付出來；修法：穩定 workload 用 provisioned + auto-scaling（對應軸 1 + 軸 2）
- **Case 2：auto-scaling 跟不上 spike** — 流量在 1 分鐘內 10x、auto-scaling alarm 5 分鐘才觸發、前 4 分鐘全 throttle；修法：peak/avg 高且 spike 突然 → on-demand、或 scheduled scaling 預先升配（對應軸 1 + 軸 4）
- **Case 3：on-demand hot partition 隱藏** — on-demand 不顯示 throttle、latency 從 5ms 變 50ms、application timeout retry 加劇問題；修法：on-demand 仍要看 partition-level metric（Contributor Insights）、不能假設 mode 解決設計問題（跟 [partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/) cross-link）
- **Case 4：provisioned target utilization 設太高** — target = 90% 看似省、實際每次 spike 都先 throttle 再 scale；建議 70% buffer 給 scale latency
- **Case 5：頻繁切 mode 撞 24h 限制** — team 想「白天 provisioned 晚上 on-demand」省 cost、但 mode 切換 24h 一次、計畫破產；修法：白天 provisioned + 晚上把 capacity 設低、不切 mode
- **Case 6（新增）：surge 後沒重評 mode、長期燒錢**（軸 3 對應）— Zoom 式 30x permanent baseline 上移後、原 on-demand 設計成本爆炸；修法：surge 結束 4-8 週後重評、若 baseline 維持 70%+ 改 provisioned
- Anti-recommendation：流量 < 100 RPS、cost < $50/月 的小 table 不用糾結 mode、on-demand 簡單；workload 穩定且 cost 高才值得做 provisioned + auto-scaling 的工程投入

## 容量與觀測（Capacity & observability）

- CloudWatch metric：`ConsumedRead/WriteCapacityUnits` / `Provisioned*` / `ThrottledRequests` / `SuccessfulRequestLatency`（p99 是 on-demand hot partition 訊號）
- **新增**：read/write ratio 7-day rolling avg（軸 2 觀測）、surge baseline 4-week rolling avg（軸 3 觀測）
- AWS Cost Explorer：按 table + mode 切 cost trend、月對比；DynamoDB cost 分 read / write / storage / DAX / Streams / replication
- Auto-scaling activity log：CloudWatch alarm history + scaling activity，觀察 scaling 是否頻繁但 utilization 低
- 接回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)
- Cost gate：每月 finance review 把 DynamoDB cost 對齊 access pattern volume、不只看絕對數字
- **指標口徑紀律**（Frame 7）：引用 case 數字（C5 90M reads/sec / C20 90% latency 降）時明示「最大瞬時 / 99 百分位 / 常態 / 滾動」哪個口徑

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/)（capacity mode 不解 hot partition、軸對應）、[single-table-design-pattern](/backend/01-database/vendors/dynamodb/single-table-design-pattern/)（access pattern 影響 peak/avg ratio 跟 read/write ratio）
- Migration playbook：跨 vendor cost optimization（如 [Zomato TiDB → DynamoDB](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)）對應 type C operational hybrid
- 替代路由：cost 極度敏感 + 流量穩定 + DBA 團隊已存在 → 自管 PostgreSQL / MySQL 可能更便宜（軸 6 crossover、回 [PostgreSQL vendor](/backend/01-database/vendors/postgresql/)）
- 跟 [Zoom 9.C18](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) 互引：30x permanent surge 後的 mode 重評（軸 3 主案例）
- 跟 [Capcom 9.C19](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/) + [Lemino 9.C29](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) 互引：DBA 工時釋放（軸 5 主案例）
- 跟 Frame 8 event-driven scaling 5 種模式 cross-link：本篇從 DynamoDB 視角切入、Aurora `read-replica-scaling.md` 從讀副本視角切入、兩篇互引不重複展開

## 寫作前置 checklist

- [ ] case anchor 確認（Zomato 9.C20 主、Zoom 9.C18 / Amazon Ads 9.C5 / Capcom 9.C19 / Lemino 9.C29 補）
- [ ] knowledge card 雙引用（peak-forecast + cost-per-request、補 scheduled-scaling）
- [ ] sibling 對比（partition-key-antipatterns + single-table 互引）
- [ ] **Scope warning 明示**：「peak/avg > 5x」+「scheduled scaling 30-60 分鐘前」+ on-demand 「6-7x base rate」這些具體數字標為「經驗值 / 通用工程估算、case 未揭露具體閾值」、不寫成 case 揭露
- [ ] 6 軸決策清楚標 fact vs derive 分層（軸 2 / 3 / 4 / 5 / 6 都有 case 揭露、軸 1 具體閾值屬通用工程估算）
- [ ] 引用 case 數字（C5 90M / C20 90%）標口徑（最大瞬時 / 滾動 / customer-facing）
- [ ] DBA 工時釋放公式（軸 5）明示「總成本 = direct cost + 工程工時機會成本」
- [ ] vendor crossover 段（軸 6）明示「mode 選擇之上的決策、不是每篇都展開、本篇只在邊界段提醒」
- [ ] 預估寫作長度：320-360 行（含 6 軸決策表 + mode 對照表 + cost 模型 + 6 failure case + 軸對應）
