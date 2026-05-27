---
title: "MongoDB Aggregation Pipeline Optimization：stage 順序、index 配合與 memory 邊界"
date: 2026-05-27
description: "MongoDB aggregation pipeline stage 順序、index 配合、100MB memory 邊界、cross-shard `$lookup` 限制；report dashboard 跑爆 primary 的 anti-pattern 治理路徑"
weight: 34
tags: ["backend", "database", "mongodb", "aggregation", "query-optimization", "deep-article"]
---

MongoDB aggregation pipeline 是 document model 做 analytical query 的主要介面、stage stream 設計直觀但 production 容易踩雷 — 上線時 200ms、半年後資料量翻倍變 8s、加 index 沒用；profiler 顯示 stage 之間在 memory 累積上百 MB temp data。Aggregation pipeline 的最佳化跟 RDBMS 的 SQL planner 完全不同邏輯 — RDBMS 靠 planner 自動重排 join / filter、MongoDB 靠寫 query 的人手動排 stage 順序。本文把 stage 機制、index 配合、memory 邊界、cross-shard 限制講清楚、並對「report dashboard 跑爆 primary」這個常見 anti-pattern 給治理路徑。

本文不重複 [MongoDB vendor overview](/backend/01-database/vendors/mongodb/) 已寫過的 aggregation 簡介 — 而是 production tuning + 失敗修復的實作層教學。

