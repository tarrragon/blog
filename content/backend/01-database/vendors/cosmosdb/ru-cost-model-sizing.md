---
title: "Cosmos DB RU/s 成本模型 + 容量規劃：RU 思維、payload、index、provisioned vs autoscale vs serverless"
date: 2026-05-27
description: "從 CPU+IOPS 思維轉到 RU 思維的學習曲線、依負載形狀選容量模式、payload + index policy 對 RU 的影響、autoscale reactive 限制 — 從 ASOS Black Friday + Minecraft Earth 1M RU/s 壓測切入"
weight: 40
tags: ["backend", "database", "cosmosdb", "ru-sizing", "capacity-planning", "deep-article"]
---

Cosmos DB 用單一 Request Unit（RU）抽象 read / write / query / replace 的成本。這個抽象 *簡化* 容量規劃（不用拆 RCU/WCU、不用估 CPU + IOPS）、但也引入 *團隊知識遷移* 成本 — 從 MongoDB / PostgreSQL 自管團隊轉過來、工程師要重新學「query 為什麼吃 200 RU」「payload 從 1KB 變 10KB cost 怎麼變」「index 改一個欄位 write RU 漲 30%」這些 RU 思維問題。本文先講 RU 思維的學習曲線、再進操作流程（依負載形狀選容量模式）、再進失敗模式（autoscale reactive 限制等）。

本文不是 Cosmos DB overview（請看 [Cosmos DB vendor 頁](/backend/01-database/vendors/cosmosdb/)）— 而是 *RU 成本模型 + sizing* 的深度展開。Case anchor 是 [9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/)（24h 1.67 億 request、autoscale + RU budgeting）+ [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/)（測試到 1M RU/s、RU 抽象單位定義）。

## 問題情境：RU 思維的學習曲線

典型觸發場景：團隊原本用 MongoDB 自管 / PostgreSQL、把容量規劃成「CPU + IOPS + working set RAM」三軸；遷到 Cosmos DB 後第一個問題是「我們的 query 要設多少 RU/s」 — 文件回答「估每個操作的 RU × 操作頻率」、但工程師沒有 RU 的直覺、不知道「200 RU 是貴還是便宜」。

讀者徵兆：

- 「為什麼這個 query 吃 200 RU」
- 「payload 從 1KB 變 10KB、cost 怎麼變」
- 「Autoscale vs Provisioned 怎麼選」
- 「Serverless 跟 Provisioned 的 break-even 在哪」
- 「Index policy 改了一個欄位、write RU 漲 30%」

真實壓力：Black Friday 流量 10x、autoscale 跟不上 throttle；dev 環境 24/7 跑、付 provisioned 月費卻只用 1 小時；team 估 RU 估到一半發現「不知道怎麼估」、回去問 PM「我們的 access pattern 是什麼」、PM 給不出答案。

### 從 CPU + IOPS 思維轉到 RU 思維

9.C11 Minecraft Earth 案例的平台特性段揭露的 RU 對照：

- 1 RU = 1 KB document 的 strong-consistent read 成本
- 寫成本約 5 RU
- 複雜 query 可達數百 RU

這個對照看起來簡單、但 *容量規劃變成「估每個操作多少 RU × 操作頻率」*、跟傳統 RDB「估 CPU / IOPS / working set RAM」是完全不同的思維。具體差異：

- 用 RU 思考、不是用 CPU 思考 — 不需要估「query 跑多久」、要估「query 吃多少 RU」
- 量單一 query 的 `x-ms-request-charge` header、不是看 slow query log — 監控位置從 server 端移到 SDK response
- 拆 query 為 RU budget、不是調 indexing strategy — Cosmos DB index policy 影響 RU、但 *改 index 不改 query 速度*、改的是 cost

跨 vendor 的 capacity 抽象差距（本章合成 frame、跨 vendor case 比對）：

- MongoDB 用 CPU + IOPS + working set 三軸
- DynamoDB 用 WCU / RCU 二軸 + on-demand vs provisioned 模式選擇 + adaptive capacity
- Cosmos DB 用 RU 單軸 + 5 consistency level

*思維遷移成本可能高過 vendor 廣告的價格差距* — 工程師需要 4-6 週才會建立 RU 直覺、selection 評估時不能只看 monthly bill 就做 ROI 結論。對中型團隊、這個學習曲線可能直接決定遷移成功率。

**Scope warning**：9.C11 揭露「100 萬 RU/s 壓測通過」 — *壓測通過數字、不是 production 持續跑*（case 自己警示）。引用 1M RU/s 時必須帶 scope：壓測 vs 持續、case 明示「實際營運要看 partition key 設計是否均勻」。把壓測數字當 production capacity 推算的後果是 sizing 嚴重低估 hot partition 風險。

