---
title: "MongoDB Schema Design Pattern：contract layer 在哪 vs embedded / reference"
date: 2026-05-27
description: "MongoDB document schema 真正的 production 議題不是 embedded vs reference 二選一、是 schema contract 該放 DB 層 validator 還是 app 層 abstraction；含 Toyota polymorphic governance、Forbes abstraction layer、time-series collection 邊界"
weight: 30
tags: ["backend", "database", "mongodb", "schema-design", "document-model", "deep-article"]
---

MongoDB schema design 的初學討論常停在「embedded vs reference 二選一」。真實 production 議題遠不止此：document model 給的 schema flexibility 在第一年是紅利、跑半年後同 collection 開始混三代 schema、application code 三層 if-else 處理欄位缺失與型別漂移。這時候讀者要解的不是「embed 還是 reference」、是 **schema contract 該由誰守、守在哪一層**。本文把這個議題拆成三條 contract layer 路徑（DB-layer validator / app-layer abstraction / 混合）、配合 embedded / reference / polymorphic 機制與 time-series collection 邊界一起討論。

本文不重複 [MongoDB vendor overview](/backend/01-database/vendors/mongodb/) 已寫過的 document model 適用條件 — 而是 production 部署 + schema governance + 失敗修復 的實作層教學。

## 問題情境：document 自由的後座力

MongoDB 適用度的前置判讀有三件事要確認：

- **document shape 是否主導資料**：sensor signal / CMS article / order aggregate 這類「形狀本來就多型 + 隨產品演進」適合 document model；access pattern 固定 + 欄位定型的反而該回 KV 系統或 SQL
- **contract layer 該放哪**：DB-layer validator 適合 schema 穩定 / 跨服務共用 collection 的場景；app-layer abstraction 適合 schema 演進快 / 微服務獨立 owner；混合適合大型 production
- **跨雲 hedging 是否需要**：若團隊未來雲商策略不確定、Atlas 跨雲是 selection 訊號；只在單雲跑就不必為 hedging 多付代價

確認 MongoDB 該用之後，讀者真正在 production 撞到的徵兆：

- Document model 早期 schema-less 紅利、跑半年後 collection 同時混三代 schema、application 寫 if-else 處理欄位缺失與型別漂移
- 子文件越塞越深、單 document 突破 1-2MB、partial update 仍要把整顆 document load + write、IO 跟 working set 雙重壓力
- 反向過度 normalize：訂單跟訂單 item 拆兩個 collection、單一查詢得 N+1 `$lookup`、aggregation cost 飆
- IoT / sensor / event log workload 寫進 regular collection、寫入吞吐撞牆但沒考慮 time-series collection
- `$lookup` 出現在 hot path、document size warning（16MB 上限預警）、partial update 卻產生大量 disk write、schema validation 報錯比例突然爬升

Case anchor：[9.C38 Toyota Connected](/backend/09-performance-capacity/cases/toyota-connected-mongodb-telematics-iot/) 揭露車載 sensor schema 隨車型 / 年份 / 規範演進、polymorphic document 與 schema governance 並存；[9.C37 Forbes](/backend/09-performance-capacity/cases/forbes-mongodb-atlas-multi-cloud-migration/) 揭露 CMS 50+ 微服務透過自建中介 abstraction layer 隔離 schema 變動；[9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) 揭露 document model 保留 + 跨 vendor 形狀治理。早期 startup MongoDB 三代 schema 並存的具體 incident 細節需未來 case 補完、本文先以「常見 failure pattern」處理。

## 核心機制：aggregate root、embedded、reference、polymorphic

MongoDB schema design 的第一層是 *aggregate root 決定 atomicity 邊界*。MongoDB 把寫入 atomicity 限制在「單 document 內」、跨 document 要 multi-document transaction（5.0+ 在 replica set / sharded cluster 都支援、但跨 shard 有性能成本）。aggregate root 是 DDD 概念落地到 MongoDB 的具體實作 — 把「一起讀、一起寫、一致性邊界一致」的資料塞同一個 document。

