# DynamoDB Single-Table Design Pattern：從 access pattern 反推到 PK/SK 與 GSI

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：team 用 RDBMS 設計思維建多個 DynamoDB table（user table / order table / order_item table），第二季開始撞「每個 query 要打 2-3 個 table、latency 線性增、cost 跟著上升」
- 讀者徵兆：跨 table batch read 比例上升、application 端拼接邏輯爆炸、GSI 數量超過 5 個還是抓不到 access pattern；team 開始問「DynamoDB 怎麼 join」（誤問）
- Case anchor: [9.C27 Disney+](/backend/09-performance-capacity/cases/disney-plus-content-metadata/) — 每日數十億 actions、watchlist + 播放進度 + cross-device sync 全打進 single table；用 PK = userId、SK = 不同前綴（`PROFILE#`、`WATCH#movieId`、`PROGRESS#deviceId#movieId`）區分 entity，避免 cross-table fan-out

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

- Sibling deep articles：[partition-key-antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/)（hot partition 細節）、[gsi-lsi-design](/backend/01-database/vendors/dynamodb/gsi-lsi-design/)（GSI 補不到的 access pattern）
- Migration playbook：RDBMS → DynamoDB single-table 在 [1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/) 的延伸
- 跟 [Lemino 9.C29](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) 的對照：connection-bound RDB → single-table DynamoDB 不只是換 vendor，是 access pattern 重寫
- 反向路由：access pattern 探索期 → 回 [PostgreSQL vendor](/backend/01-database/vendors/postgresql/)

## 寫作前置 checklist

- [ ] case anchor 確認（Disney+ 主、Capcom / Amazon Ads 補）
- [ ] knowledge card 雙引用（hot partition + workload model）
- [ ] sibling 對比（partition-key-antipatterns + gsi-lsi-design 互引）
- [ ] 預估寫作長度：260-300 行（含 PK/SK 設計表、access pattern audit 表、5 case）
