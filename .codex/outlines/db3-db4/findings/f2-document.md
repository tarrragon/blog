# F2：MongoDB + Cosmos DB Case Audit Findings

## Audit 範圍跟邊際遞減判讀

讀的 case（依 weight 排序）：

1. 9.C11 Minecraft Earth（Cosmos DB / Azure / AR 遊戲、surge）— **medium case**（60 行、平台特性 + 容量測試數字、無 production 事故敘事）
2. 9.C21 ASOS（Cosmos DB / Azure / 季節 peak）— **rich case**（59 行、具體 RPS / latency / SKU 數字、業務驅動明確）
3. 9.C30 Microsoft 365（Cosmos DB / Azure / MongoDB-API、跨產品遷移）— **medium case**（60 行、遷移敘事 + dogfood frame、無具體數字）
4. 9.C36 Coinbase（MongoDB / AWS / 1.5M reads/sec identity）— **rich case**（74 行、connection storm 數字、predictive scaling 數字、freshness token 機制、雙峰負載敘事）
5. 9.C37 Forbes（MongoDB Atlas / GCP / 媒體爆量）— **rich case**（73 行、build 時間 / TCO / 微服務數量、自管 → managed 遷移敘事）
6. 9.C38 Toyota Connected（MongoDB Atlas / AWS / IoT 900 萬車）— **rich case**（78 行、18B txn/月 / 99.99 vs 99% 差距 / 20 個 DB 邊界、雙模式負載敘事）

**邊際遞減判讀**：

| 輪次    | Case                   | 純新議題                                                                                                  | 重複 frame                                |
| ------- | ---------------------- | --------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| 第 1 個 | 9.C30 Microsoft 365    | MongoDB-API 遷移路徑、dogfood frame、multi-model API 廣度、analytics vs transaction 取捨                  | -                                         |
| 第 2 個 | 9.C36 Coinbase         | Ruby+GVL connection storm、mongobetween proxy、freshness token、predictive scaling、federated DB by shape | dogfood（無、保留 MongoDB）               |
| 第 3 個 | 9.C37 Forbes           | 同 DB 換託管 vs 換 DB 種類、跨雲彈性 vs 單雲鎖定、abstraction layer 隔離 schema、TCO 規模依賴             | 遷移路徑（vs 9.C30 + 9.C36）              |
| 第 4 個 | 9.C38 Toyota Connected | IoT polymorphic document、20 DB blast radius 切分、99.99 vs 99% 鏈路差、time-series collection 未揭露     | event-driven CDC（vs Coinbase）           |
| 第 5 個 | 9.C11 Minecraft Earth  | RU 抽象單位、5 consistency level spectrum、turnkey global distribution、synthetic key                     | global distribution（vs 9.C30、跨 region) |
| 第 6 個 | 9.C21 ASOS             | 24h 持續高峰 vs flash-sale 形狀差、48ms latency 拆解、85K SKU 高更新 catalog                              | season peak（vs Black Friday frame）      |

第 6 個 case 時純新議題 ~2 個（多數議題已被 9.C11 + 前面 MongoDB 案例覆蓋）、frame 重複度開始上升（season peak / global distribution / vendor dogfood）。**Stop signal 在第 6 個 case 觸發**、不需要再往外擴讀 case。

抽出 18 個 findings、足以校準 10 個 outline。

---

## Findings 列表

### Finding F2.1：Document model 跨 vendor 遷移路徑分三型、不能混為一談

- **來源**：9.C36 Coinbase「保留 MongoDB + 補周邊」、9.C37 Forbes「同 DB 換託管」、9.C30 Microsoft 365「同 model 換 vendor」
- **Case 類型**：rich + rich + medium 三 case 合成 frame
- **揭露內容**：document model 系統的演進路徑有三型 — (a)「保留原 DB、補周邊工具」（Coinbase mongobetween / Memcached freshness token）、(b)「同 DB 換託管」（Forbes 自管 → Atlas、6 個月、保留 schema 與 access pattern）、(c)「同 model 換 vendor」（Microsoft 365 → Cosmos DB MongoDB API、保留 driver 但底層架構換）。三型風險跟 ROI 完全不同、Forbes case 明示「換 DB」跟「換託管」是兩個不同議題、Coinbase case 證明「保留主 DB 補周邊」是大規模 OLTP 第三條路。
- **Outline mapping**：
  - MongoDB 已覆蓋於：`schema-design-pattern.md` 結尾「Migration playbook」一行帶過、未拆三型
  - Cosmos DB 已覆蓋於：`mongodb-api-vs-sql-api.md` 整篇聚焦 vendor 切換、但沒展現「保留 / 換託管 / 換 vendor」三型對照
  - **該補但漏了**：`mongodb-api-vs-sql-api.md` 開頭「為何選 Cosmos DB MongoDB API」段該對照三型路徑、提出讀者真正在比的是 *Atlas 跨雲 vs Cosmos DB Azure-only vs 保留自管*；現只說「Azure 生態 lock-in」太單薄
  - **Outline 缺口**：MongoDB 5 篇 outline 都缺「保留 + 補周邊」這條路徑、Coinbase 揭露的 mongobetween / freshness token / predictive scaling 可放進 `shard-key-selection.md` 或新 sibling

