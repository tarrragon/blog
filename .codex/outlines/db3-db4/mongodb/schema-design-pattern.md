# MongoDB Schema Design Pattern：contract layer 在哪 vs embedded / reference

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。
>
> **校準說明**：本 outline 由 case-first audit 重寫、framing 從「embedded vs reference 二選一」推進到「contract layer 在哪」三選一（DB 層 validator / app 層 abstraction / 混合）。embedded vs reference 仍是核心機制、但讀者真正的 production 議題是 *誰來守 schema 契約*（F2.3 來源）。

## 問題情境（Production pressure）

- **MongoDB 適用度前置判讀**（Frame 1 / F2.1 / F2.3 / F2.10）— 讀者進到 schema design 之前要先確認三件事：
  - **document shape 是否主導資料**：sensor signal / CMS article / order aggregate 這類「形狀本來就多型 + 隨產品演進」適合 document model；access pattern 固定 + 欄位定型的反而該回 KV（DynamoDB）或 SQL
  - **contract layer 該放哪**：DB-layer validator 適合 schema 穩定 / 跨服務共用 collection 的場景；app-layer abstraction 適合 schema 演進快 / 微服務獨立 owner；混合適合大型 production
  - **跨雲 hedging 是否需要**：若團隊未來雲商策略不確定、Atlas 跨雲是 selection 訊號；只在單雲跑就不必為 hedging 多付代價
- Document model 早期 schema-less 紅利、跑半年後 collection 同時混三代 schema、application 寫 if-else 處理欄位缺失與型別漂移
- 子文件越塞越深、單 document 突破 1-2MB、partial update 仍要把整顆 document load + write、IO 跟 working set 雙重壓力
- 反向過度 normalize：訂單跟訂單 item 拆兩個 collection、單一查詢得 N+1 `$lookup`、aggregation cost 飆
- IoT / sensor / event log workload 寫進 regular collection、寫入吞吐撞牆但沒考慮 time-series collection（F2.8）
- 讀者徵兆：`$lookup` 出現在 hot path、document size warning（16MB 上限預警）、partial update 卻產生大量 disk write、schema validation 報錯比例突然爬升
- Case anchor: primary [9.C38 Toyota Connected](/backend/09-performance-capacity/cases/toyota-connected-mongodb-telematics-iot/)（車載 sensor schema 隨車型 / 年份 / 規範演進、polymorphic document 與 schema governance 並存）；secondary [9.C37 Forbes](/backend/09-performance-capacity/cases/forbes-mongodb-atlas-multi-cloud-migration/)（自建中介 abstraction layer 做 app-layer contract、CMS 50+ 微服務隔離 schema 變動）；side-light [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/)（document model 保留 + 跨 vendor 形狀治理壓力）；needs new case：早期 startup MongoDB 三代 schema 並存的 failure-mode incident

## 核心機制（Vendor-specific mechanism）

### Aggregate root 與 embedded / reference

- **Aggregate root**：把「一起讀、一起寫、一致性邊界一致」的資料塞同一個 document，呼應 DDD aggregate；MongoDB 把 atomicity 限制在 *單 document*
- **Embedded（subdocument / array）**：寫入 atomic、讀取一次到位；代價是 update sub-element 仍要 rewrite 整顆 document
- **Reference（手動 `_id` foreign key + `$lookup`）**：document 大小可控，但 join 在 application 或 aggregation 階段做
- **Polymorphic pattern**：同 collection 用 `type` discriminator 存多型實體；MongoDB 沒 inheritance，靠 schema validator 與 partial index 維持邊界
- 16MB document hard limit + working set 在 RAM 的隱性軟限制（單 doc 大小直接影響 page cache 效率）

### Contract layer 三條路徑（F2.3 frame）

跨 case 合成 frame（Toyota + Forbes）：document model 的 schema flexibility 在 production 必須以 schema governance 對沖、否則「schema 自由」變「production data inconsistency」（Toyota case 明示）。三條 contract layer 路徑：

- **DB-layer contract（MongoDB `$jsonSchema` validator）**：`$jsonSchema` + `validationLevel` + `validationAction`、production 是「契約 enforcement」工具、不是 dev-time linter；適合多服務共用 collection、需要 DB 層擋住髒資料
- **App-layer contract（abstraction layer）**：API 包裝 + middleware schema 驗證、microservice 看到的是穩定 contract API、DB schema 變動限制在 owner microservice 內；9.C37 Forbes 揭露：50+ 微服務透過自建中介 abstraction layer 隔離 schema 變動、跨雲彈性才用得起來
- **混合**：DB 層 validator 守底線（型別 / 必填）、app 層 abstraction 守業務（版本欄位 / 相容處理）；Atlas Application Services 跟 enterprise schema registry 屬此類

