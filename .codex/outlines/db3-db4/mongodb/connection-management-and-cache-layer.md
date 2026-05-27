# MongoDB Connection Management and Cache Layer：driver × 部署模型 × cache × predictive scaling

> **Status**: L5 outline skeleton（planning artifact、非 published article、新 sibling）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。
>
> **校準說明**：本 outline 由 case-first audit 新建、補 MongoDB 5 篇既有 outline 集體缺的 *connection layer + cache layer + scaling trigger* 視角（F2.2 / F2.4 / F2.5 來源、9.C36 Coinbase 為 primary case anchor）。frame 是「應用層連 MongoDB cluster 的真實架構不只是 driver、是 driver × 部署模型 × cache layer × scaling trigger 的合成」、Coinbase 1.5M reads/sec 不是 MongoDB 單一服務扛下、是這個跨層架構合成的結果。

## 問題情境（Production pressure）

- **大規模 OLTP 撞 connection ceiling**：應用層 deploy 規模一上來、單一 MongoDB cluster 看到 connection storm — 60K connections/min（9.C36 Coinbase 揭露：Ruby + GVL + blue-green deploy 把 instance 數 ×2、連線數隨之 ×2）；MongoDB cluster 的 connection limit 撞牆、新 deploy 連不上、線上服務 cascade 失敗
- **單純加 replica 撐不住大規模 read**：讀者把所有 read 都打 secondary、replica 加到 5-7 仍撐不住 sustained 高 read（>500K reads/sec）；replication lag 升 + secondary CPU 飽和；單靠 MongoDB cluster 內機制（replica scaling + read preference）拿不到那個量級
- **Cluster 擴容是天級議題、不是即時擴容**：MongoDB cluster 擴容傳統路徑 70 分鐘（9.C36 Coinbase 揭露口徑：reactive scaling 起點到擴容完成）；surge 開始時才動來不及、預測性流量必須提前出手
- **Surge 形狀不規則**：加密貨幣 surge（隨外部市場波動）/ 媒體爆量（事件驅動）/ IoT 緊急通報（雙模式並存）— 都不適合單純 reactive auto-scaling 接住、必須 predictive + reactive 兩段式
- 讀者徵兆：MongoDB Atlas console 看到 connection count 在 deploy 後 spike 到上限、p99 read latency 在事件時段集體爬、Atlas auto-scaling event log 顯示 *triggered too late*、cache hit rate 跟 read latency 反向相關
- Case anchor: primary [9.C36 Coinbase](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/)（rich case、含具體數字 60K → 2K connections / 1.5M reads/sec 含 cache / 70 → 25 分鐘擴容）；side-light [9.C38 Toyota Connected](/backend/09-performance-capacity/cases/toyota-connected-mongodb-telematics-iot/) 雙模式負載敘事（持續 sensor + 緊急事件）、[9.C37 Forbes](/backend/09-performance-capacity/cases/forbes-mongodb-atlas-multi-cloud-migration/) 媒體爆量形狀

## 核心機制（Vendor-specific mechanism）

### 三層合成 frame（本章合成、case 原文沒這個 frame）

跨案合成 frame：應用層連 MongoDB cluster 在大規模 production 是 *三層協作*、不是 driver 一個元件：

| 層次                    | 角色                                     | 9.C36 Coinbase 對應元件                   |
| ----------------------- | ---------------------------------------- | ----------------------------------------- |
| Driver / Proxy          | 連線多工、應用 process 跟 cluster 的橋接 | MongoDB driver + mongobetween proxy       |
| Cache + freshness token | read scaling 主路、跨層一致性協議        | Memcached + freshness token + OCC version |
| Scaling trigger         | cluster 擴容啟動時機                     | ML predictive scaling + reactive fallback |

三層缺一都會在大規模時撞牆。本文聚焦這三層如何協作、單一層的深度議題（read preference 機制、schema 治理、aggregation pipeline）推到 sibling。

### Driver / Proxy 層（F2.2、9.C36 Coinbase mongobetween）

- **MongoDB driver 原生 connection 模式**：driver 在 application process 內維護 connection pool、每個 process 跟 MongoDB cluster 開固定數量 socket
- **跨 process connection 多工問題**：driver 沒跨 process pool — 跟 PostgreSQL 走 pgbouncer 是同樣需求
- **Connection storm trigger**：
  - 部署模型放大 process 數：CRuby + GVL 強制每 CPU core 一 process、blue-green 部署 instance 數 ×2、連線數隨之 ×2（9.C36 Coinbase 揭露：單 cluster 看到 60K connections/min）
  - 微服務數量多：50+ microservice 各自連 cluster、每服務 connection 加總後撞上限（9.C37 Forbes side-light）