> **前置閱讀**：MongoDB workload 適配判讀（document shape 主導 / contract layer 該放哪 / 跨雲 hedging 是否需要）見 [schema-design-pattern 開頭 3 軸前置判讀](../schema-design-pattern/#問題情境document-自由的後座力)。本文聚焦 aggregation pipeline 操作層、是 *已選 MongoDB 後* 的 query 層工程議題、不重複前置判讀。

## 問題情境：aggregation 是 hot path 的反模式

典型觸發場景：報表 pipeline 上線時 200ms、半年後資料量翻倍變 8s、加 index 沒用；profiler 顯示 stage 之間在 memory 累積上百 MB temp data。

進一步徵兆：

- 「OLTP collection 上跑 analytical query」的混合 workload：把 `$group + $lookup + $sort` 接成長 pipeline、aggregation 把整個 working set 從 cache 擠走
- Sharded cluster 上跑 cross-shard aggregation：`$group` / `$sort` 必須在 mongos 合併、mongos 變單點瓶頸
- `$lookup` 出現在 hot path：每筆 input doc 都要去另一個 collection 查、嚴格意義上是 N+1
- `db.serverStatus().metrics.aggStageCounters` 飆、`executionStats.executionTimeMillis` 跟 doc 數線性增長
- Profiler 報 `usedDisk: true`、aggregation OOM kill `QueryExceededMemoryLimitNoDiskUseAllowed`

Case anchor：report dashboard 跑爆 primary 的具體 incident 細節需未來 case 補完、本文以「常見 anti-pattern」處理、不憑空編造 incident 數字。側面引用 [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — 從 MongoDB 把 analytics 分離出來的 driver。

## 核心機制

Aggregation pipeline 是 stage 序列：每個 stage 接 stream of document、產出 stream of document。Stage 順序直接決定後續 stage 處理量 — 第一個 stage 是 IXSCAN 還是 COLLSCAN、`$match` 推到前面還是後面、`$project` 早 drop 還是晚 drop、都會放大或縮小後續 cost。

**Optimizer rewrite**：MongoDB 會自動把 `$match` / `$project` 往前推、把 `$sort + $limit` 合併成 top-K、但不保證所有 case。用 `explain("executionStats")` 看 rewrite 後的 effective pipeline、不要靠原始 pipeline 推斷實際執行順序。

**Index 配合**：pipeline 的 *第一個 stage* 若是 `$match` 或 `$sort`、且能對到 index、就走 IXSCAN。中間 stage 都是 in-memory stream、沒 index 概念。所以 `$match` 永遠該排第一、配合對應 index。

**Memory 邊界**：每個 aggregation stage 預設 100MB memory 上限、超過要 `allowDiskUse: true`（4.2+ 是預設）。Disk spill 啟動後 IO 嚴重拖慢、aggregation 變慢 50-100x。

**`$lookup` 在 sharded cluster**：foreign collection 不能 sharded（5.0 前完全不行、5.0+ 有限放寬）；`$lookup` 本質是 nested loop join、沒 hash join / merge join — 對大 collection 不可用。

**`$facet` 平行多 pipeline**：但所有 facet 共享同一個 100MB 限制、複雜 facet 容易撞 memory ceiling。

**`$merge` / `$out`**：把結果寫回 collection（pre-computed view / materialized view）— 把 hot analytical query 移出 read path、是治理 anti-pattern 的主要工具。

對應 knowledge card：[hot-partition](/backend/knowledge-cards/hot-partition/)（aggregation 集中讀單 shard 的副作用）、[document-store](/backend/knowledge-cards/document-store/)、[stale-read](/backend/knowledge-cards/stale-read/)（從 secondary 跑 aggregation 的 trade-off）。

## 操作流程

**Step 0：把壞 pipeline 跟好 pipeline 並排**。看一個簡化但典型的優化：

```javascript
// 壞：lookup 在 match 前、sort 沒 limit、project 在最後
db.orders.aggregate([
  { $lookup: { from: "users", localField: "userId", foreignField: "_id", as: "user" } },
  { $match: { status: "completed", "user.region": "ap-tokyo" } },
  { $sort: { createdAt: -1 } },
  { $project: { _id: 1, total: 1, createdAt: 1 } }
])

// 好：可推前的 match 寫前面、sort + limit 配對、project 早寫
db.orders.aggregate([
  { $match: { status: "completed" } },
  { $sort: { createdAt: -1 } },
  { $limit: 100 },
  { $lookup: { from: "users", localField: "userId", foreignField: "_id", as: "user" } },
  { $match: { "user.region": "ap-tokyo" } },
  { $project: { _id: 1, total: 1, createdAt: 1, "user.name": 1 } }
])
```

差別：壞 pipeline 對整個 orders 做 lookup、然後才過濾；好 pipeline 先過濾 + top-100、只對 100 筆做 lookup、再過濾 lookup 結果。實際 collection 大時兩者差 50-100x。

**Step 1：拿 explain plan**。

```javascript
db.coll.explain("executionStats").aggregate([...])
```

看 `stages[]` 顯示 rewrite 後的 effective pipeline、`executionTimeMillis`、`totalDocsExamined / totalDocsReturned` 比值、是否 `usedDisk`。

**Step 2：把 `$match` 推到最前**。越早過濾、後續 stage 處理量越小。Optimizer 通常自己會推、但 `$lookup` 之後的 `$match` 不會自動推到 `$lookup` 之前 — 因為 lookup 出的欄位才能被那個 match 用、邏輯依賴。寫 query 時就把能推前的 `$match` 寫前面。

**Step 3：對 `$match` 欄位建 compound index**。確保 `executionStages` 顯示 `IXSCAN` 而不是 `COLLSCAN`。Compound index 順序敏感 — `{ status: 1, createdAt: -1 }` 對 `{ status: ..., createdAt: $gte: ... }` 高效、對 `{ createdAt: $gte: ... }` 走不到 index。

**Step 4：`$sort + $limit` 寫在一起**。Optimizer 才會推 top-K（不需要 full sort、只需要 heap）。單 `$sort` 不限 limit 會做 full sort、容易撞 memory。

**Step 5：`$project` 早寫**。把不需要的欄位早期 drop、減少後續 stage 處理 doc size。對大 document 特別有效。

**Step 6：把 hot analytical pipeline 寫成 materialized view**。

```javascript
db.orders.aggregate([
  { $match: { createdAt: { $gte: ISODate("2026-05-01") } } },
  { $group: { _id: "$customerId", total: { $sum: "$amount" } } },
  { $merge: {
      into: "monthly_customer_summary",
      on: "_id",
      whenMatched: "merge",
      whenNotMatched: "insert"
  }}
])
```

定時更新（cron / 5 分鐘一次）、application 讀 materialized view 而不是即時跑 aggregation。

**Step 7：sharded cluster 處理**。避免在 hot path 用 cross-shard `$lookup` / `$group`、或把這類 query 路由到 analytical replica（用 tag set + read preference）、見 [replica set read preference](../replica-set-read-preference/)。

驗證點：

- `executionTimeMillis` 在預期 budget 內
- `totalDocsExamined / totalDocsReturned` 比值接近 1（過濾效率高）
- 無 `usedDisk: true`
- 無 stage 看到 `inMemory > 50MB`

Rollback boundary：pipeline 改寫是 application code 變更、可以灰度；materialized view（`$merge`）需備份 target collection 才能還原。

### 典型 tuning 過程（200ms → 8s → 250ms）

一個常見的 production pipeline 演化路徑：

1. **上線時 200ms**：collection 100K doc、`$match` 過濾 95%、`$lookup` 只跑 5K 次、in-memory `$sort` 處理 5K row 在 100MB 內
2. **半年後 8s**：collection 長到 2M doc、`$match` 仍過濾 95% 但變 100K row、`$lookup` 跑 100K 次（5K → 100K 是 20x）、`$sort` 在 in-memory 撞 100MB 開始 disk spill、IO 100x 退化
3. **加 compound index 沒用**：index 是給 `$match` 用的、但 `$match` 之後的 stage（`$lookup` / `$sort`）走的是 in-memory pipeline、index 救不了
4. **修法到 250ms**：(a) `$sort + $limit` 配對讓 optimizer 走 top-K、避免 full sort (b) 改 schema embed 把 `$lookup` 拿掉（見 [schema design pattern](../schema-design-pattern/)）(c) hot pipeline 寫成 `$merge` materialized view、application 讀 view 不跑 aggregation

關鍵教訓：aggregation 慢的原因不在 query 本身、在 *資料形狀演進*。Index 是 hot path 的第一個槓桿、但只對 `$match` / `$sort` 第一 stage 有效；後續 stage 要靠 stage 順序、materialized view、schema denormalize 來救。

## 失敗模式

**`$lookup` 在 hot path**：list page 每行去另一 collection 查、p99 隨 page size 線性增。應在 schema design 階段 denormalize、把 read-together 資料 embed 回 aggregate root（見 [schema design pattern](../schema-design-pattern/)）。

**`$sort` 不帶 limit + 沒 index**：全表 in-memory sort、撞 100MB 限制 → OOM 或 disk spill。`allowDiskUse: true` 解 OOM 但 IO 100x 退化。修法是建對應 index 走 IXSCAN sort、或限 limit 走 top-K。

**Sharded cluster cross-shard aggregation**：`$group` 階段所有 partial result 跑到 mongos 合併、mongos memory + CPU 爆。修法是 group key 包含 shard key prefix（讓 group 在 shard 內完成）、或路由到 analytical replica 跑。

**Stage 順序錯**：`$lookup` 放在 `$match` 前、等於對全表都做 lookup 再過濾、每個 input doc 都觸發 lookup。`$match` 永遠該排第一。

**Aggregation 把 working set 擠走**：OLTP 的 hot page 被 aggregation 的 cold scan 擠出 cache、整體 query latency 一起退化。修法是 analytical workload 跟 OLTP read 隔離（read preference tag）、或搬走 analytical（見下面 anti-recommendation）。

**`$facet` 滿載**：四個 facet 各跑大 pipeline、共享 100MB 限制立刻爆。修法是拆成獨立 query、不要硬塞 facet。

Anti-recommendation：

- **報表 / BI / analytics workload 跑 MongoDB primary 是反模式**：應該 (a) 設定 analytical secondary + read preference tag (b) 用 `$merge` 寫到 reporting collection (c) 進階用 BI Connector / data lake / 把 analytical workload 整批搬到 [ClickHouse](https://clickhouse.com) / BigQuery
- **「report dashboard 跑爆 primary」典型 anti-pattern**：BI 工具直連 MongoDB primary 跑長 pipeline、cache eviction 把 OLTP working set 擠走、p99 latency 在報表時段集體升。沒拿到具體 incident 數字、不在本文編造、改寫成「常見 anti-pattern」並推到治理路徑
- **Aggregation 不能解 read scaling**：aggregation 是 OLTP 的補位、不是 read scaling 的主路。Read scaling 在大規模 OLTP 走 cache + freshness token（見 [connection management and cache layer](../connection-management-and-cache-layer/)）、不是把 aggregation 跑爆 secondary

## 容量與觀測

關鍵 metric：

- Aggregation operation time 分布
- Disk spill 次數
- `opcounters.command` 中 aggregate 比例
- Cache eviction rate 在 aggregation 高峰時的變化

Mongo command：

- `db.currentOp({ "command.aggregate": { $exists: true } })`：當前 aggregation 在跑
- `db.serverStatus().metrics.aggStageCounters`：stage 級別 counter
- `explain("executionStats")`：單 query 詳細分析

Profiler：`db.setProfilingLevel(1, {slowms: 200})`、看 `usedDisk` flag 跟 `numYield`。

回到 [4.20 observability evidence](/backend/04-observability/observability-evidence-package/)：aggregation slow log + cache hit ratio + disk spill rate 是「analytical 壓力」的 evidence 三件套。

回到 [9.5 bottleneck localization](/backend/09-performance-capacity/bottleneck-localization/)：用 explain executionStats 把 pipeline stage 對到瓶頸（IXSCAN 還是 COLLSCAN、in-memory 還是 disk spill、shard-local 還是 mongos merge）。

## 邊界與整合

Sibling deep articles：

- [schema design pattern](../schema-design-pattern/) — embedded 設計可消除大部分 `$lookup`
- [shard key selection](../shard-key-selection/) — 決定 aggregation 是 shard-local 還是 cross-shard
- [replica set read preference](../replica-set-read-preference/) — aggregation 跑 secondary 的 stale read trade-off
- [connection management and cache layer](../connection-management-and-cache-layer/) — report dashboard 跑爆 primary 時的 cache + read scaling 主路

Migration playbook：analytical workload 大到不能繼續混在 MongoDB → split 出 [→ Cosmos DB MongoDB API + Synapse](/backend/01-database/vendors/cosmosdb/) 或 [→ DynamoDB + Athena/Glue](/backend/01-database/vendors/dynamodb/)（access pattern 重設計）。

跟 1.x 互引：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) 把 aggregation 列為 read-shape 的成本維度；[1.1 高併發資料存取](/backend/01-database/high-concurrency-access/) 處理「OLTP + analytical 同 cluster」的反模式。

## 相關連結

- [MongoDB vendor overview](/backend/01-database/vendors/mongodb/) — 本文是該頁尾「aggregation pipeline optimization」backlog 的深度展開
- [Vendor 深度技術文章方法論](/posts/vendor-deep-article-methodology/)
- 官方：[Aggregation Pipeline](https://www.mongodb.com/docs/manual/aggregation/)、[Optimize Pipelines](https://www.mongodb.com/docs/manual/core/aggregation-pipeline-optimization/)、[$merge](https://www.mongodb.com/docs/manual/reference/operator/aggregation/merge/)
