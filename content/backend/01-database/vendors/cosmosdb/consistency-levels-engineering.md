---
title: "Cosmos DB 5 Consistency Levels：Session 預設、Bounded staleness、Strong 邊界跟跨 collection 分流策略"
date: 2026-05-27
description: "Cosmos DB 5 個 consistency level 的工程選擇邏輯、Session 為何是 production 預設、per-request override 跟跨 collection 分流的進階策略、Strong + multi-region 互斥的 cross-link — 從 Minecraft Earth + ASOS 切入"
weight: 70
tags: ["backend", "database", "cosmosdb", "consistency", "session-token", "deep-article"]
---

Cosmos DB 文件列 *5 個 consistency level*（Strong / Bounded staleness / Session / Consistent prefix / Eventual）、用 [PACELC](/backend/knowledge-cards/pacelc/) 講概念、但沒給具體工程判準。team 啟動 Cosmos DB 第一個要決定的就是 account 預設 level、再決定哪些 query 要 per-request override。本文先講 5 個 level 的精確語義、再進 Session 為什麼是 production 預設、再進「同一 application 內不同操作選不同 level」的進階策略；*Strong + multi-region write 互斥*議題 cross-link 到 [multi-region-write-conflict](../multi-region-write-conflict/)、本篇不展開。

本文不是 Cosmos DB overview（請看 [Cosmos DB vendor 頁](/backend/01-database/vendors/cosmosdb/)）— 而是 *consistency level 工程選擇邏輯* 的深度展開。Case anchor 是 [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/)（用 session consistency 撐 AR 全球同步、5 level 跨 collection 分流）+ [9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/)（Black Friday 用較弱 consistency 換 throughput）。

