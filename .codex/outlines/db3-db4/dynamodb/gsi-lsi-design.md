# DynamoDB GSI 與 LSI 設計：access pattern 補位、projection、consistency 與 cost

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。
>
> **Stage 3 校準紀錄**：原 outline 主軸正確。本次 keep + 補強：補 DAX 作為讀峰值補位（F1.8、明示 case 揭露 vs derive 分層）、明示 LSI 數量上限 5 個屬 vendor 規格需 cross-verify AWS doc、GSI cost > base table 屬通用工程知識 case 沒揭露具體 ratio。

## 問題情境（Production pressure）

- 啟動壓力：single-table design 上線後第三個月、PM 提新 query 需求「依商品分類查訂單」、「依 status 查 user」、「依時間 range 取最近活動」；team 第一反應是加 GSI、結果 GSI 從 1 個變 6 個、cost 跟 latency 一起上升
- 讀者徵兆：GSI 數量超過 3 個、`ReplicatedWriteCapacityUnits` 接近主表 WCU、GSI 反向 scan 出現、application 端開始抱怨「query 結果延遲幾秒才看到剛寫的 item」
- Case anchor: [9.C27 Disney+](/backend/09-performance-capacity/cases/disney-plus-content-metadata/) — watchlist + 播放進度 + cross-device sync 用主表 + 少量 GSI、避免 GSI 爆炸；[9.C19 Capcom](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/) — 跨遊戲共用平台、玩家 leaderboard / 戰績用 GSI 反向查詢
- 補充 anchor: [9.C29 Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) — DAX 作為讀峰值補位（見「DAX 作為讀峰值補位」段）

## 核心機制（Vendor-specific mechanism）

- GSI（Global Secondary Index）：獨立 partition、可選新的 PK + SK、async replication from base table、跨 partition 可用
- LSI（Local Secondary Index）：同 PK、不同 SK、跟 base table 同 partition、strongly consistent read 可用；*只能在 create table 時定義*、不能後加
  - **Scope warning**：「LSI 數量上限 5 個」屬 vendor 規格事實、需 cross-verify AWS doc 確認當前數字、case 沒揭露
- Projection type：`KEYS_ONLY` / `INCLUDE` / `ALL`；決定 GSI 儲存 cost 與 query 能否避免 base table lookup
- Read 路徑：GSI strongly consistent 不支援（只 eventual）；LSI 支援 strong（同 partition 內 quorum）
- Write 路徑：base table write → GSI replication（async、latency 通常 < 1s 但無保證）；每個 GSI 都按主表 WCU 收費
- 對應 knowledge card：[hot partition](/backend/knowledge-cards/hot-partition/)、[consistency level](/backend/knowledge-cards/consistency-level/)

### DAX 作為讀峰值補位（F1.8、9.C29 Lemino「策略」段第 3 條揭露 + 9.C19 Capcom 是 derive）

DAX 不是 DynamoDB 預設配置、不是 GSI 跟 LSI 的同層方案、是「讀峰值持續高時的補位」：

- **9.C29 Lemino case 揭露**：「DAX 是 DynamoDB 讀 cache 的標準解法」、觸發條件是「當讀峰值持續高、加 DAX 減少 DynamoDB 讀次數、降低成本」（熱門節目首播時段）。Lemino 是 case 直接揭露 DAX 使用。
- **9.C19 Capcom 是判讀層 derive、不是 case fact**：原 finding F1.8 明示「single-digit ms 反推 Capcom 必須用 sub-region cache + DynamoDB DAX、不能單靠 DynamoDB」、是作者從 latency 數字反推、Capcom case *沒有公開揭露* 用 DAX。寫稿時引用 Capcom 必須明示「DAX 是作者判讀層推論、Capcom 沒公開使用」（對應陷阱 4：把作者推論寫成 case 揭露）。
- **跟 GSI/LSI 的關係**：DAX 是「讀路徑加速層」、GSI/LSI 是「access pattern 補位」、兩者不互斥但解不同問題。GSI 解「無法用主 PK 查」、DAX 解「同 query 重複打 DynamoDB 太貴或太慢」。
- **觸發條件**：讀峰值持續高 + cache 命中率可預期高（熱門節目 / 共用 leaderboard / 全平台共享 metadata）。
- **不適用情境**：寫密集 / 每次讀都不同 key / cache invalidation 太頻繁。

## 操作流程（Operations）

- Step 1：每個 access pattern 標記 *最小成本路徑* — 能用主表 PK/SK 直接 query 的優先、不能的才看 GSI / LSI
- Step 2：選 LSI 還是 GSI — strongly consistent 必要 + 同 PK 內 SK 變化 → LSI；跨 PK 或 base table 已建好 → GSI
- Step 3：projection 設計 — query 只回 key → `KEYS_ONLY`、需常見欄位 → `INCLUDE`、全要 → `ALL`；INCLUDE 是常用 sweet spot
- Step 4：sparse index pattern — GSI PK 只在某 attribute 存在時填、自動「只索引子集」、節省 50-90% GSI storage
  - **Scope warning**：「50-90% GSI storage 節省」屬通用工程估算、case 沒給具體節省比例