- **mongobetween proxy**：Coinbase 自建、把多 application process 的連線合成少量到 MongoDB cluster 的連線、connection 從 60K 降到 ~2K（一個量級）
- **Scope warning（必明示）**：mongobetween 是 Coinbase 為 Ruby + GVL 需求自建、case 自承「Go / Java / Node.js 應用因原生支援連線多工、通常不需要這層 proxy」；寫稿時不能寫成「MongoDB 在大規模都需要 mongobetween」、要寫成「特定部署模型才需要」

### Cache + freshness token 層（F2.4、9.C36 Coinbase）

- **觸發條件**：直接打 MongoDB 不可能撐 1.5M reads/sec（口徑：users 服務應用層觀察、含 cache、非 MongoDB cluster 純讀取）
- **cache + DB 一致性問題**：write 進 MongoDB primary、cache 還是舊版、user 下次 read 拿到舊資料
- **freshness token 機制**：write 成功給 client token（含 OCC version / clusterTime）、client read 帶 token、server 保證返回的資料版本 ≥ token、必要時 bypass cache 直接打 DB
- **跟 DB 層 causal consistency session 對照**：causal session 解 MongoDB 內 read-your-own-write、freshness token 解 *DB + cache 跨層* read-your-own-write；機制細節見 [replica set read preference](./replica-set-read-preference.md)、本文不重複展開
- **Scope warning（必明示）**：1.5M reads/sec 是 *users 服務 + cache* 合成數字、不是 MongoDB cluster 純讀取 benchmark；寫進文章必須明示口徑、避免讀者把 1.5M reads/sec 當成「MongoDB 單獨能撐」

### Scaling trigger 層（F2.5、9.C36 Coinbase predictive scaling）

- **MongoDB cluster 擴容時間**：傳統 reactive scaling 起點到完成 ~70 分鐘（9.C36 Coinbase 揭露口徑：含 instance provisioning + 資料 sync + balancer rebalance）
- **Reactive 為主撐不住快變流量**：CPU / queue 觸發 reactive scaling 在 surge 開始時才動、來不及；surge 已經結束擴容才到位
- **Predictive scaling 機制**：用外部訊號（加密貨幣價格、賽事行程、票務開賣時間）訓練 ML 模型、提前 60 分鐘預測流量、預先擴容、把擴容啟動時間從 70 分鐘壓到 25 分鐘（口徑：trigger 提前、不是擴容本身變快）
- **Predictive + reactive 並存紀律**：case 警示「ML 預測有 false positive / false negative、Coinbase 沒揭露準確率、所以仍保留 reactive scaling 作為 safety net」；寫稿時要明示兩段式設計、不能寫成「Predictive scaling 取代 reactive scaling」

對應 knowledge card: [connection-pool](/backend/knowledge-cards/connection-pool/)（若存在）、[stale-read](/backend/knowledge-cards/stale-read/)、[session-consistency](/backend/knowledge-cards/session-consistency/)、[hot-partition](/backend/knowledge-cards/hot-partition/)（cache 失效時打穿 DB 的 hot key）

## 操作流程（Operations）

- Step 1：**connection ceiling audit** — 量測現有 deploy 在 peak 的 connection count、推算 deploy ×2 / 微服務新增時 connection 走勢；對照 MongoDB cluster 的 hard limit（Atlas tier 決定、典型 1500-32000）
- Step 2：**部署模型判讀** — 若部署模型放大 process 數（CRuby + GVL / 大量微服務 / blue-green 雙環境）、需 proxy 層；若用 Go / Java / Node.js 單一 binary 多 thread、原生 driver pool 通常夠
- Step 3：proxy 選型 — Coinbase mongobetween 是參考實作、社群還有 mongoproxy / DocumentDB 內建 connection multiplexer；自建 proxy 是 Coinbase 規模才合理、中型團隊先評估 Atlas tier 升級
- Step 4：**cache layer 設計**（read scaling 主路）：
  - 前置 Memcached / Redis、cache key = collection + document id + version
  - Write API 返回 `{result, version_token}` — token 含 OCC version 或 MongoDB clusterTime
  - Read API 接受 optional version token、cache lookup 比對 entry version 跟 token、低於就 invalidate + bypass
  - DB 層 fallback `readConcern: "majority"` 保證返回 version ≥ token
