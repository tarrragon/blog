---
title: "Cosmos DB Stored Procedure / Trigger（JavaScript）：partition-scoped 交易、server-side 邏輯邊界、何時用何時讓 application 層處理"
date: 2026-06-02
description: "Cosmos DB 用 JavaScript 寫的 stored procedure、pre/post trigger 與 UDF 的工程展開：single-partition transaction 語義、bounded execution 與 continuation 模式、何時值得用 server-side 邏輯、為何多數邏輯應留在 application 層 — 跟 Change Feed 的非同步路徑對照"
weight: 72
tags: ["backend", "database", "cosmosdb", "stored-procedure", "trigger", "deep-article"]
---

本文是 [Cosmos DB](/backend/01-database/vendors/cosmosdb/) overview 的 deep article、寫作參照 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。Cosmos DB 的 stored procedure、trigger 與 user-defined function 是用 JavaScript 寫、執行在 Cosmos DB engine 內的 server-side 邏輯。它最有價值的能力是把同一 logical partition 內的多個操作包成一個原子交易 — 這是 application 層無法用 SDK 單獨做到的。本文先講這層 server-side 邏輯的精確語義與限制、再進操作流程、最後重點放在「何時用、何時不用」的判準 — 因為多數應用邏輯放在 application 層更好維護、stored procedure 應該是少數有明確理由的場景。

本文沒有專屬 production case anchor：stored procedure 的設計取捨在公開 case 庫覆蓋稀薄、機制以 Azure vendor 規格與通用工程展開、情境用 partition 內原子交易這個具體需求驅動。