讀者選哪條路徑要看：team 規模 / collection 跨服務程度 / schema 演進速度。

### Time-series collection（6.0+）

- **適用情境**：timestamp 主導資料、metadata + measurement 三段式、寫入吞吐主導（IoT / sensor / event log / metrics）
- **vs regular collection**：寫入吞吐高 3-5x、storage 壓縮率更好；但 schema flexibility 降低（必須有 timestamp 欄位）、跨 document update 受限
- 9.C38 Toyota 警示：case 自承「20 個 Atlas database 沒明確說有沒有用 time series collection — 對 IoT 案例這是重要區分、但 case study 沒揭露」；寫稿時要明示「IoT / sensor 場景該考慮 time-series collection、Toyota case 未揭露實際是否使用」、不能寫成「Toyota 使用 time-series collection」（fact vs derive 紀律）
- **對應 knowledge card**: [document-store](/backend/knowledge-cards/document-store/)、[transaction-boundary](/backend/knowledge-cards/transaction-boundary/)（aggregate boundary = transaction boundary）、[data-inconsistency](/backend/knowledge-cards/data-inconsistency/)

## 操作流程（Operations）

- Step 1：access pattern 盤點 — 列出 top 10 query / write、標 read together / write together 集合
- Step 2：**contract layer 決策** — 依下表選一條路徑

  | 條件                                      | 路徑                                              |
  | ----------------------------------------- | ------------------------------------------------- |
  | Collection 跨多服務 + schema 穩定         | DB-layer validator                                |
  | Schema 演進快 + 微服務獨立 owner          | App-layer abstraction                             |
  | 大型 production + 多 owner + 跨團隊       | 混合（兩者並用）                                  |
  | IoT / sensor / event log + timestamp 主導 | Time-series collection（取代 regular collection） |

- Step 3：embed 判準（1:few、life-cycle 同步、< 1MB 預期上限）vs reference 判準（1:many 寫頻不對稱、跨 aggregate 引用）
- Step 4：DB-layer 路徑 — 用 `$jsonSchema` 寫 validator、`validationLevel: "moderate"` 先放行 legacy、再 `"strict"` 封死新寫入
- Step 5：App-layer 路徑 — 中介 abstraction 介面層擋 schema 變動、internal microservice 看到的是穩定 contract（9.C37 Forbes 揭露的模式）
- Step 6：polymorphic 用 partial index `{ type: 1, ... }` + `partialFilterExpression` 避免冷分支吃 index 成本
- Step 7：用 `bsondump` + `$bsonSize` + `collStats` 量測 doc 形狀，把違規 doc 列名單
- 驗證點：`db.coll.aggregate([{$group:{_id:null, avg:{$avg:{$bsonSize:"$$ROOT"}}, max:{$max:{$bsonSize:"$$ROOT"}}}}])` 看分布、validator failure rate 看寫入契約執行狀況、abstraction layer 的 schema 版本相容矩陣
- Rollback boundary：validator 從 `strict` 退回 `moderate` 是 single-command；abstraction layer 換版需 application code 灰度；已 embed 進去的 schema 變更要靠 backfill migration script，無法 in-place 還原

## 失敗模式（Failure modes）

- **Unbounded array growth**：把「使用者所有訊息」embed 進 user document、document 撞 16MB → 寫入直接 reject
- **Hot subdocument update**：所有寫都打同一個 nested field、wiredTiger document-level lock 退化成熱點，concurrency 看似多核卻被序列化
- **$lookup 在 hot path**：reference 沒設好變 join、p99 latency 隨 collection 大小線性退化
- **Schema 三代並存（缺 contract layer）**：缺 validator 跟 abstraction layer、舊版欄位殘留、application code 三層 fallback、新 dev onboarding 看不懂哪個欄位是現役（9.C38 Toyota 揭露：document model 的彈性「成本是 production 必須做 schema governance」）
- **Abstraction layer 變成 lock-in**：app-layer contract 寫得太重、跨 vendor 遷移時 abstraction 本身要重寫；該層應該薄、只做 schema 隔離不做業務邏輯
- **Polymorphic 全表掃描**：discriminator 沒進 index、`type: "rare"` 查詢全表 scan
- **Time-series collection 用錯場景**：把非 timestamp 主導資料塞進 time-series collection、失去 flexibility 又拿不到吞吐紅利
- Anti-recommendation：
  - access pattern 還沒穩定的早期 MVP 不需要鎖死 schema validator；先用 app-layer abstraction、production 穩定後再決定 DB 層該不該封死
  - JOIN-heavy / 強 normalize workload 一開始就該回 PostgreSQL JSONB 或 SQL，不是塞進 MongoDB 再 `$lookup`
  - 跨案合成 frame：「不是所有資料都該進 MongoDB」、document-shaped + 形狀變化頻繁的進、access pattern 固定的 KV 走 KV（F2.18 federated DB frame、9.C36 Coinbase 揭露 MongoDB + DynamoDB 按 workload 分流）