- Step 5：**predictive scaling 設計**（適用「外部訊號可預測流量」）：
  - 識別 driver 訊號：加密貨幣價格 / 賽事行程 / 票務開賣 / 促銷活動 / IoT 緊急事件預警
  - 訓練 ML：用歷史流量 vs 訊號 correlation 訓練、輸出未來 30-60 分鐘流量預測
  - 觸發擴容：預測超 threshold 時主動 trigger Atlas scaling API、不等 reactive metric
  - **保留 reactive safety net**：ML failure 時 reactive scaling 仍會接、不可拿掉
- Step 6：**全鏈路驗證**：staging 灌入 deploy ×2 模擬 connection storm、灌入 stale cache 驗證 freshness token bypass、放假流量驗證 predictive scaling trigger
- 驗證點：connection count 在 deploy 後不爆 cluster limit、cache hit rate vs freshness bypass rate 比例正常（典型 cache hit > 90% + bypass < 5%）、predictive scaling 領先窗 ≥ 30 分鐘、reactive scaling 仍保留作 safety
- Rollback boundary：proxy 層可下線（流量改直連 cluster、但短時 connection storm 風險回來）；cache 層可下線（read 全部打 DB、需 cluster 容量能撐）；predictive scaling 可下線（退回純 reactive、但快變 surge 接不住）；三層都要設計 graceful degradation

## 失敗模式（Failure modes）

- **Connection storm during deploy**：blue-green 部署 instance 數 ×2、connection 隨之爆、新 deploy 連不上 cluster、cascade 失敗；解法 — proxy 層 + cluster connection limit 預留 headroom
- **Proxy 變成單點瓶頸**：mongobetween / pgbouncer 風格 proxy 自己變熱點、proxy 故障時下游全死；解法 — proxy 集群 + health check + 客戶端 retry
- **Cache hit rate 崩塌**：cache 失效 + 大量 read bypass、DB 突然吃 100% 流量、cluster 飽和；解法 — freshness token 設計時要監控 bypass rate、過高表示 cache invalidation 邏輯有問題
- **Freshness token 漏寫**：write 沒帶 token / client 沒帶 token、token silently 失效、user 拿到舊資料；解法 — protocol 強制（middleware 攔截 write / read、自動帶 token）
- **Predictive scaling false positive 浪費容量**：ML 預測 surge 但實際沒來、cluster 預先擴容後閒置；接受成本、保留 ML model retraining
- **Predictive scaling false negative 漏接 surge**：ML 沒預測到、cluster 沒提前擴、surge 來時 reactive scaling 開始動但 70 分鐘來不及；解法 — reactive safety net + 服務降級（限流 / 部分 read 降級拿舊資料 + freshness token 告警）
- **三層協作脫節**：proxy 擋住 connection storm 但 cluster 內部 read scaling 沒設計、application 仍打爆；三層必須一起設計、不是各自獨立
- Anti-recommendation：
  - 中小流量（< 100K reads/sec、單 deploy < 50 instance）不需要這三層；Atlas tier 升級 + cluster 內 replica + 簡單 cache 就夠
  - mongobetween 風格 proxy 只在 Ruby + GVL / 類似部署模型才必要、Go / Java / Node.js 通常不需要（case 自承）
  - Predictive scaling 只在外部訊號可預測時有效；無預測訊號的純隨機 surge 還是回 reactive + headroom
  - 大規模 OLTP 不該為了省成本拿掉 cache 層；read scaling 主路就是 cache、單靠 MongoDB cluster 拿不到 1.5M reads/sec 量級

## 容量與觀測（Capacity & observability）

- 關鍵 metric：
  - **Connection 層**：cluster connection count / Atlas tier limit / proxy 到 cluster 的 connection multiplex 比、deploy 前後 connection 走勢
  - **Cache 層**：cache hit rate、freshness token bypass rate、cache key collision rate
  - **Scaling 層**：predictive scaling trigger event count / 領先窗、reactive scaling fallback 觸發頻率、實際擴容啟動到完成時間、ML 預測準確率（precision / recall）