- **Embedded（subdocument / array）**：寫入 atomic、讀取一次到位；代價是 update sub-element 仍要 rewrite 整顆 document，sub-element 寫頻很高時不適合
- **Reference（手動 `_id` foreign key + `$lookup`）**：document 大小可控，但 join 在 application 或 aggregation 階段做；JOIN-heavy workload 跑這條路徑會 N+1
- **Polymorphic pattern**：同 collection 用 `type` discriminator 存多型實體；MongoDB 沒 inheritance、靠 schema validator 與 partial index 維持邊界
- **16MB document hard limit**：是 MongoDB 機制邊界；working set 在 RAM 的隱性軟限制（單 doc 大小直接影響 page cache 效率）更早就會出問題

### Contract layer 三條路徑

跨 case 合成 frame（本章合成、Toyota + Forbes 共同揭露）：document model 的 schema flexibility 在 production 必須以 schema governance 對沖、否則「schema 自由」變「production data inconsistency」（Toyota case 明示）。讀者要選的不是「要不要做 schema governance」、是「contract 守在哪一層」。三條路徑：

| 路徑               | 實作機制                                                                 | 適用條件                                           |
| ------------------ | ------------------------------------------------------------------------ | -------------------------------------------------- |
| DB-layer contract  | MongoDB `$jsonSchema` validator + `validationLevel` + `validationAction` | Schema 穩定、多服務共用 collection、要 DB 擋髒資料 |
| App-layer contract | 自建 API abstraction + middleware schema 驗證                            | Schema 演進快、微服務獨立 owner、跨雲彈性需求      |
| 混合               | DB 層擋型別 / 必填、app 層擋業務語意 / 版本                              | 大型 production、多 owner、跨團隊                  |

**DB-layer 路徑**：`$jsonSchema` validator 在 production 是「契約 enforcement」工具、不是 dev-time linter。設 `validationAction: "error"` 寫入直接擋；設 `"warn"` 只記 log。`validationLevel: "moderate"` 對既有 doc 放行、對新寫入嚴格；`"strict"` 對所有寫入都嚴格。適合 schema 穩定到「跨服務共用 collection」的程度。

**App-layer 路徑**：9.C37 Forbes 揭露的模式 — 50+ 微服務透過自建中介 abstraction layer 看到穩定的 contract API、DB schema 變動限制在 owner microservice 內。Forbes 跨雲彈性能用起來、核心原因是 abstraction layer 把 schema 治理收斂到單點、跨雲遷移時 abstraction layer 不變、微服務不知道底層 DB 換 cluster 換雲。

**混合路徑**：Atlas Application Services、enterprise schema registry 屬此類。DB 層 validator 守底線（欄位型別、必填欄位）、app 層 abstraction 守業務（版本欄位 / 相容處理 / cross-document 一致性）。代價是兩層都要維護、版本同步成本高、適合 production 規模真的撐住這個複雜度的團隊。

讀者選哪條路徑要看：team 規模 / collection 跨服務程度 / schema 演進速度。

### Time-series collection（6.0+）

Time-series collection 是 MongoDB 為 IoT / sensor / event log / metrics 設計的 vendor-specific 機制 — 比 regular collection 寫入吞吐高 3-5x、storage 壓縮率更好。資料形狀必須是 `{ timestamp, metadata, measurement }` 三段式、timestamp 主導。

適用情境：sensor signal 高頻寫入、metrics 系統的 time series、application event log。**不適用情境**：schema 不以 timestamp 為主、需要跨 document update、需要 polymorphic discriminator。

9.C38 Toyota Connected 自承「20 個 Atlas database 沒明確說有沒有用 time series collection — 對 IoT 案例這是重要區分、但 case study 沒揭露」。寫進 production 時必須明示：IoT / sensor 場景該考慮 time-series collection、Toyota case 未揭露實際使用情況、不可寫成「Toyota 使用 time-series collection」。

對應 knowledge card：[document-store](/backend/knowledge-cards/document-store/)、[transaction-boundary](/backend/knowledge-cards/transaction-boundary/)（aggregate boundary = transaction boundary）、[data-inconsistency](/backend/knowledge-cards/data-inconsistency/)。

## 操作流程

**Step 1：access pattern 盤點**。列出 top 10 query / write、標 read together / write together 集合 — 這份清單決定 embedded vs reference vs polymorphic 的候選。

