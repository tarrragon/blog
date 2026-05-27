# MongoDB Shard Key Selection：hashed vs ranged、單 cluster 切 shard vs 多 cluster 切 blast radius

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。
>
> **校準說明**：本 outline 由 case-first audit 補強、新增「單 cluster 切 shard vs 多 cluster 切 blast radius」對照（F2.6 Toyota）跟「partition key 可逆性跨 vendor 對照」（F2.15、MongoDB / DynamoDB / Cosmos DB）。原機制段保留、補強段集中在問題情境、anti-recommendation、邊界整合。

## 問題情境（Production pressure）

- Single replica set 撐到上限：writes 已經把 primary 推到 CPU 90% / disk IO 飽和、working set 超出 RAM；橫向擴充路徑有兩條 — *分 shard*（同 cluster 切 partition）或 *分 cluster*（多 cluster 切 blast radius / ownership）
- 第一次 shard key 設定錯：用 `_id`（單調遞增 ObjectId）→ 所有寫入打最後一個 chunk，sharded cluster 有 4 個 shard 但只有 1 個在工作
- Tenant skew：B2B SaaS 用 `tenantId` 當 shard key，大客戶獨佔一個 chunk，chunk 無法 split，整個 shard 變熱點
- 4.4+ 有 `reshardCollection` 但仍是長時間運算 + 額外磁碟 + 寫入暫停窗口、不是 free lunch
- 讀者徵兆：`mongos` 的 `targeted query / scatter-gather query` 比例失衡、單一 shard CPU 遠高其他 shard、balancer 移 chunk 跟不上寫入速度、`chunkMigrated` 異常頻繁
- Case anchor: primary [9.C38 Toyota Connected](/backend/09-performance-capacity/cases/toyota-connected-mongodb-telematics-iot/) 「20 個 Atlas database 是業務邊界切分」段（單 cluster 切 shard vs 多 cluster 切 blast radius 對照）；needs new case（hot shard 在 e-commerce flash sale / 遊戲開新區的 incident）；側面引用 [BookMyShow ticketing](/backend/09-performance-capacity/cases/bookmyshow-indian-ticketing-platform/) 的 burst pattern 對照「事件流量集中在窄 key 範圍」

## 核心機制（Vendor-specific mechanism）

- Shard key 三特性決定一切：**cardinality**（基數夠不夠分）、**frequency**（值分布是否平均）、**monotonicity**（是否單調遞增）
- Hashed shard key：hash function 把 key 打散、寫入分布均勻、但 range query 變 scatter-gather（每個 shard 都問）
- Ranged shard key：相同 key 相近 → 同 chunk → range query 高效；但單調 key + ranged → 所有寫打最後 chunk
- Compound shard key（5.0+ 是常用做法）：`{ tenantId: 1, _id: "hashed" }` — 先 tenant 隔離、再 hash 避免 tenant 內熱點
- Zone sharding：把特定 chunk 釘到特定 shard（地域 / 合規 / 硬體分層）
- Chunk + balancer：MongoDB 把 collection 切成 64MB（預設）chunk、balancer 在 shard 間搬；chunk 不可 split 的條件 = shard key 在該範圍只有一個值
- `reshardCollection`（4.4+）：透過 temporary collection + chunk 重切 + 雙寫 + cutover，耗時等比於資料量、需額外 ~1.2x 磁碟
- 對應 knowledge card: [database-sharding](/backend/knowledge-cards/database-sharding/)、[hot-partition](/backend/knowledge-cards/hot-partition/)、[partition](/backend/knowledge-cards/partition/)

### 單 cluster 切 shard vs 多 cluster 切 blast radius（F2.6 frame）

跨案合成 frame（本章合成、case 原文沒這個 frame）：橫向擴展不是只有「sharded cluster 一條路」、多 cluster 是另一條路、兩者 trigger 完全不同。

9.C38 Toyota Connected 揭露：

- 18B transactions/月 ÷ 30 天 ÷ 86400 秒 ≈ 7K txn/sec（口徑：月度滾動平均、非瞬時尖峰）
- 單一 MongoDB cluster 完全撐得下這個吞吐
- Toyota 切 20 個 Atlas database **不是吞吐切分**、是 *microservice ownership* + *blast radius* 切分
- 「每個 microservice 擁有自己的 DB、單一 DB 故障不影響其他服務」

兩條路徑的判讀條件不同：

