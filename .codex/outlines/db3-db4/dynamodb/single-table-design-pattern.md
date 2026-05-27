# DynamoDB Single-Table Design Pattern：從 access pattern 反推到 PK/SK 與 GSI

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。
>
> **Stage 3 校準紀錄**：原 outline framing 偏「access pattern 反推 PK/SK」、但 F1.3 / F1.6 / F1.7 / F1.20 揭露 outline 跳過了「DynamoDB 是否適用本 workload」的前置判讀、跟「DynamoDB 在系統中是哪一層」的角色定位。本次 rewrite 在問題情境段補 4 軸前置判讀、邊界段補 durable queue / write-buffer 正向用例 + connection limit 對照、案例 anchor 改 9.C18 Zoom（control plane / data plane 分離）為主。

## 問題情境（Production pressure）

### 啟動壓力

- team 用 RDBMS 設計思維建多個 DynamoDB table（user table / order table / order_item table），第二季開始撞「每個 query 要打 2-3 個 table、latency 線性增、cost 跟著上升」
- 讀者徵兆：跨 table batch read 比例上升、application 端拼接邏輯爆炸、GSI 數量超過 5 個還是抓不到 access pattern；team 開始問「DynamoDB 怎麼 join」（誤問）

### DynamoDB 適用度前置判讀（rewrite 新增、F1.20 / F1.6 / F1.3 跨 case 合成 frame）

進到 single-table 設計細節之前、要先判讀 *workload 是否屬於 DynamoDB 適用區*。4 個維度同時成立、single-table 才有意義；任一條不成立、改回 SQL / 多 vendor 組合可能更便宜。

- **Partition key 是否天然均勻**（F1.20、跨 9.C18 / 9.C19 / 9.C26 / 9.C27 合成 frame）：meeting_id（Zoom）/ player_id（Capcom）/ message_id（PayPay）/ user_id（Disney+）這類 ID 天然散布、不會集中；反之 event_id（Tixcraft 售票）/ date（時間序）/ status（少數枚舉值）這類天然不均勻、要 composite key 修補才能 single-table（修補成本見 partition-key-antipatterns）。
- **Workload 是 control plane 還是 data plane**（F1.6、9.C18 Zoom「判讀」段第 3 條跨 9.C27 Disney+「策略」段第 1 條合成）：DynamoDB 適合存 metadata / state、實際大流量（影音串流 / 大型 BLOB / 全文搜尋）走 CDN / WebRTC / object store。Zoom 把媒體串流放 P2P + edge servers、DynamoDB 只承擔會議 metadata；Disney+ 把 content 放 S3 + CDN、DynamoDB 只承擔 watchlist + 播放進度。如果 workload 是 data plane（大物件 / 大 payload）、用 DynamoDB 是反模式。
- **Consistency 需求是否可接受 eventual**（屬通用工程判讀、case 未直接揭露閾值）：最終一致性可接受才適合、strong consistency 必要（跨 entity 原子寫入 / 跨 region 強一致）必須走 SQL / NewSQL。
- **Access pattern 是否穩定**（屬通用工程判讀、case 未直接揭露 access pattern 數量閾值）：access pattern 數量穩定且窮舉可列、single-table 才能精準設計 PK/SK 跟 GSI；查詢仍在探索期 / pattern 頻繁變動、SQL 多 table 較容易演化。

### Case anchor

