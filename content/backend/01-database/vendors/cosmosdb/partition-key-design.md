---
title: "Cosmos DB Partition Key Design：synthetic / composite / hierarchical + 不可逆性硬約束"
date: 2026-05-27
description: "Cosmos DB logical partition 10000 RU/s 上限、partition key 不可改、三種設計模式（synthetic / composite / hierarchical）、跟 DynamoDB / MongoDB 可逆性對比、latency budget 拆解 — 從 Minecraft Earth + ASOS 切入"
weight: 60
tags: ["backend", "database", "cosmosdb", "partition-key", "hot-partition", "deep-article"]
---

Cosmos DB 的 *logical partition 上限是 10,000 RU/s + 20 GB storage*、partition key 一旦上 production *改不了*（要 export → recreate container → import）。partition key 選錯的後果是 Black Friday / 上線日 / VIP 用戶把流量壓在少數 partition、p99 latency 從 50ms 飆到 5s、整體 container 還有 70% RU 剩餘卻全 throttle。Cosmos DB partition key 設計是 *selection 階段就要決定的硬約束*、不是「先選錯再改」可承擔的風險 — 這個不可逆性跟 MongoDB（`reshardCollection` 線上完成）跟 DynamoDB（建新 table backfill）形成關鍵對比。

本文不是 Cosmos DB overview（請看 [Cosmos DB vendor 頁](/backend/01-database/vendors/cosmosdb/)）— 而是 partition key 設計 + 故障演練的深度展開。Case anchor 是 [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/)（synthetic partition key 強制分散、AR 遊戲玩家位置）+ [9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/)（Black Friday 流量分散 + latency budget 拆解）。

