# MongoDB Shard Key Selection：hashed vs ranged、hot partition 與 resharding 痛點

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- Single replica set 撐到上限：writes 已經把 primary 推到 CPU 90% / disk IO 飽和、working set 超出 RAM；唯一橫向擴充路徑是 sharded cluster
- 第一次 shard key 設定錯：用 `_id`（單調遞增 ObjectId）→ 所有寫入打最後一個 chunk，sharded cluster 有 4 個 shard 但只有 1 個在工作
- Tenant skew：B2B SaaS 用 `tenantId` 當 shard key，大客戶獨佔一個 chunk，chunk 無法 split，整個 shard 變熱點
- 4.4+ 有 `reshardCollection` 但仍是長時間運算 + 額外磁碟 + 寫入暫停窗口、不是 free lunch
- 讀者徵兆：`mongos` 的 `targeted query / scatter-gather query` 比例失衡、單一 shard CPU 遠高其他 shard、balancer 移 chunk 跟不上寫入速度、`chunkMigrated` 異常頻繁
- Case anchor: needs new case（hot shard 在 e-commerce flash sale / 遊戲開新區的 incident）；側面引用 [BookMyShow ticketing](/backend/09-performance-capacity/cases/bookmyshow-indian-ticketing-platform/) 的 burst pattern 對照「事件流量集中在窄 key 範圍」

## 核心機制（Vendor-specific mechanism）

- Shard key 三特性決定一切：**cardinality**（基數夠不夠分）、**frequency**（值分布是否平均）、**monotonicity**（是否單調遞增）
- Hashed shard key：hash function 把 key 打散、寫入分布均勻、但 range query 變 scatter-gather（每個 shard 都問）
- Ranged shard key：相同 key 相近 → 同 chunk → range query 高效；但單調 key + ranged → 所有寫打最後 chunk
- Compound shard key（5.0+ 是常用做法）：`{ tenantId: 1, _id: "hashed" }` — 先 tenant 隔離、再 hash 避免 tenant 內熱點
- Zone sharding：把特定 chunk 釘到特定 shard（地域 / 合規 / 硬體分層）
- Chunk + balancer：MongoDB 把 collection 切成 64MB（預設）chunk、balancer 在 shard 間搬；chunk 不可 split 的條件 = shard key 在該範圍只有一個值
- `reshardCollection`（4.4+）：透過 temporary collection + chunk 重切 + 雙寫 + cutover，耗時等比於資料量、需額外 ~1.2x 磁碟
- 對應 knowledge card: [database-sharding](/backend/knowledge-cards/database-sharding/)、[hot-partition](/backend/knowledge-cards/hot-partition/)、[partition](/backend/knowledge-cards/partition/)

## 操作流程（Operations）

- Step 1：access pattern audit — 列出所有讀寫 query，標出哪些 query 必須走 single shard（targeted）
- Step 2：候選 key 評估表 — 對每個候選打 cardinality / frequency / monotonicity 三項評分
- Step 3：dry-run 用既有資料採樣，跑 `db.coll.aggregate([{$sample:{size:100000}}, {$group:{_id:"$candidateKey", c:{$sum:1}}}, {$sort:{c:-1}}])` 看分布
- Step 4：`sh.shardCollection("db.coll", { tenantId: 1, _id: "hashed" })`，先在 staging 跑流量重放
- Step 5：監控 `sh.status()` 跟 `db.coll.getShardDistribution()`、確認 chunk 在 shard 間均勻
- Step 6：若已上錯 key — 評估 `reshardCollection` vs application-level 雙寫遷移
- 驗證點：targeted query 比例 > 90%、單 shard QPS 變異係數 < 20%、balancer migration 速率追上寫入速率
- Rollback boundary：`shardCollection` 是不可逆操作（5.0 前完全不可逆、5.0+ 透過 reshardCollection 可改但需重做）；`reshardCollection` 進入 cutover 後不能回退

## 失敗模式（Failure modes）

- **單調 key 寫熱點**：`_id` (ObjectId) / 時間戳 / 自增 ID 當 ranged shard key → 所有寫進最後 chunk，scale-out 等於零
- **低 cardinality key**：用 `country` 當 shard key，某個 country 佔 80% 流量，chunk 無法繼續 split，該 shard 永久熱
- **Tenant skew**：B2B 場景大客戶獨佔 chunk，且該 tenant 的 chunk 還會繼續長大，balancer 搬不走
- **Scatter-gather 過多**：選了 hashed `_id` 但業務查詢主要是 `tenantId` 範圍查，每筆 query 打所有 shard、p99 隨 shard 數線性退化
- **Resharding 卡在 build 階段**：磁碟不夠（需 1.2x source size）、IO 飽和影響線上 workload、預期 4 小時實際跑 14 小時
- **Zone sharding 規則打架**：合規規則跟負載平衡規則衝突，balancer 無法移動 chunk → 熱點固化
- Anti-recommendation：寫入 < 5K WPS、storage < 1TB、single replica set 還能撐就不該分 shard；分了之後 aggregation、transaction、$lookup、index 成本全部跳一級

## 容量與觀測（Capacity & observability）

- 關鍵 metric：每 shard QPS / CPU / disk usage 變異係數、targeted vs scatter-gather query 比例、chunk migration rate、balancer round duration
- Mongo command：`sh.status()`、`db.coll.getShardDistribution()`、`db.adminCommand({balancerStatus:1})`、`db.serverStatus().sharding`
- mongos profiler：每 query 帶 `executionStats.executionStages.shards[]`，看是否 single shard
- 回到 [4.20 observability evidence](/backend/04-observability/observability-evidence-package/)：把 shard distribution、targeted ratio、resharding 進度列為 evidence
- 回到 [9.4 saturation discovery](/backend/09-performance-capacity/saturation-discovery/)：hot shard 是 partition-level saturation 的典型例子
- 回到 [9.5 bottleneck localization](/backend/09-performance-capacity/bottleneck-localization/)：當整 cluster CPU 看似只用 25%、實際是 1/4 shard 在 100%

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[schema design pattern](./schema-design-pattern.md)（document 形狀決定 shard key 選擇空間）、[aggregation pipeline optimization](./aggregation-pipeline-optimization.md)（cross-shard aggregation 的 `$out` / `$merge` 限制）、[change streams + Kafka](./change-streams-kafka.md)（cluster-wide vs collection-level change stream 在 sharded cluster 的差異）
- Migration playbook：避免自管 sharding 走 [→ Atlas](/backend/01-database/vendors/mongodb/migrate-to-atlas/) 用 managed shard tier；徹底重新分區走 [shard expansion + multi-DC](/backend/01-database/vendors/mongodb/shard-expansion-multi-dc/)
- 跟 1.x 互引：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) 把 shard key 列為 capacity 決策；[1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/) 收 resharding 失敗 retrospective

## 寫作前置 checklist

- [ ] Case anchor：hot shard incident 強烈需要新建 case（flash sale / 遊戲開新區 / B2B 大客戶獨佔 chunk）；不補的話故障演練段會缺證據
- [ ] Knowledge card 雙引用：database-sharding + hot-partition 都已存在、partition 卡可第三引用
- [ ] Sibling 對比清楚：跟 DynamoDB partition key、Cosmos DB partition key 比照——本文是 MongoDB-specific（hashed/ranged/compound + balancer 自動搬 chunk）、DynamoDB 是 hash-only + 不自動 rebalance、Cosmos DB 是 logical partition + RU bound
- [ ] 預估寫作長度：280-340 行（核心議題、需要 cardinality / frequency / monotonicity 三軸 + resharding 操作細節）
