---
title: "DynamoDB"
date: 2026-05-13
description: "AWS managed key-value、partition-based scaling、9000 萬 RPS sustained 實戰證據"
weight: 5
tags: ["backend", "database", "vendor", "dynamodb", "kv"]
---

DynamoDB 是 AWS managed key-value store、用 partition-based scaling 提供 *可預測 P99 latency* 跟 *elastic capacity*。Amazon 自家 Ads（9000 萬 RPS）、Disney+、Zoom（COVID 30x surge）、Capcom（billions of requests / single-digit ms）都用 DynamoDB 撐核心 workload — 它是目前公開 case 最多、最被驗證的 managed KV 服務。

## 教學路線：Access pattern 與 partition capacity

DynamoDB 服務頁的教學目標是把 access pattern 轉成 partition key、sort key、GSI、capacity mode 與 global tables 的設計判斷。讀者讀完後要能從查詢路徑反推資料模型，並估算 hot partition、成本與 consistency trade-off。

| 學習段         | 核心問題                                                                                             | 對應段落                       |
| -------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------ |
| Access pattern | 查詢形狀如何先於資料表設計                                                                           | 定位、適用場景                 |
| Partition key  | [hot partition](/backend/knowledge-cards/hot-partition/)、single-digit latency、GSI 如何成為設計核心 | 容量規劃要點、常見陷阱         |
| Capacity mode  | on-demand、provisioned、auto scaling 如何對應高峰與成本                                              | 容量特性、案例對照             |
| Global tables  | multi-region availability 與 consistency 會付出哪些代價                                              | 適用場景、跟其他 vendor 的取捨 |
| 替代路由       | 何時回 SQL、MongoDB、Cosmos DB 或 cache / queue                                                      | 不適用場景、下一步路由         |

## 定位：partition-based KV scale

DynamoDB 的核心設計是「partition 透明、capacity 抽象化」。不像 MongoDB 要主動 shard、不像 Cassandra 要管 ring topology、不像 PostgreSQL 要選 instance type — DynamoDB 把所有底層 scaling 隱藏在 RCU / WCU 抽象層後。

**容量單位**：

- 1 RCU（Read Capacity Unit）= 1 strongly consistent read of 4KB / sec、2 eventually consistent reads
- 1 WCU（Write Capacity Unit）= 1 write of 1KB / sec
- 每個 partition 上限：3000 RCU / 1000 WCU
- 總容量 = partition 數量 × 每 partition 上限（partition 數量透明、vendor 自動管理）

**延遲特性**：

- single-digit millisecond p99 latency（read / write）
- 同 region 跨 AZ replication 內建、預設 eventually consistent reads
- strongly consistent reads 依 region 內 [quorum](/backend/knowledge-cards/quorum/) 成立，跨 region 讀寫要看 Global Tables 語意

詳見 [1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) 跟 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 的 partition 設計章節。

## 適用場景

按公開 case 提煉的典型適用場景：

**1. KV / single-table design 為主的查詢**：

- 用 partition key + sort key 設計、單筆 / 範圍查詢
- 查詢路徑固定，JOIN / ad-hoc query 需求低
- 對應案例：[9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) — 9000 萬 reads/sec + 500 萬 writes/sec、99.999% 可用

**2. 可預測 sub-10ms p99 latency 需求**：

- 遊戲後端（玩家狀態、戰績）
- 內容平台 metadata（watchlist、播放進度）
- 對應案例：[9.C19 Capcom](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/)（billions of requests / single-digit ms）、[9.C27 Disney+](/backend/09-performance-capacity/cases/disney-plus-content-metadata/)（每日數十億 actions）

**3. 流量 spiky 或 surge 場景**：

- on-demand capacity 自動吸收 burst
- 不需 connection pool（HTTP API、無 stateful connection）
- 對應案例：[9.C18 Zoom](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/)（COVID 1000 萬 → 3 億 DAU）、[9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)（IOPS 20 → 135K、售票搶購）、[9.C29 Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/)（RDB connection limit → 改 DynamoDB）