## 容量與觀測（Capacity & observability）

- 關鍵 metric：`collStats.avgObjSize`、`collStats.size` vs `storageSize`（壓縮比）、`document validation failure rate`、abstraction layer 的 schema mismatch rate、`wiredTiger.cache.bytes currently in the cache` 對比 working set 估算
- Mongo command：`db.coll.stats()`、`db.coll.aggregate([{$collStats:{...}}])`、`db.runCommand({collMod:..., validator:...})`
- Profiler：`db.setProfilingLevel(1, {slowms: 100})` 抓 slow op，看是否 `$lookup` / `$unwind` 進 hot path
- 回到 [4.20 observability evidence](/backend/04-observability/observability-evidence-package/)：把 doc size 分布、validator failure rate、abstraction layer schema mismatch、`$lookup` 出現位置列為 evidence
- 回到 [9.5 bottleneck localization](/backend/09-performance-capacity/bottleneck-localization/)：working set 撐爆 RAM 時的 page fault 信號

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：
  - [shard key selection](./shard-key-selection.md)（document 形狀決定 shard key 候選）
  - [aggregation pipeline optimization](./aggregation-pipeline-optimization.md)（`$lookup` 與 schema reference 互相牽動）
  - [connection management and cache layer](./connection-management-and-cache-layer.md)（document model 在 production 主角位置的跨層架構、abstraction layer 跟 cache 層協作）
- Migration playbook：
  - document 形狀走樣到無法治理時的 [→ MongoDB → PostgreSQL 拆 normalize](/backend/01-database/large-scale-db-migration/) 路徑
  - 保留 document model 換 vendor 三型對照（F2.1）— 保留主 DB 補周邊（Coinbase）/ 同 DB 換託管（Forbes Atlas）/ 同 model 換 vendor（Microsoft 365 Cosmos DB MongoDB API）；SSoT 在 [`cosmosdb/mongodb-api-vs-sql-api.md`](../cosmosdb/mongodb-api-vs-sql-api.md) 開頭段、本文 cross-link
- 跟 1.x 互引：[1.2 schema design](/backend/01-database/schema-design/) 處理通用 schema 演進原則、本文是 MongoDB-specific 落地；[1.4 transaction boundary](/backend/01-database/transaction-boundary/) 對齊 aggregate = atomic 邊界

## 寫作前置 checklist

- [ ] Case anchor：primary 9.C38 Toyota（polymorphic + governance）+ secondary 9.C37 Forbes（app-layer abstraction）已充分；3 代 schema 並存 startup incident 需新建 case 或借用 vendor overview 段落補述
- [ ] Knowledge card 雙引用：document-store + transaction-boundary 都已存在、直接連
- [ ] Sibling 對比清楚：embedded 推到極致導致 unbounded array，自然引到 shard key 與 resharding；reference 推到極致導致 `$lookup`，自然引到 aggregation；contract layer 路徑引到 connection-management（app-layer abstraction 跟 cache layer 同層協作）
- [ ] Fact vs derive 分層：「Toyota 用 polymorphic document + schema governance」是 case 揭露事實；「Toyota 是否用 time-series collection」是 case 自承知識缺口、必須寫成「IoT 場景該考慮、Toyota 未揭露實際使用」；「contract layer 三條路徑」是跨案合成 frame、case 原文沒這個 frame、寫進文章時明示「本章合成」
- [ ] Scope warning：time-series collection 部分明示 Toyota case 未揭露使用情況、不可寫成「Toyota 使用 X」
- [ ] 預估寫作長度：280-340 行（contract layer 三選一框架是新增主軸、需多花篇幅鋪概念 + case 對應）
