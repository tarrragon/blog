# DB3 Vendor Selection：document / KV / multi-model 三方選型 + workload shape 前置判讀

> **Status**: L5 outline skeleton（planning artifact、非 published article）、DB3 entry point candidate（_module-outline.md C.1）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。
>
> **Entry point 定位**：本篇承擔 DB3 document / KV / multi-model 選型的 reader entry point — 讀者進來時還沒決定哪個 vendor、甚至還沒釐清「我的 workload 是 document / KV / multi-model 哪一類」。本篇先用「workload shape × access pattern × consistency 三軸前置判讀」幫讀者識別自己的 workload type、再過 migration path 三型 + federated DB 視角、最後落到三 vendor 對比。
>
> **校準說明**：本 outline 為 case-first audit 後新增、整合 F1 DynamoDB（22 findings）+ F2 Document MongoDB / Cosmos DB（18 findings）的跨 vendor frame、補 _module-outline.md Section A 揭露的「DB3 reader journey 在選型層的缺口」。

## 問題情境（Production pressure）

- 啟動壓力：團隊評估 document / KV / multi-model NoSQL 三家（MongoDB / DynamoDB / Cosmos DB）、文件都說「scalable schema-less」、看不出實際取捨；或既有 RDB workload 撞 connection limit、想換 KV 但不知道是否適合
- 讀者徵兆：「我的資料是 document-shaped 還是 KV-shaped？」「partition key 該怎麼選？」「為什麼 Atlas 跟 Cosmos DB MongoDB API 不一樣？」「Cosmos DB multi-model 是真用得到還是行銷話術？」「我已經有 Memcached、還要再用 MongoDB cache 層嗎？」「on-demand vs provisioned 怎麼選？」
- Case anchor: 多型 document workload [9.C38 Toyota Connected](/backend/09-performance-capacity/cases/toyota-connected-mongodb-telematics-iot/)（車載 sensor polymorphic + 20 個 Atlas DB blast radius、F2.3 / F2.6）、document 跨雲 [9.C37 Forbes](/backend/09-performance-capacity/cases/forbes-mongodb-atlas-multi-cloud-migration/)（自管 → Atlas 6 個月、跨雲 hedging、F2.1 / F2.10）、document → KV-compatible 跨 vendor [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/)（MongoDB → Cosmos DB MongoDB API、保留 driver、F2.1 / F2.16 / F2.17）、KV-as-buffer [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)（DynamoDB 寫入緩衝、6750x 擴展、F1.3 / F1.21）、PK 天然均勻典範 [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)（9000 萬 reads/sec、F1.2 / F1.20）、federated DB 真實系統 [9.C36 Coinbase](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/)（MongoDB + DynamoDB + Memcached + mongobetween、F2.18）

## Workload shape × access pattern × consistency 三軸前置判讀（前置問題 0、Frame 1）

讀者進來前先回答：你的 workload 屬哪一型？三軸的組合決定 vendor 候選清單、不識別 workload shape 直接比 vendor 是源頭錯誤。

### 軸 1 — 資料形狀：document / KV / 不清楚

| 訊號                                                                                  | 適配資料模型                                            | 對應 case                                                                                     |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| 資料天然多型（不同記錄欄位不同）、隨產品演進 schema 增刪欄位、aggregate root 邊界明確 | document（MongoDB / Cosmos DB SQL API / DocumentDB）    | 9.C38 Toyota sensor schema 隨車型演進、9.C37 Forbes CMS article 多型                          |
| 資料形狀固定、access pattern < 5 種、固定 lookup by key                               | KV（DynamoDB / Cosmos DB Table API / Redis 持久化變體） | 9.C5 Amazon Ads（用 ad_id 查）、9.C26 PayPay（message_id）、9.C27 Disney+（user_id 觀看紀錄） |
| 資料形狀還在探索、access pattern 變動頻繁                                             | 暫緩 NoSQL 選型、用 PostgreSQL + JSONB 過渡             | 屬 anti-pattern、case 沒揭露但是常見讀者誤判                                                  |

### 軸 2 — Access pattern 穩定度（KV vendor 適用度前置判讀、Frame 1 / F1.3 + F1.20）

- **天然均勻 PK + 穩定 access pattern**（meeting_id / player_id / message_id / user_id）→ DynamoDB / Cosmos DB Table API 適用、PK 不需 composite key 修補（F1.20、9.C18 Zoom / 9.C19 Capcom / 9.C26 PayPay / 9.C27 Disney+ 都揭露這 frame）
- **天然不均勻 PK**（event_id 一場演唱會集中 / date 時間序集中）→ 需 composite key 或 write sharding 修補（F1.2、9.C15 Tixcraft 用 composite key 解 event_id 集中）
- **Access pattern 變動頻繁**（探索期、< 5 種 query 還會增加）→ 不適合 DynamoDB single-table design、回 RDB