### Finding F2.2：MongoDB connection storm 是 driver 跟部署模型耦合問題、不是 DB 自身瓶頸

- **來源**：9.C36 Coinbase「MongoDB + Ruby 連線爆炸需要外部 connection pool」段
- **Case 類型**：rich case（具體數字：60K connections/min、降到 ~2K）
- **揭露內容**：CRuby GVL 強制每 CPU core 一 process、blue-green 部署 instance 數 ×2、連線數隨之 ×2、單 cluster 看到 60K connections/min。MongoDB 原生 driver 沒跨 process connection pool — 跟 PostgreSQL 走 pgbouncer 同需求。Coinbase 自建 mongobetween proxy 把連線降到 ~2K（一個量級）。case 明確標明：Go / Java / Node.js 應用因原生支援連線多工、通常不需要這層 proxy — 這條 caveat 防止讀者過度推廣。
- **Outline mapping**：
  - MongoDB 已覆蓋於：5 篇 outline 都未提
  - Cosmos DB 已覆蓋於：N/A（managed 服務不暴露此問題）
  - **該補但漏了**：`replica-set-read-preference.md` 的容量觀測段、或新 sibling「mongodb-connection-management」處理「driver × 部署模型 → connection storm」議題
  - **Outline 缺口**：MongoDB 5 篇 outline 集體缺 *connection layer* 視角、目前都聚焦 schema / shard / aggregation / replica / CDC、沒講「應用層怎麼連 cluster」

### Finding F2.3：document model schema 自由是契約管理問題、不是技術自由

- **來源**：9.C38 Toyota Connected「document model 適合 sensor schema 隨產品演進」段（含警告「production 必須做 schema governance」）、9.C37 Forbes「中介 abstraction layer 隔離 schema 變動」段
- **Case 類型**：rich + rich 兩 case 合成 frame
- **揭露內容**：document model 的 polymorphic 彈性 *在 production 必須以 schema governance 對沖*。Toyota case 明示：「但這個彈性的成本是 production 必須做 schema governance（validation、版本欄位、application 層相容處理）、否則『schema 自由』會變『production data inconsistency』」。Forbes 走 *中介 abstraction layer* — 不是 DB 本身解、是在應用層擋。兩 case 都揭露：document model 的真實工程議題是 *contract layer 在哪*、不是 schema-less 自由不自由。
- **Outline mapping**：
  - MongoDB 已覆蓋於：`schema-design-pattern.md` 機制段提 `$jsonSchema` validator、失敗模式段有「Schema 三代並存」
  - Cosmos DB 已覆蓋於：N/A（Cosmos DB SQL API 是 JSON document、MongoDB API 走 MongoDB 同問題、但 outline 未討論）
  - **該補但漏了**：`schema-design-pattern.md` 該把 frame 推到「contract layer」層次、不只是 validator 工具；要明說「validator 是 DB 層契約 / abstraction layer 是 app 層契約 / 兩者選一或並用」三選一
  - **Outline 缺口**：`schema-design-pattern.md` 缺「contract layer 在哪」這個 frame、`mongodb-api-vs-sql-api.md` 沒提 schema governance 跨 API 行為一致

### Finding F2.4：Read 1.5M reads/sec 是 *DB + cache + freshness token* 的合成數字、不是 MongoDB 純讀取

- **來源**：9.C36 Coinbase「document model 撐 1.5M reads/sec 靠 cache + freshness token」段 + 警示段
- **Case 類型**：rich case（具體機制 + 警示明示「1.5M reads/sec 是 users 服務 *加上 cache* 的數字、不是 MongoDB cluster 純讀取數字」）
- **揭露內容**：MongoDB 直接打不可能撐 1.5M reads/sec — 必須在 users 服務前加 Memcached query cache、單 document query 先查 cache。cache + write 一致性問題用 OCC version + freshness token 解：write 成功給 client token、之後 read 帶 token、server 保證返回的資料版本 ≥ token、必要時 bypass cache 直接打 DB。case 警示讀者：「讀案例時要區分『應用層觀察到』跟『DB 層實際承擔』」— 直接打進 read preference 跟容量規劃議題。
- **Outline mapping**：
  - MongoDB 已覆蓋於：`replica-set-read-preference.md` 的 causal consistency session 段對應 read-your-own-write、但這是 DB 內機制、case 揭露的是 *DB + cache 層的 token*
  - Cosmos DB 已覆蓋於：N/A
  - **該補但漏了**：`replica-set-read-preference.md` 該補「causal consistency session（DB 層）vs freshness token（cache 層）」對照、揭露讀者真實系統是 *跨層的*、單靠 DB 機制解不了 1.5M reads/sec
  - **Outline 缺口**：MongoDB 5 篇 outline 缺「cache + DB 一致性」這條 frame、跟 read preference 緊密相關但被切開

