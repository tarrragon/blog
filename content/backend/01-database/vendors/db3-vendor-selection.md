---
title: "DB3 Vendor Selection：document / KV / multi-model 三方選型 + workload shape 前置判讀"
date: 2026-05-27
description: "MongoDB / DynamoDB / Cosmos DB 三家 NoSQL 選型 entry point：workload shape × access pattern × consistency 三軸前置判讀、migration path 三型、federated DB 視角、三 vendor 對比 10 軸"
weight: 1
tags: ["backend", "database", "vendor-selection", "nosql", "mongodb", "dynamodb", "cosmosdb", "decision-tree", "deep-article"]
---

DB3 vendor selection 的核心責任是把讀者從「我該選 MongoDB / DynamoDB / Cosmos DB 哪一家」這個問題、推到「我的 workload 是 document / KV / multi-model 哪一類」這個更前置的問題。三家文件都標榜 scalable schema-less、但實際取捨在 *資料形狀、access pattern 穩定度、consistency 可接受度* 三軸決定 — 不識別 workload shape 直接比 vendor 是源頭錯誤。本文是 DB3 reader 進來的第一站：先做 workload shape 三軸前置判讀、再過 migration path 三型 + federated DB 視角、最後落到三 vendor 對比 10 軸。

本文 *不* 展開 vendor 機制細節（partition key 設計 / consistency level / RU sizing / connection management 等）— 那些屬 per-vendor deep article 的責任、本文在每個軸後 cross-link 過去。本文也 *不* 比較三家「誰比較強」— 三 vendor 在 workload-by-workload 適配光譜上各有位置、寫成優劣比較會誤導讀者把選型壓成單軸。

## 問題情境：讀者進來時的真實壓力

典型啟動壓力分兩類：

第一類、團隊評估 document / KV / multi-model NoSQL 三家、文件都說「scalable schema-less」、看不出實際取捨。讀者徵兆是「我的資料是 document-shaped 還是 KV-shaped？」「partition key 該怎麼選？」「Atlas 跟 Cosmos DB MongoDB API 不一樣的點在哪？」「Cosmos DB multi-model 是真用得到還是行銷話術？」「on-demand vs provisioned 怎麼選？」

第二類、既有 PostgreSQL / MySQL workload 撞 connection limit（surge 下 1K-5K pool 是隱性天花板、F1.7）、想換 KV 但不知道是否適合。讀者徵兆是「我已經有 Memcached、還要再加 MongoDB cache 層嗎？」「DynamoDB 適合當 OLTP 嗎？」「換 NoSQL 是不是解 connection 問題的銀彈？」

這兩類讀者進來時的 *真實問題* 不在 vendor 之間、在 *workload 自己屬哪一型*。Case anchor 覆蓋六個 unique 角度：

- 多型 document workload — [9.C38 Toyota Connected](/backend/09-performance-capacity/cases/toyota-connected-mongodb-telematics-iot/)（車載 sensor schema 隨車型演進、20 個 Atlas DB blast radius 切分）
- Document 跨雲 hedging — [9.C37 Forbes](/backend/09-performance-capacity/cases/forbes-mongodb-atlas-multi-cloud-migration/)（自管 → Atlas、6 個月遷移、跨雲彈性）
- 同 model 換 vendor 的 dogfood signal — [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/)（MongoDB → Cosmos DB MongoDB API、保留 driver、wire compat 限制）
- KV-as-buffer 正向用例 — [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)（DynamoDB 寫入緩衝、6750x 彈性、後端慢消費）
- PK 天然均勻典範 — [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)（90M reads/sec 年度峰值、KV pattern 純粹）
- Federated DB 真實系統 — [9.C36 Coinbase](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/)（MongoDB + DynamoDB + Memcached + mongobetween + freshness token）

## Workload shape × access pattern × consistency 三軸前置判讀

進三家 vendor 對比前先回答：你的 workload 屬哪一型？三軸的組合決定 vendor 候選清單、軸不識別清楚直接比 vendor 是把選型壓成「品牌偏好」、不是工程決策。