**Step 2：contract layer 決策**。

| 條件                                      | 路徑                                              |
| ----------------------------------------- | ------------------------------------------------- |
| Collection 跨多服務 + schema 穩定         | DB-layer validator                                |
| Schema 演進快 + 微服務獨立 owner          | App-layer abstraction                             |
| 大型 production + 多 owner + 跨團隊       | 混合（兩者並用）                                  |
| IoT / sensor / event log + timestamp 主導 | Time-series collection（取代 regular collection） |

**Step 3：embed 判準** — 1:few、life-cycle 同步、< 1MB 預期上限；**reference 判準** — 1:many 寫頻不對稱、跨 aggregate 引用。

**Step 4：DB-layer 路徑 validator 配置**：

```javascript
db.runCommand({
  collMod: "orders",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "tenantId", "createdAt", "items"],
      properties: {
        tenantId: { bsonType: "string" },
        createdAt: { bsonType: "date" },
        items: {
          bsonType: "array",
          minItems: 1,
          items: {
            bsonType: "object",
            required: ["sku", "qty"],
            properties: {
              sku: { bsonType: "string" },
              qty: { bsonType: "int", minimum: 1 }
            }
          }
        }
      }
    }
  },
  validationLevel: "moderate",
  validationAction: "warn"
})
```

灰度策略：先 `validationLevel: "moderate"` + `validationAction: "warn"` 觀察兩週、確認 application 不寫違規 doc、再切 `"strict"` + `"error"` 封死。

**Step 5：App-layer 路徑 abstraction 介面**。9.C37 Forbes 揭露的模式 — middleware 攔截 microservice 寫入、驗 schema、套版本欄位、把 owner microservice 的 schema 變動隔離在 abstraction 內。

**Step 6：Polymorphic + partial index** — `partialFilterExpression` 避免冷分支吃 index 成本：

```javascript
db.events.createIndex(
  { type: 1, timestamp: -1 },
  { partialFilterExpression: { type: { $in: ["click", "purchase"] } } }
)
```

**Step 7：量測 doc 形狀**。用 `bsondump` + `$bsonSize` + `collStats` 量測：

```javascript
db.coll.aggregate([
  { $group: {
      _id: null,
      avg: { $avg: { $bsonSize: "$$ROOT" } },
      max: { $max: { $bsonSize: "$$ROOT" } }
  }}
])
```

驗證點：avgObjSize 在預期範圍、validator failure rate < SLO、abstraction layer schema mismatch rate 可追溯。

**Rollback boundary**：validator 從 `strict` 退回 `moderate` 是 single-command、application code 不必改；abstraction layer 換版需 application code 灰度；已 embed 進去的 schema 變更要靠 backfill migration script、無法 in-place 還原。

## 失敗模式

**Unbounded array growth**：把「使用者所有訊息」embed 進 user document、document 撞 16MB → 寫入直接 reject。修法是改 reference、訊息獨立 collection、用 `userId` 索引。

**Hot subdocument update**：所有寫都打同一個 nested field、wiredTiger document-level lock 退化成熱點，concurrency 看似多核卻被序列化。修法是把熱寫欄位拆 reference document、或改 sharded collection 把寫散開（見 [shard key selection](../shard-key-selection/)）。

**`$lookup` 在 hot path**：reference 沒設好變 join、p99 latency 隨 collection 大小線性退化。修法是 schema design 階段 denormalize、把 read-together 資料 embed 回 aggregate root；或 `$merge` 寫 materialized view（見 [aggregation pipeline optimization](../aggregation-pipeline-optimization/)）。

**Schema 三代並存（缺 contract layer）**：缺 validator 跟 abstraction layer、舊版欄位殘留、application code 三層 fallback、新 dev onboarding 看不懂哪個欄位是現役。9.C38 Toyota 揭露：document model 的彈性「成本是 production 必須做 schema governance」、否則「schema 自由」變「production data inconsistency」。

**Abstraction layer 變成 lock-in**：app-layer contract 寫得太重、跨 vendor 遷移時 abstraction 本身要重寫。該層應該薄、只做 schema 隔離、不做業務邏輯。