### 軸 3 — Consistency 需求是否可接受 eventual

- **可接受 eventual / session consistency**：DynamoDB（default eventually consistent reads、可選 strong）、Cosmos DB（5 個 consistency level、default session）、MongoDB（read concern 多級）— 三家都可
- **需要強一致 cross-partition transaction**：DynamoDB 跨 partition transaction 限制（最多 100 個 action）、MongoDB 4.0+ 支援 multi-document transaction 但 sharded cluster 有 limitation、Cosmos DB 跨 logical partition transaction 受限 — 都不如 SQL／distributed SQL，回 DB4
- **跨 region active-active write**：Cosmos DB multi-region write（Strong 互斥）、DynamoDB Global Tables LWW、MongoDB Atlas 跨 region 需手動 conflict 處理 — 三家機制不同、見各自 outline

## Migration path 三型（前置問題 1、F2.1 跨 case 合成 frame）

讀者進來時可能已有既有系統、不是綠地。三型遷移路徑風險跟 ROI 完全不同、選錯路徑會推到錯的 vendor：

- **保留原 DB + 補周邊工具型**（9.C36 Coinbase 模式、F2.18）：
  - 不換 vendor、加 connection proxy（mongobetween）+ cache（Memcached + freshness token）+ predictive scaling
  - 路徑成本：中（自建工具）、風險：低、ROI：保留主資料 + 解 driver / 部署模型瓶頸
  - **適合**：MongoDB 主資料無問題、但應用層 connection / cache 撐不下
- **同 DB 換託管型**（9.C37 Forbes 模式、F2.1）：
  - 自管 MongoDB → Atlas、保留 schema 跟 access pattern、6 個月遷移
  - 路徑成本：中、風險：中（dual-write / shadow read 驗證）、ROI：operation transfer + TCO 改善（Forbes 揭露 -25%、屬特定流量規模、需驗）
  - **適合**：自管 ops burden 大、不想換 model
- **換 vendor 保留 model 型**（9.C30 Microsoft 365 模式、F2.1）：
  - MongoDB → Cosmos DB MongoDB API、保留 wire protocol + driver、底層架構換
  - 路徑成本：高（必須 dual-write per query pattern 驗證、wire compat ≠ 100% 行為相同、F2.9）、風險：高、ROI：跨 vendor 換 + 保留應用層
  - **適合**：vendor 特性差異（Azure 生態 / multi-model API / global distribution）值得付遷移成本
  - **Scope warning**：Microsoft 365 是 Microsoft 自家 dogfood、case 沒揭露具體 throughput / latency / cost 數字、是 selection signal 不是 production benchmark（F2.17）
- **不在 DB3 範圍：paradigm shift 換引擎**（KV → SQL 或 SQL → distributed SQL）— 進 DB4 entry point [`aurora-dsql-spanner-decision-tree`](./cockroachdb/aurora-dsql-spanner-decision-tree.md)

## Federated DB + system role 視角（前置問題 2、F2.18 + F1.6）

讀者可能誤以為「全用 X」是正解。真實 production case 揭露：document / KV 系統是 *federated*、不是 monolithic、且每個 vendor 在系統中扮演 *特定角色*。

### Federated DB by workload（F2.18、9.C36 Coinbase）

Coinbase production 配置：MongoDB Atlas（document 主資料）+ DynamoDB（部分固定 KV workload）+ Memcached（read cache）+ mongobetween（connection proxy）+ Kinesis（event stream）。不是「全用 MongoDB」也不是「全遷 DynamoDB」、是按 workload shape 分流。

**對照 Toyota（9.C38）**：MongoDB Atlas 20 DB + Lambda + Kinesis + Redis + Kubernetes — 也是 federated。Forbes（9.C37）：Atlas + abstraction layer + 50+ microservice — 同類。

**反指標**：寫 production 系統時假設「DB 一個服務搞定」、忽略 cache / queue / proxy 跨層責任。

### System role：control plane vs data plane（F1.6、9.C18 Zoom + 9.C27 Disney+ + 9.C19 Capcom）

DynamoDB 在 surge 場景能撐 nearly infinitely 不是 DynamoDB 自己神奇、是 *系統架構解耦* 的結果：

- **Control plane（metadata、state、user record）**：DynamoDB / MongoDB / Cosmos DB 適合
- **Data plane（影音、大型 BLOB、media stream）**：CDN / S3 / object storage、不在 DB3 範圍
- **Cache layer**：Redis / Memcached / DAX（DynamoDB 補位）— 跟主 DB 形成跨層架構