> **Cosmos DB 適用度前置判讀**：本篇假設 workload 已通過 Cosmos DB 適用度四層 framing（API model 三型遷移路徑 / RU 思維轉換成本 / multi-model 差異化是否真用上 / 跨雲 hedging vs 單雲 lock-in）— 詳見 [mongodb-api-vs-sql-api 開頭四層 framing](../mongodb-api-vs-sql-api/#四層-framingvendor-selection-的真實決策軸)、本篇不重複展開。Partition key 設計是 *已選 Cosmos DB 後* 的硬約束議題；若 workload 不適用 Cosmos DB、partition key 設計無法救回 vendor 選錯的不可逆性風險。

## 問題情境

典型觸發場景：團隊用 user_id 當 partition key 上 production、平常正常、Black Friday 或 VIP 大客戶上線當天 — application 收到 `429 TooManyRequests`、p99 從 50ms 飆到 5s；查 portal Metrics 發現 *整體 RU 使用率才 30%* 但少數 partition 100% 滿、其他 partition 閒置。Cosmos DB 設了 10000 RU/s、實際只能用 2000 就 throttle。

讀者徵兆：

- 「Cosmos DB throughput 我設了 10000 RU、但寫入只有 2000 就 throttle」
- 「user_id 當 partition key 結果 VIP 用戶全卡在一個 partition」
- 「Hierarchical partition key 是 2023 後才有的、跟 composite 差在哪」
- 「partition key 選錯能改嗎」

真實壓力：

- 遊戲玩家位置（同伺服器集中同 partition、Minecraft Earth 場景）
- IoT 裝置遙測（單一裝置高頻寫入、device_id 不均）
- SaaS 多租戶（大客戶 vs 小客戶不均、tenant_id 直接當 partition key 會 hot）
- 零售商品 catalog（熱門 SKU vs 冷門 SKU 不均）

partition key 選錯的隱性成本：要改就是 *export → recreate container with new partition key → import*、無 in-place migration、production 等於停機窗口 + 全量資料搬移。selection 階段就要決定、不能 phase 後補。

## 核心機制

### Partition 模型

每個 container 有 N 個 *physical partition*、每個 physical 上有多個 *logical partition*。同 partition key value 的所有 document 落到同一個 logical partition。Cosmos DB 動態調整 physical partition 數量（透明 split）、但 logical partition 的歸屬 *永遠不變*（同 PK value 永遠在同 logical）。

9.C11 Minecraft Earth 案例的平台特性段揭露「partition 動態分裂：透明」 — physical partition 的 split 對 application 透明、不需要 application 重連 / 重新 hash。但這個透明 *只解 physical partition 容量* 問題、*不解 logical partition 熱點* — logical partition 由 PK value 決定、application 必須自己均勻散佈 value。

### Logical partition 上限

10,000 RU/s + 20 GB storage、達 limit 後即使 container 還有總 RU、單一 partition key 一樣 throttle。這是 *硬上限*、不是 soft limit、不能調高。

20 GB storage 限制在小用戶通常碰不到、但對「以 tenant_id 為 PK 的大客戶」、storage 也可能先到上限（單一大客戶 50GB 資料、塞不進一個 logical partition）。

### Partition key 設計三種模式

#### Synthetic（人工合成 key）

機制：用 `{userId}_{random_0_to_99}` 把單一 user 的寫入散到 100 個 logical partition。application 端 hash userId + random suffix、寫入時組合成 partition key。

副作用：read 需 fan-out 100 個 partition、單一 query RU 暴漲 100x。適合 *write-heavy + 不需精準 read* 場景（如 IoT telemetry、log）。

9.C11 Minecraft Earth 用 synthetic partition key 強制分散 — AR 遊戲玩家位置寫入頻繁、partition 分散讓單一玩家不會打爆一個 partition。但 case 沒揭露具體 schema、synthetic 細節屬 outline knowledge 推論。

#### Composite（多欄位合成）

機制：用 `{tenantId}_{deviceId}` 兩個欄位合成、避免單一 high-cardinality 欄位 hot。適合 *多租戶 SaaS*、單一 tenant 內又有多個 device、避免大 tenant 把所有寫入集中。

副作用：read 必須帶兩個欄位、否則 cross-partition query；query API 設計要強制帶 tenant + device。

#### Hierarchical（2023+ 原生支援）

機制：原生支援多層 key（最多 3 層、如 `tenantId / deviceId / sessionId`）、不用手動合成；query 可指定前綴做 partition scope query（如「拿 tenant X 的所有 device」單一 partition scope）。

適合：多層業務 hierarchy 場景（tenant → user → session、organization → team → project）。比 composite 優勢是 *支援 prefix query*、composite key 只能完整匹配。

```bash
az cosmosdb sql container create \
  --partition-key-paths "/tenantId" "/deviceId" \
  --partition-key-kind "MultiHash" \
  ...
```

設計順序要從 *低 cardinality* 到 *高 cardinality*（tenant 少、device 多、session 最多）— 反序會讓 prefix query 無意義。

### 跟其他 vendor 的可逆性對照（本章合成 frame）

partition / shard key 的可逆性在 vendor 間差異懸殊：

| Vendor    | 可逆性                           | 機制                                      | 工程成本         |
| --------- | -------------------------------- | ----------------------------------------- | ---------------- |
| MongoDB   | 可改（4.4+ `reshardCollection`） | 線上完成、cluster 內搬移                  | 高、但 in-place  |
| DynamoDB  | 可改                             | 建新 table、backfill + dual-write 切換    | 中、要 backfill  |
| Cosmos DB | *不可改*                         | 必須 export → recreate container → import | 最高、需停機窗口 |

**對照表是本章合成 frame、9.C11 Minecraft Earth 沒直接揭露此對比、是從 outline knowledge 跟 MongoDB shard-key-selection 對照得出**。引用時必須明示：Cosmos DB partition key 不可改是 *設計選型的硬約束*、不是「先選錯再改」可承擔的風險 — 這個約束直接決定 selection 階段的 partition key audit 嚴格度該多高。

對 selection 的意義：若團隊對 access pattern 不確定、不能用「先上 Cosmos DB 再說、不行再改」的心態、要先用 MongoDB / DynamoDB 試 access pattern、確定後再評估 Cosmos DB。

### 跟 DynamoDB partition key 對比

- **DynamoDB**：partition key + optional sort key、無 hierarchical key、adaptive capacity 自動補 hot partition（部分減緩、不完全解決）
- **Cosmos DB**：hierarchical key 是 *原生功能*、不靠 adaptive；單 logical partition 限制嚴格、必須前期設計

Cosmos DB 的 *硬上限 + 不可逆性* 跟 DynamoDB 的 *adaptive + 可遷移* 是兩種設計哲學 — selection 時要評估團隊能不能負擔前期 design effort。

對應 knowledge cards：[hot-partition](/backend/knowledge-cards/hot-partition/) / [database-sharding](/backend/knowledge-cards/database-sharding/)。

## 操作流程

### 設定 partition key

建 container 時指定、*無法事後修改*：

```bash
az cosmosdb sql container create \
  --account-name mycosmos --database-name mydb \
  --name mycontainer --resource-group myrg \
  --partition-key-path "/userId" \
  --partition-key-version 2 \
  --throughput 10000
```

### Hierarchical key 設定（C# SDK 範例）

```csharp
var properties = new ContainerProperties("mycontainer",
    new[] { "/tenantId", "/deviceId" });
properties.PartitionKeyDefinitionVersion = PartitionKeyDefinitionVersion.V2;
var container = await database.CreateContainerAsync(properties);

// 寫入時帶完整 hierarchical key
var pk = new PartitionKeyBuilder()
    .Add("tenant-123")
    .Add("device-456")
    .Build();
await container.CreateItemAsync(item, pk);

// Prefix query：拿 tenant-123 的所有 device
var prefixPk = new PartitionKeyBuilder()
    .Add("tenant-123")
    .Build();
var iterator = container.GetItemQueryIterator<Item>(
    "SELECT * FROM c",
    requestOptions: new QueryRequestOptions { PartitionKey = prefixPk });
```

### Synthetic key 寫入

application 端 hash + random suffix、寫入時組合成 partition key：

```python
import hashlib
import random

def get_partition_key(user_id, fanout=100):
    suffix = random.randint(0, fanout - 1)
    return f"{user_id}_{suffix}"

# Read 時 fan-out 所有可能 suffix
def read_user_data(user_id, fanout=100):
    results = []
    for suffix in range(fanout):
        pk = f"{user_id}_{suffix}"
        results.extend(query_partition(pk))
    return results
```

注意 fanout 的 trade-off：fanout = 100 等於 read 成本 × 100；要在 *write 分散* 跟 *read 效率* 間平衡、通常 fanout 10-100 之間。

### 查 partition 分布

portal Metrics > Storage by partition key、看分布是否均勻；或用 `SELECT * FROM c WHERE c.partitionKey = "specific-value"` query + diagnostic log 看 RU 分布。

### 驗證點

- 每個 logical partition 的 RU 消耗 < 80% limit（給 burst 留 20% buffer）
- 單一 partition 的 storage < 16 GB（給成長預留 4 GB buffer）
- p99 latency 在 hot partition 不退化
- 跨 partition query 比例 < 5%（多數 query 帶 partition key 條件）

### Rollback boundary

partition key 選錯只能 export → recreate container with new partition key → import；無 in-place migration、生產系統等於停機窗口 + dual-write cutover 流程。對應 [1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/) 的遷移模型。

## 失敗模式

### Failure 1：user_id 直接當 partition key

高活躍用戶（VIP / bot / 大客戶）超過 10,000 RU/s、全 container 被 throttle；徵兆是 `429 TooManyRequests` 集中在少數 partition、整體 RU 利用率才 30%。

修：

- 短期：把 hot user 拉到獨立 container（合規上有時要這樣做、把 VIP / 企業客戶獨立治理）
- 長期：換 synthetic key（user_id + random suffix）或 composite key（tenant + user）
- selection 階段 audit：access pattern 是否會有「少數 user 主導流量」現象（B2B SaaS、VIP 用戶都有）

### Failure 2：時間當 partition key

`/createdDate` 或 `/yyyyMM`、新資料全寫入最新 partition、舊 partition 冷掉浪費 — write hot + read 不均。徵兆：最新月份 partition throttle、其他月份 partition 閒置。

修：時間 + 業務維度組合（如 `/yyyyMM-userId`、`/userId-yyyy`）、避免純時間維度。time-series workload 該考慮 Azure Time Series Insights 或 Cosmos DB time-series 專屬模式。

### Failure 3：Synthetic key 沒考慮 read 路徑

寫入散開但 read 必須 fan-out 100 partition、單一 query RU 暴漲 100x。徵兆：read 成本遠高於估算、`RetrievedDocumentCount` 跟 `OutputDocumentCount` 比例 > 50。

修：

- 用 Change Feed 把投影預先寫到 read-optimized container（partition key 用 user_id）、read 走投影
- 或調 fanout（10 而非 100）、平衡 write 分散跟 read 成本
- 或重新評估「真的需要 synthetic key 嗎」 — 多數場景用 composite 就夠

### Failure 4：Hierarchical key 設計順序顛倒

把 high-cardinality 放第一層、prefix query 變得無意義。如 `/userId/tenantId` 而非 `/tenantId/userId` — 想拿「tenant X 的所有 user」變成 cross-partition query、完全失去 hierarchical 優勢。

修：設計順序從 *低 cardinality* 到 *高 cardinality*、跟業務 query pattern 對齊。建 container 前畫 access pattern 表、列每個 query 的 hierarchy 順序、再決定 partition key path。

### Failure 5：不監控 partition 分布

partition skew 累積幾個月、直到事故才發現。production 上線初期 access pattern 還不明顯、半年後 VIP 客戶開始用、partition 失衡 — 來不及改 partition key、只能在 throttle 中應急。

修：上線第一天就設 alert：

- 單 partition RU 利用 > 80% 持續 5 min
- 單 partition storage > 16 GB
- 429 error rate 突增

每週看 portal Insights > Top contributors > Partition key range、early detect skew。

### Failure 6：Container 之間 partition 設計不一致

跨 container query 需要 fan-out、cross-partition query 成本爆炸。常見 anti-pattern：訂單 container 用 user_id、商品 container 用 product_id、join 訂單 + 商品時兩邊都 cross-partition。

修：跨 container 的 access pattern 在 selection 階段就要設計、不能各 container 各自決定 partition key。或者用 Change Feed 把跨 container 資料合成 single container 的 materialized view。

## 容量與觀測

- 必看 metric：`PhysicalPartitionThroughputInfo`、`NormalizedRUConsumption` per partition、`StorageDistributionPerPartition`
- Hot partition 偵測：portal Insights > Top contributors > Partition key range
- 容量估算公式：peak RU per partition × partition 數 + 預留 buffer（一般 30%）= total RU/s
- 回 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)：把 partition skew 當 saturation signal
- Alert：單 partition RU 利用 > 80% 持續 5 min；429 error rate 突增