- **主**：[9.C18 Zoom](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) — control plane（會議 metadata / 用戶 session 在 DynamoDB）跟 data plane（影音 P2P + edge servers）分離、是 30x DAU surge 能撐的工程前提。本篇用 Zoom 作為 *DynamoDB 角色定位* 的主 case。
- **補**：[9.C27 Disney+](/backend/09-performance-capacity/cases/disney-plus-content-metadata/) — 每日數十億 actions、watchlist + 播放進度 + cross-device sync 全打進 single table；用 PK = userId、SK = 不同前綴（`PROFILE#`、`WATCH#movieId`、`PROGRESS#deviceId#movieId`）區分 entity。
- **補**：[9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — DynamoDB 作為 durable queue / 寫入緩衝、不是 OLTP（見邊界段詳述）。

## 核心機制（Vendor-specific mechanism）

- Single-table design 不是「資料表越少越好」，是 *access pattern 先於 schema*：先列 15-30 個 query 才開始設 key
- DynamoDB 的 first-class concept：PK（partition key）決定資料散布、SK（sort key）決定同 partition 內排序與範圍查詢、composite SK 用 `#` 分隔層級
- 對比 RDBMS：RDB 用 JOIN 解 entity 關聯、DynamoDB 用 *同 PK 不同 SK 前綴* 把相關 entity 物理共置（item collection）
- 對應 knowledge card：[hot partition](/backend/knowledge-cards/hot-partition/)、[workload model](/backend/knowledge-cards/workload-model/)
- 跟 [consistency-model-optimization](/backend/01-database/vendors/dynamodb/consistency-model-optimization/) 的關係：single-table 設計後再考慮 consistency 取捨

## 操作流程（Operations）

- Step 1：access pattern 表（user story → query → 期望 latency / consistency）窮舉、不可省略
- Step 2：entity-relationship → PK/SK 映射；常見模式包括 `entity#id` PK、`PROFILE` / `ORDER#` / `ITEM#` SK 前綴
- Step 3：GSI 補需要「反向查詢」或「跨 entity 用其他欄位查」的 pattern；GSI 數量上限 20 但實務 < 5
- Step 4：CloudFormation / Terraform DDL 範例、含 BillingMode + AttributeDefinitions + GSI projection
- Step 5：驗證點 — 每個 access pattern 對應一個 query/get_item call，沒有 scan、沒有 application-side join
- Rollback boundary：access pattern 改動可加 GSI 補上；entity 拆 table 比合 table 容易，先合再拆

## 失敗模式（Failure modes）

- **Case 1：late-binding access pattern** — production 上線半年後 PM 要新 query「按地區列訂單」，PK 沒包 region，只能 scan 或加 GSI；根因是 access pattern 沒在設計階段窮舉
- **Case 2：SK 排序衝突** — 同 PK 下兩種 entity（`ORDER#timestamp` 與 `PAYMENT#timestamp`）混用同 SK 空間、range query 時 entity 邊界錯亂
- **Case 3：item collection 超過 10GB** — 單 PK 下所有 item 加起來超 10GB 上限、DynamoDB 拒絕新寫入；常見於「user 為 PK + user 有大量歷史 event」
- **Case 4：GSI 反向變主表** — 開始 GSI 只補 1-2 個 query，半年後 GSI 流量超過主表、cost 翻倍；應重新設計 PK
- **Case 5：DynamoDB 當 RDBMS 用** — 把 normalize 過的 schema 直接搬，每個 query 要 2-3 個 get_item，latency 從 5ms 變 30ms
- Anti-recommendation：access pattern < 5 個、entity 間關聯弱、查詢仍在探索期 → 用 SQL 或 multi-table 先寫、access pattern 穩定再 single-table

## 容量與觀測（Capacity & observability）

- CloudWatch：`ConsumedReadCapacityUnits` / `ConsumedWriteCapacityUnits` 按 partition 分布、`ThrottledRequests` 早期 hot partition 訊號
- Contributor Insights：top-N partition key 訪問頻率、揭露 single-table 設計後是否仍均勻
- 觀測 GSI：每個 GSI 獨立 RCU/WCU、projection type（KEYS_ONLY / INCLUDE / ALL）決定 storage cost
- 接回 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)、[9.5 Bottleneck localization](/backend/09-performance-capacity/bottleneck-localization/)

## 邊界與整合（Boundary & next steps）

### DynamoDB 在系統中的角色：control plane / metadata / state（F1.6 跨 case 合成 frame）

DynamoDB 不是 universal store、不是 SQL 替代品。三個 case 重複揭露同一定位：

