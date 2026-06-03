---
title: "Cosmos DB Change Feed (CDC)：persistent change log、Azure Functions trigger、latest-version vs all-versions-and-deletes 與跟 DynamoDB Streams 對照"
date: 2026-06-02
description: "Cosmos DB Change Feed 的工程展開：partition-scoped 持久變更 log、change feed processor 的 lease / continuation token、latest-version 與 all-versions-and-deletes 兩種模式的取捨、Azure Functions trigger 整合、跟 DynamoDB Streams 的語義差 — 從 ASOS catalog 寫入投影切入"
weight: 71
tags: ["backend", "database", "cosmosdb", "change-feed", "cdc", "deep-article"]
---

本文是 [Cosmos DB](/backend/01-database/vendors/cosmosdb/) overview 的 deep article、寫作參照 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。Change Feed 是 Cosmos DB 把 container 內每次寫入按 logical partition 順序持久化成一條可重讀變更序列的能力、對應 [Change Data Capture](/backend/knowledge-cards/change-data-capture/) 的概念分層。它讓「寫入後要做的後續工作」（投影、cache 失效、事件發布、跨 store 同步）從 application 寫入路徑解耦出來、由獨立 consumer 按自己的進度消費。本文先講 Change Feed 的精確語義與兩種模式、再進 change feed processor 與 Azure Functions trigger 的操作流程、最後拆失敗模式與跟 DynamoDB Streams 的對照。

Case anchor 是 [9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/)（85,000 SKU、每週新增 5,000 件的高更新頻率 catalog、寫入後需要 search index / 推薦排序投影）。ASOS case 本身沒有揭露 Change Feed 的實作細節、本文只取它的 catalog 寫入投影壓力當情境 anchor、機制以 Azure vendor 規格與通用工程展開。

## 問題情境

典型觸發場景：catalog 寫入 Cosmos DB 後、下游還有一連串工作要做 — 把商品同步到 search index、刷新推薦排序、讓 cache 失效、發 event 給庫存服務。團隊一開始把這些工作塞進寫入 API 的同步路徑、寫一筆商品要等 search index 更新完才返回、寫入 latency 被下游拖垮；高峰時下游 search service 變慢、整條寫入鏈一起阻塞。

讀者徵兆：

- 「寫入 API latency 被下游投影工作拖高、想把它非同步化」
- 「下游 consumer 掛掉一段時間、重啟後要怎麼補回漏掉的變更」
- 「同一筆 document 在短時間內改三次、下游只需要最終狀態還是每次都要」
- 「要做 audit / 要知道刪除事件、但 Change Feed 預設讀不到 delete」

真實壓力：寫入路徑與下游處理耦合會讓寫入 SLA 受制於最不穩的 consumer；而把投影改成「掃全表」的 batch job 又有延遲與成本問題。Change Feed 提供的是 *持久、可重讀、按 partition 有序* 的變更來源、讓下游用 pull 或 trigger 模式按自己的進度消費。

## 核心機制：partition-scoped persistent change log

Change Feed 是 container 的內建能力、把每個 logical partition 內的寫入按發生順序記錄成一條持久序列。它的關鍵語義有幾個面向。

順序保證是 *per logical partition*、不是 container 全域。同一 partition key 內的變更嚴格有序、跨 partition 之間沒有全域順序 — 這跟 [partition-key-design](../partition-key-design/) 的設計直接相關、consumer 必須假設不同 partition 的事件可能交錯到達。

進度由 continuation token 表達。consumer 讀到哪裡、用一個 continuation token 標記；下次帶 token 回來、從上次的位置繼續。token 是 per partition range 的、container 做 partition split 時 token 要能跟著 range 拆分 — 這是 change feed processor 幫忙處理的部分。

讀取是 pull-based 持久來源、不是 push 通知。Change Feed 不主動推、是 consumer 主動拉。Azure Functions 的 Cosmos DB trigger 看起來像 push、底層仍是 trigger runtime 持續 poll Change Feed。

### 兩種模式：latest-version vs all-versions-and-deletes

