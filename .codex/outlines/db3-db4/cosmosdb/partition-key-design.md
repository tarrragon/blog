# Cosmos DB Partition Key Design：synthetic / composite / hierarchical + 跟 DynamoDB 對比

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：Cosmos DB logical partition 上限 10,000 RU/s + 20GB storage、partition key 選錯一旦上 production 改不了（要 export-recreate-import）；Black Friday / 上線日 / VIP 用戶都會把流量壓在少數 partition、p99 latency 從 50ms 飆到 5s
- 讀者徵兆：「Cosmos DB throughput 我設了 10000 RU、但寫入只有 2000 就 throttle」「user_id 當 partition key 結果 VIP 用戶全卡在一個 partition」「Hierarchical partition key 是 2023 後才有的、跟 composite 差在哪」
- 真實壓力：遊戲玩家位置（同伺服器集中同 partition）、IoT 裝置遙測（單一裝置高頻寫入）、SaaS 多租戶（大客戶 vs 小客戶不均）
- Case anchor: [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) — synthetic partition key 強制分散；對照 [9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) Black Friday 流量分散

## 核心機制（Vendor-specific mechanism）

- Partition 模型：每個 container 有 N 個 *physical partition*、每個 physical 上有多個 *logical partition*（同 partition key value 落到同 logical partition）
- Logical partition 上限：10,000 RU/s + 20GB；達 limit 後即使 container 還有總 RU、單一 partition key 一樣 throttle
- Partition key 設計三種模式：
  - **Synthetic**：`{userId}_{random_0_to_99}`、把單一 user 的寫入散到 100 個 logical partition；副作用是 read 需 fan-out 100 partition
  - **Composite**：`{tenantId}_{deviceId}`、用兩個欄位合成、避免單一 high-cardinality 欄位 hot
  - **Hierarchical**（2023+）：原生支援多層 key（最多 3 層、如 `tenantId / deviceId / sessionId`）、不用手動合成；query 可指定前綴做 partition scope query
- 跟 [hot-partition](/backend/knowledge-cards/hot-partition/) 卡片的關係：Cosmos DB 是該卡的主要 vendor 範例
- 跟 DynamoDB partition key 對比：
  - DynamoDB：partition key + optional sort key、無 hierarchical key、adaptive capacity 自動補 hot partition（部分減緩、不完全解決）
  - Cosmos DB：hierarchical key 是原生功能、不靠 adaptive；單 logical partition 限制嚴格、必須前期設計
- 對應 knowledge card：[hot-partition](/backend/knowledge-cards/hot-partition/)、[database-sharding](/backend/knowledge-cards/database-sharding/)

### Partition / shard key 可逆性跨 vendor 對照（F2.15 本章合成）

| Vendor    | 可逆性       | 機制                                          | 成本             |
| --------- | ------------ | --------------------------------------------- | ---------------- |
| MongoDB   | 可改（4.4+） | `reshardCollection`、線上完成、cluster 內搬移 | 高、但 in-place  |
| DynamoDB  | 可改         | 建新 table、backfill + dual-write 切換        | 中、要 backfill  |
| Cosmos DB | 不可改       | 必須 export → recreate container → import     | 最高、需停機窗口 |

**本章合成 frame**：三 vendor 的「partition / shard key 可逆性」不在同一光譜、Cosmos DB 最嚴格 — F2.15 跨 case 合成、9.C11 Minecraft Earth 沒直接揭露此對比、是從 outline knowledge 跟 MongoDB shard-key-selection 對照得出。寫稿時必須明示「Cosmos DB partition key 不可改是設計選型的硬約束、不是『先選錯再改』可承擔的風險」。

## 操作流程（Operations）

- 設定 partition key：建 container 時指定、*無法事後修改*

  ```bash
  az cosmosdb sql container create \
    --partition-key-path "/userId" \
    --partition-key-version 2
  ```

- Hierarchical key（C# SDK 範例 / REST API）：建 container 時用 `partitionKey.paths = ["/tenantId", "/deviceId"]`、`kind = "MultiHash"`
- Synthetic key 寫入：app 端 hash userId + random suffix、寫入時組合成 partition key
- 查 partition 分布：portal Metrics > Storage by partition key、看分布是否均勻
- 驗證點：
  - 每個 logical partition 的 RU 消耗 < 80% limit
  - 單一 partition 的 storage < 16GB（留 buffer）
  - p99 latency 在 hot partition 不退化
- Rollback boundary：partition key 選錯只能 export → recreate container with new partition key → import；無 in-place migration

## 失敗模式（Failure modes）