## RU 的核心機制

### RU 基準

1 RU = strong-consistent read of 1KB document、用 CPU + memory + IOPS 綜合抽象。每個操作的 RU charge 從 SDK response 的 `x-ms-request-charge` header 拿、不是事後估算。

操作 RU 對照（rule of thumb、實際以 `x-ms-request-charge` 為準）：

- Read 1KB（point read）：1 RU（eventual / session 更便宜、strong / bounded staleness 約 2x）
- Write 1KB：5-10 RU（含 index 更新）
- Replace 1KB：10-15 RU
- Query：跟 query plan + result count + index hit 強相關、可從 5 RU 到 1000+ RU

### Payload size 的影響

每多 1 KB payload、write RU 線性增加；read 同 partition 多個 doc 用 query / feed 比多次 point read 更便宜。常見誤區是「拆小 doc 比較便宜」 — 不一定、要看 read pattern：若每次 read 都拿 10 個小 doc、不如合成一個大 doc 一次 read。

### Index policy 的影響

預設 indexing 全欄位（auto-indexing）、降 query cost 但提 write cost；customize index policy（exclude path / include path）可降 write RU 30-50%。寫稿時的判讀：write-heavy collection 通常該 exclude 不查的欄位、read-heavy collection 通常該 include 常用 query 欄位。

```json
{
  "indexingMode": "consistent",
  "includedPaths": [{"path": "/userId/?"}, {"path": "/orderDate/?"}],
  "excludedPaths": [{"path": "/*"}]
}
```

### 三種容量模式

- **Provisioned throughput**：訂死 RU/s、不用也付、適合穩定流量
- **Autoscale provisioned**：訂 max、實際用多少算多少（10% min ceiling）、適合 unpredictable
- **Serverless**：完全按 request 計、小流量 / dev / 稀疏負載

模式選擇不是「哪個便宜」、是「負載形狀適配哪個」— 下節展開。

## 操作流程：依負載形狀選容量模式

### 量測單一 query RU

SDK response header `x-ms-request-charge`、或 portal Query Stats。Phase 0 audit 一定要 *把 production query corpus 跑一遍量 RU*、不是估算 — 估算誤差通常 5-10x。

### 量測 container baseline RU

`az cosmosdb sql container show-throughput`、portal Metrics > Normalized RU Consumption。

### 設定 autoscale

```bash
az cosmosdb sql container update \
  --max-throughput 40000 \
  --resource-group myrg --account-name mycosmos \
  --database-name mydb --name mycontainer
```

### 依負載形狀對應容量模式

不同負載形狀的容量決策完全不同、不能用同一個模板：

**持續高峰（24h 整天高）** — Provisioned + scheduled scaling

- Trigger 訊號：峰值 / 平均 < 2x、預測性高
- Case anchor：[9.C21 ASOS Black Friday](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) — 24h 1.67 億 request、峰值 / 平均 = 1.81、整天高
- 為什麼選 provisioned：autoscale 的 reactive trigger 在持續高峰時仍會被拖累 p99、provisioned 鎖定 RU 反而平穩
- Scheduled scaling 在 event 前 30-60 分鐘 pre-warm、避免事件開始 trigger autoscale

**隨機 surge（不可預測 timing）** — Autoscale + reactive safety net

- Trigger 訊號：不規則尖峰、預測訊號弱、流量曲線無規律
- 為什麼選 autoscale：成本不浪費（10% min ceiling）、reactive 雖然有延遲但比 over-provisioned 划算
- Case anchor 屬本章合成 frame、case 庫未直接揭露純「隨機 surge」的 Cosmos DB 案例

**預測性 surge（外部訊號可預測）** — Pre-provision + scheduled scaling

- Trigger 訊號：賽事 / 上線 / 季節 peak、有外部訊號可學
- Case anchor：[9.C36 Coinbase predictive scaling](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/) 模型對 KV / document 同適用 — ML 預測 60 分鐘領先窗、改善的是 *trigger 提前*、不是擴容本身變快
- Coinbase case 是 MongoDB 場景、模型可借鑑、但 Cosmos DB 沒有直接對應 ML 預測整合、需要自建

**稀疏 / dev / 低流量** — Serverless

- Trigger 訊號：< 1000 RU/s 預期、長時間閒置（如 dev / test / 內部工具）
- Serverless 是建 account 時選、*不能事後轉 provisioned*、要在 Phase 0 決定
- 屬本章合成 frame、case 庫未直接揭露 serverless 場景（多數案例都是 production 流量）

