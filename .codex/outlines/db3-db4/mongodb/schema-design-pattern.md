# MongoDB Schema Design Pattern：embedded vs reference 與 aggregate root

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- Document model 早期 schema-less 紅利、跑半年後 collection 同時混三代 schema、application 寫 if-else 處理欄位缺失與型別漂移
- 子文件越塞越深、單 document 突破 1-2MB、partial update 仍要把整顆 document load + write、IO 跟 working set 雙重壓力
- 反向過度 normalize：訂單跟訂單 item 拆兩個 collection、單一查詢得 N+1 `$lookup`、aggregation cost 飆
- 讀者徵兆：`$lookup` 出現在 hot path、document size warning（16MB 上限預警）、partial update 卻產生大量 disk write、schema validation 報錯比例突然爬升
- Case anchor: primary [9.C38 Toyota Connected](/backend/09-performance-capacity/cases/toyota-connected-mongodb-telematics-iot/)（車載 sensor schema 隨車型 / 年份 / 規範演進、polymorphic document 與 schema governance 並存）、secondary [Microsoft 365 Cosmos DB analytics](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/)（document model 保留 + 形狀治理壓力）；needs new case：早期 startup MongoDB 三代 schema 並存的 failure-mode incident

## 核心機制（Vendor-specific mechanism）

- Aggregate root：把「一起讀、一起寫、一致性邊界一致」的資料塞同一個 document，呼應 DDD aggregate；MongoDB 把 atomicity 限制在 *單 document*
- Embedded（subdocument / array）：寫入 atomic、讀取一次到位；代價是 update sub-element 仍要 rewrite 整顆 document
- Reference（手動 `_id` foreign key + `$lookup`）：document 大小可控，但 join 在 application 或 aggregation 階段做
- Polymorphic pattern：同 collection 用 `type` discriminator 存多型實體；MongoDB 沒 inheritance，靠 schema validator 與 partial index 維持邊界
- 16MB document hard limit + working set 在 RAM 的隱性軟限制（單 doc 大小直接影響 page cache 效率）
- Schema validation（`$jsonSchema`、`validationLevel`、`validationAction`）：production 是「契約 enforcement」的工具、不是 dev-time linter
- 對應 knowledge card: [document-store](/backend/knowledge-cards/document-store/)、[transaction-boundary](/backend/knowledge-cards/transaction-boundary/)（aggregate boundary = transaction boundary）、[data-inconsistency](/backend/knowledge-cards/data-inconsistency/)

## 操作流程（Operations）

- Step 1：access pattern 盤點 — 列出 top 10 query / write、標 read together / write together 集合
- Step 2：embed 判準（1:few、life-cycle 同步、< 1MB 預期上限）vs reference 判準（1:many 寫頻不對稱、跨 aggregate 引用）
- Step 3：用 `$jsonSchema` 寫 validator、`validationLevel: "moderate"` 先放行 legacy、再 `"strict"` 封死新寫入
- Step 4：polymorphic 用 partial index `{ type: 1, ... }` + `partialFilterExpression` 避免冷分支吃 index 成本
- Step 5：用 `bsondump` + `$bsonSize` + `collStats` 量測 doc 形狀，把違規 doc 列名單
- 驗證點：`db.coll.aggregate([{$group:{_id:null, avg:{$avg:{$bsonSize:"$$ROOT"}}, max:{$max:{$bsonSize:"$$ROOT"}}}}])` 看分布、validator failure rate 看寫入契約執行狀況
- Rollback boundary：validator 從 `strict` 退回 `moderate` 是 single-command；已 embed 進去的 schema 變更要靠 backfill migration script，無法 in-place 還原

## 失敗模式（Failure modes）

- **Unbounded array growth**：把「使用者所有訊息」embed 進 user document、document 撞 16MB → 寫入直接 reject
- **Hot subdocument update**：所有寫都打同一個 nested field、wiredTiger document-level lock 退化成熱點，concurrency 看似多核卻被序列化
- **$lookup 在 hot path**：reference 沒設好變 join、p99 latency 隨 collection 大小線性退化
- **Schema 三代並存**：缺 schema validator 期間舊版欄位殘留、application code 三層 fallback、新 dev onboarding 看不懂哪個欄位是現役
- **Polymorphic 全表掃描**：discriminator 沒進 index、`type: "rare"` 查詢全表 scan
- Anti-recommendation：access pattern 還沒穩定的早期 MVP 不需要鎖死 schema validator；JOIN-heavy / 強 normalize workload 一開始就該回 PostgreSQL JSONB 或 SQL，不是塞進 MongoDB 再 `$lookup`

## 容量與觀測（Capacity & observability）

- 關鍵 metric：`collStats.avgObjSize`、`collStats.size` vs `storageSize`（壓縮比）、`document validation failure rate`、`wiredTiger.cache.bytes currently in the cache` 對比 working set 估算
- Mongo command：`db.coll.stats()`、`db.coll.aggregate([{$collStats:{...}}])`、`db.runCommand({collMod:..., validator:...})`
- Profiler：`db.setProfilingLevel(1, {slowms: 100})` 抓 slow op，看是否 `$lookup` / `$unwind` 進 hot path
- 回到 [4.20 observability evidence](/backend/04-observability/observability-evidence-package/)：把 doc size 分布、validator failure rate、`$lookup` 出現位置列為 evidence
- 回到 [9.5 bottleneck localization](/backend/09-performance-capacity/bottleneck-localization/)：working set 撐爆 RAM 時的 page fault 信號

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[shard key selection](./shard-key-selection.md)（document 形狀決定 shard key 候選）、[aggregation pipeline optimization](./aggregation-pipeline-optimization.md)（`$lookup` 與 schema reference 互相牽動）
- Migration playbook：document 形狀走樣到無法治理時的 [→ MongoDB → PostgreSQL 拆 normalize](/backend/01-database/large-scale-db-migration/) 路徑；保留 document model 改 [→ Atlas](/backend/01-database/vendors/mongodb/migrate-to-atlas/) 或 [→ Cosmos DB MongoDB API](/backend/01-database/vendors/mongodb/) 升級路徑
- 跟 1.x 互引：[1.2 schema design](/backend/01-database/schema-design/) 處理通用 schema 演進原則、本文是 MongoDB-specific 落地；[1.4 transaction boundary](/backend/01-database/transaction-boundary/) 對齊 aggregate = atomic 邊界

## 寫作前置 checklist

- [ ] Case anchor：3 代 schema 並存 incident 需要新建 case（或借用 vendor overview 段落補述）
- [ ] Knowledge card 雙引用：document-store + transaction-boundary 都已存在、直接連
- [ ] Sibling 對比清楚：embedded 推到極致導致 unbounded array，自然引到 shard key 與 resharding；reference 推到極致導致 `$lookup`，自然引到 aggregation
- [ ] 預估寫作長度：240-280 行（schema pattern 是 MongoDB deep article 第一篇、需多花篇幅鋪 aggregate / document 概念）