### 軸 1 — 資料形狀：document / KV / 不清楚

資料形狀的核心判讀是 *aggregate root 邊界是否明確* 跟 *schema 是否會隨產品演進新增欄位*。document 適合的場景是資料天然多型、單筆記錄欄位差異大、應用層用 aggregate root 模式存取；KV 適合的場景是資料形狀固定、access pattern 數量少（< 5 種）、固定 lookup by key。

| 訊號                                                                                         | 適配資料模型                                            | 對應 case                                                                                                                         |
| -------------------------------------------------------------------------------------------- | ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| 資料天然多型（不同記錄欄位不同）、隨產品演進 schema 增刪欄位、aggregate root 邊界明確        | Document（MongoDB / Cosmos DB SQL API / MongoDB API）   | Toyota sensor schema 隨車型演進、Forbes CMS article 欄位多型                                                                      |
| 資料形狀固定、access pattern < 5 種、固定 lookup by key（meeting_id / message_id / user_id） | KV（DynamoDB / Cosmos DB Table API / Redis 持久化變體） | Amazon Ads 用 ad_id 查、Disney+ 用 user_id 查 watchlist、PayPay 用 message_id 查通知                                              |
| 資料形狀還在探索、access pattern 變動頻繁、未來 6 個月會加 5+ 種新 query                     | 暫緩 NoSQL 選型、用 PostgreSQL + JSONB 過渡             | 屬讀者誤判常見模式、case 沒揭露但 F1.3 / F1.6 推論：NoSQL 假設 access pattern 穩定、未穩定就上 NoSQL 會撞 single-table 設計天花板 |

第三列的「暫緩 NoSQL」是反指標。NoSQL（特別是 DynamoDB single-table design）的核心假設是「access pattern 在設計時已知、後續變動有限」。資料模型還在探索、access pattern 半年內會大幅增減的場景、PostgreSQL + JSONB 給的彈性遠高於 NoSQL — JSONB 欄位可以演進、ad-hoc query 可以用 SQL 跑、未來釐清穩定 access pattern 後再選 NoSQL 不遲。

### 軸 2 — Access pattern 穩定度（KV 適用度前置判讀）

KV 適用度的核心判讀是 *partition key 天然均勻度*。partition key 不均勻會讓 vendor 廣告的「scale infinitely」變成「scale 到 hot partition 為止」、單一 logical key 流量超過該 partition 上限就 throttle 或 latency spike（F1.1）。

- **天然均勻 PK + 穩定 access pattern**（meeting_id / player_id / message_id / user_id）→ DynamoDB / Cosmos DB Table API 適用、PK 不需 composite key 修補。Amazon Ads 用 ad_id 撐 90M reads/sec、Zoom 用 meeting_id、Capcom 用 player_id、PayPay 用 message_id、Disney+ 用 user_id — 五個 case 都揭露同一 frame：*業務天然存在均勻 key 時 KV 是最自然的選擇*。
- **天然不均勻 PK**（event_id 一場演唱會集中 / date 時間序集中）→ 需 composite key 或 write sharding 修補。Tixcraft（9.C15）用 `event_id + user_id_hash` composite key 把單一熱門演唱會的 6750x spike 攤平到 partition 上 — 不是 DynamoDB 自身彈性、是 partition key 均勻分散的結果（F1.2）。
- **Access pattern 變動頻繁**（探索期、< 5 種 query 還會增加）→ 不適合 DynamoDB single-table design、回 RDB。Single-table 把 access pattern 編進 PK / SK 結構、增加新 query 等於改 schema、改 schema 等於重新 load 資料、成本不對。

KV 適用度判讀的延伸細節（hot partition 反模式 / composite key 設計 / adaptive capacity）見 [DynamoDB partition key antipatterns](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/)。

### 軸 3 — Consistency 需求是否可接受 eventual

Consistency 需求的核心判讀是 *跨 partition / 跨 region transaction 是否為產品契約*。三家 vendor 都支援單 partition / 單 region 強一致、但 cross-partition / cross-region transaction 的機制跟限制差異大。