**本章合成 frame 警示**：上表是跨 4 個 case 合成（9.C21 ASOS 提供「持續高峰」明確 anchor、9.C36 Coinbase 提供「預測性 surge」模型）、其他兩格屬 outline knowledge — 寫稿時必須明示「對照表是本章合成、case 原文沒有此分類」。

### 切換 provisioned ↔ autoscale

portal / CLI 支援、不需停機；但 Serverless 是建 account 時選、*不能轉 provisioned*。Phase 0 決定 mode 後若要切 serverless ↔ provisioned 等於重建 account + 資料遷移。

### 驗證點

- autoscale min ceiling = 10% max；若 traffic 預測 baseline > 25% peak、autoscale 不划算（baseline 已經超過 min ceiling、autoscale 的彈性沒用上）
- p99 query RU < provisioned / 100（給 burst 留 100x buffer 是 rule of thumb、實際視 query 分布）
- 每個 query pattern 的 `x-ms-request-charge` < SLA budget

### Rollback boundary

throughput 可即時改、index policy 改完背景 rebuild（rebuild 期間 query 用舊 index、性能可能下降但不中斷）；mode（serverless ↔ provisioned）不可改。

## 失敗模式

### Failure 1：用 point read 取代 query

要拿同 partition 100 個 doc、做 100 次 point read（100 RU）vs 一次 query（可能 10-20 RU）— point read 雖然每次便宜、總成本反高。這個 anti-pattern 在 application code 很常見 — 「每次 read 一個 doc 比較簡單」是 application 角度、不是 RU 角度。

修：拉 access pattern audit、把 N+1 read pattern 改 batch query；用 query 拿同 partition 多 doc、用 cross-partition query 拿不同 partition（成本高、但比 N+1 point read 通常還便宜）。

### Failure 2：Index 全開不審

所有欄位 auto-index、write 大表時 RU 暴漲；徵兆是 `Total RU consumption` 寫入路徑佔 80%、read 只佔 20%、但 application 明明 read-heavy。原因是 index 維護成本太高。

修：customize index policy、exclude 不查的欄位（特別是 array / nested object 等高成本欄位）、include 常用 query 路徑。改完背景 rebuild、不中斷服務。

### Failure 3：Autoscale min 沒考慮

max 40000、min 4000（10% max ceiling）、實際 baseline 是 500、付 8x baseline 費；應該降 max 或改 serverless。autoscale 的 *min ceiling* 是常見的隱性成本來源 — 訂太高 max 就被 min 綁住、autoscale 反而比 provisioned 貴。

修：先量 baseline 跟 peak、算 peak / baseline ratio；ratio > 10x 用 autoscale 划算、ratio < 4x 用 provisioned 划算（autoscale min ceiling 吃掉彈性）。

### Failure 4：Autoscale 撐不住預測性流量、必須 scheduled scaling 或 pre-provision

autoscale 的 min ceiling = 10% max、實際擴容仍是 *reactive*（看到 throttle 才往上推）。對預測性流量（季節 peak / 賽事 / 上線日）、autoscale 跟不上、必須 scheduled scaling 或 pre-provision。

9.C21 ASOS Black Friday 是「持續高峰」、整天高 — 用 provisioned + scheduled 比 autoscale 划算（autoscale 仍會被 reactive trigger 拖累 p99）。9.C36 Coinbase 模型雖然是 MongoDB case、可借鑑：cluster 擴容 70 分鐘、reactive 來不及、ML 預測 60 分鐘領先窗、改善的是 *trigger 提前*、不是擴容本身變快 — Cosmos DB autoscale 的 10% ceiling 同樣是 reactive 限制。

修：預測性 event 前 30-60 分鐘 pre-warm RU/s、事件結束後降回；用 scheduled scaling pipeline（Azure Function trigger + ARM template）自動化。

### Failure 5：Provisioned 沒退場

dev / staging container 全開 provisioned、月費 $300+ × N 個 environment；應切 serverless 或共用 shared throughput（多個 container 共享一個 RU pool）。dev 環境的 cost waste 是長尾、月底帳單才發現。

修：dev / staging 改 serverless、production 才 provisioned；或用 *shared database throughput*、多個 container 共用 400-1000 RU pool。

### Failure 6：跨 partition query 浪費

query 沒包含 partition key 條件、fan-out 全 partition、RU × partition 數；徵兆是 `RetrievedDocumentCount` 跟 `OutputDocumentCount` 比例 > 10（拿了 10x doc 才篩出要的）。