- Step 5：驗證點 — `ReturnConsumedCapacity=INDEXES` 看每個 query 是否走 GSI、CloudWatch GSI metric 看 WCU usage 跟主表的比例
- Step 6（新增）：DAX 評估 — 讀峰值持續高 + cache hit rate 可預期、才加 DAX；不要把 DAX 當預設配置（Lemino 揭露的觸發條件）
- Rollback boundary：GSI 可隨時刪、但 deletion 是 async 且不可逆；建議先 application 切回 base table query、觀察 1 週再刪 GSI

## 失敗模式（Failure modes）

- **Case 1：GSI 寫入 throttle 拖累主表 write** — GSI 用了集中型 PK、單 partition 上限 1000 WCU 撞牆；主表 write 因 GSI replication 失敗而 retry、整體 latency 上升；修法：GSI PK 設計獨立 review、不可繼承主表 PK 的均勻假設
- **Case 2：GSI eventual read 餵錯資料** — 用 GSI 讀「user 最新 status」、application 假設 strong；實際 100-500ms staleness 導致 UI 顯示舊狀態；修法：read-your-write 場景改回主表 query、或加 application-side write-through cache
  - **Scope warning**：「100-500ms staleness」具體數字屬通用工程估算、case 未揭露
- **Case 3：projection ALL 把 cost 翻 3 倍** — 圖省事所有 GSI 用 `ALL`、實際 query 只需 3 個 column；storage + WCU 都浪費；修法：每個 GSI 單獨設 projection、INCLUDE 列出實際 column
  - **Scope warning**：「cost 翻 3 倍」具體數字屬通用工程估算、case 未揭露
- **Case 4：LSI 用完了才發現要的是 GSI** — LSI 數量上限（vendor 文件確認當前值）且建 table 時定，半年後想加 strongly consistent 索引發現要重建 table；修法：建 table 前列完 access pattern、不確定走 GSI 不走 LSI
- **Case 5：GSI 反向 scan 取代 query** — application 用 GSI 做 `Scan` 而非 `Query`、全 GSI 掃過去、cost 跟 latency 都炸；修法：scan 是 *程式碼錯誤訊號*、不是 capacity 不夠
- **Case 6（新增）：把 DAX 當預設配置** — 寫密集 workload / cache hit rate 低的場景加 DAX、cache invalidation 成本超過 cache 收益、cost 上升 latency 沒降；修法：DAX 是「讀峰值持續高」的補位、不是預設（Lemino 揭露的觸發條件、Capcom 是 derive 不是 case fact）
- Anti-recommendation：access pattern < 3 個、主表 PK 已能覆蓋 → 不要預先建 GSI；GSI 從少到多容易、從多到少要 application 端配合

## 容量與觀測（Capacity & observability）

- CloudWatch：每個 GSI 獨立 `ConsumedReadCapacityUnits` / `ConsumedWriteCapacityUnits`、`ReplicationLatency`（async replication 延遲、p99 通常 < 1s）
- `ReturnConsumedCapacity` flag：query 時帶 `INDEXES` 看 GSI consumption；`TOTAL` 看 base + GSI 合計
- Cost monitoring：每個 GSI 都重複收 storage + WCU；GSI 多時 cost 容易超過 base table；用 AWS Cost Explorer 按 GSI 維度看
  - **Scope warning**：「GSI 多時 cost 超過 base table」屬通用工程知識、Disney+ / Capcom case 沒揭露具體 cost ratio
- DAX 觀測（新增）：cache hit rate / cache miss rate、cache size utilization；hit rate < 70% 應重評 DAX 是否該存在
  - **Scope warning**：「70% hit rate 閾值」屬通用工程估算
- 接回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 的 NoSQL index cost section
- 對應 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[single-table-design-pattern](/backend/01-database/vendors/dynamodb/single-table-design-pattern/)（GSI 是 single-table 沒覆蓋的 access pattern 補位）、[partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/)（GSI 自己也會 hot partition）、[consistency-model-optimization](/backend/01-database/vendors/dynamodb/consistency-model-optimization/)（GSI 強制 eventual 對應 consistency 軸）、[on-demand-vs-provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/)（GSI 多時 cost 跟 mode 互動）
- 替代路由：access pattern 變動頻繁 → 考慮 OpenSearch / Aurora、單純 search 不要拿 GSI 當 inverted index
- 跟 [Capcom 9.C19](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/) 互引：leaderboard 用 GSI vs Redis sorted set 的選擇；DAX 是 derive 不是 case fact、引用要明示
- 跟 [Lemino 9.C29](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) 互引：DAX 作為讀峰值補位的 case 揭露

## 寫作前置 checklist

- [ ] case anchor 確認（Disney+ 9.C27 + Capcom 9.C19 主、Lemino 9.C29 補 DAX 段）
- [ ] knowledge card 雙引用（hot partition + consistency level）
- [ ] sibling 對比（partition-key-antipatterns + consistency-model-optimization + on-demand-vs-provisioned）
- [ ] **Scope warning 明示**：「LSI 數量上限 5 個」需 cross-verify AWS doc、「GSI 多時 cost > base table」屬通用工程知識 case 沒揭露具體 ratio、「DAX 是 Capcom 必用」是 derive 不是 case fact（Capcom 沒公開揭露用 DAX）
- [ ] DAX 段嚴格分層：Lemino 是 case 揭露、Capcom 是作者 derive、寫稿時明示
- [ ] 預估寫作長度：240-280 行（含 GSI/LSI 對照表 + projection 對照 + DAX 補位段 + 6 case）