### Finding F2.5：Predictive scaling 適用「外部訊號可預測流量」、不是普適、要 reactive 做 safety net

- **來源**：9.C36 Coinbase「加密貨幣 surge 用 ML 預測、不靠 reactive scaling」段 + 警示段「ML 預測有 false positive / false negative、Coinbase 沒揭露準確率、所以仍保留 reactive scaling 作為 safety net」
- **Case 類型**：rich case（具體數字：70 分鐘 → 25 分鐘擴容時間、60 分鐘領先窗）
- **揭露內容**：cluster 擴容要 70 分鐘、傳統 reactive scaling 在 surge 開始時才動來不及。Coinbase 訓練 ML 分析價格資料、提前 60 分鐘預測流量、預先擴容、把擴容時間從 70 → 25 分鐘 — 改善的是 *trigger 提前*、不是擴容本身變快。case 警示揭露真正的工程紀律：predictive 必須跟 reactive 並存、ML 失敗時 reactive 接住。
- **Outline mapping**：
  - MongoDB 已覆蓋於：5 篇 outline 都未提（capacity planning 議題在 9.x 章、但 MongoDB-specific 的「擴容慢、提前預測」沒寫進 outline）
  - Cosmos DB 已覆蓋於：`ru-cost-model-sizing.md` 的 autoscale vs provisioned 段、揭露 autoscale 是 *reactive*、不討論 predictive
  - **該補但漏了**：`ru-cost-model-sizing.md` 的失敗模式段該補「autoscale min ceiling 是 reactive、預測性流量（季節 peak / 賽事）autoscale 跟不上、必須 scheduled scaling 或 pre-provision」；現在「autoscale 跟不上 throttle」這條徵兆是寫了、但 *解法* 沒寫
  - **Outline 缺口**：`shard-key-selection.md` 或新 sibling 該收 MongoDB cluster 擴容時間是天級議題、不是 manage console 點點就好

### Finding F2.6：Cluster 切分由 *blast radius* 決定、不是技術上限

- **來源**：9.C38 Toyota Connected「20 個 Atlas database 不是技術上限、是業務邊界切分」段
- **Case 類型**：rich case（具體推算：18B txn/月 ÷ 30 天 ÷ 86400 秒 ≈ 7K txn/sec、單一 cluster 可撐）
- **揭露內容**：Toyota 18B transactions/月 = 7K txn/sec、單一 MongoDB cluster 完全撐得下。切 20 個 DB 不是吞吐問題、是 *microservice ownership* + *blast radius* — 每個 microservice 擁有自己的 DB、單一 DB 故障不影響其他服務。case 明示：「把『總吞吐』拆成『per-DB 邊界』」。
- **Outline mapping**：
  - MongoDB 已覆蓋於：`shard-key-selection.md` 的 anti-recommendation 提「寫入 < 5K WPS 不該分 shard」、但這是 *分 shard*、不是 *分 cluster*
  - Cosmos DB 已覆蓋於：N/A（partition-key-design 在 container 內部討論）
  - **該補但漏了**：`shard-key-selection.md` 的 anti-recommendation 該補「shard vs 多 cluster」對照 — 切多 cluster 是 blast radius 切分、不是 capacity 切分；兩者完全不同 trigger
  - **Outline 缺口**：MongoDB outline 缺 *單 cluster vs 多 cluster* 視角、寫起來容易讓讀者以為 sharded cluster 是唯一橫向擴展選項

### Finding F2.7：99.99% 是 end-to-end 鏈路、不只是 DB 自身

- **來源**：9.C38 Toyota Connected「99.99% target vs 99% 實測差距揭露 telematics 的可用性挑戰」段
- **Case 類型**：rich case（具體數字：99.99% = 4 min/月、99% = 7.2hr/月、MongoDB Atlas SLA 通常 99.95%）
- **揭露內容**：99.99% target 跟 99% 實測差兩個 9、不是 MongoDB 自身可用性問題 — 是 *end-to-end* 鏈路：車輛無線網路 / cellular tower / AWS network / event bus / microservice / Atlas cluster 任一環節掉都會打掉可用性。MongoDB Atlas 自身 SLA 通常 99.95%、達到 99.99% 必須 multi-region + 跨雲冗餘。case 明示讀者：DB 99.99% 廣告不等於 *系統* 99.99%。
- **Outline mapping**：
  - MongoDB 已覆蓋於：`replica-set-read-preference.md` 提「failover 期間 read recovery < 15s」、但這是 DB 內部、case 是 *鏈路*
  - Cosmos DB 已覆蓋於：`consistency-levels-engineering.md` 觀察到 multi-region 99.999%、但沒拆鏈路
  - **該補但漏了**：`multi-region-write-conflict.md` 的容量觀測段該補「multi-region 跑下來實測可用性 = DB SLA × 網路 SLA × 應用層 SLA、不是廣告值」
  - **Outline 缺口**：兩邊 outline 都缺「廣告 SLA vs 實測可用性」拆解