Change Feed 有兩種模式、語義差很大、選錯會在 audit / 補償場景出問題（模式名稱與可用性屬時間敏感、查 [最新文件](https://learn.microsoft.com/azure/cosmos-db/change-feed)）。

Latest-version 模式（過去稱 incremental feed）只給每個 document 的 *最新狀態*。同一 document 在兩次消費之間改了三次、consumer 只會看到最後一個版本、中間版本看不到；delete 也看不到（document 消失、feed 裡沒有對應的 tombstone）。這個模式適合「我只要把最終狀態投影到下游」的場景 — search index 同步、cache 刷新、物化視圖更新。

All-versions-and-deletes 模式給 *每一次* 變更、包含中間版本與 delete / TTL 過期事件。同一 document 改三次、feed 給三筆；刪掉給一筆刪除事件。這個模式適合需要完整變更歷史的場景 — audit log、event sourcing、需要對 delete 做反應的跨 store 同步。代價是事件量更大、且這個模式對 retention 與 partition 行為有額外約束（時間敏感、查文件）。

選擇判準：問「我需要中間版本與刪除事件嗎」。投影類工作（只要最終狀態）用 latest-version；audit 與需要對刪除反應的同步用 all-versions-and-deletes。預設選 latest-version、只有明確需要歷史與 delete 時才升級。

### change feed processor 的角色

直接讀 Change Feed 要自己管 partition range、lease、continuation token、failover — 這些 plumbing 用 change feed processor library 處理。它的核心元件是 *lease container*：一個獨立的 Cosmos DB container、記錄每個 partition range 由哪個 consumer instance 處理、處理到哪個 continuation token。多個 consumer instance 共用同一個 lease container 時、processor 自動把 partition range 分配到不同 instance、達成水平擴展與 failover。

## 操作流程

### 啟用與確認

Change Feed 對 SQL API container 是預設啟用的、不需要額外開關（latest-version 模式）。all-versions-and-deletes 模式需要在 container 層設定、且要設 retention window。

```bash
# 確認 container 存在、Change Feed 自動可用（latest-version）
az cosmosdb sql container show \
  --account-name mycosmos --resource-group myrg \
  --database-name catalog --name products \
  --query "resource.id"
```

驗證：container 存在即可讀 latest-version feed。要用 all-versions-and-deletes、先確認 account / SDK 版本支援（時間敏感、查文件）並設好 retention。

### change feed processor（C# SDK）

```csharp
// lease container 獨立於 monitored container
Container monitored = client.GetContainer("catalog", "products");
Container leases = client.GetContainer("catalog", "leases");

ChangeFeedProcessor processor = monitored
    .GetChangeFeedProcessorBuilder<Product>(
        processorName: "search-index-sync",
        onChangesDelegate: HandleChangesAsync)
    .WithInstanceName(Environment.MachineName)  // 每個 instance 唯一
    .WithLeaseContainer(leases)
    .Build();

await processor.StartAsync();

async Task HandleChangesAsync(
    IReadOnlyCollection<Product> changes,
    CancellationToken ct)
{
    foreach (var product in changes)
    {
        // 投影到 search index — 必須 idempotent
        await searchIndex.UpsertAsync(product);
    }
    // delegate 正常返回 = processor 自動推進 lease 的 continuation token
}
```

驗證：lease container 內會出現每個 partition range 的 lease document、`ContinuationToken` 欄位隨消費推進；多開一個 instance、觀察 lease 被重新分配到兩個 instance。失敗時 delegate 拋例外、processor 不推進該 range 的 token、下次重讀同一批（at-least-once、所以 handler 要 idempotent）。

### Azure Functions trigger（消費端最省維運的形態）

```csharp
[FunctionName("SyncSearchIndex")]
public static async Task Run(
    [CosmosDBTrigger(
        databaseName: "catalog",
        containerName: "products",
        Connection = "CosmosConnection",
        LeaseContainerName = "leases",
        CreateLeaseContainerIfNotExists = true)]
    IReadOnlyList<Product> changes,
    ILogger log)
{
    foreach (var p in changes)
        await searchIndex.UpsertAsync(p);  // idempotent
}
```

Functions trigger 底層就是 change feed processor、lease 與 scale-out 由 Functions runtime 管。驗證：function 的 invocation count 隨寫入增加、Application Insights 看 `changes` batch size 與 lag。

### Rollback boundary

Change Feed 是讀取側機制、停掉 consumer 不影響寫入。要重放：刪掉 lease container 的對應 lease（或建新 processor name）會從 container 起點或指定時間點重讀。重放前確認下游投影是 idempotent、否則重放會重複寫。

## 失敗模式

### 把 handler 寫成非 idempotent

Change Feed 是 at-least-once。consumer 在處理一批後、推進 token 前 crash、重啟會重讀同一批。handler 若是「append 一筆 audit row」這種非 idempotent 操作、重放會產生重複。徵兆是下游出現重複事件、且重複數對應 consumer 重啟次數。修法是讓投影用 upsert（以 document id + version 為 key）、audit 用 dedup key、發 event 帶 idempotency key 讓下游去重 — 對應 [idempotency](/backend/knowledge-cards/idempotency/) 的設計。

### 用 latest-version 模式卻期待看到 delete

team 用預設 latest-version feed 做跨 store 同步、上線後發現「source 刪掉的 document、target 還在」。latest-version 模式不發 delete 事件、刪除在 feed 裡是「該 document 不再出現」、consumer 無從得知。修法是 audit / 需要刪除反應的場景改 all-versions-and-deletes 模式；或在 application 層用 soft delete（寫一個 `deleted: true` 的版本、latest-version feed 就看得到這次寫入）。

### lease container 配置不足成為瓶頸

lease container 自己也吃 RU、且 processor 對它有頻繁讀寫。lease container RU 配太低、processor 推進 token 被 throttle、表現成 Change Feed 消費 lag 升高、但 monitored container 看起來健康。徵兆是消費 lag 持續增長、診斷發現 429 來自 lease container 而非 source。修法是給 lease container 足夠 RU、把它跟 source container 的容量分開規劃、見 [ru-cost-model-sizing](../ru-cost-model-sizing/)。

### 假設 Change Feed 有跨 partition 全域順序

consumer 假設事件按全域時間到達、做了依賴順序的邏輯（例如「先建立帳號事件、後消費事件」）。Change Feed 只保證 per logical partition 有序、跨 partition 交錯。徵兆是偶發的「後續事件先到、依賴的前置事件後到」。修法是讓有順序依賴的 document 落在同一 partition key、或在 consumer 端用業務 timestamp / version 做排序與 buffer、不依賴 feed 到達順序。

### Anti-recommendation：不是所有「寫入後工作」都要 Change Feed

寫入後若只是同一 request 內、同一 partition 的小量同步工作、直接在 application 寫入路徑處理、或用 stored procedure 在 partition 內做（見 [stored-procedure-trigger](../stored-procedure-trigger/)）更簡單。Change Feed 的價值在 *解耦下游、可重放、水平擴展* — 當下游處理慢、會失敗、需要重放、或要被多個獨立 consumer 各自消費時才成立。下游工作輕、不需要重放、強耦合在寫入語義內時、引入 Change Feed + lease container 是多一層維運成本。

## 容量與觀測

- 必看 metric：Change Feed 消費 lag（最新寫入時間 vs consumer 已處理位置）、processor 每批 `changes` 數量、lease container 的 `NormalizedRUConsumption`
- consumer 端 throughput 受 partition range 數限制 — 並行度上限約等於 physical partition 數；range 不夠多時加 consumer instance 不會更快
- 成本：Change Feed 讀取本身吃 RU、all-versions-and-deletes 模式事件量更大、lease container 額外 RU — 三項都進容量公式、見 [ru-cost-model-sizing](../ru-cost-model-sizing/)
- 回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)：把 Change Feed consumer 當獨立 throughput 單位、不要跟 OLTP 寫入共用同一個 RU budget 估算
- Alert：消費 lag 持續增長（consumer 跟不上寫入）、lease container 429、handler 例外率上升