| 路徑                        | Trigger                                                                               | 代價                                                              |
| --------------------------- | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Sharded cluster（分 shard） | 單一 collection 寫入飽和、storage 撐爆單 replica set、access pattern 在同一個資料域內 | aggregation / transaction / `$lookup` 成本全部跳一級              |
| 多 cluster（分 DB）         | 微服務 ownership 邊界、blast radius 隔離、合規 boundary、不同 workload shape 共處風險 | 跨 cluster transaction 不存在、跨 DB join 必須在 application 層做 |

兩者可以同時用：每個 microservice 有獨立 cluster、cluster 內部該分 shard 還是分。寫作時要避免讓讀者以為「sharded cluster 是唯一橫向擴展選項」。

### Partition key 可逆性跨 vendor 對照（F2.15 frame）

| Vendor    | 機制                           | 可逆性                                          | 成本                                   |
| --------- | ------------------------------ | ----------------------------------------------- | -------------------------------------- |
| MongoDB   | Shard key（`shardCollection`） | 4.4+ `reshardCollection` 可改、5.0 前完全不可逆 | 等比資料量、~1.2x 磁碟、雙寫 + cutover |
| DynamoDB  | Partition key                  | 可改（用 backfill 到新 table）                  | 重設計 access pattern、流量切換成本    |
| Cosmos DB | Partition key                  | 不可改（必須 export-recreate-import）           | 全量重灌、雙寫驗證、最大遷移成本       |

三者不在同一光譜：DynamoDB / MongoDB 5.0+ 有遷移路徑、Cosmos DB 必須前期設計到位。寫進文章時必須附 vendor + 版本、避免讓讀者把三家當「partition key 都不可改」。

## 操作流程（Operations）

- Step 1：**横向擴展路徑決策** — 先問「我要解的是 *單一資料域寫入飽和* 還是 *blast radius / ownership*」、選分 shard 或分 cluster；若兩者都要、決定 cluster 邊界後再在 cluster 內分 shard
- Step 2：access pattern audit — 列出所有讀寫 query，標出哪些 query 必須走 single shard（targeted）
- Step 3：候選 key 評估表 — 對每個候選打 cardinality / frequency / monotonicity 三項評分
- Step 4：dry-run 用既有資料採樣，跑 `db.coll.aggregate([{$sample:{size:100000}}, {$group:{_id:"$candidateKey", c:{$sum:1}}}, {$sort:{c:-1}}])` 看分布
- Step 5：`sh.shardCollection("db.coll", { tenantId: 1, _id: "hashed" })`，先在 staging 跑流量重放
- Step 6：監控 `sh.status()` 跟 `db.coll.getShardDistribution()`、確認 chunk 在 shard 間均勻
- Step 7：若已上錯 key — 評估 `reshardCollection`（4.4+）vs application-level 雙寫遷移；對照 DynamoDB（backfill 可改）/ Cosmos DB（必 export-recreate）的 vendor lock-in 紀律
- 驗證點：targeted query 比例 > 90%、單 shard QPS 變異係數 < 20%、balancer migration 速率追上寫入速率
- Rollback boundary：`shardCollection` 是不可逆操作（5.0 前完全不可逆、5.0+ 透過 reshardCollection 可改但需重做）；`reshardCollection` 進入 cutover 後不能回退

## 失敗模式（Failure modes）

- **單調 key 寫熱點**：`_id` (ObjectId) / 時間戳 / 自增 ID 當 ranged shard key → 所有寫進最後 chunk，scale-out 等於零
- **低 cardinality key**：用 `country` 當 shard key，某個 country 佔 80% 流量，chunk 無法繼續 split，該 shard 永久熱
- **Tenant skew**：B2B 場景大客戶獨佔 chunk，且該 tenant 的 chunk 還會繼續長大，balancer 搬不走
- **Scatter-gather 過多**：選了 hashed `_id` 但業務查詢主要是 `tenantId` 範圍查，每筆 query 打所有 shard、p99 隨 shard 數線性退化
- **Resharding 卡在 build 階段**：磁碟不夠（需 1.2x source size）、IO 飽和影響線上 workload、預期 4 小時實際跑 14 小時
- **Zone sharding 規則打架**：合規規則跟負載平衡規則衝突，balancer 無法移動 chunk → 熱點固化
- **誤把多 cluster 當分 shard 解**：blast radius 議題塞到 sharded cluster、單 cluster 故障仍打掉全部 microservice；該分 cluster 的就分 cluster、不是塞到 shard
- **Cluster 擴容時間估計太樂觀**：MongoDB cluster 擴容是天級議題、不是 console 點點就好；F2.5 揭露 Coinbase cluster 擴容要 70 分鐘（口徑：傳統 reactive scaling）、預測性流量必須走 predictive / scheduled scaling、不能只靠 sharded cluster 動態橫向擴展接住 surge
- Anti-recommendation：
  - 寫入 < 5K WPS、storage < 1TB、single replica set 還能撐就不該分 shard；分了之後 aggregation、transaction、`$lookup`、index 成本全部跳一級
  - **shard vs 多 cluster 對照**：吞吐沒撞牆但 blast radius / ownership 是議題、走多 cluster 不是強行分 shard（9.C38 Toyota 7K txn/sec 仍切 20 DB 的 trigger）
  - 跨 case 合成 frame：「不是所有資料都該進同一個 MongoDB cluster」、按 microservice ownership / blast radius / 合規邊界切（F2.6 + F2.18 federated DB frame）