**讀者陷阱**：把 DynamoDB 當「全系統一個 KV」、把影音串流也塞 DynamoDB document — 違反 control plane vs data plane 分離、容量規劃會錯。

## 三 vendor 對比軸

| 軸                                   | MongoDB                                                                     | DynamoDB                                            | Cosmos DB                                                                                                                                  |
| ------------------------------------ | --------------------------------------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **資料模型核心**                     | Document（aggregate root）+ aggregation pipeline                            | KV with optional document fields + GSI/LSI          | Multi-model（SQL / MongoDB / Cassandra / Gremlin / Table API）                                                                             |
| **部署 topology**                    | 跨雲（Atlas AWS / GCP / Azure / 自管）+ self-hosted                         | AWS-only managed                                    | Azure-only managed                                                                                                                         |
| **跨雲 hedging（F2.10）**            | 高（Atlas 跨雲）                                                            | 無（AWS lock-in）                                   | 無（Azure lock-in）                                                                                                                        |
| **Capacity 抽象（F2.12 / Frame 4）** | CPU + IOPS + working set RAM（三軸思維）                                    | WCU/RCU + on-demand/provisioned + adaptive capacity | RU（Request Unit）+ 5 consistency level                                                                                                    |
| **Contract layer（F2.3）**           | DB 層 `$jsonSchema` validator / app 層 abstraction / 混合                   | DynamoDB Stream + app 層 validator                  | DB 層 stored procedure + app 層 validator                                                                                                  |
| **Partition key 可逆性（F2.15）**    | `reshardCollection` 4.4+ 可改、成本高                                       | 可改用 backfill                                     | 不可改、必 export-recreate                                                                                                                 |
| **Consistency model**                | Read concern（local / majority / linearizable）+ causal consistency session | Eventually / strongly consistent reads              | 5 level spectrum（Strong / Bounded staleness / Session / Consistent prefix / Eventual）                                                    |
| **Multi-region write**               | Atlas 跨 region 手動 conflict                                               | Global Tables LWW                                   | Multi-region write（Strong 互斥、Section G SSoT 主寫於 [cosmosdb/multi-region-write-conflict](./cosmosdb/multi-region-write-conflict.md)） |
| **Dogfood signal（F2.17）**          | 無（不適用）                                                                | Amazon 自家高頻使用、9.C5 / 9.C27 等                | Microsoft 365 dogfood、9.C30（**Scope warning**：dogfood 數字不公開、selection signal 不是 benchmark）                                     |
| **Multi-model 差異化（F2.16）**      | 單一 document model                                                         | 單一 KV-with-document                               | **唯一單服務支援 5 API**（差異化價值）                                                                                                     |

## 失敗模式（反模式）

- **把 DynamoDB 當 OLTP**（F1.3 + F1.6）：access pattern 還在探索期、5+ 種 query 還會增加、強一致 cross-partition transaction 是產品契約 — 應回 PostgreSQL / Aurora；DynamoDB *正確* 用法是 control plane KV 或 durable queue / write buffer（9.C15 Tixcraft 揭露的非 OLTP 正向用例）
- **把 MongoDB 當 KV**（F2.6 反向）：access pattern 固定 + PK 天然均勻 + 不需 aggregation pipeline、應改 DynamoDB；MongoDB 在這場景的 overhead（document overhead / connection model）不划算
- **把 Cosmos DB 當跨雲服務**：Cosmos DB 是 Azure-only、想跨雲應改 MongoDB Atlas；multi-model 差異化是 *Azure 生態內* 的價值（F2.16）
- **federated DB 假設「全用 X」**（F2.18 反向）：production 真實系統都是 federated、寫架構時假設一個 DB 搞定會撞 connection limit / cache miss / cross-region replication 等隱性瓶頸
- **誤判 dogfood case 數字**：Microsoft 365 / Amazon Prime Day 等 dogfood case 數字不公開或不適用 customer-facing、寫作引用要明示 selection signal vs production benchmark（F2.17 + Frame 7）
- **partition key 一上 production 才發現不可逆**（F2.15）：MongoDB shard key 4.4+ 可改但成本高、DynamoDB partition key 可改用 backfill、Cosmos DB partition key 不可改 — 三家不在同一光譜、選 Cosmos DB 前必須前期完整 access pattern audit
- **wire compatibility 當 100% 行為相同**（F2.9）：Cosmos DB MongoDB API「100% wire compat」是行銷話術、實際是「在某些 query pattern 下相容」、遷移必須 dual-write per query pattern 驗證

## 不該選 DB3 的訊號（升 SQL / 升 distributed SQL 路徑）

