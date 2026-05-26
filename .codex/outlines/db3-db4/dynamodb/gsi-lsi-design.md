# DynamoDB GSI 與 LSI 設計：access pattern 補位、projection、consistency 與 cost

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：single-table design 上線後第三個月、PM 提新 query 需求「依商品分類查訂單」、「依 status 查 user」、「依時間 range 取最近活動」；team 第一反應是加 GSI、結果 GSI 從 1 個變 6 個、cost 跟 latency 一起上升
- 讀者徵兆：GSI 數量超過 3 個、`ReplicatedWriteCapacityUnits` 接近主表 WCU、GSI 反向 scan 出現、application 端開始抱怨「query 結果延遲幾秒才看到剛寫的 item」
- Case anchor: [9.C27 Disney+](/backend/09-performance-capacity/cases/disney-plus-content-metadata/) — watchlist + 播放進度 + cross-device sync 用主表 + 少量 GSI、避免 GSI 爆炸；[9.C19 Capcom](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/) — 跨遊戲共用平台、玩家 leaderboard / 戰績用 GSI 反向查詢

## 核心機制（Vendor-specific mechanism）

- GSI（Global Secondary Index）：獨立 partition、可選新的 PK + SK、async replication from base table、跨 partition 可用
- LSI（Local Secondary Index）：同 PK、不同 SK、跟 base table 同 partition、strongly consistent read 可用；*只能在 create table 時定義*、不能後加
- Projection type：`KEYS_ONLY` / `INCLUDE` / `ALL`；決定 GSI 儲存 cost 與 query 能否避免 base table lookup
- Read 路徑：GSI strongly consistent 不支援（只 eventual）；LSI 支援 strong（同 partition 內 quorum）
- Write 路徑：base table write → GSI replication（async、latency 通常 < 1s 但無保證）；每個 GSI 都按主表 WCU 收費
- 對應 knowledge card：[hot partition](/backend/knowledge-cards/hot-partition/)、[consistency level](/backend/knowledge-cards/consistency-level/)

## 操作流程（Operations）

- Step 1：每個 access pattern 標記 *最小成本路徑* — 能用主表 PK/SK 直接 query 的優先、不能的才看 GSI / LSI
- Step 2：選 LSI 還是 GSI — strongly consistent 必要 + 同 PK 內 SK 變化 → LSI；跨 PK 或 base table 已建好 → GSI
- Step 3：projection 設計 — query 只回 key → `KEYS_ONLY`、需常見欄位 → `INCLUDE`、全要 → `ALL`；INCLUDE 是常用 sweet spot
- Step 4：sparse index pattern — GSI PK 只在某 attribute 存在時填、自動「只索引子集」、節省 50-90% GSI storage
- Step 5：驗證點 — `ReturnConsumedCapacity=INDEXES` 看每個 query 是否走 GSI、CloudWatch GSI metric 看 WCU usage 跟主表的比例
- Rollback boundary：GSI 可隨時刪、但 deletion 是 async 且不可逆；建議先 application 切回 base table query、觀察 1 週再刪 GSI

## 失敗模式（Failure modes）

- **Case 1：GSI 寫入 throttle 拖累主表 write** — GSI 用了集中型 PK、單 partition 上限 1000 WCU 撞牆；主表 write 因 GSI replication 失敗而 retry、整體 latency 上升；修法：GSI PK 設計獨立 review、不可繼承主表 PK 的均勻假設
- **Case 2：GSI eventual read 餵錯資料** — 用 GSI 讀「user 最新 status」、application 假設 strong；實際 100-500ms staleness 導致 UI 顯示舊狀態；修法：read-your-write 場景改回主表 query、或加 application-side write-through cache
- **Case 3：projection ALL 把 cost 翻 3 倍** — 圖省事所有 GSI 用 `ALL`、實際 query 只需 3 個 column；storage + WCU 都浪費；修法：每個 GSI 單獨設 projection、INCLUDE 列出實際 column
- **Case 4：LSI 用完了才發現要的是 GSI** — LSI 數量上限 5 個且建 table 時定，半年後想加 strongly consistent 索引發現要重建 table；修法：建 table 前列完 access pattern、不確定走 GSI 不走 LSI
- **Case 5：GSI 反向 scan 取代 query** — application 用 GSI 做 `Scan` 而非 `Query`、全 GSI 掃過去、cost 跟 latency 都炸；修法：scan 是 *程式碼錯誤訊號*、不是 capacity 不夠
- Anti-recommendation：access pattern < 3 個、主表 PK 已能覆蓋 → 不要預先建 GSI；GSI 從少到多容易、從多到少要 application 端配合

## 容量與觀測（Capacity & observability）

- CloudWatch：每個 GSI 獨立 `ConsumedReadCapacityUnits` / `ConsumedWriteCapacityUnits`、`ReplicationLatency`（async replication 延遲、p99 通常 < 1s）
- `ReturnConsumedCapacity` flag：query 時帶 `INDEXES` 看 GSI consumption；`TOTAL` 看 base + GSI 合計
- Cost monitoring：每個 GSI 都重複收 storage + WCU；GSI 多時 cost 容易超過 base table；用 AWS Cost Explorer 按 GSI 維度看
- 接回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 的 NoSQL index cost section
- 對應 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[single-table-design-pattern](/backend/01-database/vendors/dynamodb/single-table-design-pattern/)（GSI 是 single-table 沒覆蓋的 access pattern 補位）、[partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/)（GSI 自己也會 hot partition）、[consistency-model-optimization](/backend/01-database/vendors/dynamodb/consistency-model-optimization/)（GSI 強制 eventual 對應 consistency 軸）
- 替代路由：access pattern 變動頻繁 → 考慮 OpenSearch / Aurora、單純 search 不要拿 GSI 當 inverted index
- 跟 [Capcom 9.C19](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/) 互引：leaderboard 用 GSI vs Redis sorted set 的選擇

## 寫作前置 checklist

- [ ] case anchor 確認（Disney+ + Capcom）
- [ ] knowledge card 雙引用（hot partition + consistency level）
- [ ] sibling 對比（partition-key-antipatterns + consistency-model-optimization）
- [ ] 預估寫作長度：220-260 行（含 GSI/LSI 對照表、projection 對照、5 case）
