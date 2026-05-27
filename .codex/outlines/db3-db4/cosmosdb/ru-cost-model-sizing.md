# Cosmos DB RU/s Cost Model + Sizing：payload、index、provisioned vs on-demand vs serverless

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：Cosmos DB 用單一 Request Unit 抽象 read / write / query / replace cost、但 *什麼 query 吃多少 RU* 沒直觀對應；團隊配 10000 RU/s 結果 query 一跑 throttle、或反過來付了 50000 RU/s 卻只用 5%
- 讀者徵兆：「為什麼這個 query 吃 200 RU」「payload 從 1KB 變 10KB、cost 怎麼變」「Autoscale vs Provisioned 怎麼選」「Serverless 跟 Provisioned 的 break-even 在哪」「Index policy 改了一個欄位、write RU 漲 30%」
- 真實壓力：Black Friday 流量 10x、autoscale 跟不上 throttle；Dev 環境 24/7 在跑、付 provisioned 月費卻只用 1 小時
- Case anchor: [9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/)（24h 1.67 億 request、autoscale + RU budgeting）、[9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/)（測試到 1M RU/s）

### 從 CPU + IOPS 思維轉到 RU 思維的學習曲線（F2.12）

- 9.C11 Minecraft Earth 平台特性「Request Unit (RU) 是抽象容量單位」段揭露的對照：
  - 1 RU = 1 KB document 的 strong-consistent read 成本
  - 寫成本約 5 RU
  - 複雜 query 可達數百 RU
- 容量規劃變成「估每個操作多少 RU × 操作頻率」、跟傳統 RDB「估 CPU / IOPS / working set RAM」是完全不同的思維
- 從 MongoDB / PostgreSQL 自管團隊遷到 Cosmos DB 時、RU 抽象的隱性成本是 *團隊知識遷移* — 工程師需要學會：
  - 用 RU 思考、不是用 CPU 思考
  - 量單一 query 的 `x-ms-request-charge` header、不是看 slow query log
  - 拆 query 為 RU budget、不是調 indexing strategy（Cosmos DB index policy 影響 RU、但 *改 index 不改 query 速度*、改的是 cost）
- 跨 vendor 的 capacity 抽象差距（依 _module-outline.md frame 4）：MongoDB 用 CPU + IOPS + working set 三軸 / DynamoDB 用 WCU/RCU 二軸 + adaptive capacity / Cosmos DB 用 RU 單軸；轉換成本可能高過 vendor 廣告的價格差距、不是只看 monthly bill 就能 ROI 評估
- **Scope warning**：9.C11「100 萬 RU/s 壓測通過」是 *壓測通過* 數字、不是 *production 持續跑*（case 自己警示）— 寫稿時引用 1M RU/s 必須帶 scope（壓測 vs 持續、case 明示「實際營運要看 partition key 設計是否均勻」）

## 核心機制（Vendor-specific mechanism）

- RU 的基準：1 RU = strong-consistent read of 1KB document、用 CPU + memory + IOPS 綜合抽象
- 操作 RU 對照（rule of thumb、實際看 RU charge）：
  - Read 1KB（point read）：1 RU（eventual / session 更便宜、strong / bounded 2x）
  - Write 1KB：5-10 RU（含 index 更新）
  - Replace 1KB：10-15 RU
  - Query：跟 query plan + result count + index hit 強相關、可從 5 RU 到 1000+ RU
- Payload size 的影響：每多 1KB payload、write RU 線性增加；read 同 partition 多個 doc 用 query / feed 比多次 point read 更便宜
- Index policy 影響：預設 indexing 全欄位（auto-indexing）、降 query cost 但提 write cost；customize index policy（exclude path / include path）可降 write 30-50%
- 三種容量模式：
  - **Provisioned throughput**：訂死 RU/s、不用也付、適合穩定流量
  - **Autoscale provisioned**：訂 max、實際用多少算多少（10% min ceiling）、適合 unpredictable
  - **Serverless**：完全按 request 計、小流量 / dev / 稀疏負載
- 對應 knowledge card：[peak-forecast](/backend/knowledge-cards/peak-forecast/)、[hot-partition](/backend/knowledge-cards/hot-partition/)

## 操作流程（Operations）

- 量測單一 query RU：SDK response header `x-ms-request-charge`、或 portal Query Stats
- 量測 container baseline RU：`az cosmosdb sql container show-throughput`、portal Metrics
- 設定 autoscale：`az cosmosdb sql container update --max-throughput 40000`
- 切換 Provisioned ↔ Autoscale：portal / CLI 支援、不需停機；Serverless 是建 account 時選、不能轉

### 依負載形狀選容量模式對照（F2.11、F2.5）

| 負載形狀                       | 推薦模式                          | Trigger 訊號                          | Case anchor                                        |
| ------------------------------ | --------------------------------- | ------------------------------------- | -------------------------------------------------- |
| 持續高峰（24h 整天高）         | Provisioned + scheduled scaling   | 峰值 / 平均 < 2x、預測性              | 9.C21 ASOS Black Friday（峰值 / 平均 = 1.81）      |
| 隨機 surge（不可預測 timing）  | Autoscale + reactive safety net   | 不規則尖峰、預測訊號弱                | （跨 case 合成 frame）                             |
| 預測性 surge（外部訊號可預測） | Pre-provision + scheduled scaling | 賽事 / 上線 / 季節 peak、外部訊號可學 | 9.C36 Coinbase predictive scaling 模型對 KV 同適用 |
| 稀疏 / dev / 低流量            | Serverless                        | < 1000 RU/s、長時間閒置               | （outline knowledge、case 未直接揭露）             |