### Latency budget 拆解：vendor SLA vs end-to-end 實測

9.C21 ASOS 觀察「48ms 平均響應 = 全球分散下 Cosmos DB 的代表性數字」段揭露：48ms 包含 *網路 + DB + 應用層*、DB 本身可能只佔 5-10ms、其他是網路與應用層。引用時不能把 vendor 廣告的 5-10ms p99 當「使用者體驗」、要明示「48ms 是 9.C21 ASOS 案例的 end-to-end 觀察、Cosmos DB 自身可能只佔 5-10ms（case 揭露的拆解推論、不是 case fact）」。

操作上要把 end-to-end latency 拆 budget：

- **DB 端 latency**（vendor SLA、p99 < 10ms 地區內讀、9.C11 揭露）
- **跨 region replication latency**（multi-region read 從就近 region 拿、不會跨洲、但 cross-region write 不同、見 [multi-region-write-conflict](../multi-region-write-conflict/)）
- **應用層 latency**（serialize / business logic / HTTP overhead）
- **客戶端網路 latency**（mobile / 跨洲）

跟 partition skew 的關係：partition 失衡時即使 vendor 端 SLA 達標、實測 p99 仍會被 hot partition 拉高 — 單一 partition 的 RU consumption 飽和 → 429 retry → 應用層 latency 暴漲 → end-to-end 從 48ms 變 500ms。partition 設計直接影響 end-to-end SLA 鏈路。