> **Scope warning**：本文涉及的 script 大小上限、執行時間上限、bounded execution 行為等具體限制屬時間敏感、不同 account 配置可能不同、實作前以 [Cosmos DB stored procedure 官方文件](https://learn.microsoft.com/azure/cosmos-db/nosql/stored-procedures-triggers-udfs) cross-verify。

## 問題情境

典型觸發場景：業務需要「讀一筆庫存、檢查數量、扣減、寫一筆扣減記錄」這四步必須原子完成 — 中間不能被別的請求插入。用 application 層 SDK 做、四步是四個獨立 round-trip、中間有 race window；兩個請求同時扣同一筆庫存、可能都讀到 10、各扣 1、結果是 9 而非 8。這類 read-modify-write 在同一 partition 內、需要 server-side 原子性。

讀者徵兆：

- 「同一 partition 內的 read-modify-write 有 race、想要原子交易」
- 「想做批次 upsert、減少 round-trip 與 RU」
- 「想在寫入時自動加 timestamp / 算衍生欄位、用 pre-trigger 行不行」
- 「stored procedure 能不能跨 partition 做交易」（不行 — 這是常見誤解）

真實壓力：Cosmos DB 的 transaction 邊界是 *single logical partition*、跨 partition 沒有原生 ACID 交易。partition 內需要原子性時、SDK 多次 round-trip 無法保證、stored procedure 是 vendor 提供的 partition-scoped transaction 機制。但這個能力有強約束、且容易被濫用成「把業務邏輯都搬進 DB」。

## 核心機制：partition-scoped JavaScript execution

Cosmos DB 的 server-side 邏輯有三類、責任不同。

Stored procedure 是執行在單一 logical partition 內的 JavaScript 函式、它內部對該 partition 的所有 document 操作包在一個 *隱式交易* 裡 — 全部成功 commit、任一失敗整個 rollback。呼叫時必須指定 partition key、procedure 的所有操作都限定在那個 partition。

Trigger 分 pre-trigger 與 post-trigger、綁在 create / replace / delete 等操作上、但 *不會自動觸發* — 必須在 request 明確指定要跑哪個 trigger（這跟關聯式 DB 的 trigger 自動執行不同）。pre-trigger 在操作前跑（常用來補欄位、驗證）、post-trigger 在操作後跑（常用來更新同 partition 的彙總 document）。

UDF（user-defined function）是 query 內可呼叫的純函式、用來在 query projection / filter 階段做自訂計算、沒有寫入能力。

### 交易邊界與 bounded execution

交易嚴格限 single logical partition。stored procedure 不能跨 partition 寫、傳不同 partition key 的操作會失敗。跨 partition 的原子需求要改 workflow（saga / 補償）或重新設計 partition key 讓相關資料同 partition、見 [partition-key-design](../partition-key-design/)。

執行有 bounded execution 限制：每次呼叫有時間與 resource 上限（時間敏感、查文件）、跑太久 Cosmos DB 會中止。處理大量 document 的 stored procedure 必須自己檢查每個操作的回傳、發現「快到上限」時停下、回傳一個 continuation 標記、讓 client 帶著標記再呼叫一次 — 這個 continuation 模式是寫批次 stored procedure 的必備 pattern。

### RU 成本

stored procedure 內每個 document 操作都吃 RU、整個 procedure 的 RU 是內部所有操作的總和、由 response header 回報。一個掃很多 document 的 procedure 可能很貴、且因為 bounded execution 要分多次呼叫、成本與複雜度都比想像高、見 [ru-cost-model-sizing](../ru-cost-model-sizing/)。

## 操作流程

### 寫一個 partition-scoped 原子扣減

```javascript
// deductStock.js — 在單一 partition 內原子扣減庫存
function deductStock(productId, qty) {
    var context = getContext();
    var container = context.getCollection();
    var response = context.getResponse();

    var query = "SELECT * FROM c WHERE c.id = '" + productId + "'";
    var accepted = container.queryDocuments(
        container.getSelfLink(), query,
        function (err, docs) {
            if (err) throw err;
            if (!docs || docs.length === 0)
                throw new Error("product not found");

            var product = docs[0];
            if (product.stock < qty)
                throw new Error("insufficient stock");  // 整個交易 rollback

            product.stock -= qty;
            var ok = container.replaceDocument(
                product._self, product,
                function (e) { if (e) throw e; });
            if (!ok) throw new Error("replace not accepted");
            response.setBody({ remaining: product.stock });
        });
    if (!accepted) throw new Error("query not accepted");
}
```

註冊與呼叫（C# SDK）：

```csharp
await container.Scripts.CreateStoredProcedureAsync(
    new StoredProcedureProperties("deductStock", File.ReadAllText("deductStock.js")));

var result = await container.Scripts.ExecuteStoredProcedureAsync<dynamic>(
    "deductStock",
    new PartitionKey(productId),   // 必須指定 partition key
    new dynamic[] { productId, 1 });
```

驗證：兩個並行請求扣同一筆、總扣減量等於兩次之和、不會 lost update（交易原子性）。庫存不足時拋例外、整個 procedure rollback、stock 不變。回傳 header 的 `x-ms-request-charge` 是這次交易的總 RU。

### 批次操作的 continuation 模式

掃多筆 document 的 procedure 要在 callback 內檢查回傳的 `accepted`、為 false（快到上限）時停下並回傳已處理數量、由 client loop 呼叫直到全部處理完。驗證：對一個大 partition 跑、觀察需要多次呼叫、每次回傳的已處理數累加到總數。

### pre-trigger 補欄位

```javascript
function addTimestamp() {
    var doc = getContext().getRequest().getBody();
    doc.createdAt = new Date().toISOString();
    getContext().getRequest().setBody(doc);
}
```

呼叫時要明確指定 trigger、否則不執行：

```csharp
await container.CreateItemAsync(item, new PartitionKey(item.pk),
    new ItemRequestOptions { PreTriggers = new[] { "addTimestamp" } });
```

驗證：帶 trigger 的寫入有 `createdAt`、不帶 trigger 的寫入沒有 — 確認 trigger 非自動。

### Rollback boundary

stored procedure 本身的交易是 all-or-nothing、procedure 內拋例外即整個 rollback。部署層面：stored procedure / trigger 是 container 內的 resource、replace 即更新、delete 即移除、不影響 data。

## 何時用、何時不用

這是本文的主判讀段：多數應用邏輯放在 application 層更好、stored procedure 只有少數場景值得。

值得用 stored procedure 的條件：

- *partition 內的多步原子交易* — read-modify-write、需要 all-or-nothing、且相關資料確實在同一 partition。這是 stored procedure 不可替代的能力。
- *省 round-trip 的批次操作* — 一次寫入幾百筆同 partition document、用 stored procedure 比幾百次 SDK 呼叫省 latency 與部分 RU overhead。

讓 application 層處理的條件（多數情況）：

- 業務邏輯複雜、會頻繁變動 — JavaScript stored procedure 的版本管理、測試、debug、observability 都比 application 層差；邏輯放 DB 內、CI / 單元測試 / log / APM 都接不上。
- 不需要原子性、或跨 partition — 跨 partition 的協調用 application 層 workflow 或 saga、stored procedure 做不到。
- 寫入後的非同步工作（投影、通知、同步）— 用 [Change Feed](../change-feed-cdc/) 解耦、不要塞進 stored procedure 拖長寫入路徑。
- 衍生欄位 / 計算 — 簡單的放 application 層或 pre-trigger、複雜的不要進 DB 邏輯。

判讀句：stored procedure 的正當理由幾乎只有「partition-scoped atomicity」與「批次 round-trip 縮減」。看到「想把業務規則集中到 DB」「想讓 DB 自動做某件事」這類動機、優先回 application 層 — server-side JavaScript 的維護成本長期高於它省下的東西。

## 失敗模式

### 期待跨 partition 交易

team 把多個不同 partition key 的寫入放進一個 stored procedure、期待原子性。procedure 對非當前 partition 的操作會失敗。徵兆是「跨用戶 / 跨類別的原子操作報錯或部分寫入」。修法是重新設計 partition key 讓相關資料同 partition（若業務允許）、或改用 application 層補償 / saga workflow 處理跨 partition 一致性。

### 沒處理 bounded execution

批次 stored procedure 假設「一次呼叫處理完所有 document」、資料量大時被中止、只處理了一部分、client 以為全做完。徵兆是大 partition 上批次操作結果不完整、且沒有錯誤（procedure 被 bounded execution 截斷但回傳了部分成功）。修法是實作 continuation 模式、每個操作檢查 `accepted`、回傳已處理數、client loop 直到完成。

### 把可變業務邏輯固化進 stored procedure

把定價規則、折扣計算、狀態機這類會變的邏輯寫進 JavaScript stored procedure、之後每次改規則都要改 DB resource、無法走正常 application CI / code review / 測試流程、且 production debug 缺 log。徵兆是「改一個業務規則要動 DB、且改完不確定對不對」。修法是把邏輯搬回 application 層、stored procedure 只保留無法在 application 層做的 partition-scoped atomicity。

### 依賴 trigger 自動執行

從關聯式 DB 過來的 team 假設 trigger 像 SQL trigger 一樣自動跑、寫了 audit / 補欄位的 trigger 卻發現大部分寫入沒觸發 — 因為 Cosmos DB trigger 必須 per-request 指定。徵兆是「trigger 有時跑有時不跑」、實際是只有明確帶 trigger 的 request 才跑。修法是確認所有相關寫入路徑都指定 trigger、或把「必須每次都做」的邏輯放 application 層 / pre-trigger 並在 SDK wrapper 統一帶上。

## 容量與觀測

- 必看 metric：stored procedure 執行的 `x-ms-request-charge`（整個交易的總 RU）、執行例外率、bounded execution 中止比例
- 成本：一個掃多 document 的 procedure 可能比等量單筆操作貴、且 continuation 多次呼叫累加 — 把它當「一個複合操作的總 RU」進容量公式、見 [ru-cost-model-sizing](../ru-cost-model-sizing/)
- observability gap：stored procedure 內部沒有 application APM / structured log、debug 靠回傳 body 與例外訊息 — 這個 gap 本身是「邏輯不該放這裡」的訊號之一
- 回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)：partition-scoped transaction 的 RU 要算進該 partition 的 budget、熱門 partition 上跑重 procedure 會放大 hot partition、見 [Hot Partition](/backend/knowledge-cards/hot-partition/)
- Alert：stored procedure 例外率上升、執行 RU 異常偏高、bounded execution 截斷比例升高

