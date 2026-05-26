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

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[ru-cost-model-sizing](./ru-cost-model-sizing.md)（partition skew 直接影響 RU sizing）、[consistency-levels-engineering](./consistency-levels-engineering.md)（partition 失衡時即使設 Strong 也看到 throttle）、[multi-region-write-conflict](./multi-region-write-conflict.md)（partition key 影響 conflict 分布）
- 跟 DynamoDB 對比：[DynamoDB partition key](/backend/01-database/vendors/dynamodb/)（若該頁有 deep article）、回 hot-partition card
- Migration playbook 連結：MongoDB → Cosmos DB MongoDB API 時、shard key 對應 partition key、轉換規則進 [mongodb-api-vs-sql-api](./mongodb-api-vs-sql-api.md)
- 跟 1.x 章節：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)
- Anti-recommendation：小流量（< 1000 RU/s 預期）不必過度設計 synthetic key、Cosmos DB autoscale + 簡單 partition key 即可

## 寫作前置 checklist

- [ ] case anchor 確認：9.C11 Minecraft Earth（synthetic key 主案例）+ DynamoDB hot partition 案例當對照
- [ ] knowledge card 雙引用：hot-partition、database-sharding
- [ ] sibling 對比：DynamoDB partition key + adaptive capacity、MongoDB shard key
- [ ] 預估寫作長度：260-320 行（3 種設計模式 + 5 失敗模式 + DynamoDB 對比）