**本章合成 frame 警示**：上表是跨 4 個 case 合成（9.C21 ASOS 提供「持續高峰」明確 anchor、9.C36 Coinbase 提供「外部訊號可預測 surge」模型、其他兩格屬 outline knowledge）— 寫稿時必須明示「對照表是本章合成、case 原文沒有此分類」。

- Index policy 調整：

  ```json
  {
    "indexingMode": "consistent",
    "includedPaths": [{"path": "/userId/?"}],
    "excludedPaths": [{"path": "/*"}]
  }
  ```

- 驗證點：
  - autoscale min ceiling = 10% max；若 traffic 預測 baseline > 25% peak、autoscale 不划算
  - p99 query RU < provisioned / 100（給 burst 留 100x buffer 大概足夠）
- Rollback boundary：throughput 可即時改、index policy 改完背景 rebuild（rebuild 期間 query 用舊 index）

## 失敗模式（Failure modes）

- 用 point read 取代 query：要拿同 partition 100 個 doc、做 100 次 point read（100 RU）vs 一次 query（可能 10-20 RU）— point read 雖然每次便宜、總成本反高
- Index 全開不審：所有欄位 auto-index、write 大表時 RU 暴漲；徵兆是 `Total RU consumption` 寫入路徑佔 80%
- Autoscale min 沒考慮：max 40000、min 4000、實際 baseline 是 500、付 8x baseline 費；應該降 max 或改 serverless
- **Autoscale min ceiling 是 reactive、預測性流量必須 scheduled scaling 或 pre-provision**（F2.5 補強）：
  - Autoscale min ceiling = 10% max、實際擴容仍是 *reactive*（看到 throttle 才往上推）
  - 預測性流量（季節 peak / 賽事 / 上線日）autoscale 跟不上、必須 scheduled scaling 或 pre-provision
  - 9.C21 ASOS Black Friday 是「持續高峰」、整天高 — 用 provisioned + scheduled 比 autoscale 划算（autoscale 仍會被 reactive trigger 拖累 p99）
  - 9.C36 Coinbase 模型（雖然是 MongoDB case、可借鑑）：cluster 擴容 70 分鐘、reactive 來不及、ML 預測 60 分鐘領先窗、改善的是 *trigger 提前*、不是擴容本身變快 — Cosmos DB autoscale 的 10% ceiling 同樣是 reactive 限制
  - 跟「徵兆寫了、解法沒寫」的盲區：原 outline 失敗模式只說「autoscale 跟不上 throttle」、沒給操作解法；補上後變成「徵兆 + scheduled scaling / pre-provision 解法 / Coinbase 模型借鑑」三段
- Provisioned 沒退場：dev / staging container 全開 provisioned、月費 $300+ × N 個 environment；應切 serverless 或共用 shared throughput
- 跨 partition query 浪費：query 沒包含 partition key 條件、fan-out 全 partition、RU × partition 數；徵兆是 `RetrievedDocumentCount` 跟 `OutputDocumentCount` 比例 > 10
- 沒設 budget alert：cost 失控直到月底帳單才發現

## 容量與觀測（Capacity & observability）

- 必看 metric：`NormalizedRUConsumption`（peak）、`TotalRequestUnits`（cumulative）、`MetadataRequests`、`UserErrors` for `429 throttle`
- 成本分析：Azure Cost Management 按 container / region tag；portal Insights > Cost insights
- 容量公式：peak RPS × avg RU per request × peak duration factor = required RU/s
- 回到 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 把 RU 當主要 capacity 軸（不只 storage / CPU）
- Alert：429 rate > 0.1%、RU consumption > 80% provisioned 持續 5 min、daily cost 超預算 1.5x

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[partition-key-design](./partition-key-design.md)（partition skew 讓 RU 失效）、[consistency-levels-engineering](./consistency-levels-engineering.md)（Strong / Bounded 對 read RU 2x）、[multi-region-write-conflict](./multi-region-write-conflict.md)（multi-region RU × region 數）
- Migration playbook 連結：MongoDB → Cosmos DB 時、原本 cluster instance cost 對應 Cosmos DB RU/s + region cost、轉換比例進 migration playbook
- 跟 1.x 章節：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)
- 跟 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 對齊：把 429 throttle 當 saturation 訊號
- Anti-recommendation：流量 < 1000 RU/s 不需 autoscale tuning、用 serverless 或 400 RU/s shared throughput；過度 sizing 比 under-sizing 更常見

## 寫作前置 checklist

- [ ] case anchor 確認：9.C21 ASOS（Black Friday RU budgeting）為主、9.C11 Minecraft Earth 補容量極限 + RU 思維學習曲線
- [ ] knowledge card 雙引用：peak-forecast、hot-partition
- [ ] sibling 對比：DynamoDB RCU/WCU、Spanner processing unit
- [ ] fact vs derive 分層：
  - 9.C11「1 RU = 1KB strong read / 寫 ~5 RU / 複雜 query 數百 RU」是 case fact（平台特性段）
  - 「100 萬 RU/s 壓測通過」是 case fact、但 case 自己警示「壓測 ≠ 持續跑」、寫稿必明示 scope
  - 「依負載形狀選容量模式」對照表是本章合成 frame（F2.11）、case 原文無此分類
  - 「autoscale min ceiling 是 reactive、解法是 scheduled / pre-provision」屬 outline knowledge + Coinbase 模型借鑑（跨 vendor 借用、非 Cosmos DB case 直接揭露）
  - 「CPU + IOPS vs RU 思維」是跨 vendor frame、case 隱含、寫稿時要從 vendor 文件補佐證
- [ ] 預估寫作長度：320-380 行（3 種模式 + 6 失敗模式 + index policy + query 範例 + RU 思維學習曲線段 + 負載形狀對照）