## 邊界與整合

- Sibling deep articles：[change-feed-cdc](../change-feed-cdc/)（寫入後的非同步工作走 Change Feed、不要塞 stored procedure）、[partition-key-design](../partition-key-design/)（transaction 邊界 = partition 邊界、跨 partition 原子需求要重設計 partition key）、[ru-cost-model-sizing](../ru-cost-model-sizing/)（複合交易的 RU 估算）、[consistency-levels-engineering](../consistency-levels-engineering/)（partition 內原子性 vs 跨 session consistency 是兩個不同議題）
- 跟 Spanner 對照：需要 *跨 partition / 全域* ACID 交易時、Cosmos DB stored procedure 做不到 — 轉 [Spanner vendor](/backend/01-database/vendors/spanner/) 或 Aurora DSQL
- 跟 DynamoDB 對照：DynamoDB 的 TransactWriteItems 提供跨 item（含跨 partition、有上限）的交易、語義跟 Cosmos DB 的 single-partition stored procedure 不同 — 從 DynamoDB transaction 過來的 team 要注意 Cosmos DB 沒有等價的開箱跨 partition 交易、見 [DynamoDB vendor](/backend/01-database/vendors/dynamodb/)
- 回 overview：[Cosmos DB vendor overview](/backend/01-database/vendors/cosmosdb/) 的「跨 partition transaction 要改 workflow / stored procedure 邊界」

## 相關連結

- [Cosmos DB vendor overview](/backend/01-database/vendors/cosmosdb/) — 本文是該頁尾 stored procedure / trigger backlog 的深度展開
- [change-feed-cdc](../change-feed-cdc/) — 寫入後非同步工作的對照路徑
- [partition-key-design](../partition-key-design/) — transaction 邊界 = partition 邊界
- [ru-cost-model-sizing](../ru-cost-model-sizing/) — 複合交易 RU 估算
- [Spanner vendor](/backend/01-database/vendors/spanner/) / [DynamoDB vendor](/backend/01-database/vendors/dynamodb/) — 跨 partition 交易能力對照
- [Hot Partition 卡片](/backend/knowledge-cards/hot-partition/) — 熱 partition 上的重交易放大效應
- 官方：[Stored procedures, triggers, and UDFs](https://learn.microsoft.com/azure/cosmos-db/nosql/stored-procedures-triggers-udfs)