## 邊界與整合

- Sibling deep articles：[stored-procedure-trigger](../stored-procedure-trigger/)（partition 內同步邏輯 vs Change Feed 的非同步解耦）、[synapse-link-federation](../synapse-link-federation/)（分析 workload 用 analytical store、不要用 Change Feed 自己搭 analytics pipeline）、[partition-key-design](../partition-key-design/)（per-partition 順序的來源）、[ru-cost-model-sizing](../ru-cost-model-sizing/)（Change Feed + lease container 的 RU 成本）
- 跟 DynamoDB Streams 對照：兩者都是 partition-ordered 變更 log + at-least-once consumer。差異在 DynamoDB Streams 有固定 24 小時 retention、原生發 INSERT / MODIFY / REMOVE（含 delete）；Cosmos DB latest-version 模式預設不發 delete、要 all-versions-and-deletes 模式才有完整事件與 delete。從 DynamoDB Streams 思維過來的 team 容易假設「delete 一定看得到」、要先確認模式。對照 [DynamoDB vendor](/backend/01-database/vendors/dynamodb/)
- Knowledge card：[Change Data Capture](/backend/knowledge-cards/change-data-capture/) / [idempotency](/backend/knowledge-cards/idempotency/)
- 回 overview：[Cosmos DB vendor overview](/backend/01-database/vendors/cosmosdb/) 的「忽略 Change Feed」常見陷阱

## 相關連結

- [Cosmos DB vendor overview](/backend/01-database/vendors/cosmosdb/) — 本文是該頁尾 Change Feed backlog 的深度展開
- [9.C21 ASOS case](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) — 高更新頻率 catalog 投影壓力的情境 anchor
- [stored-procedure-trigger](../stored-procedure-trigger/) — partition 內同步邏輯的對照
- [partition-key-design](../partition-key-design/) — per-partition 順序的設計來源
- [DynamoDB vendor](/backend/01-database/vendors/dynamodb/) — DynamoDB Streams 對照
- [Change Data Capture 卡片](/backend/knowledge-cards/change-data-capture/) / [Idempotency 卡片](/backend/knowledge-cards/idempotency/) — 概念基底
- 官方：[Change feed in Azure Cosmos DB](https://learn.microsoft.com/azure/cosmos-db/change-feed) / [Change feed processor](https://learn.microsoft.com/azure/cosmos-db/nosql/change-feed-processor)