> **Cosmos DB 適用度前置判讀**：本篇假設 workload 已通過 Cosmos DB 適用度四層 framing（API model 三型遷移路徑 / RU 思維轉換成本 / multi-model 差異化是否真用上 / 跨雲 hedging vs 單雲 lock-in）— 詳見 [mongodb-api-vs-sql-api 開頭四層 framing](../mongodb-api-vs-sql-api/#四層-framingvendor-selection-的真實決策軸)、本篇不重複展開。Consistency level 選擇是 *已選 Cosmos DB 後* 的 read / write 語義決策；若 workload 不適用 Cosmos DB、level 選擇無法救回 vendor 選錯的取捨。

## 問題情境

典型觸發場景：team 啟動 Cosmos DB account、setup wizard 問「預設 consistency level」 — 5 個選項、文件講概念、不知道實際業務該選哪個。production 上線後使用者反映「加入購物車後立刻看『我的購物車』讀到舊狀態」、「跨 region 看到玩家瞬移回舊位置」 — debug 發現是 consistency level 沒選對。

讀者徵兆：

- 「Session 跟 Eventual 看起來差不多、為什麼 Session 是預設」
- 「Bounded staleness 的 K 跟 T 該設多少」
- 「Strong 在 multi-region account 為什麼有額外限制」
- 「跨 region read 拿到舊版本、是 consistency 設錯還是 partition key 問題」

真實壓力：

- 購物車場景：加入購物車後立刻看「我的購物車」、結果讀到舊狀態（user 體驗破洞）
- 遊戲場景：玩家位置同步、跨 region 看到「玩家瞬移」回舊位置（遊戲體驗 bug）
- 金融場景：跨服務寫入後立即 read confirm、看不到剛寫的 — 業務邏輯誤判「沒寫進去」、重試 / rollback

consistency level 選錯不是 config 問題、是 *影響 user-facing 行為* 的 selection 決策、必須在 selection 階段釐清。

## 核心機制：5 個 level 的精確語義

### Strong

- 機制：read 拿到最新 commit、提供 linearizable read
- 限制：*single-write region 限制*；multi-region write 不可同時用 Strong（時間敏感 claim、查 [最新文件](https://learn.microsoft.com/azure/cosmos-db/consistency-levels)）；跨 region 配 Strong 還要付 [Cross-Region Quorum](/backend/knowledge-cards/cross-region-quorum/) 的物理 latency tax（跨洲 100-200ms）
- 適合：金融交易、庫存扣減、status 機器寫後 read confirm
- 為什麼互斥：詳見 [multi-region-write-conflict](../multi-region-write-conflict/) 的 AP 取捨段、本篇不展開

### Bounded staleness

- 機制：read 落後 *不超過 K 個 version 或 T 秒*（取較嚴格者）；單 region 內 linearizable、跨 region 有 bounded lag、跟 [Freshness Token](/backend/knowledge-cards/freshness-token/) 是兩種「跨層 read-after-write」協議的選擇（前者 vendor 內建、後者 application-level）
- 設定：K（version 上限）+ T（時間上限）兩個參數
- 適合：multi-region 但需要「有 bound 的 staleness 保證」、如 trading system 跨 region read with SLA

### Session（預設、最常用）

- 機制：同一 session token 內讀寫一致；session 之外 eventual
- 適合：*多數互動式產品的甜蜜點* — 使用者寫入後自己立刻讀得到、其他 session 可接受 eventual
- 為什麼是預設：cost 接近 eventual（不像 Strong 多 2x RU）、體驗接近 Strong（自己讀寫一致）— 是 trade-off 的甜蜜點

### Consistent prefix

- 機制：read 不會看到亂序的寫入（看到 A→B→C、不會看到 A→C→B）、但可能落後
- 適合：時序敏感但可 stale 的場景（如新聞 feed 不能跳序、但可以晚幾秒）
- 風險：常被誤用為 Session 替代、跨 session 一樣 stale、但比 Eventual 多保證 *順序*

### Eventual

- 機制：最便宜、無順序保證
- 適合：完全可 stale + 不需順序的場景（分析、log 聚合、推薦系統）

### 跟 Cosmos DB account / container 的關係

- account 預設一個 level
- 單一 request 可以 *降級*（讀更弱 level）、*不可升級*（讀更強）
- container 層 *無法獨立設定 consistency level*（時間敏感、查最新文件）— 分流靠 *collection 切分* + *per-request override*

### RU 成本差異

- Strong / Bounded read ≈ 2x Session / Eventual 的 [Request Unit](/backend/knowledge-cards/request-unit/)
- write 成本不直接受 read level 影響、但 multi-region replication 開銷會（每多一個 region、寫成本 ×N）
- selection 階段要把 consistency level 當「RU 倍數」進入容量公式、見 [ru-cost-model-sizing](../ru-cost-model-sizing/)

### 跟通用 consistency 卡片的對應

Cosmos DB 是 *少數把 5 level 都商品化* 的服務、其他系統通常只給 2-3 級（MongoDB read concern majority / local / linearizable、DynamoDB strong / eventual）。對應 [consistency-level](/backend/knowledge-cards/consistency-level/) 卡片的概念分層。

跟 [linearizability](/backend/knowledge-cards/linearizability/) 的關係：Cosmos DB Strong = single-region linearizable、*不是* 跨 region external consistency（跟 Spanner 的 TrueTime + Paxos 不同）。這個區別是 selection 階段的常見誤判 — 別把 Cosmos DB Strong 當成 Spanner 替代品。

對應 knowledge cards：[consistency-level](/backend/knowledge-cards/consistency-level/) / [linearizability](/backend/knowledge-cards/linearizability/) / [stale-read](/backend/knowledge-cards/stale-read/)。

## 進階設計策略：同一 application 內不同操作選不同 level

9.C11 Minecraft Earth 案例的平台特性段揭露「一致性是 spectrum、不是 binary」 — AR 遊戲玩家位置稍 stale OK（用 session / eventual）、庫存交易需要 strong；*同一 application 內不同 collection / container 配不同 consistency 是進階策略*、不一定是 account 一刀切。

container 層無法獨立設定 consistency level（時間敏感、查最新文件）、所以分流靠：

- **Collection / container 切分**：高一致需求的資料放獨立 account、預設 Strong；低一致需求放另一 account、預設 Session
- **Per-request override**：account 預設 Session、特定「寫入後立即讀」場景升 Bounded、批次分析降 Eventual；用 SDK 的 `RequestOptions.ConsistencyLevel`

### Per-request override 範例（C# SDK）

```csharp
// account 預設 Session
// 但這個 read 需要 Bounded staleness
var response = await container.ReadItemAsync<Item>(
    id: "item-123",
    partitionKey: new PartitionKey("user-456"),
    requestOptions: new ItemRequestOptions {
        ConsistencyLevel = ConsistencyLevel.BoundedStaleness
    });

// 批次分析、降到 Eventual 換成本
var queryOptions = new QueryRequestOptions {
    ConsistencyLevel = ConsistencyLevel.Eventual
};
var iterator = container.GetItemQueryIterator<Item>(query, requestOptions: queryOptions);
```

注意 *不可升級* 的限制：account 預設 Eventual、per-request 不能升 Strong（會 error）。要保留升級彈性、account 預設應該是 *最強需要的 level*、再 per-request 降級。

### 跟 partition-key-design 的關係

partition 失衡時即使設 Strong consistency 也看到 throttle、application 看到的是 *429 retry 後的高 latency*、不是 stale data — consistency level 跟 partition key 共同決定 *真實一致性體驗*。partition skew 把 Strong 的 SLA 拉到比 Session 還差、見 [partition-key-design](../partition-key-design/) 的 latency budget 拆解段。

## 操作流程

### account 層設定

```bash
# Portal / ARM template / CLI
az cosmosdb update --name mycosmos --resource-group myrg \
  --default-consistency-level Session
```

切換 level 是即時生效、但 production 切換需要 audit 所有 client 的 session 邏輯（特別是 Strong → Session 的降級會讓「跨 session read 變 stale」）。

### Request 層 override

SDK 傳 `RequestOptions.ConsistencyLevel`（C# / Java / Node SDK 行為一致）。注意 *只能降級*、升級會 reject。

### Session token 管理

每個 read response 帶 session token、client 下次 read 帶回去；跨 service 共享 token 需要顯式傳遞（不然每個 service 自己一個 session）。

```csharp
// 拿到 session token
var response = await container.ReadItemAsync<Item>(id, pk);
var sessionToken = response.Headers["x-ms-session-token"];

// 跨 service 傳遞（如 HTTP header）
httpClient.DefaultRequestHeaders.Add("X-Cosmos-Session-Token", sessionToken);

// 下游 service 取得 token、用在 SDK request
var requestOptions = new ItemRequestOptions { SessionToken = sessionToken };
var downstreamResponse = await container.ReadItemAsync<Item>(id, pk, requestOptions);
```

### 驗證 level 行為

寫入後立即 read 同 partition key、量 staleness window。用 Cosmos DB Diagnostic Log 看 request 的實際 consistency level；對照 SDK 設定確認沒被預設 override。

### Rollback boundary

account 預設可改、但 production 切換 level 需要 audit 所有 client 的 session 邏輯；container 層無法獨立設定（時間敏感、查最新文件）。

## 失敗模式

### Failure 1：全用 Strong consistency

互動式產品 Session 即足夠、用 Strong 浪費 2x RU + 限制 multi-region write、cost 暴漲且 multi-region 配置受限。徵兆是「RU consumption 明顯偏高、且 multi-region write 開不起來」 — 才發現預設選 Strong。

修：

- 盤點業務需求、絕大多數讀寫場景 Session 就夠
- 把需要 Strong 的少數 collection 拆獨立 account、其他 default Session
- 計算 cost：Session vs Strong 在多數 workload 差距 1.5-2x、長期成本顯著

### Failure 2：Session token 沒回傳

read 後拿 token、下次 read 沒帶、實際變 Eventual；徵兆是「自己的寫立刻 read 看不到」、debug 才發現 SDK 設定漏。SDK 預設會自動管理 session token、但跨 service 傳遞時容易漏。

修：

- 同一 service 內用 SDK 預設行為、不要關 session token cache
- 跨 service 通信時把 session token 隨 HTTP header 傳遞
- 或改 account 層 Bounded staleness（提供跨 session 的 K/T bound、不依賴 token）

### Failure 3：跨 service 共享 session 假設

service A 寫、service B 讀、B 沒拿到 A 的 session token → 看不到 A 的寫。常見場景：order service 寫訂單、notification service 立刻 read 訂單寄通知 — notification 沒拿到 order 的 token、讀到舊狀態（或讀不到）。

修：

- service A 寫完、把 session token 進 message（Kafka event / HTTP response）傳給 B
- B 用 token 做 read、保證讀到 A 的寫
- 或業務上接受 eventual、design notification 有 retry / reconcile 機制

### Failure 4：Bounded staleness 設太鬆

K = 100,000、T = 1 hour、實際等於 Eventual、team 以為自己有保護。bounded staleness 的 K/T 要對應業務 SLA、不是 vendor 預設值。

修：

- 根據業務 read-after-write SLA 設 T（如「5 秒內必須讀到」設 T=5）
- K 通常設成「peak QPS × T」的合理倍數
- 量測：production 觀察實際 staleness 分布、調整 K/T

### Failure 5：multi-region write 配 Strong

文件不允許 / 行為退化（時間敏感、查最新）— 必須改 Bounded / Session。這是 *AP 取捨的硬約束*、不是 config 問題；詳見 [multi-region-write-conflict](../multi-region-write-conflict/) 的 AP 取捨段。

修：在 selection 階段就決定「要 active-active write 還是要 Strong」、不能事後補；要全球 linearizable 轉 Spanner / Aurora DSQL、要 active-active 接受 eventual / session / bounded。

### Failure 6：Consistent prefix 誤用

把它當 Session 用、跨 session read 還是 stale、但比 Eventual 多一個順序保證；用錯地方等於浪費。常見誤判：「我要『順序對』、所以選 Consistent prefix」 — 但實際業務需求是「自己讀到自己寫的」、應該是 Session 而非 Consistent prefix。

修：

- Consistent prefix 適合 *時序敏感但可跨 session stale* 場景（新聞 feed、event log）
- 「自己讀到自己寫的」場景用 Session
- 跨 session 也要強一致用 Bounded / Strong

## 容量與觀測

- 必看 metric：`NormalizedRUConsumption`、`TotalRequestUnits`、`ReplicationLatency`（跨 region lag）
- Diagnostic Log：每個 request 的實際 consistency level、確認沒被預設 override
- 成本計算：Strong / Bounded read 算 2x RU；multi-region 開後寫入成本 × region 數；level 跟 region 數的 cost matrix 是規劃必算
- 回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)：consistency level 當「RU 倍數」進入容量公式
- Alert：
  - `ReplicationLatency` 突增（跨 region 同步異常）
  - Diagnostic log 偵測 Strong read 突增（成本失控）
  - 跨 service session token 缺失導致 stale read 比例上升

## 邊界與整合

- Sibling deep articles：[partition-key-design](../partition-key-design/)（partition key 跟 consistency 共同決定真實一致性體驗）、[ru-cost-model-sizing](../ru-cost-model-sizing/)（RU 倍數量化）、[multi-region-write-conflict](../multi-region-write-conflict/)（multi-region 下 consistency 的特殊行為、Strong + multi-region 互斥的 SSoT 主寫位置）、[mongodb-api-vs-sql-api](../mongodb-api-vs-sql-api/)（MongoDB read concern → Cosmos DB consistency level 對應）
- 跟 [Spanner vendor](/backend/01-database/vendors/spanner/) 對比：external consistency vs Cosmos DB Strong 不是同一個 thing
- 跟 [DynamoDB vendor](/backend/01-database/vendors/dynamodb/) 對比：DynamoDB 只 strong / eventual 兩級、Cosmos DB 5 級提供細粒度
- 跟 1.x 章節：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)（Cosmos DB 5 level 跟 Spanner external consistency 並陳）
- Knowledge cards：[consistency-level](/backend/knowledge-cards/consistency-level/) / [linearizability](/backend/knowledge-cards/linearizability/) / [stale-read](/backend/knowledge-cards/stale-read/)
- Anti-recommendation：別把 Cosmos DB Strong 跟 Spanner external consistency 等同視之；產品需要真正全球 linearizable transaction 時、Cosmos DB 不是替代品 — 轉 Spanner / Aurora DSQL

## 相關連結

- [Cosmos DB vendor overview](/backend/01-database/vendors/cosmosdb/) — 本文是該頁尾 5 consistency levels backlog 的深度展開
- [9.C11 Minecraft Earth case](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) — session consistency + 跨 collection 分流主案例
- [9.C21 ASOS case](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) — 高 throughput + 較弱 level 補充
- [multi-region-write-conflict](../multi-region-write-conflict/) — Strong + multi-region 互斥的 SSoT 主寫位置
- [Consistency Level 卡片](/backend/knowledge-cards/consistency-level/) / [Linearizability 卡片](/backend/knowledge-cards/linearizability/) / [Stale Read 卡片](/backend/knowledge-cards/stale-read/) — 概念基底
- 官方：[Cosmos DB consistency levels](https://learn.microsoft.com/azure/cosmos-db/consistency-levels) / [Consistency level overrides](https://learn.microsoft.com/azure/cosmos-db/how-to-manage-consistency)