- Mongo / Atlas command：`db.serverStatus().connections`、`db.currentOp({})` 看 connection 使用、Atlas API 看 cluster scaling event
- Application observability：APM 看 connection acquire latency、cache hit rate time series、freshness token 流動完整性（write 是否發 token、read 是否帶 token、cache 是否驗 token）
- 回到 [4.20 observability evidence](/backend/04-observability/observability-evidence-package/)：把 connection storm event、cache hit rate / bypass rate、scaling trigger leadtime 列為跨層 evidence 三件套
- 回到 [9.5 bottleneck localization](/backend/09-performance-capacity/bottleneck-localization/)：大規模 OLTP 撞牆時要區分 (a) connection ceiling (b) cache hit rate 下降 (c) cluster 內 replica 飽和 (d) scaling 跟不上

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：
  - [replica set read preference](./replica-set-read-preference.md)（DB 層 causal session 機制、freshness token 跨層協議；本文聚焦三層協作、那篇聚焦 DB 層機制）
  - [shard key selection](./shard-key-selection.md)（cluster 擴容是天級議題、是 scaling layer 的 trigger；單 cluster vs 多 cluster 切分）
  - [schema design pattern](./schema-design-pattern.md)（app-layer abstraction 跟本文 cache + freshness token 同層協作、contract layer 三選一）
  - [aggregation pipeline optimization](./aggregation-pipeline-optimization.md)（report dashboard 跑爆 primary 的補位路徑是本文的 cache + read scaling、不是讓 aggregation 自己優化）
- Migration playbook：
  - federated DB 模式（F2.18、9.C36 Coinbase MongoDB + DynamoDB）— 不是「全用 MongoDB」、document-shaped 用 MongoDB、access pattern 固定的 KV 用 DynamoDB；對應 [DynamoDB vendor page](/backend/01-database/vendors/dynamodb/) 跨 vendor 對照
  - 跨雲 hedging（F2.10、9.C37 Forbes 跨雲彈性）— Atlas 跨 AWS / GCP / Azure 是規避未來雲商鎖定的 selection 訊號
- 跟 1.x 互引：
  - [1.6 高併發資料存取](/backend/01-database/high-concurrency-access/) 處理 connection storm 通用模式（pgbouncer / mongobetween 對應）
  - [1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) 把三層架構列為大規模 OLTP 容量規劃必看點
  - [9.6 容量規劃模型](/backend/09-performance-capacity/) 處理 predictive scaling 的 ML 訓練紀律
  - [9.C2 GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) AI 預測式擴容跨 vendor 對照

## 寫作前置 checklist

- [ ] Case anchor：primary 9.C36 Coinbase 充分（含具體數字 60K → 2K / 1.5M reads/sec / 70 → 25 分鐘 / 60 分鐘領先窗）；side-light 9.C37 Forbes 媒體爆量形狀 + 9.C38 Toyota 雙模式負載
- [ ] Knowledge card 雙引用：connection-pool（若存在）/ stale-read / session-consistency / hot-partition
- [ ] Sibling 對比清楚：本文是「三層協作合成 frame」、不是單一機制深化；DB 層機制細節在 read preference、schema 細節在 schema design、shard 細節在 shard key selection；本文只談跨層協作
- [ ] Fact vs derive 分層（陷阱 4 防護、本文最高風險）：
  - 9.C36 Coinbase 揭露事實：「mongobetween 把連線從 60K 降到 2K」、「用 ML 預測加密貨幣 surge 把擴容時間從 70 → 25 分鐘」、「freshness token 配合 Memcached 撐應用層觀察的 1.5M reads/sec」— 寫文章時直接引用 + 附口徑
  - 跨案合成 frame：「三層協作（driver × cache × scaling）是大規模 OLTP 必走」是本章合成、case 原文沒這個 frame、寫文章時明示「本章合成」
  - 通用工程估算：cache hit rate > 90% / proxy 集群 health check / ML retraining 頻率 — 屬通用工程經驗、case 未揭露具體數字、寫文章時標明「屬通用工程估算」
- [ ] Scope warning（必明示、本文最高風險）：
  - **mongobetween caveat**：Coinbase 為 Ruby + GVL 需求自建、case 自承「Go / Java / Node.js 應用通常不需要」、寫文章時不可寫成「大規模 MongoDB 都需要 mongobetween」
  - **1.5M reads/sec 口徑**：users 服務應用層觀察、含 cache、非 MongoDB cluster 純讀取；寫文章時必須明示
  - **70 / 25 分鐘擴容時間口徑**：Coinbase 特定環境（cluster tier / 資料量 / Atlas API），非 MongoDB 普遍承諾、不可寫成「MongoDB cluster 擴容都要 70 分鐘」
  - **predictive scaling 適用範圍**：只在外部訊號可預測時有效、非普適、必須保留 reactive safety net
- [ ] 預估寫作長度：320-380 行（三層合成 frame 是新主軸、需多花篇幅鋪三層各自的議題 + 整合操作流程；Coinbase rich case 數字密度高、需多段對應 + 口徑說明）