修：query 強制帶 partition key 條件、改 access pattern 讓 query 自然帶 partition key；若必須跨 partition、用 [Change Feed](https://learn.microsoft.com/azure/cosmos-db/change-feed) 把投影預先寫到另一個 container 用單一 partition 查。

### Failure 7：沒設 budget alert

cost 失控直到月底帳單才發現。Cosmos DB 的成本可以在幾天內飆 10x（hot partition + index 全開 + autoscale max 設太高 互相加乘）、月底才看是災難。

修：Azure Cost Management 設 daily budget alert（超預算 1.5x trigger）、portal Insights > Cost insights 每週 review。

## 容量與觀測

- 必看 metric：`NormalizedRUConsumption`（peak）、`TotalRequestUnits`（cumulative）、`MetadataRequests`、`UserErrors`（for `429 throttle`）
- 成本分析：Azure Cost Management 按 container / region tag；portal Insights > Cost insights
- 容量公式：peak RPS × avg RU per request × peak duration factor = required RU/s
- 回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 把 RU 當主要 capacity 軸（不只 storage / CPU）
- 對應 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)：把 429 throttle 當 saturation 訊號
- Alert：429 rate > 0.1%、RU consumption > 80% provisioned 持續 5 min、daily cost 超預算 1.5x

### Latency budget 拆解：vendor SLA vs end-to-end 實測

[9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) 觀察「48ms 平均響應」段揭露：48ms 包含 *網路 + DB + 應用層*、DB 本身可能只佔 5-10ms。寫稿時不能把 vendor 廣告的 5-10ms p99 當「使用者體驗」 — 詳細拆解見 [partition-key-design](../partition-key-design/) 的 latency budget 段。

### 跟其他 vendor capacity 抽象的對照

| Vendor      | Capacity 抽象                                   | 思維重點                    |
| ----------- | ----------------------------------------------- | --------------------------- |
| MongoDB     | CPU + IOPS + working set RAM                    | 估資源、調 indexing         |
| DynamoDB    | WCU / RCU + on-demand vs provisioned + adaptive | mode 選擇 + PK 均勻度       |
| Cosmos DB   | RU + 5 consistency level                        | RU 預算、每 query 量 charge |
| Aurora      | instance class + replica count + storage IOPS   | provisioned                 |
| Spanner     | processing unit（100 pu 起跳）                  | node count                  |
| CockroachDB | range × replication factor × node count         | distributed                 |

對照表是本章合成 frame、case 庫沒有單一案例橫跨多 vendor。寫稿時要明示「思維遷移成本是 selection 評估的隱性軸、不是只看 monthly bill」。

## 邊界與整合

- Sibling deep articles：[partition-key-design](../partition-key-design/)（partition skew 讓 RU 失效、hot partition 是 sizing 假設失敗的主因）、[consistency-levels-engineering](../consistency-levels-engineering/)（Strong / Bounded 對 read RU 2x）、[multi-region-write-conflict](../multi-region-write-conflict/)（multi-region RU × region 數）、[mongodb-api-vs-sql-api](../mongodb-api-vs-sql-api/)（MongoDB API 翻譯層多 10-20% RU）
- 跟 1.x 章節：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)
- 跟 9.x 章節：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)（429 throttle 當 saturation 訊號）
- Knowledge cards：[Peak Forecast](/backend/knowledge-cards/peak-forecast/) / [Hot Partition](/backend/knowledge-cards/hot-partition/)
- Anti-recommendation：流量 < 1000 RU/s 不需 autoscale tuning、用 serverless 或 400 RU/s shared throughput；過度 sizing 比 under-sizing 更常見、特別是 dev / staging

## 相關連結

- [Cosmos DB vendor overview](/backend/01-database/vendors/cosmosdb/) — 本文是該頁尾 RU/s cost model backlog 的深度展開
- [9.C21 ASOS Black Friday case](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) — 持續高峰 + RU budgeting 主案例
- [9.C11 Minecraft Earth case](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) — RU 抽象單位定義 + 1M RU/s 壓測（scope warning：壓測非持續）
- [9.C36 Coinbase predictive scaling case](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/) — 預測性 surge 模型借鑑（跨 vendor）
- [Peak Forecast 卡片](/backend/knowledge-cards/peak-forecast/) / [Hot Partition 卡片](/backend/knowledge-cards/hot-partition/) — 概念基底
- 官方：[Cosmos DB Request Units](https://learn.microsoft.com/azure/cosmos-db/request-units) / [Provisioned throughput vs autoscale vs serverless](https://learn.microsoft.com/azure/cosmos-db/throughput-serverless)
