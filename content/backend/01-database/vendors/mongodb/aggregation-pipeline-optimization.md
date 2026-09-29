---
title: "MongoDB Aggregation Pipeline Optimization：stage 順序、index 配合與 memory 邊界"
date: 2026-05-27
description: "MongoDB aggregation pipeline stage 順序、index 配合、100MB memory 邊界、cross-shard `$lookup` 限制；report dashboard 跑爆 primary 的 anti-pattern 治理路徑"
weight: 34
tags: ["backend", "database", "mongodb", "aggregation", "query-optimization", "deep-article"]
---

這篇整理 MongoDB aggregation pipeline 在 production 的調校：stage 的執行順序與 optimizer 會自動做哪些重排、index 在哪些 stage 生效、每個 stage 的 100MB memory 上限、sharded cluster 上 `$lookup` 與 `$group` 的限制，以及把報表 pipeline 從 primary 移走的治理路徑（「report dashboard 跑爆 primary」這個常見 anti-pattern）。Aggregation 的基本介紹在 [MongoDB vendor overview](/backend/01-database/vendors/mongodb/)。

MongoDB 的 optimizer 只做幾種固定的重排——把不依賴前面 stage 輸出的 `$match` 條件往前移、把相鄰的 `$sort` 與 `$limit` 合併成 top-K——依賴 `$lookup` 輸出欄位的條件移不動，所以 pipeline 的寫法仍然決定每個 stage 要處理多少 document。