### Finding F2.8：IoT / sensor workload 該考慮 time-series collection、case 沒揭露但是 production 議題

- **來源**：9.C38 Toyota Connected 警示段「MongoDB 6.0+ 有 time series collection 對 IoT 寫入有專屬優化。Toyota 揭露的 20 個 DB 沒明確說有沒有用 time series collection — 對 IoT 案例這是重要區分、但 case study 沒揭露」+ 策略段「IoT 高頻 sensor 寫入考慮 MongoDB time series collection（6.0+）」
- **Case 類型**：rich case + 自承知識缺口
- **揭露內容**：MongoDB 6.0+ time-series collection 比 regular collection 寫入吞吐高 3-5x、storage 壓縮率更好、專為 timestamp + metadata + measurement 三段式資料優化。case 自承 Toyota 沒揭露是否用 — 這是 *讀 case 要小心的盲區*、不是直接抄 case fact。
- **Outline mapping**：
  - MongoDB 已覆蓋於：5 篇 outline 都未提 time-series collection
  - Cosmos DB 已覆蓋於：N/A
  - **該補但漏了**：`schema-design-pattern.md` 的失敗模式 / anti-recommendation 段該補 time-series collection 適用情境；現只提 unbounded array growth、沒給「sensor / event log 等 timestamp 主導資料」的專用方案
  - **Outline 缺口**：MongoDB outline 缺 time-series collection 議題、寫 IoT 場景時必要

### Finding F2.9：MongoDB-compatible API 跟 native API 的相容性是 *特定 query pattern* 問題、不是普遍相容

- **來源**：9.C30 Microsoft 365 警示段「『MongoDB 不夠用』是行銷話術。實際是 *MongoDB 在某些 workload pattern 下不夠用*、不是普遍結論」+ 策略段「但要驗證 *特定 query pattern* 在兩邊行為一致」
- **Case 類型**：medium case + 自承知識缺口（case 沒提具體 throughput / latency / cost 數字）
- **揭露內容**：MongoDB → Cosmos DB MongoDB API 的相容性宣稱要落到 *特定 query pattern* 才有意義。case 警示讀者：「MongoDB 不夠用」是 vendor 行銷話術、實際是「在某些 workload pattern 下不夠用」。遷移時必須 dual-write 驗證每個 query pattern。
- **Outline mapping**：
  - MongoDB 已覆蓋於：`aggregation-pipeline-optimization.md` 提 `$lookup` 在 sharded cluster 限制、但 *跨 vendor* 對照沒展開
  - Cosmos DB 已覆蓋於：`mongodb-api-vs-sql-api.md` 整篇處理此議題、含 Phase 0「相容性 audit、列 unsupported aggregation stage」
  - **該補但漏了**：`mongodb-api-vs-sql-api.md` 該明示「vendor 廣告『100% compat』指 wire compat、不是行為 100% compat」、需 production query corpus 跑一遍才算數
  - **Outline 缺口**：`mongodb-api-vs-sql-api.md` 失敗模式段有「假設 wire compat = 100% 行為相同」一條、但是 Phase 0 audit 流程沒明示 *case-by-case query pattern 驗證* 的重要性

### Finding F2.10：跨雲 vs 單雲 DB 取捨是 *未來雲商策略不確定性* 的 hedging、不是當下省錢

- **來源**：9.C37 Forbes「跨雲彈性的價值在規避未來鎖定、不是當下省成本」段
- **Case 類型**：rich case（具體規模：120M MAU + 70+ Atlas region）
- **揭露內容**：Atlas 提供 AWS / GCP / Azure 跨雲部署、Forbes 選 GCP 是當下決策、但跨雲能力讓未來雲商選型不再綁定。case 對照三大單雲服務：DynamoDB（AWS only）、Cosmos DB（Azure only）、Spanner（GCP only）— 都是單雲鎖定。對 *未來雲商策略尚未底定* 的團隊、跨雲服務的選項保留價值高。
- **Outline mapping**：
  - MongoDB 已覆蓋於：5 篇 outline 都未提 cross-cloud 議題
  - Cosmos DB 已覆蓋於：`mongodb-api-vs-sql-api.md` anti-recommendation 提「跨雲需求（Atlas 仍是首選）」、但沒展開為什麼
  - **該補但漏了**：`mongodb-api-vs-sql-api.md` 的「為何選 Cosmos DB MongoDB API」段該明示「跨雲彈性是 hedging、不是當下省錢」、把 Forbes case 的對照拉進來
  - **Outline 缺口**：MongoDB outline 集體缺 Atlas 跨雲價值的 framing、寫 sibling 對比段時必要

### Finding F2.11：負載形狀分三型（sustained-growth / predictable peak / event-driven burst）、不能套同個 capacity 模板

