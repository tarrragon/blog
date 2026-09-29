---
title: "MongoDB Shard Key Selection：hashed vs ranged、單 cluster 切 shard vs 多 cluster 切 blast radius"
date: 2026-05-27
description: "MongoDB sharded cluster shard key 選型（hashed / ranged / compound）、單 cluster 分 shard vs 多 cluster 分 blast radius 對照、跟 DynamoDB / Cosmos DB partition key 可逆性的跨 vendor 紀律"
weight: 31
tags: ["backend", "database", "mongodb", "sharding", "shard-key", "deep-article"]
---

這篇整理 MongoDB sharded cluster 的 shard key 選型：cardinality、frequency、monotonicity 三個特性怎麼決定寫入分布，hashed、ranged、compound shard key 各自的取捨，橫向擴展該在單一 cluster 內切 shard 還是切成多個 cluster，以及選錯 shard key 之後 `reshardCollection` 能補救到什麼程度。Sharding 的基本介紹在 [MongoDB vendor overview](/backend/01-database/vendors/mongodb/)。

Shard key 在 5.0 之前設定之後不能更換；5.0 起可以用 `reshardCollection` 更換，而重切的耗時與資料量成正比、需要額外磁碟，結束前還有一段寫入暫停窗口，所以 shard key 仍是 sharded cluster 上線時最難回頭的決策。

