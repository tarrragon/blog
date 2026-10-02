---
title: "Cosmos DB RU/s 成本模型 + 容量規劃：RU 思維、payload、index、provisioned vs autoscale vs serverless"
date: 2026-05-27
description: "從 CPU+IOPS 思維轉到 RU 思維的學習曲線、依負載形狀選容量模式、payload + index policy 對 RU 的影響、autoscale reactive 限制 — 從 ASOS Black Friday + Minecraft Earth 1M RU/s 壓測切入"
weight: 40
tags: ["backend", "database", "cosmosdb", "ru-sizing", "capacity-planning", "deep-article"]
---

Cosmos DB 用單一 [Request Unit](/backend/knowledge-cards/request-unit/)（RU）抽象 read / write / query / replace 的成本。這個抽象 *簡化* 容量規劃（不用拆 RCU/WCU、不用估 CPU + IOPS）、但也引入 *團隊知識遷移* 成本 — 從 MongoDB / PostgreSQL 自管團隊轉過來、工程師要重新學「query 為什麼吃 200 RU」「payload 從 1KB 變 10KB cost 怎麼變」「index 改一個欄位 write RU 漲 30%」這些 RU 思維問題。這篇涵蓋 RU 的計價基準、payload 與 index policy 對 RU 的影響、依負載形狀選 provisioned／autoscale／serverless，以及 RU sizing 常見的失敗模式。

Case anchor 是 [ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/)（24h 1.67 億 request、autoscale + RU budgeting）+ [Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/)（測試到 1M RU/s、RU 抽象單位定義）。