- **可接受 eventual / session consistency**：DynamoDB（default eventually consistent reads、可選 strong）、Cosmos DB（5 個 consistency level、default session）、MongoDB（read concern 多級）— 三家都可以、選擇看其他軸。多數 KV / document workload 屬此類（social timeline、watchlist、message queue、analytics aggregation）。
- **需要強一致 cross-partition transaction**：DynamoDB 跨 partition transaction 限制（單一 transaction 最多 100 個 action、跨 region 不支援）、MongoDB 4.0+ 支援 multi-document transaction 但 sharded cluster 仍有 limitation、Cosmos DB 跨 logical partition transaction 受限 — 都不如 SQL／distributed SQL 自然、應回 DB4 entry point 評估 [Aurora DSQL / Spanner / CockroachDB](/backend/01-database/vendors/cockroachdb/aurora-dsql-spanner-decision-tree/)。
- **跨 region active-active write**：三家機制完全不同 — Cosmos DB multi-region write 跟 Strong consistency 是 *互斥* 設定（CAP 取捨硬約束、見 [Cosmos DB multi-region write conflict](/backend/01-database/vendors/cosmosdb/multi-region-write-conflict/) SSoT 主寫位置）；DynamoDB Global Tables 走 LWW（last-writer-wins）conflict resolution；MongoDB Atlas 跨 region 需手動 conflict 處理。三家不在同一光譜、選擇前必看各 vendor outline 的機制段。

## Migration path 三型（跨 case 合成 frame）

> 本段是 *跨 case 合成 frame*、不是單一 case 揭露 — 從 Coinbase（9.C36）/ Forbes（9.C37）/ Microsoft 365（9.C30）三 case 萃取的共通結構（F2.1）。

讀者進來時通常不是綠地、是 *既有系統演進*。三型遷移路徑的風險、ROI、適用條件完全不同、選錯路徑會推到錯的 vendor。

### 第一型：保留原 DB + 補周邊工具

不換 vendor、加 connection proxy（mongobetween / pgbouncer 類）、加 cache（Memcached + freshness token）、加 predictive scaling — 主資料層不動、應用層跟 ops 層補強。

- **代表 case**：Coinbase（9.C36）保留 MongoDB Atlas、自建 mongobetween 把 60K connections/min 降到 ~2K（一個量級）、用 Memcached + freshness token 撐 1.5M reads/sec、用 ML predictive scaling 把擴容時間從 70 → 25 分鐘提前 60 分鐘
- **路徑成本**：中（自建工具、需要工程資源 build & operate proxy / cache layer / ML model）
- **風險**：低（主資料層不動、回滾代價小）
- **ROI**：保留主資料 schema + access pattern、解 driver / 部署模型 / cache 一致性瓶頸
- **適合**：MongoDB（或主 DB）資料層撐得住、但應用層 connection storm / cache miss / 擴容慢卡瓶頸；團隊有工程能力 build 跟 maintain 周邊工具

延伸實作細節見 MongoDB connection management（per-vendor article、cross-link 待寫稿）。

### 第二型：同 DB 換託管

自管 → managed（Atlas / Cosmos DB / DocumentDB）、保留 schema 跟 access pattern、遷移期 6 個月量級。

- **代表 case**：Forbes（9.C37）自管 MongoDB → MongoDB Atlas、保留 CMS schema、6 個月遷移、揭露「TCO 改善 25%」
- **路徑成本**：中（dual-write + shadow read 驗證、driver 行為差異、operation runbook 重寫）
- **風險**：中（dual-write 期間雙寫一致性、cutover 時點選擇）
- **ROI**：operation transfer（DBA bandwidth 釋放給 schema design / query tuning）+ TCO 改善
- **適合**：自管 ops burden 大（DBA bandwidth 被 backup / patching / replica lag 吃光）、不想換 model

**Scope warning（Forbes 25% TCO）**：「25% TCO 改善」是 Forbes 特定流量規模（120M MAU、70+ Atlas region）下的數字、*不普適*。引用要帶條件 — 不要寫成「Atlas 比自管便宜 25%」這種 vendor-neutral 結論。實際省多少要看自管當下的 license / hardware / ops 工時分配、跟 Atlas 在你流量規模下的 pricing tier。