**4. 大規模通知 / 訊息系統**：

- TTL 自動清理過期 records
- partition key 用 user_id / message_id 天然均勻
- 對應案例：[9.C26 PayPay](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/)（行動支付每日 3 億訊息）

**5. 5 個 9 可用性 B2B SaaS**：

- multi-region Global Tables active-active
- 對應案例：[9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/)（99.999% 跨 15 region）

**6. 高吞吐 budget 敏感**：

- on-demand 適合突發、provisioned 適合 sustained
- 對應案例：[9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — TiDB over-provision 壓力轉成 DynamoDB on-demand pay-per-use，成本下降 50%

## 不適用場景

**1. 複雜 ad-hoc query / JOIN**：

- DynamoDB query 以 partition key + sort key 為主，JOIN-heavy workload 交給 SQL 系統
- PartiQL 提供 SQL-like 語法但底層還是 KV、複雜 query 會 scan 全表
- 替代：用 Aurora / PostgreSQL / Spanner

**2. 強一致 multi-row transaction**：

- DynamoDB Transaction 支援 25 個 item 的 ACID
- 超過 25 個 item 或跨 region 的 transaction 要改用 workflow / SQL / distributed SQL 設計
- 替代：Spanner / Aurora DSQL / CockroachDB

**3. 跨雲需求**：

- DynamoDB only on AWS、vendor lock-in
- 替代：Cosmos DB（Azure global NoSQL）、自管 ScyllaDB

**4. 大物件 / 文件儲存**：

- 單一 item 最大 400KB
- 大物件用 S3、metadata 用 DynamoDB

**5. 預算極度敏感 + 流量穩定**：

- 流量高度 predictable 的 sustained workload，自管 PostgreSQL / MySQL 可能更便宜
- DynamoDB 的 managed 跟 elastic 是有溢價的

## 跟其他 vendor 的取捨

**vs MongoDB（自管或 Atlas）**：

- DynamoDB：managed、partition 透明、application 主要管理 partition key，有 5 個 9 SLA
- MongoDB：彈性高、可自管、aggregation pipeline 強、跨雲可用
- 選 DynamoDB：AWS-only、想轉移 operation、partition 設計簡單可預測
- 選 MongoDB：跨雲、複雜 query、ad-hoc analysis

**vs Aurora（同 AWS）**：

- DynamoDB：KV、partition 擴展、無 connection pool 限制
- Aurora：SQL（PostgreSQL / MySQL）、有 transaction、ad-hoc query
- 詳見 [1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) 跟 [9.C29 Lemino case](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) — connection limit 是 RDB vs DynamoDB 的關鍵差異

**vs Redis（含 ElastiCache）作為 KV 替代**：

- DynamoDB：持久化、單 item 持久查得到、有 TTL 但物件不會自動失蹤
- Redis：純記憶體、預設不持久（MemoryDB 例外）、快但易失
- 選 DynamoDB：data 是 [source of truth](/backend/knowledge-cards/source-of-truth/)，需要持久保存
- 選 Redis：data 是 cache、丟了能 recompute

**vs Cosmos DB（cross-cloud）**：

- DynamoDB：AWS-only、KV 為主、無 multi-model
- Cosmos DB：Azure-only、multi-model（SQL / Mongo / Cassandra / Gremlin / Table）、5 個 [consistency level](/backend/knowledge-cards/consistency-level/)s
- 選 DynamoDB：AWS 生態、KV 純粹
- 選 Cosmos DB：Azure 生態、需要 multi-model、需要 multi-region active-active write

**vs Cassandra / ScyllaDB（self-managed）**：

- DynamoDB：managed、5 個 9 SLA、無 ops 負擔
- Cassandra / ScyllaDB：可自管、更深 tuning、跨雲可用
- 選 DynamoDB：團隊想把 DBA / SRE 操作責任交給 AWS
- 選 Cassandra / ScyllaDB：有 DBA、想 lock-in 風險低、需要極限 throughput tuning

**vs PostgreSQL（SQL baseline）**：

- 詳見 [PostgreSQL vendor page](/backend/01-database/vendors/postgresql/) 取捨段、跟 [1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) 的 connection model 對比
- 摘要：DynamoDB 是 *access pattern 固定 + 需要避免 connection-bound* 的選項；ad-hoc query / 複雜 transaction 留 PostgreSQL

## 容量規劃要點

從 09 案例庫提煉的 DynamoDB 容量規劃實踐：

**1. partition key 設計是命脈**：

- partition key 不均 → hot partition → 名義容量達不到
- composite key（event_id + user_id_hash）強制分散
- 對應 [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) 9000 萬 RPS 靠 partition 均勻、[9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 用 composite key 分散售票流量
- 詳見 [Hot Partition 卡片](/backend/knowledge-cards/hot-partition/)

**2. on-demand vs provisioned 選型**：

- 流量 peak/avg > 5x → on-demand
- sustained predictable → provisioned + auto-scaling
- 知名大事件（Black Friday）→ provisioned baseline + scheduled scale-up
- 對應 [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — on-demand 解放 over-provisioning

**3. Global Tables（multi-region active-active）**：

- 每個 region 都能寫、conflict resolution 用 LWW
- 容量在每個 region 獨立配置，全球總和要按 region 分別估算
- 對應 [9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) — 15 region 達 5 個 9 可用

**4. DAX（DynamoDB Accelerator）**：

- DynamoDB 前置 in-memory cache
- 從 single-digit ms 降到 microsecond
- 適合超高 read 重複的 workload（同樣 key 大量讀）
- 對應 [9.C29 Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) 用 DAX 加速

**5. Streams + Lambda**：

- DynamoDB 寫入 → Stream event → Lambda 處理
- 適合 CDC、event-driven 工作流
- 對應 [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 用 Stream 把 DynamoDB 當 durable queue 給 legacy server 消費

## Anti-recommendation 與升級路由

DynamoDB 的 managed elasticity 會讓團隊忽略 access pattern 的前置成本。這一段先說何時維持單純 table / index，再說何時升級到 Global Tables、DAX、Streams、或改回 SQL / document DB。

| 機制 / 路線               | 維持簡單設計的條件                                        | 升級訊號                                                               | 主要引用路徑                                                                                                                                 |
| ------------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 單 table / 少量 GSI       | access pattern 穩定、partition key 均勻、query 成本可預測 | 新查詢路徑大量增加、GSI 成本壓過主表、hot partition 出現               | [Hot Partition](/backend/knowledge-cards/hot-partition/)、[Workload Model](/backend/knowledge-cards/workload-model/)                         |
| On-demand capacity        | peak/avg 差距大、流量有事件性 surge                       | sustained traffic 穩定、成本曲線可預測                                 | [Peak Forecast](/backend/knowledge-cards/peak-forecast/)、[Cost Per Request](/backend/knowledge-cards/cost-per-request/)                     |
| Provisioned + autoscaling | baseline 穩定、團隊能預測高峰                             | 黑五、售票、直播等已知大事件需要預先升配                               | [Scheduled Scaling](/backend/knowledge-cards/scheduled-scaling/)                                                                             |
| DAX                       | read 重複率低、single-digit ms 已足夠                     | 同 key 超高讀取、需要 microsecond read                                 | [Cache Aside](/backend/knowledge-cards/cache-aside/)、[Stale Data](/backend/knowledge-cards/stale-data/)                                     |
| Global Tables             | single-region availability 已足夠                         | RTO/RPO、region residency 或 active-active write 是產品需求            | [RTO](/backend/knowledge-cards/rto/)、[RPO](/backend/knowledge-cards/rpo/)、[Consistency Level](/backend/knowledge-cards/consistency-level/) |
| SQL / document DB         | access pattern 可提前列舉                                 | ad-hoc query、JOIN、multi-row transaction 或 document traversal 成主題 | [Aurora vendor](/backend/01-database/vendors/aurora/)、[MongoDB vendor](/backend/01-database/vendors/mongodb/)                               |

DynamoDB 的簡單路徑是先把每個 query path 寫成契約。table、partition key、sort key、GSI 與 TTL 都應從 access pattern 反推；如果需求仍在探索期，PostgreSQL 或 MongoDB 可能提供更低的變更成本。

Global Tables 的升級路徑要先處理 conflict 與讀寫語意。它提供 multi-region availability，但 LWW conflict resolution、region-local capacity 與跨 region [reconciliation](/backend/knowledge-cards/data-reconciliation/) 仍要由 application contract 承擔。

## Deep article（已完成）

本 vendor 現有 deep article 覆蓋 DynamoDB 從 access pattern 反推到寫一致性、讀加速、事件驅動與資料生命週期的核心 production 議題：

| 主題                                                               | 文章                                                                | 對應 production 議題                                                           |
| ------------------------------------------------------------------ | ------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| 適用度 4 軸前置判讀 + access pattern 反推 PK/SK + durable queue    | [single-table-design-pattern](single-table-design-pattern/)         | 適用度判讀 + control plane vs data plane + 9.C15 Tixcraft Stream durable queue |
| 1000 WCU partition 上限 + composite key / calculated shard 修法    | [partition-key-antipatterns](partition-key-antipatterns/)           | 9.C15 Tixcraft 6750x 擴展、mode × partition 在 provisioned / on-demand 表現    |
| GSI / LSI projection 三型、sparse、DAX 補位                        | [gsi-lsi-design](gsi-lsi-design/)                                   | GSI 自己會 hot partition、Capcom derive vs Lemino case fact 分層               |
| 6 軸 capacity mode 決策 + auto-scaling 邊界 + cost crossover       | [on-demand-vs-provisioned](on-demand-vs-provisioned/)               | Zomato 50% 成本下降、Zoom 30x permanent surge、Amazon Ads sustained workload   |
| Multi-region active-active + LWW conflict + cross-device sync      | [global-tables-conflict](global-tables-conflict/)                   | Genesys 99.999% / 15 region、Disney+ 跨裝置同步                                |
| Strongly / eventually consistent read 取捨                         | [consistency-model-optimization](consistency-model-optimization/)   | read consistency 成本選擇                                                      |
| 跨 item 原子性 + conditional write + optimistic lock + idempotency | [transactions-conditional-writes](transactions-conditional-writes/) | 雙寫不一致、超賣 race、transaction 2x 成本邊界                                 |
| DAX cluster + item/query cache + write-through + invalidation 邊界 | [dax-caching-strategy](dax-caching-strategy/)                       | 讀峰值 p99 尖刺、query cache 只靠 TTL 失效、strong read 繞過 cache             |
| Streams CDC + shard 順序 + Lambda 消費 + 失敗處理                  | [streams-lambda-event-driven](streams-lambda-event-driven/)         | 下游即時反應、at-least-once 冪等、毒丸 record 隔離                             |
| TTL 自動過期 + 48h 刪除延遲 + 過期仍可讀 + storage 成本            | [ttl-data-lifecycle](ttl-data-lifecycle/)                           | 9.C26 PayPay 每日上億訊息 storage 清理、過期未刪 item 讀取陷阱                 |

Migration playbook：[從 RDS / MongoDB 遷移到 DynamoDB](migrate-rds-mongodb-to-dynamodb/)（Type E paradigm shift、access-pattern-first 重建模 + 混合架構 + Zomato cost crossover）。

跨 vendor entry：先看 [DB3 vendor selection](../db3-vendor-selection/)（MongoDB / DynamoDB / Cosmos DB 三方選型 + workload shape 前置判讀），再進本 vendor 的 deep article。

## 後續擴充（仍待補）

- DynamoDB Streams 進階 lab：Kinesis Data Streams for DynamoDB 多消費者 fan-out 與長 retention 重播（Lambda vs Kinesis 比較層已在 [streams-lambda-event-driven](streams-lambda-event-driven/) 覆蓋、此處指可操作的深度 hands-on lab）
- Export to S3 / point-in-time export 做離線分析
- DynamoDB → SQL / search / analytics split（遷出方向 playbook）
- Backup / PITR restore drill（hands-on lab）

## 案例對照

| 案例                                                                                          | 規模                                     | 教學重點                             |
| --------------------------------------------------------------------------------------------- | ---------------------------------------- | ------------------------------------ |
| [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)     | 9000 萬 RPS + 500 萬 WPS                 | partition 均勻設計典範               |
| [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) | IOPS 20 → 135K（6750x 擴展）             | flash-sale 緩衝模式                  |
| [9.C18 Zoom](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/)               | 30x DAU surge（1000 萬 → 3 億）          | SaaS surge baseline 重新校準         |
| [9.C19 Capcom](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/)            | billions of requests / single-digit ms   | 遊戲後端 KV、跨遊戲共用平台          |
| [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)     | 4x 吞吐、90% latency 降、50% 成本降      | TiDB → DynamoDB cross-DB 遷移        |
| [9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/)  | 99.999% / 15 region / 8000+ orgs         | B2B SaaS 5 個 9 可用性               |
| [9.C26 PayPay](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/)       | 3 億 訊息 / 天                           | 行動支付通知系統、TTL 自動清理       |
| [9.C27 Disney+](/backend/09-performance-capacity/cases/disney-plus-content-metadata/)         | 每日數十億 actions                       | 串流 metadata 層 + cross-device 同步 |
| [9.C29 Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/)  | tens of thousands req/sec、5M MAU / 3 月 | RDB connection limit → DynamoDB      |

DynamoDB case 的讀法是先分類 access pattern，再看容量模式。Amazon Ads / Capcom / Disney+ 說明高吞吐 KV，Zoom / Tixcraft / Lemino 說明 surge 與 connection-free scaling，Zomato 則說明 on-demand cost model 如何改變 over-provision 壓力。

## 反向 sibling 路由

DynamoDB 的反向 sibling 路由用來把 RDBMS 退場條件寫清楚。若讀者從 PostgreSQL / MySQL 的 connection bottleneck 過來，先讀 [Lemino case](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) 與 [1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)；若需求仍需要 ad hoc SQL、join 與 transaction report，回 [Aurora vendor](/backend/01-database/vendors/aurora/) 或 [PostgreSQL vendor](/backend/01-database/vendors/postgresql/)；若需求是 global document model 與 Azure 生態，再對照 [Cosmos DB vendor](/backend/01-database/vendors/cosmosdb/)。

這條路由的判準是 access pattern 是否穩定到可以先設計 key。DynamoDB 擅長固定 lookup、寫入尖峰、connection-free scaling 與 TTL 類生命週期；資料探索、報表 join 與多條件查詢仍應留在 SQL / search / analytics service。

## 常見陷阱

從公開 incident 跟 case 提煉：

- **partition key 集中**：event_id 一個演唱會、bot user 大量同 user_id 寫入 → 用 composite key 或 write sharding
- **單一 partition 達 3000 RCU / 1000 WCU 上限**：throttling event 出現、即使整體 capacity 還沒滿
- **Scan 全表**：scan 會吃光 capacity，正式讀取路徑應回到 query / index design
- **DAX 跟 DynamoDB 直連混用**：寫入直連 DynamoDB、讀經過 DAX → cache 一致性問題
- **Global Tables conflict**：跨 region 同 key 同時被寫、LWW 可能丟失寫入、要設計 idempotency

## 下一步路由

- 完整 T1 對照：[01-database vendors index](/backend/01-database/vendors/)
- 平行：[Aurora vendor page](/backend/01-database/vendors/aurora/)（SQL 對比）
- 上游：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)
- 下游：[1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)（從 RDBMS 遷 DynamoDB 案例）
- 跨模組：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)、[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)
- Last reviewed：2026-05-22（capacity mode / Global Tables / best practices 屬時間敏感 claim）
- 官方：[Amazon DynamoDB Customers](https://aws.amazon.com/dynamodb/customers/)、[DynamoDB 設計 best practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
