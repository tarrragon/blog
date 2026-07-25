---
title: "Cosmos DB Multi-Region Write：active-active、LWW、custom merge、Strong + multi-region 互斥的 AP 取捨"
date: 2026-05-27
description: "Multi-region active-active write 的 conflict resolution（LWW / custom merge / conflict feed）、Strong 跟 multi-region write 為什麼互斥、廣告 SLA vs 實測可用性鏈路拆解 — 從 Minecraft Earth + Toyota Connected 切入"
weight: 50
tags: ["backend", "database", "cosmosdb", "multi-region", "active-active", "conflict-resolution", "deep-article"]
---

Cosmos DB 是 *AP 系統*（[CAP](/backend/knowledge-cards/cap/) 三選二、放棄跨 region linearizability 換取 multi-region write 可用性）。跨 region 寫同一筆 document 必然有 conflict、Cosmos DB 提供三種 resolution policy 處理：LWW（Last-Writer-Wins）、custom merge stored procedure、conflict feed manual [reconciliation](/backend/knowledge-cards/data-reconciliation/)。本文先講 AP 取捨的硬約束（為什麼 Strong consistency 跟 multi-region write 互斥）、再進三種 resolution 機制、再進廣告 SLA vs 實測可用性的鏈路拆解（DB 端 SLA 不等於使用者體驗）。

本文是 [Cosmos DB vendor 頁](/backend/01-database/vendors/cosmosdb/) 的深度展開、也是 *Strong + multi-region 互斥* 議題的 SSoT 主寫位置（[consistency-levels-engineering](../consistency-levels-engineering/) cross-link 過來、不展開）。Case anchor 是 [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/)（AR 遊戲跨 region 寫入、5 consistency level + multi-region SLA）+ [9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/)（Black Friday 全球零售）+ [9.C38 Toyota Connected](/backend/09-performance-capacity/cases/toyota-connected-mongodb-telematics-iot/)（鏈路 SLA 拆解、跨 vendor 適用做 frame anchor）。