- **來源**：9.C21 ASOS「Black Friday 24h 1.67 億 = 平均 1,930 req/sec、峰值 3,500 req/sec」（持續高峰）+ 9.C36 Coinbase「low-latency-sustained 中夾雜 surge」（隨外部市場波動）+ 9.C37 Forbes「事件驅動、難以精確預測」（爆量）+ 9.C38 Toyota「持續低頻 + 緊急事件高優先低延遲」（雙模式）
- **Case 類型**：4 個 rich case 合成 frame
- **揭露內容**：document model 系統 production 跑下來、負載形狀至少有 4 種：(a) 24h 持續高峰（ASOS Black Friday、峰值 / 平均 = 1.81）、(b) 隨外部訊號可預測但 timing 不確定的 surge（Coinbase 加密貨幣價格、用 predictive scaling）、(c) 事件驅動爆量（Forbes 熱門文章發布）、(d) 持續低頻 + 緊急事件混合（Toyota 持續 sensor + 緊急通報）。每種形狀對應的擴容策略不同、不該套同個模板。
- **Outline mapping**：
  - MongoDB 已覆蓋於：5 篇 outline 都缺負載形狀分類、capacity 議題分散在各篇
  - Cosmos DB 已覆蓋於：`ru-cost-model-sizing.md` 三種容量模式（provisioned / autoscale / serverless）對應到部分形狀、但沒系統性
  - **該補但漏了**：`ru-cost-model-sizing.md` 的操作流程段該補「依負載形狀選容量模式」對照表 — 持續高峰用 provisioned、隨機 surge 用 autoscale + scheduled、稀疏用 serverless
  - **Outline 缺口**：MongoDB outline 缺對應的 capacity 形狀分類（如 Forbes 媒體爆量該觸發 Atlas auto-scaling 的判讀）

### Finding F2.12：RU 是抽象容量單位、規劃思維跟 CPU / IOPS 不同

- **來源**：9.C11 Minecraft Earth「Request Unit (RU) 是抽象容量單位」段
- **Case 類型**：medium case（具體數字：1 RU = 1KB strong read、寫 ~5 RU、複雜 query 數百 RU、100 萬 RU/s 壓測通過）
- **揭露內容**：1 RU = 1 KB document 的 strong read 成本、寫成本約 5 RU、複雜 query 可達數百 RU。容量規劃變成「估每個操作多少 RU × 操作頻率」、跟「估 CPU / IOPS」是不同的思維。case 警示：「100 萬 RU/s 通過測試」是壓測通過、不是生產持續跑、實際營運要看 partition key 設計是否均勻。
- **Outline mapping**：
  - MongoDB 已覆蓋於：N/A（MongoDB 沒 RU 抽象）
  - Cosmos DB 已覆蓋於：`ru-cost-model-sizing.md` 整篇處理此議題、core 是「RU 抽象 / payload size / index policy」
  - **該補但漏了**：`ru-cost-model-sizing.md` 該明示「RU 抽象的隱性成本」— 工程師需要學會用 RU 思考、不是用 CPU 思考、團隊知識遷移成本可能高
  - **Outline 缺口**：`ru-cost-model-sizing.md` 的問題情境段該補「團隊從『CPU + IOPS 思維』轉到『RU 思維』的學習曲線」

### Finding F2.13：48ms latency 是合成數字、DB 自身可能只佔 5-10ms

- **來源**：9.C21 ASOS「48ms 平均響應 = 全球分散下 Cosmos DB 的代表性數字」段（含拆解）
- **Case 類型**：rich case（具體拆解：48ms 包含網路、DB、應用層、DB 本身可能只佔 5-10ms）
- **揭露內容**：跨 region Cosmos DB 平均 48ms 包含 *網路 + DB + 應用層*、DB 本身可能只 5-10ms、其他是網路與應用層。讀者看 vendor 廣告 latency 數字時要拆 budget — case 明示這層、避免讀者把 DB latency 跟 end-to-end latency 混為一談。
- **Outline mapping**：
  - MongoDB 已覆蓋於：5 篇 outline 都未提 latency budget 拆解
  - Cosmos DB 已覆蓋於：`consistency-levels-engineering.md` 提 multi-region 但沒拆 latency
  - **該補但漏了**：`partition-key-design.md` 容量觀測段該補「latency budget 拆解 — vendor SLA 是 DB 端 / 實測是 end-to-end」
  - **Outline 缺口**：兩邊 outline 都缺 *budget 拆解* 思維、容易讓讀者把廣告 latency 當實測 latency

### Finding F2.14：Multi-region write 跟 Strong consistency 互斥、是 CAP 取捨硬約束