### 第三型：換 vendor 保留 model

MongoDB → Cosmos DB MongoDB API、或 MongoDB → DocumentDB — wire protocol + driver 不變、底層架構整個換、ops 模型整個換。

- **代表 case**：Microsoft 365（9.C30）MongoDB → Cosmos DB MongoDB API、保留 MongoDB driver
- **路徑成本**：高（dual-write per query pattern 驗證、wire compat ≠ 100% 行為相同、aggregation pipeline 跟 transaction 行為要逐項驗證）
- **風險**：高（每個 query pattern 都可能踩到不相容 edge case、cutover 點選擇難）
- **ROI**：跨 vendor 換（Azure 生態 / multi-model API / global distribution）+ 保留應用層 driver code

**Scope warning（Microsoft 365 dogfood）**：Microsoft 365 是 Microsoft 自家 dogfood、case 沒揭露具體 throughput / latency / cost 數字（F2.17）。dogfood 是 *高權重 selection signal*（雲商賭自家旗艦產品）、但 *不是 production benchmark*（沒公開數字可比對）。引用要明示「dogfood signal」而非「production proof」。

**Scope warning（100% wire compat）**：Cosmos DB MongoDB API 廣告「100% wire compatibility」是 *vendor 行銷話術*、實際是「在某些 query pattern 下相容」（F2.9）。遷移時必須 *dual-write per query pattern* 驗證 — 不是看 vendor 文件 spec list、是用 production query corpus 跑一遍實測行為。Phase 0 audit checklist 應列出 unsupported aggregation stage、transaction edge case、index behavior 差異、change stream 跟 Change Feed 對應關係。

延伸 Cosmos DB MongoDB API vs SQL API 選型見 [Cosmos DB MongoDB API vs SQL API](/backend/01-database/vendors/cosmosdb/mongodb-api-vs-sql-api/)。

### 第四型不在 DB3 範圍：paradigm shift 換引擎

KV → SQL 或 SQL → distributed SQL 屬 paradigm shift、應進 [DB4 entry point: Aurora DSQL / Spanner / CockroachDB decision tree](/backend/01-database/vendors/cockroachdb/aurora-dsql-spanner-decision-tree/)。本文範圍是 DB3 三家內部選型、不展開 paradigm shift。

## Federated DB + system role 視角（跨 case 合成 frame）

> 本段也是 *跨 case 合成 frame*（F2.18 + F1.6）— 三個 rich case（Coinbase / Toyota / Forbes）都揭露 production 系統是 *DB + 周邊工具* 組合、不是單一 DB monolithic 撐起來。

讀者常誤以為「全用 X」是正解 — 全用 MongoDB、或全遷 DynamoDB、或全換 Cosmos DB。真實 production case 揭露兩個更前置的事實：(a) production 系統是 *federated*（多 DB 按 workload 分流）、不是 monolithic；(b) 每個 vendor 在系統中扮演 *特定角色*（control plane vs data plane vs cache）、不是 all-purpose store。

### Federated DB by workload

Coinbase（9.C36）production 配置：MongoDB Atlas（document 主資料、identity service）+ DynamoDB（部分固定 KV workload）+ Memcached（read cache）+ mongobetween（connection proxy）+ Kinesis（event stream）。不是「全用 MongoDB」也不是「全遷 DynamoDB」、是按 workload shape 分流。

Toyota Connected（9.C38）：MongoDB Atlas 20 個 DB（microservice 拆 blast radius）+ Lambda + Kinesis + Redis + Kubernetes。20 個 DB 不是吞吐撐不住（18B txn/月 ≈ 7K txn/sec、單一 cluster 撐得下）、是 *microservice ownership* + *blast radius* 切分（F2.6）。

Forbes（9.C37）：MongoDB Atlas + 中介 abstraction layer + 50+ microservice。abstraction layer 隔離 schema 變動、避免 50 個服務都依賴 DB schema 細節（F2.3）。