> **Cosmos DB 適用度前置判讀**：本篇假設 workload 已通過 Cosmos DB 適用度四層 framing（API model 三型遷移路徑 / RU 思維轉換成本 / multi-model 差異化是否真用上 / 跨雲 hedging vs 單雲 lock-in）— 詳見 [mongodb-api-vs-sql-api 開頭四層 framing](../mongodb-api-vs-sql-api/#四層-framingvendor-selection-的真實決策軸)、本篇不重複展開。Multi-region write + conflict resolution 是 *已選 Cosmos DB 後* 的拓樸決策；strong global consistency 必要的 workload 應走 Spanner 或 Cosmos DB Strong（單一 write region）、不是用 LWW 補。

## 問題情境：active-active 的 conflict 是必然代價

典型觸發場景：產品要 global active-active（每個 region 都能寫、低延遲）、Cosmos DB 是 AP 系統、不像 Spanner 用 quorum 強一致；跨 region 寫同一筆 document 必然有 conflict、團隊不知道「conflict 真的發生時、誰贏 / 怎麼處理 / 業務語義保不保得住」。

讀者徵兆：

- 「multi-region write 開了、user 在 A region 寫『加入購物車』、B region 寫『移除購物車』、最後哪個贏」
- 「LWW 用 timestamp 決定、client clock skew 不就破壞了嗎」
- 「conflict feed 是什麼、要不要消費」
- 「multi-region write 開了之後 consistency level 還能設 Strong 嗎」
- 「廣告寫 99.999%、為什麼實測只有 99%」

真實壓力：購物車跨 region 寫入丟失、遊戲玩家狀態跨 region 衝突回滾、IoT device 跨 region 寫 telemetry 後消失。這些事故的根因不是 bug、是 multi-region write 的 *設計取捨*、需要在 selection 階段就決定 conflict resolution policy。

## 核心機制

### AP 取捨的硬約束：為什麼 Strong + multi-region write 互斥

Cosmos DB 是 AP 系統（在 partition 的情況下選 availability 跟 partition tolerance、放棄 cross-region linearizability）。multi-region write 的兩個前置條件：

- account 開啟 `enableMultipleWriteLocations = true`
- consistency level *不能設 Strong*（multi-region write 跟 Strong 互斥、時間敏感 claim、查 [最新文件](https://learn.microsoft.com/azure/cosmos-db/consistency-levels)）

為什麼互斥（CAP 三選二的硬約束）：

- **Strong consistency** 在 Cosmos DB 的實作是 quorum-based linearizable read — 確保 read 拿到最新 commit、需要 *單一 write region* 來保證寫入順序
- **Multi-region write** 是 active-active、每個 region 都能寫 — 不存在「單一 write region」、寫入是 LWW-based eventual consistency
- 兩者在技術上 *不能同時成立* — 不是 Microsoft 工程選擇問題、是 distributed system 的基本限制（跟 Spanner 用 Paxos quorum + TrueTime 不同的設計路徑）

對 selection 的意義：產品要「全球都能寫」就接受 eventual consistency；產品要「全球 linearizable」就轉 Spanner / Aurora DSQL、Cosmos DB 不是替代品。把 Cosmos DB Strong 跟 Spanner external consistency 等同視之是 *常見的選型誤判*。

[consistency-levels-engineering](../consistency-levels-engineering/) 的 Strong 段只 cross-link 過來、不展開 conflict resolution 細節 — 本篇是 SSoT 主寫位置。

### Conflict 偵測

同一 document（partition key + id）在多 region 並發寫入、Cosmos DB 偵測為 conflict。偵測機制基於 LSN（log sequence number）、不是 timestamp — 兩個 region 對同一 document 寫入時、replication 過程比對 LSN 發現分歧、進 resolution。

### 三種 conflict resolution policy

#### LWW（Last-Writer-Wins、預設）

- 機制：用 `_ts`（system timestamp）或自訂 numeric property、value 大的贏
- 副作用：clock skew 在 ms 級就能讓「先寫的反而贏」、業務邏輯破洞
- 適合：純覆寫場景（如玩家位置最新值、IoT 最新讀數）— write 順序不影響業務語義

```json
"conflictResolutionPolicy": {
  "mode": "LastWriterWins",
  "conflictResolutionPath": "/customTimestamp"
}
```

#### Custom merge stored procedure

- 機制：寫一個 JavaScript stored proc、conflict 時 Cosmos DB 呼叫、proc 回傳 merge 結果
- 適合：要保留業務語義的場景（購物車 merge = union 兩邊 items、計數器 merge = sum、status 機器 merge = 狀態圖規則）
- 風險：stored proc 在 Cosmos DB JavaScript runtime 跑、有 timeout / RU 限制；複雜 merge 邏輯難 debug

```json
"conflictResolutionPolicy": {
  "mode": "Custom",
  "conflictResolutionProcedure": "dbs/mydb/colls/mycoll/sprocs/resolveCart"
}
```

#### Conflict feed manual reconciliation

- 機制：Cosmos DB 把 conflict 寫入 conflict feed、不自動解決、app 自行消費並 reconcile
- 適合：conflict 需要人工 / 業務流程判斷、不能 auto-resolve（如金融交易、合規場景）
- 風險：feed 不消費就累積、後續分析失準；app 需要實作 reconcile 流程

```json
"conflictResolutionPolicy": { "mode": "Custom" }
```

（沒指 procedure、conflict 全進 feed、app 用 SDK `ReadConflictsAsync()` / Change Feed Processor pattern 消費）

### 跟其他 vendor 對比

- **DynamoDB Global Tables**：也是 LWW、*無* custom merge、*無* conflict feed — 行為比 Cosmos DB 簡單但彈性少
- **Spanner**：用 Paxos quorum、*不會有 conflict*（CP 系統、可用性換一致性）— 跨 region write 需 quorum、latency 100-200ms
- **Aurora Global Database**：single-primary（一個 region 寫、其他 region 讀）、不是真 multi-region write、無 conflict

對應 knowledge cards：[stale-read](/backend/knowledge-cards/stale-read/)、[rpo](/backend/knowledge-cards/rpo/)、[rto](/backend/knowledge-cards/rto/)。

## 操作流程

### 開啟 multi-region write

```bash
az cosmosdb update --name mycosmos --resource-group myrg \
  --enable-multiple-write-locations true \
  --locations regionName=eastus failoverPriority=0 \
  --locations regionName=westeurope failoverPriority=1
```

開啟後 *不能直接關回*、要 disable + 改 region 配置 + re-enable、有停機窗口。

### 設定 LWW policy（container 層）

建 container 時指定、可事後改但 conflict 行為以新 policy 為準（既有 conflict 不會重 resolve）。預設用 `_ts` 比較；改成 customTimestamp 時要保證 application 寫入時 *用單調遞增* 的 timestamp source（不能用 client clock）。

### 設定 custom merge

建 stored proc：

```javascript
function resolveCart(incomingItem, existingItem, isTombstone, conflictingItems) {
  // 範例：merge 購物車 items（取 union）
  var merged = existingItem;
  merged.items = mergeArrays(existingItem.items, incomingItem.items);
  merged._ts = Math.max(existingItem._ts, incomingItem._ts);
  __.response.setBody(merged);
}
```

```json
"conflictResolutionPolicy": {
  "mode": "Custom",
  "conflictResolutionProcedure": "dbs/mydb/colls/mycoll/sprocs/resolveCart"
}
```

驗證：proc 內處理 timeout / exception；測 edge case（空 array / null / 並發 3+ region 寫入）。

### 消費 conflict feed

```csharp
// .NET SDK
var iterator = container.GetItemQueryIterator<ConflictProperties>(
    "SELECT * FROM c");
while (iterator.HasMoreResults) {
    var response = await iterator.ReadNextAsync();
    foreach (var conflict in response) {
        await ProcessConflict(conflict);
    }
}
```

用 Change Feed Processor pattern 把 conflict feed 當 stream 消費、寫到 reconcile queue、由業務流程處理。

### 驗證點

- 跨 region 並發寫測試（synthetic load）、觀察 conflict count / resolution result
- Custom merge stored proc 跑過 edge case（exception / null / 並發 3+）
- Conflict feed 不積壓（lag < 5 min）
- Region 故障時 application 仍能寫（active-active 設計、不需 manual failover）

## 失敗模式

### Failure 1：全用 LWW + 用 server timestamp

clock skew 在 ms 級可能讓「先寫的反而贏」、業務邏輯破洞。常見徵兆：使用者反映「我明明先按確認、後來改的反而是舊的」、debug 才發現是跨 region clock skew。

修：

- 用 `customTimestamp` 從 application 端 monotonic source 取（如 Snowflake ID、HLC、Lamport clock）
- 或改用 custom merge stored proc、用業務邏輯而非 timestamp 決勝
- 或拆 collection、把 conflict 高的 collection 用 stored proc、低的用 LWW

### Failure 2：業務語義不適合 LWW

購物車（要 union）、計數器（要 sum）、status 機器（要狀態圖）全用 LWW = *資料丟失*。LWW 的設計假設是「最新 write 就是正確答案」、但很多業務語義不是覆寫關係。

修：盤點 collection 的業務語義、選對應 resolution policy：

- 覆寫關係 → LWW
- 累積關係 → custom merge stored proc（union / sum / set 合併）
- 狀態機 → custom merge stored proc（按狀態圖規則 resolve）
- 需要人工裁決 → conflict feed

### Failure 3：Custom merge stored proc 沒測 edge case

proc throw exception 時 Cosmos DB 行為：conflict 留 feed、不會自動 retry。團隊以為 proc 跑了就沒事、實際 conflict 累積在 feed、後續分析失準。

修：proc 內部 try-catch、log exception、確保 *任何輸入都能 return 一個合理結果*（即使是 fallback 到 LWW）；定期掃 conflict feed 檢查積壓。

### Failure 4：不消費 conflict feed

選 manual mode 後忘記實作 feed consumer、conflict 累積、後續分析失準。常見徵兆：feed lag metric alert、或業務反映「資料對不上」、最後發現 conflict feed 裡躺著一堆未處理的 conflict。

修：選 conflict feed mode 前先實作 consumer pipeline（Azure Function trigger on Change Feed / 自建 worker）；設 alert：feed lag > 5 min 通知。

### Failure 5：期待 multi-region write 還有 Strong consistency

兩者互斥、開啟 multi-region write 後 Strong 自動 downgrade（或拒絕設定、時間敏感、查最新文件）。團隊以為「multi-region + Strong = 全球 linearizable」、底層是設計 incompatibility。

修：在 selection 階段就決定「要 active-active write 還是要 Strong」 — 兩者只能擇一。要全球 linearizable 轉 Spanner / Aurora DSQL、要 active-active 就接受 eventual / session / bounded staleness。

### Failure 6：跨 region 寫入後立即同 session read 看不到

session token 沒跨 region 傳遞、看似 inconsistency 其實是 session 沒對齊。典型 anti-pattern：service A 在 region 1 寫、用 region 1 session token；service B 在 region 2 讀、沒拿到 A 的 token、看不到 A 的寫。

修：session token 隨 request 傳遞（通常進 HTTP header）；或改 account 層 Bounded staleness（提供跨 session 的 K/T bound）；見 [consistency-levels-engineering](../consistency-levels-engineering/) 的 session token 管理段。

### Failure 7：Region 故障時的 failover 邏輯誤判

multi-region write 已是 active-active、*不需要 manual failover* — 一個 region 掛、其他 region 自動承接寫入。但若用了 `failoverPriority` 配置、failover 邏輯仍要審 — priority 是 *當 multi-region read 切到哪個 region 為 primary*、不是 active-active 的 routing。

修：multi-region write 場景不用依賴 failoverPriority、用 Traffic Manager / Front Door 做 region routing；application 端 SDK 配置 `PreferredLocations` 讓 SDK 自己選 nearest region。

## 容量與觀測

- 必看 metric：`ConflictCount`、`ReplicationLatency` per region pair、conflict feed lag
- Conflict rate 監控：正常 < 0.01%、突增代表 hot key 或 region 同步異常
- Cost 影響：multi-region write 開啟後、寫入成本 × region 數（每個 region 都 replicate）— 3 region active-active = 3x write [Request Unit](/backend/knowledge-cards/request-unit/) cost
- 對應 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)：multi-region write multiplier 進 sizing
- 對應 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)：conflict rate 當 reliability evidence
- Alert：conflict rate > 0.1%、conflict feed lag > 5 min、cross-region replication lag > SLA