## 邊界與整合

- Sibling deep articles：[ru-cost-model-sizing](../ru-cost-model-sizing/)（partition skew 直接影響 RU sizing）、[consistency-levels-engineering](../consistency-levels-engineering/)（partition 失衡時即使設 Strong 也看到 throttle）、[multi-region-write-conflict](../multi-region-write-conflict/)（partition key 影響 conflict 分布）、[mongodb-api-vs-sql-api](../mongodb-api-vs-sql-api/)（MongoDB shard key → Cosmos DB partition key 翻譯）
- 跟 [DynamoDB vendor](/backend/01-database/vendors/dynamodb/) 對比：partition key + adaptive capacity vs 不可逆 + hierarchical
- 跟 [MongoDB vendor](/backend/01-database/vendors/mongodb/) 對比：`reshardCollection` 可逆 vs 不可逆
- 跟 1.x 章節：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) / [1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)
- Knowledge cards：[Hot Partition](/backend/knowledge-cards/hot-partition/) / [Database Sharding](/backend/knowledge-cards/database-sharding/)
- Anti-recommendation：小流量（< 1000 RU/s 預期）不必過度設計 synthetic key、Cosmos DB autoscale + 簡單 partition key 即可；過度 design 比 under-design 更常見的成本浪費

## 相關連結

- [Cosmos DB vendor overview](/backend/01-database/vendors/cosmosdb/) — 本文是該頁尾 partition key design backlog 的深度展開
- [9.C11 Minecraft Earth case](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) — synthetic partition key 主案例
- [9.C21 ASOS case](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) — latency budget 拆解 + 全球零售流量分散
- [Hot Partition 卡片](/backend/knowledge-cards/hot-partition/) / [Database Sharding 卡片](/backend/knowledge-cards/database-sharding/) — 概念基底
- 官方：[Cosmos DB partitioning](https://learn.microsoft.com/azure/cosmos-db/partitioning-overview) / [Hierarchical partition keys](https://learn.microsoft.com/azure/cosmos-db/hierarchical-partition-keys)