> **MongoDB 適用度前置判讀**：進到 shard key 設計前先確認 workload 在 MongoDB 適用區（document shape 主導 / contract layer 該放哪 / 跨雲 hedging 是否需要）— 詳見 [schema-design-pattern 開頭 3 軸前置判讀](../schema-design-pattern/#mongodb-適用度前置判讀)、本篇不重複展開。Sharded cluster 是 *已選 MongoDB 後* 的容量決策、不是 vendor 選型決策。

## 問題情境：橫向擴展不是只有 sharded cluster 一條路

典型觸發場景：single replica set 撐到上限、writes 已經把 primary 推到 CPU 90% / disk IO 飽和、working set 超出 RAM。直覺的做法是「分 shard」，另一條路徑是「分 cluster」，兩者的 trigger 不同：

- **單 cluster 切 shard**：解的是 *單一資料域寫入飽和*、collection 大到單一 replica set 承接不了它的寫入量
- **多 cluster 切 DB**：解的是 *[blast radius](/backend/knowledge-cards/blast-radius/) / ownership / 合規邊界*、不一定是吞吐問題

混淆兩者的後果：吞吐沒撞牆但 blast radius 是議題、強行分 shard → aggregation / transaction / `$lookup` 成本全部跳一級、業務 ownership 仍混在一起。或反過來：吞吐撞牆但選了分 cluster → 跨 cluster transaction 不存在、單一 collection 跨多 cluster 要在 application 層拼。

讀者徵兆：

- `mongos` 的 `targeted query / scatter-gather query` 比例失衡
- 單一 shard CPU 遠高其他 shard、balancer 移 chunk 跟不上寫入速度
- `chunkMigrated` 異常頻繁、`sh.status()` 顯示 chunk 分布偏斜
- 微服務 ownership 跟 collection 邊界不對齊、某 microservice 故障打到其他服務

Case anchor：[9.C38 Toyota Connected](/backend/09-performance-capacity/cases/toyota-connected-mongodb-telematics-iot/) 揭露「20 個 Atlas database 是業務邊界切分、不是吞吐切分」（單 cluster vs 多 cluster 對照）。

## 核心機制：shard key、chunk、balancer

Shard key 三特性決定 sharded cluster 行為：

- **Cardinality（基數）**：shard key 的不同值數量。`status: "active" | "inactive"` 只有兩個值、cardinality = 2、不能分到多 chunk
- **Frequency（頻率分布）**：值的分布是否平均。`country` 在全球流量中通常一兩個國家佔 80%
- **Monotonicity（單調性）**：值是否單調遞增。`_id`（ObjectId）/ 時間戳 / 自增 ID 都是單調

Shard key 的類型決定寫入怎麼分布、range query 能不能只打一個 shard：

- **Hashed shard key**：hash function 把 key 打散、寫入分布均勻、但 range query 變 scatter-gather（每個 shard 都問）
- **Ranged shard key**：相同 key 相近 → 同 chunk → range query 高效；但單調 key + ranged → 所有寫打最後 chunk
- **Compound shard key**（5.0+ 是常用做法、對應 [Composite Partition Key](/backend/knowledge-cards/composite-partition-key/) 的 MongoDB 實作）：例如 `{ tenantId: 1, _id: "hashed" }` — 先 tenant 隔離、再 hash 避免 tenant 內熱點
- **Zone sharding**：把特定 chunk 釘到特定 shard（地域 / 合規 / 硬體分層）

Chunk 是 MongoDB 在 collection 上劃出的邏輯區塊，6.0 起預設大小 128MB（更早的版本預設 64MB）。Balancer 在 shard 間搬 chunk 達成均衡。**Chunk 不可 split 的條件**是 shard key 在該範圍只有一個值（low cardinality / 大 tenant 獨佔範圍）— chunk split 不了、balancer 也搬不開。

`reshardCollection`（5.0+）：透過 temporary collection + chunk 重切 + 雙寫 + cutover、耗時等比於資料量、需額外 ~1.2x 磁碟。是「設計錯了還有補救機會」但不是 free lunch。

對應 knowledge card：[database-sharding](/backend/knowledge-cards/database-sharding/)、[hot-partition](/backend/knowledge-cards/hot-partition/)、[partition](/backend/knowledge-cards/partition/)。

### 單 cluster 切 shard vs 多 cluster 切 blast radius

橫向擴展有兩條路：在一個 sharded cluster 內加 shard，或把資料拆到多個 cluster。下面的事實取自 Toyota Connected 案例；「單 cluster vs 多 cluster」這個對照是從案例事實整理出來的，案例原文沒有這樣分：

- 18B transactions / 月 ÷ 30 天 ÷ 86400 秒 ≈ 7K txn/sec（口徑：月度滾動平均、非瞬時尖峰）
- 單一 MongoDB cluster 完全撐得下這個吞吐
- Toyota 切 20 個 Atlas database **不是吞吐切分**、是 *microservice ownership* + *blast radius* 切分
- 「每個 microservice 擁有自己的 DB、單一 DB 故障不影響其他服務」

兩條路徑的判讀條件不同：

| 路徑                        | Trigger                                                                               | 代價                                                              |
| --------------------------- | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Sharded cluster（分 shard） | 單一 collection 寫入飽和、storage 撐爆單 replica set、access pattern 在同一個資料域內 | aggregation / transaction / `$lookup` 成本全部跳一級              |
| 多 cluster（分 DB）         | 微服務 ownership 邊界、blast radius 隔離、合規 boundary、不同 workload shape 共處風險 | 跨 cluster transaction 不存在、跨 DB join 必須在 application 層做 |

兩者可以同時用：先按 microservice ownership 切出各自的 cluster，每個 cluster 內部再依寫入量決定要不要分 shard。

### Partition key 可逆性跨 vendor 對照

MongoDB、DynamoDB、Cosmos DB 三家在其他面向的完整對照在 [NoSQL Vendor Selection 的〈MongoDB / DynamoDB / Cosmos DB 的選型對比〉](/backend/01-database/vendors/db3-vendor-selection/#mongodb--dynamodb--cosmos-db-的選型對比)與它的[〈軸的延伸子段〉](/backend/01-database/vendors/db3-vendor-selection/#軸的延伸子段)；本段只談 partition key 能不能改，以及 `reshardCollection` 對 MongoDB shard key 設計的影響。

三家的 partition key 能不能改、改的代價是什麼：

| Vendor    | 機制                           | 可逆性                                                                                     | 成本                                   |
| --------- | ------------------------------ | ------------------------------------------------------------------------------------------ | -------------------------------------- |
| MongoDB   | Shard key（`shardCollection`） | 5.0+ `reshardCollection` 可改；4.4 只能用 `refineCollectionShardKey` 在既有 key 後面加欄位 | 等比資料量、~1.2x 磁碟、雙寫 + cutover |
| DynamoDB  | Partition key                  | 可改（用 backfill 到新 table）                                                             | 重設計 access pattern、流量切換成本    |
| Cosmos DB | Partition key                  | 不可改（必須 export-recreate-import）                                                      | 全量重灌、雙寫驗證、最大遷移成本       |

寫進設計文件時必須附 vendor + 版本、避免讓讀者把三家當「partition key 都不可改」、也避免把 MongoDB 5.0+ 的 `reshardCollection` 當「便宜遷移」。

## 操作流程

**選橫向擴展路徑**。先問「我要解的是 *單一資料域寫入飽和* 還是 *blast radius / ownership*」、選分 shard 或分 cluster。若兩者都要、決定 cluster 邊界後再在 cluster 內分 shard。

**access pattern audit**。列出所有讀寫 query、標出哪些 query 必須走 single shard（targeted），哪些 query 不在意 scatter-gather。

**候選 key 評估表**。對每個候選打 cardinality / frequency / monotonicity 三項評分：

| 候選 key                         | Cardinality  | Frequency | Monotonicity | 適合？         |
| -------------------------------- | ------------ | --------- | ------------ | -------------- |
| `_id`（ObjectId）                | 極高         | 均勻      | 單調         | 否（單調寫熱） |
| `tenantId`                       | 中           | 偏斜      | 否           | 視 tenant 分布 |
| `{ tenantId: 1, _id: "hashed" }` | 高           | 均勻      | 否           | 通常合適       |
| `country`                        | 極低（~200） | 嚴重偏斜  | 否           | 否             |

**dry-run 採樣**。對既有資料採樣，看候選 key 的值分布：

```javascript
db.coll.aggregate([
  { $sample: { size: 100000 } },                       // 隨機取 10 萬筆 document
  { $group: { _id: "$candidateKey", c: { $sum: 1 } } }, // 每個 key value 各有幾筆
  { $sort: { c: -1 } }                                 // 最多的排前面
])
```

確認沒有單一 key value 佔掉超過 20% 的樣本。採樣量的是 document 分布；流量分布要另外從 profiler 或 access log 算。

**shardCollection**。

```javascript
sh.enableSharding("shop")
sh.shardCollection("shop.orders", { tenantId: 1, _id: "hashed" })
```

先在 staging 跑流量重放、確認 chunk 分布平均、targeted query 比例 > 90%。

**監控 chunk 分布與 balancer**。

```javascript
sh.status()                              // 看 cluster 狀態
db.orders.getShardDistribution()         // 看 chunk 分布
db.adminCommand({ balancerStatus: 1 })   // 看 balancer 狀態
```

**若已上錯 key**。評估 `reshardCollection`（5.0+）vs application-level 雙寫遷移：

```javascript
db.adminCommand({
  reshardCollection: "shop.orders",
  key: { tenantId: 1, region: 1, _id: "hashed" }
})
```

`reshardCollection` 進入 cutover 後不能回退、必須 dry-run 估完時間 + 磁碟 + IO 影響再上。

驗證點：targeted query 比例 > 90%、單 shard QPS 變異係數 < 20%、balancer migration 速率追上寫入速率。

Rollback boundary：`shardCollection` 是不可逆操作（5.0 前完全不可逆、5.0+ 透過 reshardCollection 可改但需重做）；`reshardCollection` 進入 cutover 後不能回退。

## 失敗模式

**單調 key 寫熱點**：`_id`（ObjectId）/ 時間戳 / 自增 ID 當 ranged shard key → 所有寫進最後 chunk，scale-out 等於零。修法是 hashed key 或 compound key 把單調軸拌散。

**低 cardinality key**：用 `country` 當 shard key、某個 country 佔 80% 流量、chunk 無法繼續 split、該 shard 永久熱。修法是加一個高 cardinality 軸（compound key）讓 chunk 可繼續分。

**Tenant skew**：B2B 場景大客戶獨佔 chunk、且該 tenant 的 chunk 還會繼續長大、balancer 搬不走。修法 compound key `{ tenantId: 1, _id: "hashed" }` — tenant 隔離但 tenant 內 hash 散開。

**Scatter-gather 過多**：選了 hashed `_id` 但業務查詢主要是 `tenantId` 範圍查、每筆 query 打所有 shard、p99 隨 shard 數線性退化。修法 compound key 把常用查詢軸放第一位、targeted query 才能對 single shard。

**Resharding 卡在 build 階段**：磁碟不夠（需 1.2x source size）、IO 飽和影響線上 workload、預期 4 小時實際跑 14 小時。修法是先擴磁碟、staging 跑 dry-run 量實際耗時、production 在低峰期啟動。

**Zone sharding 規則打架**：合規規則（資料必須留在某 region）跟負載平衡規則衝突、balancer 無法移動 chunk → 熱點固化。修法是 zone 規則 vs balancer 設計階段就劃清、不要事後加 zone。

**把該分 cluster 的問題交給分 shard 解**：blast radius 議題塞到 sharded cluster、單 cluster 故障仍打掉全部 microservice。該分 cluster 的就分 cluster、不是塞到 shard。9.C38 Toyota 揭露：7K txn/sec 仍切 20 DB 的 trigger 是 microservice ownership、不是吞吐。

**Cluster 擴容時間估計太樂觀**：MongoDB cluster 擴容不是 console 按下去就立刻生效。9.C36 Coinbase 揭露 cluster 擴容要 70 分鐘（口徑：Coinbase 特定環境 cluster tier / 資料量 / Atlas API 條件下、reactive scaling 起點到完成、非 MongoDB 普遍承諾）；預測性流量必須走 predictive / scheduled scaling、不能只靠 sharded cluster 動態橫向擴展接住 surge（見 [connection management and cache layer](../connection-management-and-cache-layer/)）。

Anti-recommendation：

- 寫入 < 5K WPS、storage < 1TB、single replica set 還能撐就不該分 shard；分了之後 aggregation、transaction、`$lookup`、index 成本全部跳一級
- **shard vs 多 cluster 對照**：吞吐沒撞牆但 blast radius / ownership 是議題、走多 cluster 不是強行分 shard（9.C38 Toyota 7K txn/sec 仍切 20 DB 的 trigger）
- 資料按 microservice ownership / blast radius / 合規邊界分到不同的 MongoDB cluster

## 容量與觀測

關鍵 metric：

- **Shard 分布健康**：每 shard QPS / CPU / disk usage 變異係數（< 20% 合理）
- **Query 路由**：targeted vs scatter-gather query 比例（targeted > 90% 合理）
- **Balancer 健康**：chunk migration rate、balancer round duration
- **Cluster 邊界**：cluster-to-cluster ownership 邊界、跨 cluster query 比例

Mongo command：

- `sh.status()`：cluster 整體狀態
- `db.coll.getShardDistribution()`：collection 在各 shard 的分布
- `db.adminCommand({balancerStatus:1})`：balancer 狀態
- `db.serverStatus().sharding`：sharding metric

透過 `mongos` 執行 `explain("executionStats")`：輸出的 `executionStats.executionStages.shards[]` 列出這個 query 打到哪些 shard，`queryPlanner.winningPlan.stage` 是 `SINGLE_SHARD` 就是 targeted query。

回到 [4.20 observability evidence](/backend/04-observability/observability-evidence-package/)：把 shard distribution、targeted ratio、resharding 進度列為 evidence 三件套。

回到 [9.4 saturation discovery](/backend/09-performance-capacity/saturation-discovery/)：hot shard 是 partition-level saturation 的典型例子。

回到 [9.5 bottleneck localization](/backend/09-performance-capacity/bottleneck-localization/)：當整 cluster CPU 看似只用 25%、實際是 1/4 shard 在 100%。

## 邊界與整合

同 vendor 的其他文章：

- [schema design pattern](../schema-design-pattern/) — document 形狀決定 shard key 選擇空間
- [aggregation pipeline optimization](../aggregation-pipeline-optimization/) — cross-shard aggregation 的 `$out` / `$merge` 限制
- [change streams + Kafka](../change-streams-kafka/) — cluster-wide vs collection-level change stream 在 sharded cluster 的差異
- [connection management and cache layer](../connection-management-and-cache-layer/) — cluster 擴容要數十分鐘（Coinbase 案例約 70 分鐘），必須跟 predictive scaling / proxy 層配合

Migration playbook：

- 避免自管 sharding 走 [→ Atlas](/backend/01-database/vendors/mongodb/migrate-to-atlas/) 用 managed shard tier
- 徹底重新分區走 [shard expansion + multi-DC](/backend/01-database/vendors/mongodb/shard-expansion-multi-dc/)

主章節：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) 把 shard key 列為 capacity 決策；[1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/) 收 resharding 失敗 retrospective。

跨 vendor 對照：[DynamoDB vendor page](/backend/01-database/vendors/dynamodb/)（partition key + adaptive capacity + backfill 可改）、[Cosmos DB vendor page](/backend/01-database/vendors/cosmosdb/)（partition key 不可改）。

## 相關連結

- [MongoDB vendor overview](/backend/01-database/vendors/mongodb/) — MongoDB 的服務定位與 sharding 簡介
- [Vendor 深度技術文章方法論](/posts/vendor-deep-article-methodology/)
- [9.C38 Toyota Connected](/backend/09-performance-capacity/cases/toyota-connected-mongodb-telematics-iot/) — 20 個 Atlas DB 切 blast radius
- [9.C36 Coinbase](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/) — cluster 擴容 70 分鐘特定環境數字
- 官方：[MongoDB Sharding](https://www.mongodb.com/docs/manual/sharding/)、[Choosing a Shard Key](https://www.mongodb.com/docs/manual/core/sharding-shard-key/)、[Resharding](https://www.mongodb.com/docs/manual/core/sharding-reshard-a-collection/)