三 case 揭露的共同 frame 是：**寫 production 系統時假設「DB 一個服務搞定」、忽略 cache / queue / proxy / abstraction layer 跨層責任、會撞 connection limit / cache miss / cross-region replication 等隱性瓶頸**。

### System role：control plane vs data plane

DynamoDB 在 surge 場景能撐 nearly infinitely 不是 DynamoDB 自己神奇、是 *系統架構解耦* 的結果（F1.6）：

- **Control plane（metadata、state、user record）**：DynamoDB / MongoDB / Cosmos DB 適合 — 流量是 small payload + high QPS pattern
- **Data plane（影音、大型 BLOB、media stream）**：CDN / S3 / object storage、*不在 DB3 範圍* — 流量是 large payload + bandwidth-bound
- **Cache layer**：Redis / Memcached / DAX（DynamoDB 補位）— 跟主 DB 形成跨層架構、處理讀峰值 + read-your-own-write 一致性

三個 case 揭露同一 frame：Zoom 視訊 metadata 走 DynamoDB、影音走 WebRTC / edge servers；Disney+ watchlist 走 DynamoDB、影片串流走 CDN + S3；Capcom game state 走 DynamoDB + DAX、game server 走 EKS。**把影音串流塞 DynamoDB 是違反 control plane vs data plane 分離、容量規劃會錯**（每筆 1KB 的 KV vs 每筆 100MB 的 media chunk 是不同 workload）。

## 三 vendor 對比 10 軸

下表是三 vendor 在 selection 階段的 10 軸對比。每個軸後續都有 per-vendor deep article 展開機制、本文不重複展開。

| 軸                               | MongoDB                                                                     | DynamoDB                                                   | Cosmos DB                                                                                                 |
| -------------------------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **資料模型核心**                 | Document（aggregate root）+ aggregation pipeline                            | KV with optional document fields + GSI / LSI               | Multi-model（SQL / MongoDB / Cassandra / Gremlin / Table API）                                            |
| **部署 topology**                | 跨雲（Atlas AWS / GCP / Azure）+ self-hosted                                | AWS-only managed                                           | Azure-only managed                                                                                        |
| **跨雲 hedging**                 | 高（Atlas 跨雲、Forbes case）                                               | 無（AWS lock-in）                                          | 無（Azure lock-in）                                                                                       |
| **Capacity 抽象**                | CPU + IOPS + working set RAM 三軸                                           | WCU/RCU + on-demand/provisioned + adaptive capacity        | RU（Request Unit）+ 5 consistency level                                                                   |
| **Contract layer**               | DB 層 `$jsonSchema` validator / app 層 abstraction / 混合                   | DynamoDB Stream + app 層 validator                         | DB 層 stored procedure + app 層 validator                                                                 |
| **Partition / shard key 可逆性** | `reshardCollection` 4.4+ 可改、成本高                                       | 可改用 backfill                                            | 不可改、必 export-recreate                                                                                |
| **Consistency model**            | Read concern（local / majority / linearizable）+ causal consistency session | Eventually / strongly consistent reads                     | 5 level spectrum（Strong / Bounded staleness / Session / Consistent prefix / Eventual）                   |
| **Multi-region write**           | Atlas 跨 region 手動 conflict 處理                                          | Global Tables LWW                                          | Multi-region write（Strong 互斥、見 cosmosdb/multi-region-write-conflict SSoT）                           |
| **Dogfood signal**               | 無（MongoDB 是獨立公司、不適用）                                            | Amazon 自家高頻使用（9.C5 Amazon Ads / 9.C27 Disney+ etc） | Microsoft 365 dogfood（9.C30、**Scope warning**：dogfood 數字不公開、是 selection signal 不是 benchmark） |
| **Multi-model 差異化**           | 單一 document model                                                         | 單一 KV-with-document model                                | 唯一單服務支援 5 API（差異化價值、F2.16）                                                                 |

### 軸的延伸子段