## 容量與觀測（Capacity & observability）

- 關鍵 metric：每 shard QPS / CPU / disk usage 變異係數、targeted vs scatter-gather query 比例、chunk migration rate、balancer round duration；cluster 級別還要看 cluster-to-cluster ownership 邊界
- Mongo command：`sh.status()`、`db.coll.getShardDistribution()`、`db.adminCommand({balancerStatus:1})`、`db.serverStatus().sharding`
- mongos profiler：每 query 帶 `executionStats.executionStages.shards[]`，看是否 single shard
- 回到 [4.20 observability evidence](/backend/04-observability/observability-evidence-package/)：把 shard distribution、targeted ratio、resharding 進度列為 evidence
- 回到 [9.4 saturation discovery](/backend/09-performance-capacity/saturation-discovery/)：hot shard 是 partition-level saturation 的典型例子
- 回到 [9.5 bottleneck localization](/backend/09-performance-capacity/bottleneck-localization/)：當整 cluster CPU 看似只用 25%、實際是 1/4 shard 在 100%

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：
  - [schema design pattern](./schema-design-pattern.md)（document 形狀決定 shard key 選擇空間）
  - [aggregation pipeline optimization](./aggregation-pipeline-optimization.md)（cross-shard aggregation 的 `$out` / `$merge` 限制）
  - [change streams + Kafka](./change-streams-kafka.md)（cluster-wide vs collection-level change stream 在 sharded cluster 的差異）
  - [connection management and cache layer](./connection-management-and-cache-layer.md)（cluster 擴容時間是天級議題、必須跟 predictive scaling / proxy 層配合）
- Migration playbook：避免自管 sharding 走 [→ Atlas](/backend/01-database/vendors/mongodb/migrate-to-atlas/) 用 managed shard tier；徹底重新分區走 [shard expansion + multi-DC](/backend/01-database/vendors/mongodb/shard-expansion-multi-dc/)
- 跟 1.x 互引：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) 把 shard key 列為 capacity 決策；[1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/) 收 resharding 失敗 retrospective

## 寫作前置 checklist

- [ ] Case anchor：primary 9.C38 Toyota（單 cluster vs 多 cluster blast radius）已可用、hot shard incident 強烈需要新建 case（flash sale / 遊戲開新區 / B2B 大客戶獨佔 chunk）；不補的話故障演練段會缺證據
- [ ] Knowledge card 雙引用：database-sharding + hot-partition 都已存在、partition 卡可第三引用
- [ ] Sibling 對比清楚：跟 DynamoDB partition key、Cosmos DB partition key 比照——本文是 MongoDB-specific（hashed/ranged/compound + balancer 自動搬 chunk + 4.4+ reshardCollection）、DynamoDB 是 hash-only + adaptive capacity + backfill 可改、Cosmos DB 是 logical partition + RU bound + 不可改
- [ ] Fact vs derive 分層：「Toyota 切 20 DB 是 blast radius 切分」是 case 明示事實（口徑：18B txn/月、月度滾動平均）；「7K txn/sec 是月度平均算出」是從 case 數字推算、明示算式；「單 cluster vs 多 cluster 兩條路徑」是合成 frame、本章明示
- [ ] Scope warning：MongoDB cluster 擴容 70 分鐘是 Coinbase（9.C36）特定環境數字、非 MongoDB 普遍承諾；引用時帶口徑
- [ ] 預估寫作長度：300-360 行（核心議題 + 補強段、cardinality / frequency / monotonicity + 單/多 cluster + 可逆性對照三軸）