- **9.C18 Zoom 揭露**：媒體串流走 P2P + edge servers、DynamoDB 只承擔會議 / 用戶 metadata。control plane 跟 data plane 分離是 surge 能撐的工程前提（不是 DynamoDB 自己魔法）。
- **9.C27 Disney+ 揭露**：content 走 S3 + CDN、DynamoDB 只承擔 metadata / watchlist / cross-device 進度。
- **9.C19 Capcom 揭露**（「策略」段第 2 條）：EKS 跑 game server / 處理即時遊戲邏輯、DynamoDB 處理持久狀態。

讀者該問的不是「DynamoDB 能撐多大流量」、是「我的系統哪一層該放 DynamoDB」。

### Durable queue / write-buffer 作為 *正向* 非 OLTP access pattern（F1.3、9.C15 Tixcraft「判讀」段第 1 條揭露）

9.C15 Tixcraft 揭露 DynamoDB 的另一種正向用法 — *寫入緩衝層*、不是 OLTP：

- 拓元用 DynamoDB 接「訂單」寫入、不是即時生效、是讓 traditional server（金流 / 票庫）用自己能承受的速度消費。
- 架構上 DynamoDB 扮演 *durable queue*、不是傳統 OLTP DB。這層解耦讓「前端可擴 130 倍、後端不用同步擴」（F1.21）。
- 對比 RDBMS：RDB 寫入要即時可讀、即時索引、即時 transaction commit；DynamoDB 寫入可以「先 durable、之後處理」。
- 寫稿時要明示：這是 *非預設* access pattern、是 flash-sale / 高峰寫入解耦的工程選擇、不是 DynamoDB 預設定位。

### RDB connection limit 機制對照（F1.7、9.C29 Lemino「判讀」段第 1 條揭露）

Lemino case 揭露 *為什麼 DynamoDB 在 surge 下不會踩 RDB 的隱性天花板*：

- 9.C29 揭露：「connection limits became bottlenecks when experiencing a rapid increase in access」、PostgreSQL/MySQL 每連線吃記憶體 / process、pool 上限 1K-5K、connection 是 RDB 在 surge 下 *第一個爆點*（不是 CPU / disk）。
- DynamoDB 的 HTTP API（無 long-lived connection state）天然解這個問題。client 不需要維護 connection pool、AWS SDK 用 connection-less HTTP request。
- 這是 single-table 設計 *外部* 的容量優勢、但寫到本篇邊界段提醒讀者：選 DynamoDB 不只是 schema 選擇、是 connection model 選擇。

### Sibling 與 cross-link

- Sibling deep articles：[partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/)（hot partition 細節、本篇前置判讀軸 1 的補救）、[gsi-lsi-design](/backend/01-database/vendors/dynamodb/gsi-lsi-design/)（GSI 補不到的 access pattern）、[on-demand-vs-provisioned](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/)（access pattern 影響 mode 選擇）
- Migration playbook：RDBMS → DynamoDB single-table 在 [1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/) 的延伸
- 跟 [Lemino 9.C29](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) 的對照：connection-bound RDB → single-table DynamoDB 不只是換 vendor，是 access pattern + connection model 重寫
- 反向路由：access pattern 探索期 / strong consistency 必要 / data plane workload → 回 [PostgreSQL vendor](/backend/01-database/vendors/postgresql/)

## 寫作前置 checklist

- [ ] case anchor 確認（Zoom 9.C18 主、Disney+ 9.C27 + Tixcraft 9.C15 + Lemino 9.C29 補）
- [ ] knowledge card 雙引用（hot partition + workload model）
- [ ] sibling 對比（partition-key-antipatterns + gsi-lsi-design 互引）
- [ ] 4 軸前置判讀清楚標 fact vs derive 分層（PK 天然均勻 + control plane / data plane 是 case 揭露；consistency / access pattern 穩定屬通用工程判讀）
- [ ] durable queue 段引用 9.C15 時明示「非預設 access pattern、Tixcraft 特殊架構選擇」
- [ ] connection limit 對照段明示「RDB 第一爆點 = connection、非 CPU / disk」（避免讀者誤以為 DynamoDB 在所有 surge 下都通用解）
- [ ] 預估寫作長度：300-340 行（含前置判讀 4 軸 + PK/SK 設計表 + access pattern audit 表 + 邊界 3 段 + 5 failure case）