- **來源**：9.C11 Minecraft Earth「一致性是 spectrum、不是 binary」段（5 個一致性層級）+ Cosmos DB 平台特性「partition 動態分裂：透明」
- **Case 類型**：medium case（具體列出 5 個 level、但沒展開取捨）
- **揭露內容**：Cosmos DB 提供 5 個一致性層級、每個 latency / throughput 特性不同。AR 遊戲玩家位置不需要 strong（位置稍 stale OK）、庫存交易需要 strong。同一 application 內不同操作選不同 consistency 是進階設計策略。case 沒明示但 outline 跟其他 Cosmos DB 文件揭露：multi-region write 跟 Strong 互斥 — 開 multi-region write 就不能設 Strong。
- **Outline mapping**：
  - MongoDB 已覆蓋於：`replica-set-read-preference.md` 處理 read concern majority / local / linearizable、概念對照
  - Cosmos DB 已覆蓋於：`consistency-levels-engineering.md` 跟 `multi-region-write-conflict.md` 都處理此議題
  - **該補但漏了**：`consistency-levels-engineering.md` 跟 `multi-region-write-conflict.md` 該 cross-link、明示「Strong + multi-region 互斥」是兩篇的 SSoT 對應點
  - **Outline 缺口**：兩篇 Cosmos DB outline 重複展開 Strong / multi-region 互斥議題、要 SSoT 對齊（Stage 2 SSoT 對應的典型風險）

### Finding F2.15：Partition key 選錯不可逆、Cosmos DB 比 DynamoDB 更嚴格

- **來源**：9.C11 Minecraft Earth 平台特性「partition 動態分裂：透明」（隱含 partition key 設計的重要性）+ outline 已揭露
- **Case 類型**：medium case 補充 + outline knowledge
- **揭露內容**：Cosmos DB 跟 DynamoDB 一樣、hot partition 會讓名義容量達不到。Cosmos DB 特殊性是「synthetic partition key」可混合多個 field 強制分散。case 沒明示但 outline 揭露：partition key 一旦上 production 改不了（要 export-recreate-import）。對比 DynamoDB adaptive capacity 自動補 hot partition（部分減緩）、Cosmos DB 沒有此自動緩解、必須前期設計。
- **Outline mapping**：
  - MongoDB 已覆蓋於：`shard-key-selection.md` 揭露 `reshardCollection`（4.4+）可改、但成本高
  - Cosmos DB 已覆蓋於：`partition-key-design.md` 整篇處理
  - **該補但漏了**：`partition-key-design.md` 跟 `shard-key-selection.md` 缺「不可逆程度」對比 — MongoDB shard key 4.4+ 可改（成本高）、DynamoDB partition key 可改（用 backfill）、Cosmos DB partition key 不可改（必 export-recreate）。三者不在同一光譜
  - **Outline 缺口**：兩邊 outline 應 cross-link、明示「partition / shard key 變更可逆性」的 vendor 差異

### Finding F2.16：Multi-model 的差異化價值是 *單一服務支援多 API*、減少多 DB 並存運維

- **來源**：9.C30 Microsoft 365「Multi-model 是 Cosmos DB 的差異化價值」段
- **Case 類型**：medium case（明示 SQL API / MongoDB API / Cassandra API / Gremlin / Table API 五個）
- **揭露內容**：Cosmos DB 同一服務支援 SQL / MongoDB / Cassandra / Gremlin / Table API、避免多個 DB 服務並存。case 對照：AWS DynamoDB（KV）+ DocumentDB（MongoDB-compatible）、GCP Firestore + Spanner + Bigtable — 各家用多個產品覆蓋 multi-model、Cosmos DB 是少數「單一產品支援多 model」。
- **Outline mapping**：
  - MongoDB 已覆蓋於：5 篇 outline 都未提此 frame
  - Cosmos DB 已覆蓋於：`mongodb-api-vs-sql-api.md` 開頭一段提兩 API、但沒把 multi-model 當差異化價值論述
  - **該補但漏了**：`mongodb-api-vs-sql-api.md` 邊界整合段該補「multi-model 差異化 — Cosmos DB 是唯一單服務覆蓋 5 API」、給讀者 vendor selection 的 framing
  - **Outline 缺口**：Cosmos DB outline 缺 multi-model strategic framing、容易讓讀者看不出 Cosmos DB 的 *選型 unique value*

### Finding F2.17：vendor dogfood 是 selection 訊號、但案例數字常不公開

- **來源**：9.C30 Microsoft 365「Microsoft 自家產品 dogfood Cosmos DB」段 + 警示「案例沒有提具體 throughput、latency、cost 數字。Microsoft 內部數字通常不公開、跟 AWS / GCP 案例的數字密度差很多」
- **Case 類型**：medium case + 自承知識缺口
- **揭露內容**：Microsoft 365 dogfood Cosmos DB、跟 Amazon Prime Day 用 DynamoDB、Google 自家用 Spanner一樣 — 雲商旗艦 DB 都會用在自家旗艦產品。讀此類 dogfood 案例的權重應該高、因為「雲商自己賭身家」。但 dogfood case 的具體數字通常不公開、跟 AWS / GCP 公開案例的數字密度差很多。
- **Outline mapping**：
  - MongoDB 已覆蓋於：N/A（MongoDB 沒 dogfood 同類概念）
  - Cosmos DB 已覆蓋於：`mongodb-api-vs-sql-api.md` 引用 Microsoft 365 但沒用 dogfood frame
  - **該補但漏了**：`mongodb-api-vs-sql-api.md` 引用 9.C30 時、該明示「Microsoft 365 dogfood = 高權重 selection signal、但數字不公開、不能直接抄」、避免讀者把 dogfood 當 production benchmark
  - **Outline 缺口**：Cosmos DB outline 引用 9.C30 case 時、要處理 *dogfood frame 的限制*