> **前置閱讀**：MongoDB workload 適配判讀（document shape 主導 / contract layer 該放哪 / 跨雲 hedging 是否需要）見 [schema-design-pattern 開頭 3 軸前置判讀](../schema-design-pattern/#mongodb-適用度前置判讀)。本文聚焦 aggregation pipeline 操作層、是 *已選 MongoDB 後* 的 query 層工程議題、不重複前置判讀。

## 問題情境：aggregation 是 hot path 的反模式

典型觸發場景：報表 pipeline 上線時 200ms、半年後資料量翻倍變 8s、加 index 沒用；profiler 顯示 stage 之間在 memory 累積上百 MB temp data。

進一步徵兆：

- 「OLTP collection 上跑 analytical query」的混合 workload：把 `$group + $lookup + $sort` 接成長 pipeline、aggregation 把整個 working set 從 cache 擠走
- Sharded cluster 上跑 cross-shard aggregation：`$group` / `$sort` 必須在 mongos 合併、mongos 變單點瓶頸
- `$lookup` 出現在 hot path：每筆 input doc 都要去另一個 collection 查、嚴格意義上是 N+1
- `db.serverStatus().metrics.aggStageCounters` 飆、`executionStats.executionTimeMillis` 跟 doc 數線性增長
- Profiler 報 `usedDisk: true`、aggregation OOM kill `QueryExceededMemoryLimitNoDiskUseAllowed`

把 analytics 從 MongoDB 分離出來的一個實例是 [Microsoft 365 的 Cosmos DB analytics 案例](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/)。

## 核心機制

Aggregation pipeline 是 stage 序列：每個 stage 接 stream of document、產出 stream of document。Stage 順序直接決定後續 stage 處理量 — 第一個 stage 是 IXSCAN 還是 COLLSCAN、`$match` 推到前面還是後面、`$project` 早 drop 還是晚 drop、都會放大或縮小後續 cost。

**Optimizer rewrite**：MongoDB 會自動把 `$match` / `$project` 往前推、把 `$sort + $limit` 合併成 top-K、但不保證所有 case。用 `explain("executionStats")` 看 rewrite 後的 effective pipeline、不要靠原始 pipeline 推斷實際執行順序。

**Index 配合**：pipeline 的 *第一個 stage* 若是 `$match` 或 `$sort`、且能對到 index、就走 IXSCAN。中間 stage 都是 in-memory stream、沒 index 概念。所以 `$match` 永遠該排第一、配合對應 index。

**Memory 邊界**：每個 aggregation stage 預設 100MB memory 上限、超過要 `allowDiskUse: true`（6.0 起由 server 參數 `allowDiskUseByDefault` 預設開啟）。Disk spill 啟動後 IO 嚴重拖慢、aggregation 變慢 50-100x。

**`$lookup` 在 sharded cluster**：foreign collection 不能 sharded（5.0 前完全不行、5.0+ 有限放寬）；`$lookup` 本質是 nested loop join、沒 hash join / merge join — 對大 collection 不可用。

**`$facet` 平行多 pipeline**：但所有 facet 共享同一個 100MB 限制、複雜 facet 容易撞 memory ceiling。

**`$merge` / `$out`**：把結果寫回 collection（pre-computed view / materialized view）— 把 hot analytical query 移出 read path、是治理 anti-pattern 的主要工具。

對應 knowledge card：[hot-partition](/backend/knowledge-cards/hot-partition/)（aggregation 集中讀單 shard 的副作用）、[document-store](/backend/knowledge-cards/document-store/)、[stale-read](/backend/knowledge-cards/stale-read/)（從 secondary 跑 aggregation 的 trade-off）。

## 操作流程

**把慢的 pipeline 跟快的 pipeline 並排**。兩段回答同一個需求——ap-tokyo 使用者最新的 100 筆 completed 訂單：

```javascript
// 慢：region 條件要等 $lookup 產出 user 欄位才讀得到
db.orders.aggregate([
  { $lookup: { from: "users", localField: "userId", foreignField: "_id", as: "user" } },
  { $match: { status: "completed", "user.region": "ap-tokyo" } },
  { $sort: { createdAt: -1 } },
  { $limit: 100 },
  { $project: { _id: 1, total: 1, createdAt: 1, "user.name": 1 } }
])
// explain：optimizer 把 status 條件移進第一個 stage（$cursor）
// user.region 條件留在 $lookup 之後，每一筆 completed 訂單都做一次 $lookup

// 快：先從 users 取出 ap-tokyo 使用者的 _id，region 條件換成 orders 自己的 userId 欄位
const tokyoIds = db.users.distinct("_id", { region: "ap-tokyo" })
db.orders.aggregate([
  { $match: { status: "completed", userId: { $in: tokyoIds } } },
  { $sort: { createdAt: -1 } },
  { $limit: 100 },   // 與 $sort 相鄰，optimizer 合併成 top-K
  { $lookup: { from: "users", localField: "userId", foreignField: "_id", as: "user" } },
  { $project: { _id: 1, total: 1, createdAt: 1, "user.name": 1 } }
])
// explain：$lookup 只對 $limit 留下的 100 筆訂單執行
```

兩段回的是同一批訂單。慢的那段的成本不來自 stage 的書寫順序本身：optimizer 會把不依賴 `$lookup` 輸出的條件（`status`）移到 `$lookup` 之前，而依賴 `$lookup` 輸出欄位的條件（`user.region`）移不動，於是 `$lookup` 的執行次數等於 completed 訂單的筆數。快的那段把篩選條件換成 orders 自己的欄位，`$lookup` 的執行次數降到 `$limit` 的 100 筆。

**拿 explain plan**。

```javascript
db.coll.explain("executionStats").aggregate([...])
```

看 `stages[]` 顯示 rewrite 後的 effective pipeline、`executionTimeMillis`、`totalDocsExamined / totalDocsReturned` 比值、是否 `usedDisk`。

**把 `$match` 推到最前**。越早過濾、後續 stage 處理量越小。Optimizer 會把 `$lookup` 之後的 `$match` 裡不依賴 `$lookup` 輸出的條件移到 `$lookup` 之前；讀 `$lookup` 輸出欄位的條件（上面的 `user.region`）移不動，要改寫成 collection 自己的欄位才能提前過濾。

**對 `$match` 欄位建 compound index**。確保 `executionStages` 顯示 `IXSCAN` 而不是 `COLLSCAN`。Compound index 的欄位順序決定它能服務哪些條件：

```javascript
db.orders.createIndex({ status: 1, createdAt: -1 })

// 條件含 index 的第一個欄位 status：走 IXSCAN
db.orders.find({ status: "completed", createdAt: { $gte: ISODate("2026-05-01") } })

// 條件只有 createdAt、缺第一個欄位：這個 index 用不上，走 COLLSCAN
db.orders.find({ createdAt: { $gte: ISODate("2026-05-01") } })
```

**`$sort + $limit` 寫在一起**。Optimizer 才會推 top-K（不需要 full sort、只需要 heap）。單 `$sort` 不限 limit 會做 full sort、容易撞 memory。

**`$project` 早寫**。把不需要的欄位早期 drop、減少後續 stage 處理 doc size。對大 document 特別有效。

**把 hot analytical pipeline 寫成 materialized view**。

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

**sharded cluster 上的 aggregation 路由**。避免在 hot path 用 cross-shard `$lookup` / `$group`、或把這類 query 路由到 analytical replica（用 tag set + read preference）、見 [replica set read preference](../replica-set-read-preference/)。

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

這條退化路徑裡 aggregation 變慢的原因不在 pipeline 的寫法、在 collection 的資料量與形狀隨時間變了。Index 只對排在最前面、且被 optimizer 併進第一個 stage 的 `$match` / `$sort` 有效；後續 stage 要靠 stage 順序、materialized view、schema denormalize 來救。

## 失敗模式

**`$lookup` 在 hot path**：list page 每行去另一 collection 查、p99 隨 page size 線性增。應在 schema design 階段 denormalize、把 read-together 資料 embed 回 aggregate root（見 [schema design pattern](../schema-design-pattern/)）。

**`$sort` 不帶 limit + 沒 index**：全表 in-memory sort、撞 100MB 限制 → OOM 或 disk spill。`allowDiskUse: true` 解 OOM 但 IO 100x 退化。修法是建對應 index 走 IXSCAN sort、或限 limit 走 top-K。

**Sharded cluster cross-shard aggregation**：`$group` 階段所有 partial result 跑到 mongos 合併、mongos memory + CPU 爆。修法是 group key 包含 shard key prefix（讓 group 在 shard 內完成）、或路由到 analytical replica 跑。

**篩選條件依賴 `$lookup` 的輸出**：`$match` 讀的是 `$lookup` 產出的欄位時，optimizer 無法把它移到 `$lookup` 之前，每一筆通過前面條件的 document 都觸發一次 lookup。修法是把條件改寫成 collection 自己的欄位（先查出對方 collection 的 `_id` 再用 `$in`），或把常用來篩選的欄位 embed 進 document。

**Aggregation 把 working set 擠走**：OLTP 的 hot page 被 aggregation 的 cold scan 擠出 cache、整體 query latency 一起退化。修法是 analytical workload 跟 OLTP read 隔離（read preference tag）、或搬走 analytical（見下面 anti-recommendation）。

**`$facet` 滿載**：四個 facet 各跑大 pipeline、共享 100MB 限制立刻爆。修法是拆成獨立 query、不要硬塞 facet。

Anti-recommendation：

- **報表 / BI / analytics workload 跑 MongoDB primary 是反模式**：應該 (a) 設定 analytical secondary + read preference tag (b) 用 `$merge` 寫到 reporting collection (c) 進階用 BI Connector / data lake / 把 analytical workload 整批搬到 [ClickHouse](https://clickhouse.com) / BigQuery
- **「report dashboard 跑爆 primary」典型 anti-pattern**：BI 工具直連 MongoDB primary 跑長 pipeline、cache eviction 把 OLTP working set 擠走、p99 latency 在報表時段集體升。治理路徑是上一條的 analytical secondary、`$merge` reporting collection 或整批搬走 analytical workload
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

同 vendor 的其他文章：

- [schema design pattern](../schema-design-pattern/) — embedded 設計可消除大部分 `$lookup`
- [shard key selection](../shard-key-selection/) — 決定 aggregation 是 shard-local 還是 cross-shard
- [replica set read preference](../replica-set-read-preference/) — aggregation 跑 secondary 的 stale read trade-off
- [connection management and cache layer](../connection-management-and-cache-layer/) — report dashboard 跑爆 primary 時的 cache + read scaling 主路

Migration playbook：analytical workload 大到不能繼續混在 MongoDB → split 出 [→ Cosmos DB MongoDB API + Synapse](/backend/01-database/vendors/cosmosdb/) 或 [→ DynamoDB + Athena/Glue](/backend/01-database/vendors/dynamodb/)（access pattern 重設計）。

主章節：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) 把 aggregation 列為 read-shape 的成本維度；[1.1 高併發資料存取](/backend/01-database/high-concurrency-access/) 處理「OLTP + analytical 同 cluster」的反模式。

## 相關連結

- [MongoDB vendor overview](/backend/01-database/vendors/mongodb/) — MongoDB 的服務定位與 aggregation pipeline 簡介
- [Vendor 深度技術文章方法論](/posts/vendor-deep-article-methodology/)
- 官方：[Aggregation Pipeline](https://www.mongodb.com/docs/manual/aggregation/)、[Optimize Pipelines](https://www.mongodb.com/docs/manual/core/aggregation-pipeline-optimization/)、[$merge](https://www.mongodb.com/docs/manual/reference/operator/aggregation/merge/)