**Polymorphic 全表掃描**：discriminator 沒進 index、`type: "rare"` 查詢全表 scan。修法用 partial index 把熱類型蓋住、冷類型走全表也只是冷路徑。

**Time-series collection 用錯場景**：把非 timestamp 主導資料塞進 time-series collection、失去 flexibility 又拿不到吞吐紅利。Time-series collection 是專屬優化、不是普適 collection 升級。

Anti-recommendation：

- access pattern 還沒穩定的早期 MVP 不需要鎖死 schema validator；先用 app-layer abstraction、production 穩定後再決定 DB 層該不該封死
- JOIN-heavy / 強 normalize workload 一開始就該回 PostgreSQL JSONB 或 SQL、不是塞進 MongoDB 再 `$lookup`
- 跨案合成 frame：「不是所有資料都該進 MongoDB」、document-shaped + 形狀變化頻繁的進、access pattern 固定的 KV 走 KV（9.C36 Coinbase 揭露 MongoDB + DynamoDB 按 workload 分流）

## 容量與觀測

關鍵 metric：

- **Document 形狀**：`collStats.avgObjSize`、`collStats.size` vs `storageSize`（壓縮比）
- **Contract 健康**：document validation failure rate、abstraction layer schema mismatch rate
- **Working set 壓力**：`wiredTiger.cache.bytes currently in the cache` 對比 working set 估算
- **Aggregation 副作用**：profiler slow op、`$lookup` / `$unwind` 在 hot path 出現位置

Mongo command：

- `db.coll.stats()` 看 document 平均 / 最大 size、storage / index size
- `db.runCommand({collMod: ..., validator: ...})` 改 validator
- `db.setProfilingLevel(1, {slowms: 100})` 抓 slow op

回到 [4.20 observability evidence](/backend/04-observability/observability-evidence-package/)：把 doc size 分布、validator failure rate、abstraction layer schema mismatch、`$lookup` 出現位置列為 evidence 三件套。

回到 [9.5 bottleneck localization](/backend/09-performance-capacity/bottleneck-localization/)：working set 撐爆 RAM 時的 page fault 信號、跟 doc size 異常增長強相關。

## 邊界與整合

Sibling deep articles：

- [shard key selection](../shard-key-selection/) — document 形狀決定 shard key 候選空間
- [aggregation pipeline optimization](../aggregation-pipeline-optimization/) — `$lookup` 與 schema reference 互相牽動
- [connection management and cache layer](../connection-management-and-cache-layer/) — abstraction layer 跟 cache 層協作

Migration playbook：

- document 形狀走樣到無法治理時的 [→ MongoDB → PostgreSQL 拆 normalize](/backend/01-database/large-scale-db-migration/) 路徑
- 保留 document model 換 vendor 三型對照 — 保留主 DB 補周邊（Coinbase）/ 同 DB 換託管（Forbes Atlas）/ 同 model 換 vendor（[Microsoft 365 Cosmos DB MongoDB API](/backend/01-database/vendors/cosmosdb/)）

跟 1.x 互引：[1.2 schema design](/backend/01-database/schema-design/) 處理通用 schema 演進原則、本文是 MongoDB-specific 落地；[1.3 transaction boundary](/backend/01-database/transaction-boundary/) 對齊 aggregate = atomic 邊界。

## 相關連結

- [MongoDB vendor overview](/backend/01-database/vendors/mongodb/) — 本文是該頁尾「schema design pattern」backlog 的深度展開
- [Vendor 深度技術文章方法論](/posts/vendor-deep-article-methodology/)
- [9.C38 Toyota Connected](/backend/09-performance-capacity/cases/toyota-connected-mongodb-telematics-iot/) — polymorphic + governance
- [9.C37 Forbes](/backend/09-performance-capacity/cases/forbes-mongodb-atlas-multi-cloud-migration/) — abstraction layer 模式
- 官方：[MongoDB Data Modeling](https://www.mongodb.com/docs/manual/core/data-modeling-introduction/)、[Schema Validation](https://www.mongodb.com/docs/manual/core/schema-validation/)、[Time Series Collections](https://www.mongodb.com/docs/manual/core/timeseries-collections/)