### 廣告 SLA vs 實測可用性鏈路拆解（本章合成 frame）

9.C11 Minecraft Earth 平台揭露的 Cosmos DB SLA：

- single-region 99.99%
- multi-region 99.999%

這是 *DB 端 SLA*、不是 *端到端系統 SLA*。真實 production 系統的可用性是鏈路乘積：

```text
實測可用性 = DB SLA × 網路 SLA × 應用層 SLA × 客戶端可達性
```

[9.C38 Toyota Connected](/backend/09-performance-capacity/cases/toyota-connected-mongodb-telematics-iot/) 揭露「99.99% target vs 99% 實測」段的觀察：兩個 9 的差距 *不是* MongoDB / Atlas 自身問題、是 end-to-end 鏈路（車輛無線網路 / cellular tower / cloud network / event bus / microservice / DB cluster 任一環節掉都會打掉可用性）。Cosmos DB multi-region write 同模型：

- 多 region active-active 可解 *DB 端可用性*、但網路 / 應用層任一掉、實測仍 < 99.99%
- 廣告 99.999% 是 multi-region availability zone 級、*不是* 「使用者 request 成功率」

引用時必須明示：Cosmos DB multi-region 廣告 99.999% 是 DB 端、要算實測可用性必須補網路 / 應用層 SLA 乘積、Toyota case 的「99% 實測」揭露的就是這個鏈路問題、跨 vendor 都適用。