### Finding F2.18：Federated DB（多 DB 按 workload 分流）是 production 常態、不是「全用 X」

- **來源**：9.C36 Coinbase「federated DB（MongoDB + DynamoDB）按 workload 分流」段
- **Case 類型**：rich case（具體配置：MongoDB Atlas 主資料層 + DynamoDB 部分 workload + Memcached cache + 自研 mongobetween proxy）
- **揭露內容**：Coinbase 的 production 配置不是「全用 MongoDB」也不是「全遷 DynamoDB」、是按 workload 形狀分流：document-shaped 用 MongoDB、access pattern 固定的 KV 用 DynamoDB。case 對照 9.C23 Netflix Aurora consolidation（Netflix 走整合方向、Coinbase 走 federated）— 兩種架構策略都有合理 trigger。
- **Outline mapping**：
  - MongoDB 已覆蓋於：5 篇 outline 都未提此 frame（容易讓讀者以為要「全用 MongoDB」）
  - Cosmos DB 已覆蓋於：`mongodb-api-vs-sql-api.md` 隱含對照（Atlas 跨雲 vs Cosmos DB Azure-only）、但沒展開「按 workload 分流」frame
  - **該補但漏了**：`schema-design-pattern.md` 或 `shard-key-selection.md` 的 anti-recommendation 段該補「不是所有資料都該進 MongoDB、document-shaped + 形狀變化頻繁的進、access pattern 固定的 KV 走 KV」
  - **Outline 缺口**：MongoDB outline 缺 *跨 DB 分工* 視角、寫 production 系統時的選型紀律

---

## Outline 校準建議

### Keep（findings 充分支撐、結構良好）

- `cosmosdb/consistency-levels-engineering.md` — F2.14 充分支撐、5 level + case 對應扎實
- `cosmosdb/partition-key-design.md` — F2.13、F2.15 充分支撐、synthetic / composite / hierarchical 三模式對應 case
- `cosmosdb/ru-cost-model-sizing.md` — F2.11、F2.12 支撐、三種容量模式 + case 對應扎實
- `cosmosdb/multi-region-write-conflict.md` — F2.14 支撐、conflict resolution 三模式扎實
- `mongodb/shard-key-selection.md` — 機制完整、F2.6、F2.15 可補強

### Rewrite（framing 需校準）

- `cosmosdb/mongodb-api-vs-sql-api.md` — 開頭「為何選 Cosmos DB MongoDB API」段太單薄、要補三型遷移路徑對照（F2.1）+ dogfood frame 限制（F2.17）+ multi-model 差異化（F2.16）；現只說「Azure 生態 lock-in」太弱
- `mongodb/schema-design-pattern.md` — 把 frame 從「embedded vs reference」推到「contract layer 在哪」（F2.3）— validator 是 DB 層契約、abstraction layer 是 app 層契約、要明說兩者選一或並用
- `mongodb/replica-set-read-preference.md` — 補「causal consistency session（DB 層）vs freshness token（cache 層）」對照（F2.4）、不只是 DB 內機制
- `cosmosdb/ru-cost-model-sizing.md` 問題情境段 — 補「團隊從 CPU + IOPS 思維轉到 RU 思維」學習曲線（F2.12）

### Add（findings 揭露但 outline 沒覆蓋的新主題）

- **新 sibling: `mongodb/connection-management-and-cache-layer`** — F2.2（connection storm）+ F2.4（cache + freshness token）+ F2.5（predictive scaling）合成一篇、處理「應用層怎麼連 MongoDB cluster」議題、補 5 篇 outline 集體缺的 *connection layer* 視角
- **新章節（已有 outline 內補段）**：`schema-design-pattern.md` 失敗模式段補 time-series collection（F2.8）；`shard-key-selection.md` anti-recommendation 補單 cluster vs 多 cluster（F2.6）；`mongodb-api-vs-sql-api.md` 補跨雲 vs 單雲 hedging frame（F2.10）+ federated DB（F2.18）；`multi-region-write-conflict.md` 容量觀測補「廣告 SLA vs 實測可用性」拆解（F2.7）

### Scope warning（over-extrapolation 風險）