**部署 topology / 跨雲 hedging**：三家 topology 是 *vendor lock-in* 跟 *跨雲彈性* 的硬取捨。Forbes 選 Atlas 不是當下省錢（自管 MongoDB 也可以、TCO 改善是副作用）、是 *未來雲商策略尚未底定* 的 hedging — Atlas 提供 AWS / GCP / Azure 三家部署、未來換雲不用換 DB（F2.10）。對照 DynamoDB / Cosmos DB / Spanner / Aurora 都是單雲鎖定 — 選了就跟著該雲商生態走。團隊雲商策略已底定（深度用 AWS / Azure / GCP 其一）時、單雲 vendor 通常較划算（更好的 IAM 整合、更深的 ops 工具、單一 support 通道）。跨雲價值真正成立是 *策略不確定* 或 *合規要求多雲* 場景。

**Capacity 抽象**：三家 capacity 抽象的 *思維遷移成本* 可能高過 vendor 廣告的價差（F2.12）。MongoDB 用 CPU + IOPS + working set RAM 三軸思維、跟自管 PostgreSQL / MySQL 類似、團隊轉換成本低。DynamoDB 用 WCU/RCU 抽象、要學「估每個操作消耗多少 unit」、加上 on-demand / provisioned / adaptive capacity 三模式選擇。Cosmos DB 用 [Request Unit](/backend/knowledge-cards/request-unit/)（RU）抽象、1 RU ≈ 1 KB document 的 strong read 成本、寫 ~5 RU、複雜 query 數百 RU — 工程師要學會用 RU 思考、不是用 CPU 思考、團隊知識遷移成本可能高。容量規劃延伸見對應 vendor 的 sizing article。

**Partition / shard key 可逆性**：三家 *不在同一光譜*、是選 vendor 前必做的 access pattern audit 重點（F2.15）。MongoDB `reshardCollection`（4.4+）可改、但成本高、需要 cluster downtime 或長時間 background migration。DynamoDB partition key 技術上可改、實作上用 backfill（建新 table、新 PK、雙寫舊新、cutover）— ops 工作量大但可逆。Cosmos DB partition key *不可改*、改 partition key 等於 export-recreate-import — 對 1TB+ 資料是大型 migration 工程。三家不可逆性遞增、選 Cosmos DB 前必須前期完整 access pattern audit、不能「先上 production 之後再調」。

**Consistency model**：三家機制設計哲學不同。MongoDB read concern 是 *per-operation* 選擇（同一 client connection 可以混用）；DynamoDB strong vs eventual 是 *per-read* 選項（write 端統一強一致）；Cosmos DB 5 個 level 是 *account-level default + per-request override*、且 Strong 跟 multi-region write 互斥（CAP 硬約束）。設計上 MongoDB 最 flexible、Cosmos DB 最 explicit、DynamoDB 介於中間。延伸機制細節見 [Cosmos DB consistency levels engineering](/backend/01-database/vendors/cosmosdb/consistency-levels-engineering/)、[Cosmos DB multi-region write conflict](/backend/01-database/vendors/cosmosdb/multi-region-write-conflict/)（SSoT 主寫位置）。

**Multi-model 差異化**：Cosmos DB 是 *唯一單一服務支援 5 API* 的雲商 DB（SQL / MongoDB / Cassandra / Gremlin / Table）— 對照 AWS 走多產品覆蓋（DynamoDB KV + DocumentDB MongoDB-compat + Neptune graph + Keyspaces Cassandra-compat）、GCP 走多產品覆蓋（Firestore + Spanner + Bigtable）。multi-model 的差異化價值是 *減少多 DB 並存運維* — 一個產品團隊只養一個 service、一套 IAM、一套 backup / DR、一套 monitoring。但 *是否真用上 multi-model* 要看團隊實際 workload — 多數團隊只用 1-2 個 API、單一 model 的競品（DynamoDB / MongoDB）可能更專注（F2.16）。

## 失敗模式（cross-vendor 反模式）

下列七條是三 vendor 都會踩、跨 case 共通的反模式。Per-vendor 特定反模式（例如 DynamoDB on-demand 隱性 hot partition、MongoDB schema 三代並存）在 per-vendor deep article。

### 反模式 1：把 DynamoDB 當 OLTP