跟 conflict resolution 的關係：多 region 高可用性 *買來* 的代價是 conflict、conflict rate 是 reliability 的暗稅 — 廣告 SLA 不計 conflict 處理成本。production 設計要把「conflict resolution 的工程成本」加進 multi-region write 的 ROI 評估。

## 邊界與整合

- Sibling deep articles：[consistency-levels-engineering](../consistency-levels-engineering/)（multi-region write 跟 Strong 互斥的 cross-link 來源）、[partition-key-design](../partition-key-design/)（hot partition 會放大 conflict）、[ru-cost-model-sizing](../ru-cost-model-sizing/)（multi-region cost × region 數）
- 跟 [Spanner vendor](/backend/01-database/vendors/spanner/) 對比：CP vs AP、無 conflict vs LWW / custom
- 跟 DynamoDB Global Tables 對比：兩者都 LWW、Cosmos DB 多 custom merge + conflict feed
- 跟 1.x 章節：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 把 multi-region write 模式並陳
- Knowledge cards：[stale-read](/backend/knowledge-cards/stale-read/) / [rpo](/backend/knowledge-cards/rpo/) / [rto](/backend/knowledge-cards/rto/)
- Anti-recommendation：single-region write + cross-region read replica 在大多數情況更便宜、更易推理；只有 *write residency* 是產品契約（合規 / latency / 業務需求）時才升 multi-region write

## 相關連結

- [Cosmos DB vendor overview](/backend/01-database/vendors/cosmosdb/) — 本文是該頁尾 multi-region write + conflict resolution backlog 的深度展開
- [9.C11 Minecraft Earth case](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) — multi-region 99.999% / single-region 99.99% SLA 來源
- [9.C21 ASOS case](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) — 全球零售 multi-region 補充
- [9.C38 Toyota Connected case](/backend/09-performance-capacity/cases/toyota-connected-mongodb-telematics-iot/) — 鏈路 SLA 拆解 frame anchor（跨 vendor 適用）
- [consistency-levels-engineering](../consistency-levels-engineering/) — Strong + multi-region 互斥的 cross-link 目的地
- [Stale Read 卡片](/backend/knowledge-cards/stale-read/) / [RPO 卡片](/backend/knowledge-cards/rpo/) / [RTO 卡片](/backend/knowledge-cards/rto/) — 概念基底
- 官方：[Cosmos DB conflict resolution](https://learn.microsoft.com/azure/cosmos-db/conflict-resolution-policies) / [Multi-region writes](https://learn.microsoft.com/azure/cosmos-db/how-to-multi-master)