- user_id 直接當 partition key：高活躍用戶（VIP / bot / 大客戶）超過 10000 RU/s、全 container 被 throttle；徵兆是 `429 TooManyRequests` 集中在少數 partition、整體 RU 利用率才 30%
- 時間當 partition key：`/createdDate` 或 `/yyyyMM`、新資料全寫入最新 partition、舊 partition 冷掉浪費 — write hot + read 不均
- Synthetic key 沒考慮 read 路徑：寫入散開但 read 必須 fan-out 100 partition、單一 query RU 暴漲 100x
- Hierarchical key 設計順序顛倒：把 high-cardinality 放第一層、prefix query 變得無意義
- 不監控 partition 分布：partition skew 累積幾個月、直到事故才發現
- Container 之間 partition 設計不一致：跨 container query 需要 fan-out、cross-partition query 成本爆炸

## 容量與觀測（Capacity & observability）

- 必看 metric：`PhysicalPartitionThroughputInfo`、`NormalizedRUConsumption` per partition、`StorageDistributionPerPartition`
- Hot partition 偵測：portal Insights > Top contributors > Partition key range
- 容量估算公式：peak RU per partition × partition 數 + 預留 buffer（一般 30%）= total RU/s
- 回到 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)：把 partition skew 當 saturation signal
- Alert：單 partition RU 利用 > 80% 持續 5 min；429 error rate 突增

### Latency budget 拆解：vendor SLA vs end-to-end 實測（F2.13）

- 9.C21 ASOS 觀察「48ms 平均響應 = 全球分散下 Cosmos DB 的代表性數字」段揭露：48ms 包含 *網路 + DB + 應用層*、DB 本身可能只佔 5-10ms、其他是網路與應用層
- 操作上要把 end-to-end latency 拆 budget：
  - DB 端 latency（vendor SLA、p99 < 10ms 地區內讀、9.C11 揭露）
  - 跨 region replication latency（multi-region read 從就近 region 拿、不會跨洲、但 cross-region write 不同）
  - 應用層 latency（serialize / business logic / HTTP overhead）
  - 客戶端網路 latency（mobile / 跨洲）
- 寫稿時不能把 vendor 廣告的 5-10ms p99 當「使用者體驗」、要明示「48ms 是 9.C21 ASOS 案例的 end-to-end 觀察、Cosmos DB 自身可能只佔 5-10ms（case 揭露的拆解推論）」
- 跟 partition skew 的關係：partition 失衡時即使 vendor 端 SLA 達標、實測 p99 仍會被 hot partition 拉高（單一 partition 的 RU consumption 飽和 → 429 retry → 應用層 latency 暴漲）

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[ru-cost-model-sizing](./ru-cost-model-sizing.md)（partition skew 直接影響 RU sizing）、[consistency-levels-engineering](./consistency-levels-engineering.md)（partition 失衡時即使設 Strong 也看到 throttle）、[multi-region-write-conflict](./multi-region-write-conflict.md)（partition key 影響 conflict 分布）
- 跟 DynamoDB 對比：[DynamoDB partition key](/backend/01-database/vendors/dynamodb/)（若該頁有 deep article）、回 hot-partition card
- Migration playbook 連結：MongoDB → Cosmos DB MongoDB API 時、shard key 對應 partition key、轉換規則進 [mongodb-api-vs-sql-api](./mongodb-api-vs-sql-api.md)
- 跟 1.x 章節：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)
- Anti-recommendation：小流量（< 1000 RU/s 預期）不必過度設計 synthetic key、Cosmos DB autoscale + 簡單 partition key 即可

## 寫作前置 checklist

- [ ] case anchor 確認：9.C11 Minecraft Earth（synthetic key 主案例、平台特性「partition 動態分裂：透明」段）+ 9.C21 ASOS（latency budget 拆解、「48ms 平均響應」段）+ DynamoDB hot partition 案例當對照
- [ ] knowledge card 雙引用：hot-partition、database-sharding
- [ ] sibling 對比：DynamoDB partition key + adaptive capacity、MongoDB shard key
- [ ] fact vs derive 分層：
  - 9.C11「partition 動態分裂：透明」是 case fact、synthetic partition key 設計細節是 outline knowledge（case 沒揭露具體 schema）
  - 9.C21「48ms 平均響應」是 case fact、「DB 本身 5-10ms / 其他是網路與應用層」是 case 判讀層拆解、不是 fact
  - 跨 vendor 可逆性對照表是本章合成 frame、case 沒直接揭露此對比
- [ ] 預估寫作長度：280-340 行（3 種設計模式 + 5 失敗模式 + DynamoDB 對比 + latency budget 段 + 可逆性對照）