訊號：access pattern 還在探索期、5+ 種 query 還會增加、強一致 cross-partition transaction 是產品契約。應回 PostgreSQL / Aurora、不是繼續加碼 DynamoDB single-table design。

DynamoDB 的 *正確* 用法包含 control plane KV（Zoom / Disney+ / Capcom）跟 durable queue / write buffer（Tixcraft 9.C15 揭露的非 OLTP 正向用例、F1.3）— DynamoDB 接「訂單」寫入、不是即時生效、是讓 traditional server（金流 / 票庫）用自己能承受的速度消費。這層解耦讓「前端可以擴 130 倍、後端不用同步擴」。

### 反模式 2：把 MongoDB 當 KV

訊號：access pattern 固定、PK 天然均勻、不需要 aggregation pipeline、document 內部從不展開（只查 root 欄位）。

應改 DynamoDB / Cosmos DB Table API。MongoDB 在這場景的 overhead（document overhead / connection model / aggregation engine 未用上）不划算 — KV vendor 的單筆讀寫成本更低、scaling 模型更簡單。

### 反模式 3：把 Cosmos DB 當跨雲服務

訊號：團隊評估 multi-cloud DR / 跨雲 portability、看到 Cosmos DB 文件強調「global distribution」就以為支援跨雲。

Cosmos DB 是 *Azure-only*、global distribution 指 Azure 內跨 region。想跨雲應改 MongoDB Atlas。multi-model 差異化是 *Azure 生態內* 的價值（F2.16）— 一旦離開 Azure、Cosmos DB 的所有獨特優勢都不存在。

### 反模式 4：federated DB 假設「全用 X」

訊號：寫架構設計時假設「DB 一個服務搞定」、不規劃 cache / queue / proxy / abstraction layer。

Production 真實系統都是 federated（Coinbase / Toyota / Forbes 都是）。寫架構時假設一個 DB 搞定會撞 connection limit（surge 下 RDB 第一個爆點、F1.7）/ cache miss（單靠 DB 撐不住讀峰值）/ cross-region replication（跨 region 一致性處理錯）等隱性瓶頸。預先設計 federated topology + 跨層責任分配、不是事後補。

### 反模式 5：誤判 dogfood case 數字

訊號：引用 Microsoft 365 / Amazon Prime Day 等 dogfood case 時、把它當 production benchmark、抄具體數字當 sizing 依據。

Dogfood case 數字常 *不公開* 或 *不適用 customer-facing*（F2.17 + F1.10）— Amazon Prime Day 「90M reads/sec」是年度峰值最高一秒不是平均、Microsoft 365 直接沒給數字、Google Spanner「10 億 req/sec」是 Google 全使用者加總不是單客戶配額。寫架構時引用要明示 selection signal（雲商賭身家、值得當高權重 vendor 訊號）vs production benchmark（具體 sizing 數字）— 兩者不可混為一談。

### 反模式 6：partition key 一上 production 才發現不可逆

訊號：選 Cosmos DB / DynamoDB 時、partition key 設計沒做完整 access pattern audit、上 production 一段時間後發現 hot partition、想改 PK。

三家不在同一光譜（見前段對比表）— MongoDB shard key 4.4+ 可改但成本高、DynamoDB 可 backfill 改、Cosmos DB *不可改* 必 export-recreate。選 Cosmos DB 前要前期完整 access pattern audit、列所有預期 query 跟對應 PK 訪問頻率、確認最熱 PK 流量在單一 partition 容量上限內（F2.15）。

### 反模式 7：wire compatibility 當 100% 行為相同

訊號：選 Cosmos DB MongoDB API 或 DocumentDB、看到「MongoDB compatible」就假設 MongoDB driver 跑得起來就是相容、跳過 query pattern 驗證。

Wire compat ≠ 行為 100% 相同（F2.9）。Cosmos DB MongoDB API 廣告「100% wire compatibility」是行銷話術、實際是「在某些 query pattern 下相容」— aggregation pipeline 某些 stage 不支援、transaction edge case 行為差異、index 行為差異都會踩到。遷移必須 dual-write per query pattern 驗證、不是看 vendor spec list。