- **Microsoft 365 case（9.C30）的數字盲區**：case 自承沒提具體 throughput / latency / cost、引用時 *只能用 frame*（dogfood / multi-model / 遷移路徑）、不能編造數字（陷阱 1 風險）
- **Toyota time-series collection（F2.8）**：case 自承沒揭露 Toyota 是否實際使用 time-series collection、寫 outline 時要寫成「IoT 場景該考慮 X、Toyota case 未揭露是否實際使用」、不能寫成「Toyota 使用 time-series collection」（陷阱 1：skeleton 擴寫成 fact）
- **Coinbase 1.5M reads/sec（F2.4）**：case 明示是 *合成數字*、寫進 outline 時要明示「應用層觀察值、含 cache、不是 MongoDB 純讀取」（陷阱 4：rich case 觀察 vs 判讀分層）
- **Forbes 25% TCO 降幅（9.C37）**：case 明示是 *特定流量規模下的數字*、不普適、引用時要帶條件、不能寫「Atlas 比自管便宜 25%」（陷阱 4：rich case 觀察 vs 判讀分層）
- **跨 case 合成 frame 風險**（F2.1、F2.11、F2.18）：三型遷移路徑、負載形狀分類、federated DB 都是 *本章合成 frame*、case 原文沒這個 frame、寫進 outline 時必須明示「本章合成、非 case 原文框架」（陷阱 8）

---

## Document model 跨 vendor frame

讀完 7 個 case 後浮現的 document model 跨 vendor 共通議題、影響 MongoDB / Cosmos DB / DynamoDB document-API 三方對比、跟整體 DB3 reader journey 的 frame 建議。

### Frame 1：document model 不是 schema-less、是 *contract layer 在哪* 的設計選擇

document model 廣告「schema flexibility」、但 production 跑下來、Toyota 跟 Forbes 都揭露：彈性必須以 schema governance 對沖、否則變成 data inconsistency。三條 contract layer 路徑：

- **DB-layer contract**：MongoDB `$jsonSchema` validator、Cosmos DB 沒原生對等（要靠 SDK 或 stored proc）
- **app-layer contract**：abstraction layer（Forbes 走這條）、middleware / SDK 包裝
- **混合**：Atlas Application Services 的 schema 跟 Cosmos DB 的 stored proc 都屬此

讀者選 vendor 時要看 *哪層 contract* 已有原生工具、不只是看 wire compat。

### Frame 2：document model 跨雲遷移阻力低於 KV / SQL、是 vendor selection 的關鍵 hedging

Forbes case 揭露：document model 的「同 DB 換託管」遷移 6 個月完成、保留 schema 跟 access pattern。對比：

- **SQL 遷移**（如 Aurora 跨雲）：schema 跨方言、stored proc 不可移植
- **KV 遷移**（如 DynamoDB → Cosmos DB Table API）：access pattern 完全重設計（9.C20 Zomato 走過）
- **Document 遷移**（如 Forbes Atlas、9.C30 Microsoft 365）：wire compat + document shape 跨 vendor 可移植度高

對 *未來雲商策略尚未底定* 的團隊、document model 比 SQL / KV 更適合 hedging。但要注意：vendor dogfood case（Microsoft 365）數字不公開、不能當 benchmark；Atlas 跨雲 vs Cosmos DB Azure-only 是 hedging vs Azure 生態 lock-in 的真實 trade-off。

### Frame 3：document model 的 capacity 議題是 *RU / WCU/RCU 抽象* vs *CPU / IOPS 思維* 的差別、不只是擴展性

MongoDB / Cosmos DB / DynamoDB 三家 document API 在 capacity 思維上分裂：

- **MongoDB**：CPU + IOPS + working set RAM 三軸思維、自管 sharding、`reshardCollection` 可改但成本高、擴容是天級
- **Cosmos DB**：RU 抽象單位、autoscale / serverless 即時、partition key 不可改、容量規劃變成「RU 預算」
- **DynamoDB**：WCU/RCU 抽象單位、on-demand / provisioned、adaptive capacity 補 hot partition、partition key 可改（用 backfill）

讀者選 vendor 時要看團隊熟悉哪種思維、轉換成本可能高過 vendor 廣告的價格差距（F2.12）。

### Frame 4：document model production 跑下來、*單一 DB 撐不下* 是常態、要 federated / cache / proxy 補

Coinbase（federated MongoDB + DynamoDB + Memcached + mongobetween）、Toyota（20 個 Atlas DB + Kinesis + Lambda + Redis）、Forbes（Atlas + abstraction layer + 50+ microservice）— 三個 rich case 都是 *DB + 周邊工具* 組合、不是 DB 一個服務搞定。MongoDB / Cosmos DB outline 寫起來容易聚焦 DB 自身機制、漏掉 production 真實系統的 *跨層架構*。

### 整體 DB3 reader journey frame 建議

讀者路徑應該分三層：

1. **vendor 選型層**：dogfood / multi-model / 跨雲 hedging（F2.16、F2.17、F2.10）— 進 `mongodb-api-vs-sql-api.md` 開頭
2. **機制深化層**：schema / partition / consistency / RU / aggregation / replica / change stream（現有 10 個 outline 主體）
3. **production 跨層架構層**：connection / cache / federated / capacity 形狀 / SLA 鏈路（F2.2、F2.4、F2.7、F2.11、F2.18）— 需新 sibling 或 outline 內補段

這三層在現有 10 個 outline 比重失衡：機制深化層（第 2 層）佔太多、選型層（第 1 層）跟跨層架構層（第 3 層）薄弱、要校準。