> **Cosmos DB 適用度前置判讀**：本篇假設 workload 已通過 Cosmos DB 適用度四層 framing（遷移路徑是保留 + 補周邊、同 DB 換託管還是同 model 換 vendor / RU 思維轉換成本 / multi-model 差異化是否真用上 / 跨雲 hedging vs 單雲 lock-in）— 詳見 [mongodb-api-vs-sql-api 開頭四層 framing](../mongodb-api-vs-sql-api/#四層-framingvendor-selection-的真實決策軸)。RU sizing + 容量模式選擇是 *已選 Cosmos DB 後* 的成本決策；若 workload 不適用 Cosmos DB、RU sizing 無法救回 vendor 選錯的成本結構落差。

## 問題情境：RU 思維的學習曲線

典型觸發場景：團隊原本用 MongoDB 自管 / PostgreSQL、把容量規劃成「CPU + IOPS + working set RAM」三軸；遷到 Cosmos DB 後第一個問題是「我們的 query 要設多少 RU/s」 — 文件回答「估每個操作的 RU × 操作頻率」、但工程師沒有 RU 的直覺、不知道「200 RU 是貴還是便宜」。

讀者徵兆：

- 「為什麼這個 query 吃 200 RU」
- 「payload 從 1KB 變 10KB、cost 怎麼變」
- 「Autoscale vs Provisioned 怎麼選」
- 「Serverless 跟 Provisioned 的 break-even 在哪」
- 「Index policy 改了一個欄位、write RU 漲 30%」

真實壓力：Black Friday 流量 10x、超過 autoscale 設定的 Tmax 開始 throttle；dev 環境 24/7 跑、付 provisioned 月費卻只用 1 小時；team 估 RU 估到一半發現「不知道怎麼估」、回去問 PM「我們的 access pattern 是什麼」、PM 給不出答案。

### 從 CPU + IOPS 思維轉到 RU 思維

Minecraft Earth 案例的平台特性段揭露的 RU 對照：

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

**Scope warning**：Minecraft Earth 揭露「100 萬 RU/s 壓測通過」 — *壓測通過數字、不是 production 持續跑*（case 自己警示）。引用 1M RU/s 時必須帶 scope：壓測 vs 持續、case 明示「實際營運要看 partition key 設計是否均勻」。把壓測數字當 production capacity 推算的後果是 sizing 嚴重低估 hot partition 風險。

## RU 的核心機制

### RU 基準

1 RU = 以 id 與 partition key 讀取（point read）一份約 1 KB 的 document 的成本，用 CPU + memory + IOPS 綜合抽象；Strong 與 Bounded staleness 下的 read 約是這個數字的兩倍。每個操作的 RU charge 從 SDK response 的 `x-ms-request-charge` header 拿、不是事後估算。

操作 RU 對照（rule of thumb、實際以 `x-ms-request-charge` 為準）：

- Read 1KB（point read）：1 RU（Session、Consistent prefix、Eventual 都是 1 RU；Strong / Bounded staleness 約 2 RU）
- Write 1KB：5-10 RU（含 index 更新）
- Replace 1KB：10-15 RU
- Query：跟 query plan + result count + index hit 強相關、可從 5 RU 到 1000+ RU

### Payload size 的影響

每多 1 KB payload、write RU 線性增加；read 同 partition 多個 doc 用 query / feed 比多次 point read 更便宜。常見誤區是「拆小 doc 比較便宜」 — 不一定、要看 read pattern：若每次 read 都拿 10 個小 doc、不如合成一個大 doc 一次 read。

### Index policy 的影響

預設 indexing 全欄位（auto-indexing）、降 query cost 但提 write cost；customize index policy（exclude path / include path）可降 write RU 30-50%。判讀時：write-heavy collection 通常該 exclude 不查的欄位、read-heavy collection 通常該 include 常用 query 欄位。

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

模式選擇看的是負載形狀適配哪個，各種負載形狀對應的模式見〈依負載形狀對應容量模式〉。

## 操作流程：依負載形狀選容量模式

### 量測單一 query RU

SDK response header `x-ms-request-charge`、或 portal Query Stats。選容量模式之前的 audit 一定要 *把 production query corpus 跑一遍量 RU*、不是估算 — 估算誤差通常 5-10x。

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

**持續高峰（24h 整天高）** — Provisioned + [scheduled scaling](/backend/knowledge-cards/scheduled-scaling/)

- Trigger 訊號：峰值 / 平均 < 2x、預測性高
- Case anchor：[ASOS Black Friday](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) — 24h 1.67 億 request、峰值 / 平均 = 1.81、整天高
- 為什麼選 provisioned：持續高峰時 RU 整天接近上限，autoscale 每小時按擴到的最高值、以 autoscale 單價計費；官方的經驗值是一個月裡用滿 Tmax 的時數超過 66%，autoscale 就不再省錢
- Scheduled scaling 在 event 前 30-60 分鐘把 provisioned RU/s 調到預測峰值以上

**隨機 surge（不可預測 timing）** — Autoscale + reactive safety net

- Trigger 訊號：不規則尖峰、預測訊號弱、流量曲線無規律
- 為什麼選 autoscale：autoscale 在 0.1×Tmax 到 Tmax 之間即時擴縮，閒置時降到 0.1×Tmax 計費，比照峰值 provisioned 划算
- 這一種負載形狀沒有案例佐證：case 庫未直接揭露純「隨機 surge」的 Cosmos DB 案例

**預測性 surge（外部訊號可預測）** — Pre-provision + scheduled scaling

- Trigger 訊號：賽事 / 上線 / 季節 peak、有外部訊號可學
- Case anchor：[Coinbase predictive scaling](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/) 模型對 KV / document 同適用 — ML 預測 60 分鐘領先窗、改善的是 *trigger 提前*、不是擴容本身變快
- Coinbase case 是 MongoDB 場景、模型可借鑑、但 Cosmos DB 沒有直接對應 ML 預測整合、需要自建

**稀疏 / dev / 低流量** — Serverless

- Trigger 訊號：< 1000 RU/s 預期、長時間閒置（如 dev / test / 內部工具）
- Serverless 是建 account 時選、*不能事後轉 provisioned*、要在建 account 之前決定
- 這一種負載形狀沒有案例佐證（case 庫的案例多數是 production 流量）

上面四種負載形狀與容量模式的對應是本篇自行歸納的分類，case 原文沒有這個分類：持續高峰有 ASOS 當案例、預測性 surge 借用 Coinbase 的模型，隨機 surge 與稀疏負載兩種沒有案例佐證。

### 切換 provisioned ↔ autoscale

portal / CLI 支援、不需停機；但 Serverless 是建 account 時選、*不能轉 provisioned*。建 account 時決定 mode 之後，若要切 serverless ↔ provisioned 等於重建 account + 資料遷移。

### 驗證點

- autoscale min ceiling = 10% max；若 traffic 預測 baseline > 25% peak、autoscale 不划算（baseline 已經超過 min ceiling、autoscale 的彈性沒用上）
- p99 query RU < provisioned / 100（給 burst 留 100x buffer 是 rule of thumb、實際視 query 分布）
- 每個 query pattern 的 `x-ms-request-charge` < SLA budget

### Rollback boundary

throughput 可即時改、index policy 改完背景 rebuild（rebuild 期間 query 用舊 index、性能可能下降但不中斷）；mode（serverless ↔ provisioned）不可改。

## 失敗模式

### 用 point read 取代 query

要拿同 partition 100 個 doc、做 100 次 point read（100 RU）vs 一次 query（可能 10-20 RU）— point read 雖然每次便宜、總成本反高。這個 anti-pattern 在 application code 很常見 — 「每次 read 一個 doc 比較簡單」是 application 角度、不是 RU 角度。

修：拉 access pattern audit、把 N+1 read pattern 改 batch query；用 query 拿同 partition 多 doc、用 cross-partition query 拿不同 partition（成本高、但比 N+1 point read 通常還便宜）。

### Index 全開不審

所有欄位 auto-index、write 大表時 RU 暴漲；徵兆是 `Total RU consumption` 寫入路徑佔 80%、read 只佔 20%、但 application 明明 read-heavy。原因是 index 維護成本太高。

修：customize index policy、exclude 不查的欄位（特別是 array / nested object 等高成本欄位）、include 常用 query 路徑。改完背景 rebuild、不中斷服務。

### Autoscale 的 10% 下限沒考慮

max 40000、min 4000（10% max ceiling）、實際 baseline 是 500、付 8x baseline 費；應該降 max 或改 serverless。autoscale 的 *min ceiling* 是常見的隱性成本來源 — 訂太高 max 就被 min 綁住、autoscale 反而比 provisioned 貴。

修：先量 baseline 跟 peak、算 peak / baseline ratio；ratio > 10x 用 autoscale 划算、ratio < 4x 用 provisioned 划算（autoscale min ceiling 吃掉彈性）。

### Autoscale 的 Tmax 低於預測峰值

autoscale 在 0.1×Tmax 到 Tmax 之間即時擴縮、範圍內不會回 429；超過 Tmax 的流量照樣被 throttle。預測性流量（季節 peak / 賽事 / 上線日）的風險在峰值高過平常設定的 Tmax，所以事件前要把 Tmax 調高，或改用 scheduled scaling 預先拉高 provisioned RU/s。

ASOS Black Friday 是「持續高峰」、整天高 — 用 provisioned + scheduled 比 autoscale 划算，理由在計費：整天接近上限時 autoscale 每小時都按最高值計價。Coinbase 模型是 MongoDB case：cluster 擴容要 70 分鐘、reactive 來不及，ML 預測 60 分鐘領先窗改善的是 *trigger 提前*、不是擴容本身變快。Cosmos DB autoscale 在 Tmax 範圍內沒有這段擴容延遲，Coinbase 的領先窗對 Cosmos DB 能借鑑的部分是「在事件前把 Tmax 或 provisioned RU/s 調上去」。

修：預測性 event 前 30-60 分鐘 pre-warm RU/s、事件結束後降回；用 scheduled scaling pipeline（Azure Function trigger + ARM template）自動化。

### Provisioned 沒退場

dev / staging container 全開 provisioned、月費 $300+ × N 個 environment；應切 serverless 或共用 shared throughput（多個 container 共享一個 RU pool）。dev 環境的 cost waste 是長尾、月底帳單才發現。

修：dev / staging 改 serverless、production 才 provisioned；或用 *shared database throughput*、多個 container 共用 400-1000 RU pool。

### 跨 partition query 浪費

query 沒包含 partition key 條件、fan-out 全 partition、RU × partition 數；徵兆是 `RetrievedDocumentCount` 跟 `OutputDocumentCount` 比例 > 10（拿了 10x doc 才篩出要的）。

修：query 強制帶 partition key 條件、改 access pattern 讓 query 自然帶 partition key；若必須跨 partition、用 [Change Feed](https://learn.microsoft.com/azure/cosmos-db/change-feed) 把投影預先寫到另一個 container 用單一 partition 查。

### 沒設 budget alert

cost 失控直到月底帳單才發現。Cosmos DB 的成本可以在幾天內飆 10x（hot partition + index 全開 + autoscale max 設太高 互相加乘）、月底才看是災難。

修：Azure Cost Management 設 daily budget alert（超預算 1.5x trigger）、portal Insights > Cost insights 每週 review。

### 把 TTL 背景刪除算錯位置

Cosmos DB 容器層的 TTL（[Time To Live](https://learn.microsoft.com/azure/cosmos-db/nosql/time-to-live)）由 background task 刪除過期文件，刪除消耗 RU、但不會出現在 application driver 的 RU 統計。provisioned throughput 的 account 上，這個刪除只用 user request 沒用掉的剩餘 RU；剩餘 RU 不夠時刪除會延後，過期文件從 query 結果裡消失、實際刪除晚一點才發生。serverless account 上，過期刪除按一般 delete 操作的 RU 計費。屬通用工程議題、case 未直接量化 TTL 對 RU 的佔比。

徵兆：

- Provisioned RU 估算「query + write」流量明明很穩、實際 `NormalizedRUConsumption` 卻偏高、找不到對應 application call
- 高寫入率 container 開啟 TTL 後、`Total Request Units` 持續高於預期、portal Insights 「Background operations」段非零
- TTL 設過短（例：分鐘級）、background delete 跟 application write 競爭同 partition、寫入 latency p99 變高

修：

- 估 RU 容量時把 TTL delete 當第三類流量（除了 user read / write 外）、用「過期 doc / 秒 × 平均 doc delete RU」估算
- 設定 TTL 不要過短、避免 delete 壓力跟 application write 撞 partition
- 對高 TTL volume 的 container 開啟 [analytical store](https://learn.microsoft.com/azure/cosmos-db/analytical-store-introduction)、避免歷史資料保留在 transactional store 持續耗 RU
- 監控 `Background operations` 跟 `NormalizedRUConsumption` 的 ratio、把 TTL 對 RU 的影響可視化

## 容量與觀測

- 必看 metric：`NormalizedRUConsumption`（peak）、`TotalRequestUnits`（cumulative）、`MetadataRequests`、`UserErrors`（for `429 throttle`）
- 成本分析：Azure Cost Management 按 container / region tag；portal Insights > Cost insights
- 容量公式：peak RPS × avg RU per request × peak duration factor = required RU/s
- 回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 把 RU 當主要 capacity 軸（不只 storage / CPU）
- 對應 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)：把 429 throttle 當 saturation 訊號
- Alert：429 rate > 0.1%、RU consumption > 80% provisioned 持續 5 min、daily cost 超預算 1.5x

### Latency budget 拆解：vendor SLA vs end-to-end 實測

[ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) 觀察「48ms 平均響應」段揭露：48ms 包含 *網路 + DB + 應用層*、DB 本身可能只佔 5-10ms。引用時不能把 vendor 廣告的 5-10ms p99 當「使用者體驗」 — 詳細拆解見 [partition-key-design](../partition-key-design/) 的 latency budget 段。

### 跟其他 vendor capacity 抽象的對照

| Vendor      | Capacity 抽象                                   | 思維重點                    |
| ----------- | ----------------------------------------------- | --------------------------- |
| MongoDB     | CPU + IOPS + working set RAM                    | 估資源、調 indexing         |
| DynamoDB    | WCU / RCU + on-demand vs provisioned + adaptive | mode 選擇 + PK 均勻度       |
| Cosmos DB   | RU + 5 consistency level                        | RU 預算、每 query 量 charge |
| Aurora      | instance class + replica count + storage IOPS   | provisioned                 |
| Spanner     | processing unit（100 pu 起跳）                  | node count                  |
| CockroachDB | range × replication factor × node count         | distributed                 |

對照表是本章合成 frame、case 庫沒有單一案例橫跨多 vendor。判讀時要明示「思維遷移成本是 selection 評估的隱性軸、不是只看 monthly bill」。

## 邊界與整合

- 同 vendor 的其他文章：[partition-key-design](../partition-key-design/)（partition skew 讓 RU 失效、hot partition 是 sizing 假設失敗的主因）、[consistency-levels-engineering](../consistency-levels-engineering/)（Strong / Bounded 對 read RU 2x）、[multi-region-write-conflict](../multi-region-write-conflict/)（multi-region RU × region 數）、[mongodb-api-vs-sql-api](../mongodb-api-vs-sql-api/)（MongoDB API 翻譯層多 10-20% RU）
- 主章節：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)
- 容量規劃模組：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)（429 throttle 當 saturation 訊號）
- Knowledge cards：[Peak Forecast](/backend/knowledge-cards/peak-forecast/) / [Hot Partition](/backend/knowledge-cards/hot-partition/)
- Anti-recommendation：流量 < 1000 RU/s 不需 autoscale tuning、用 serverless 或 400 RU/s shared throughput；過度 sizing 比 under-sizing 更常見、特別是 dev / staging

## 相關連結

- [Cosmos DB vendor overview](/backend/01-database/vendors/cosmosdb/) — Cosmos DB 其他深度文章的列表
- [ASOS Black Friday case](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) — 持續高峰 + RU budgeting 主案例
- [Minecraft Earth case](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) — RU 抽象單位定義 + 1M RU/s 壓測（scope warning：壓測非持續）
- [Coinbase predictive scaling case](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/) — 預測性 surge 模型借鑑（跨 vendor）
- [Peak Forecast 卡片](/backend/knowledge-cards/peak-forecast/) / [Hot Partition 卡片](/backend/knowledge-cards/hot-partition/) — 概念基底
- 官方：[Cosmos DB Request Units](https://learn.microsoft.com/azure/cosmos-db/request-units) / [Provisioned throughput vs autoscale vs serverless](https://learn.microsoft.com/azure/cosmos-db/throughput-serverless)