## 不該選 DB3 的訊號（升 SQL / 升 distributed SQL 路徑）

下列四條訊號出現時、選擇應跳出 DB3 範圍。

- **JOIN-heavy + 強 normalize workload**：應留 PostgreSQL（包括 PostgreSQL + JSONB 混合方案）、不該塞 NoSQL 再 `$lookup`。aggregation pipeline 的 `$lookup` 性能遠不如 SQL JOIN、在 sharded cluster 還有限制。
- **強一致 cross-region transaction 是產品契約**：應進 [DB4 entry point](/backend/01-database/vendors/cockroachdb/aurora-dsql-spanner-decision-tree/) 評估 distributed SQL（CockroachDB / Spanner / Aurora DSQL）。三家 NoSQL 的 cross-region transaction 都有 limitation、不該當主路徑。
- **大流量 + 跨業務 fleet 治理**：Aurora 200 cluster 模式（9.C4 DraftKings 揭露的 business sharding fleet）可能更合適、進 Aurora fleet 治理。NoSQL 的 fleet 治理工具鏈（cluster lifecycle / cross-cluster query / unified IAM）通常不如 managed SQL 成熟。
- **資料模型還在探索 + access pattern 變動快**：暫緩 NoSQL 選型、用 PostgreSQL + JSONB 過渡。JSONB 給 document-like flexibility、SQL 給 ad-hoc query power、未來釐清穩定 access pattern 後再選 NoSQL 不遲。

## 下一步路由（per-vendor outline 子組）

讀者識別 workload type（軸 1-3）+ migration path（三型）+ system role（federated / control plane）後、進對應 per-vendor 子組繼續深化。

### MongoDB 子組

- 入門：[schema design pattern](/backend/01-database/vendors/mongodb/schema-design-pattern/)（contract layer 三選一：DB 層 validator / app 層 abstraction / 混合）
- 容量：[shard key selection](/backend/01-database/vendors/mongodb/shard-key-selection/)（單 cluster vs 多 cluster blast radius、Toyota 20 DB 模式）
- Migration：[migrate to Atlas](/backend/01-database/vendors/mongodb/migrate-to-atlas/)（同 DB 換託管型）

### DynamoDB 子組

- 入門：[single-table design pattern](/backend/01-database/vendors/dynamodb/single-table-design-pattern/)（access pattern 設計 + 適用度前置判讀）
- 機制：[consistency model optimization](/backend/01-database/vendors/dynamodb/consistency-model-optimization/)（strong vs eventually consistent 取捨）

### Cosmos DB 子組

- 入門：[MongoDB API vs SQL API](/backend/01-database/vendors/cosmosdb/mongodb-api-vs-sql-api/)（API model 選型、四層 framing）

### 跨層架構（federated DB / cache / proxy）

跨層架構的延伸內容見對應 per-vendor connection management / cache layer article（後續會寫）— 本文只在軸 2 / federated frame 點到、不展開機制。

### 進 DB4 evaluation

若需要強一致 cross-region SQL / paradigm shift（KV → distributed SQL 或 SQL → distributed SQL）、進 [DB4 entry point: Aurora DSQL / Spanner / CockroachDB decision tree](/backend/01-database/vendors/cockroachdb/aurora-dsql-spanner-decision-tree/)。

## Knowledge card 路由

本文涉及的 knowledge card：

- [document-store](/backend/knowledge-cards/document-store/) — document model 的核心概念跟 aggregate root 邊界
- [hot-partition](/backend/knowledge-cards/hot-partition/) — KV vendor 的 partition 容量上限機制
- [database-sharding](/backend/knowledge-cards/database-sharding/) — shard key 跟 partition key 設計
- [consistency-level](/backend/knowledge-cards/consistency-level/) — strong / eventual / session 三類取捨
- [vendor-lock-in](/backend/knowledge-cards/vendor-lock-in/) — 單雲 vs 跨雲的 hedging 取捨
- [distributed-sql](/backend/knowledge-cards/distributed-sql/) — 跳出 DB3 進 DB4 的概念入口