- **JOIN-heavy + 強 normalize workload**：應留 PostgreSQL（包括 JSONB 混合）、不該塞 NoSQL 再 `$lookup`
- **強一致 cross-region transaction 是產品契約**：應進 [DB4 entry point](./cockroachdb/aurora-dsql-spanner-decision-tree.md) 評估 distributed SQL（CockroachDB / Spanner / Aurora DSQL）
- **大流量 + 跨業務 fleet 治理**：Aurora 200 cluster 模式（9.C4 DraftKings）可能更合適、進 [Aurora fleet 治理](./aurora/read-replica-scaling.md)
- **資料模型還在探索 + access pattern 變動快**：暫緩 NoSQL 選型、用 PostgreSQL + JSONB 過渡、access pattern 穩定後再決定

## 下一步路由（per-vendor outline 子組）

讀者識別 workload type + migration path + system role 後、進 per-vendor outline：

### MongoDB 子組

- 入門：[`mongodb/schema-design-pattern`](./mongodb/schema-design-pattern.md)（contract layer 三選一）
- 容量：[`mongodb/shard-key-selection`](./mongodb/shard-key-selection.md)（單 cluster vs 多 cluster blast radius）
- 觀測：[`mongodb/replica-set-read-preference`](./mongodb/replica-set-read-preference.md)（DB 層 vs cache 層一致性）
- 跨層架構：[`mongodb/connection-management-and-cache-layer`](./mongodb/connection-management-and-cache-layer.md)（connection storm + freshness token + predictive scaling）
- 進階：[`mongodb/aggregation-pipeline-optimization`](./mongodb/aggregation-pipeline-optimization.md)、[`mongodb/change-streams-kafka`](./mongodb/change-streams-kafka.md)

### DynamoDB 子組

- 入門：[`dynamodb/single-table-design-pattern`](./dynamodb/single-table-design-pattern.md)（4 軸前置判讀 + access pattern 設計）
- 容量：[`dynamodb/partition-key-antipatterns`](./dynamodb/partition-key-antipatterns.md)（hot partition 防範）
- 成本：[`dynamodb/on-demand-vs-provisioned`](./dynamodb/on-demand-vs-provisioned.md)（6 軸 mode 決策）
- 查詢：[`dynamodb/gsi-lsi-design`](./dynamodb/gsi-lsi-design.md)、[`dynamodb/global-tables-conflict`](./dynamodb/global-tables-conflict.md)

### Cosmos DB 子組

- 入門：[`cosmosdb/mongodb-api-vs-sql-api`](./cosmosdb/mongodb-api-vs-sql-api.md)（API model 選型）
- 容量：[`cosmosdb/ru-cost-model-sizing`](./cosmosdb/ru-cost-model-sizing.md)（RU 思維 + 負載形狀 × mode）
- 設計：[`cosmosdb/partition-key-design`](./cosmosdb/partition-key-design.md)、[`cosmosdb/consistency-levels-engineering`](./cosmosdb/consistency-levels-engineering.md)
- Multi-region：[`cosmosdb/multi-region-write-conflict`](./cosmosdb/multi-region-write-conflict.md)（Strong + multi-region 互斥 SSoT 主寫位置）

### 進 DB4 evaluation

若需要強一致 cross-region SQL / paradigm shift、進 [DB4 entry point: `aurora-dsql-spanner-decision-tree`](./cockroachdb/aurora-dsql-spanner-decision-tree.md)

## 寫作前置 checklist

- [ ] Case anchor：6 個 case（Toyota / Forbes / Microsoft 365 / Tixcraft / Amazon Ads / Coinbase）覆蓋 document polymorphic / 跨雲遷移 / dogfood / 寫入緩衝 / PK 均勻 / federated DB 六個軸
- [ ] Fact vs derive 分層：三型 migration 跟 federated DB 是跨案合成 frame、checklist 標明「本章合成、非單一 case 揭露」
- [ ] Dogfood frame 限制：Microsoft 365 / Amazon Prime Day 數字不公開、引用標 selection signal 不是 production benchmark（F2.17 + Frame 7）
- [ ] Knowledge card 雙引用：[document-store](/backend/knowledge-cards/document-store/)、[hot-partition](/backend/knowledge-cards/hot-partition/)、[database-sharding](/backend/knowledge-cards/database-sharding/)、[consistency-level](/backend/knowledge-cards/consistency-level/)
- [ ] SSoT 對應到位：Strong + multi-region 互斥 → Cosmos DB multi-region-write-conflict（本篇 cross-link 不展開）
- [ ] Sibling 對比清楚：三 vendor 不是「優劣」、是「workload-by-workload 適配」、避免 vendor war
- [ ] 預估寫作長度：280-340 行（entry article 含 3 個前置判讀 + 三 vendor 對比表 + 失敗模式 + 完整 routing layer）
