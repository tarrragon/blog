---
title: "1.10 KV / Document DB 容量規劃"
date: 2026-05-13
description: "DynamoDB / Cosmos DB / Bigtable / MongoDB 等 KV / Document DB 的容量設計、partition key 取捨、capacity mode 選擇"
weight: 10
tags: ["backend", "database", "kv", "capacity"]
---

## 概念定位

KV / Document DB 的容量規劃跟傳統 OLTP 完全不同。OLTP 容量靠「instance type 升級 + read replica」、KV 靠「partition 切分 + capacity unit 配置」。兩者瓶頸不同、可擴範圍不同、設計取捨也不同。

本章針對 DynamoDB、Azure Cosmos DB、Google Cloud Bigtable、MongoDB Atlas 等主流 KV / Document DB、整理容量規劃的共通方法論。讀完後讀者能回答：partition key 怎麼設計才不會 hot partition、on-demand vs provisioned 怎麼選、什麼時候從 single-region 升到 multi-region。

跟 [1.1 高併發資料存取](/backend/01-database/high-concurrency-access/) 的關係：1.1 處理 OLTP 高併發、本章處理 KV 高併發。兩者讀者群有重疊但解法不同。

跟 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 跟 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 的關係：本章從 *DB 視角* 看容量、9.4 / 9.6 從 *workload 視角* 看容量、兩者互補。

## KV / Document DB 的容量模型

KV 容量模型可以簡化成一條公式：**總容量 = partition 數量 × 每 partition 上限**。

vendor 不同、細節不同，但都遵循這個邏輯。

**Amazon DynamoDB**：

- 容量單位是 RCU（Read Capacity Unit）跟 WCU（Write Capacity Unit）
- 1 RCU = 1 strongly consistent read of 4KB / sec、2 eventually consistent reads
- 1 WCU = 1 write of 1KB / sec
- 每個 partition 上限：3000 RCU / 1000 WCU、底層 partition 數量透明

**Azure Cosmos DB**：

- 容量單位是 RU（Request Unit）— 把 read / write / query 統一抽象
- 1 RU = strongly consistent read of 1KB document
- 寫成本約 5x read、複雜 query 可達數百 RU
- 每個 logical partition 上限：10,000 RU/s

**Google Cloud Bigtable**：

- 容量單位是 node（SSD / HDD）
- 每個 node 約 10,000 reads/sec、10,000 writes/sec（依 row size）
- partition 透明、靠 tablet 自動分裂

**MongoDB Atlas**：

- 容量單位是 cluster tier（M10、M30、M60 等）+ shard
- 每個 shard 是獨立 mongod replica set、容量按 instance type 跟 storage
- 主動 sharding 設計、跟 DynamoDB 透明 partition 不同

**共通點**：容量上限不是「單一 number」、是「partition / shard 數量 × 每 partition 上限」。要擴容、要嘛加 partition、要嘛升級 partition、不能像 OLTP 一樣換更大 instance。

## Partition key 設計：容量的命脈

partition key 設計不均勻、實際容量遠低於名義。這是 KV DB 最常見的 production issue。

**Hot partition 的成因**：

- 名義容量 = partition 數量 × 每 partition 上限
- 實際容量 = 最熱 partition 上限（如果分布不均）
- 100K RPS 名義能撐、若 80% 流量集中在 1 個 partition、實際 *只能撐 3K RPS（DynamoDB partition 上限）*

**識別 hot partition 的訊號**：

- throughput 上不去、但 average resource utilization 低
- 某些 key 的 request latency 飆、其他 key 正常
- DynamoDB throttling event 出現（即使 capacity 還沒滿）
- Cosmos DB 顯示「per-partition RU consumption skew」

**設計策略**：

1. **天然均勻 partition key**：user_id、order_id、device_id 等天然分布廣的 ID。最簡單、最常用。
2. **Composite partition key**：把容易集中的維度（event_id）跟均勻的維度（user_id_hash）組合。例如 `event_id#user_id_hash_mod_100`、強制把同一 event 的流量分散到 100 個 sub-partition。
3. **Write sharding**：在 partition key 後加 random suffix。`event_id#0` ~ `event_id#9` 讓同一個 event 變成 10 個 partition。讀的時候要 scatter-gather 從 10 個 partition 讀回來。
4. **Time-bucket**：對時序資料、加 minute / hour bucket。`metric#2026-05-13-T12`、每個時段一個 partition。

**對應案例**：

- [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) — 9000 萬 reads/sec 靠 partition 設計均勻、不是純擴 capacity
- [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — 售票 event_id 天然容易 hot、必須用 composite key 或 write sharding 分散
- [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) — Cosmos DB synthetic partition key 強制分散

詳見 [Hot Partition 卡片](/backend/knowledge-cards/hot-partition/)。

## Capacity mode：on-demand vs provisioned

DynamoDB / Cosmos DB 都提供兩種容量模式、各有適用場景。

**On-demand（pay-per-use）**：

- 不需事前配置 RCU / WCU / RU
- 自動 scale up / down、處理突發流量
- 單位成本高（約 7x provisioned）
- 適合：流量不可預測、burst 頻繁、開發 / 測試環境

**Provisioned（預配置）**：

- 預先訂購 RCU / WCU / RU
- 超過配額會 throttle（除非開 auto-scaling）
- 單位成本低
- 適合：流量可預測、sustained workload、生產環境

**選型決策**：

| 場景                          | 建議 mode                                 |
| ----------------------------- | ----------------------------------------- |
| 流量 peak/avg 比 < 3x         | provisioned + auto-scaling                |
| 流量 peak/avg 比 > 5x         | on-demand                                 |
| 流量極端 bursty（flash-sale） | on-demand                                 |
| sustained growth 穩定上升     | provisioned + scheduled scaling           |
| 短期測試 / POC                | on-demand                                 |
| 已知大事件（Black Friday）    | provisioned baseline + scheduled scale-up |

**對應案例**：

- [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — TiDB 必須長期 over-provision、換 DynamoDB on-demand 後 pay-per-use、50% 成本下降
- [9.C26 PayPay](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/) — sustained 3 億 msg/day 適合 provisioned + auto-scaling
- [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) — 9000 萬 RPS sustained workload 必然 provisioned + careful tuning

詳見 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/cost-engineering/) 的成本曲線分析。

## 一致性模型：strong vs eventual vs session

KV / Document DB 通常提供多個 consistency level、不同 level 對應不同延遲跟可用性。

**DynamoDB**：

- Eventually consistent reads（預設、便宜）：1 sec 內收斂、cost = 0.5 RCU
- Strongly consistent reads：跨 AZ quorum、cost = 1 RCU、不可跨 region
- 沒有中間 level

**Cosmos DB**（最豐富）：

- **Strong**：linearizable、跨 region quorum、最高 latency
- **Bounded staleness**：訂上限（時間 / 版本差異）
- **Session**：同一 session 內強一致（最常用）
- **Consistent prefix**：保證寫入順序、不保證收斂時間
- **Eventual**：最便宜、最終一致

**Bigtable**：

- Single-region：strongly consistent
- Replicated：eventually consistent

**選 consistency level 的工程後果**：

- Strong consistency → 跨 region 延遲（quorum round-trip）
- Eventual → 用戶可能看到舊資料、需要 application 容忍
- Session → 大多數網路服務的 sweet spot（用戶看自己寫的東西要立即、別人寫的可以稍晚）

**對應案例**：

- [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) — external consistency（線性化）跨地區、付出 quorum 延遲代價
- [9.C30 Microsoft 365 Cosmos DB](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — 分析平台用 weakest consistency 換最大 throughput

詳見 [1.3 Transaction Boundary](/backend/01-database/transaction-boundary/) 的一致性取捨。

## Multi-model 取捨

部分 KV / Document DB 支援多個 model interface、同一服務跑不同抽象。

**Cosmos DB（最廣 multi-model）**：

- SQL API（document）
- MongoDB API（document、wire-protocol compatible）
- Cassandra API（wide-column）
- Gremlin（graph）
- Table（key-value）

**DynamoDB（KV + document）**：

- 原生 KV、但 attribute 可以是 nested map / list（document-like）
- 沒有 SQL interface（PartiQL 是 query language、不是 model）

**Bigtable（wide-column）**：

- 沒有 multi-model、純 wide-column
- 替代方案：用 Spanner + Bigtable 組合

**Multi-model 的優缺**：

- ✅ 同一團隊不必管多個 vendor、ops 簡化
- ✅ 不同 use case 用同一 datastore、減少 data sync
- ❌ vendor lock-in 加深、難換
- ❌ 每個 API 都不是 *最好* 的（compromise）— MongoDB API 跟 native MongoDB 有 behavior 差異

**選型建議**：

- 已用 single model → 不必為 multi-model 而換
- 多種 use case 同時上 → 評估 Cosmos DB（特別是 MongoDB workload + 新需求）
- 純 KV 高吞吐 → DynamoDB / Bigtable 比 Cosmos DB 通常便宜

**對應案例**：

- [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — MongoDB → Cosmos DB MongoDB API、應用層幾乎不改、底層改用 Cosmos 分散式架構
- [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) — 用 SQL API、不需要 MongoDB compat

## KV DB 作為寫入緩衝的特殊用法

[9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 揭露一個非傳統用法：DynamoDB 不當 OLTP、當 *durable queue*。

**模式**：前端把訂單塞進 DynamoDB（高吞吐、partition 均勻）、後端 legacy server 按自己能承受的速度從 DynamoDB 消費。

**為什麼用 DynamoDB 而非 SQS / Kafka**：

- DynamoDB Stream 提供 change data capture、後端可以 stream 消費
- 寫入後立即可查（OLTP-like）、不是純 fire-and-forget
- partition 設計讓單一事件可以分散到多個 partition
- 同樣 vendor、不必另起一個 broker 服務

**適用場景**：

- 突發流量遠超後端處理能力
- 後端是 legacy、不容易擴
- 需要寫入後立即可查（用戶看「我下單成功了」）

**不適用場景**：

- 純 fire-and-forget（用 SQS 更便宜）
- 高吞吐 stream processing（用 Kafka 更專業）
- 順序性嚴格要求（DynamoDB Streams 只在 partition 內保證順序）

詳見 [9.C15 Tixcraft 案例](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 的詳細分析。

## 連線管理：跟 OLTP 完全不同

KV / Document DB 通常是 *HTTP / gRPC 介面*、不是 *connection pool*。這是跟 OLTP 完全不同的設計、影響應用層架構。

**OLTP（PostgreSQL / MySQL）**：

- 每個 application instance 維護 connection pool（10-100 connections）
- connection 是有狀態的（transaction、session variable）
- pool size × instance 數量 ≤ DB 上限（PostgreSQL 預設 100、PgBouncer 可破百）
- [9.C29 Lemino 案例](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) 揭露 RDB connection 是隱性 bottleneck

**KV（DynamoDB / Cosmos DB）**：

- 純 HTTP / gRPC、無 stateful connection
- 每個 request 獨立、不必預先 establish connection
- 沒有 connection limit 概念
- 應用層擴容不會打爆 DB connection

這個差異是 KV DB 在 *surge 場景* 比 OLTP 有優勢的主因 — KV 不會 connection saturate。

## 案例對照

| 案例                                                                                                | 教學重點                                                                           |
| --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| [9.C1 AWS Prime Day 2025](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) | DynamoDB 24 小時 1.51 億 RPS、毫秒級延遲、可預期峰值上限參考                       |
| [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)           | 9000 萬 RPS + 99.999% 可用 — partition 均勻設計典範                                |
| [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/)   | Cosmos DB 1M RU/s + multi-model + global distribution                              |
| [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)       | DynamoDB 當 durable queue、IOPS 20→135K                                            |
| [9.C16 SeatGeek](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/)             | DynamoDB 4 表 + Lambda 實作 virtual waiting room、跟 Tixcraft 的隱性緩衝形成姊妹案 |
| [9.C18 Zoom](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/)                     | 30x DAU surge、DynamoDB 撐 control plane                                           |
| [9.C19 Capcom](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/)                  | 遊戲後端 KV、billions of requests + single-digit ms                                |
| [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)           | TiDB → DynamoDB、50% 成本下降的取捨                                                |
| [9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/)                   | Black Friday 1.67 億請求 / 24h、Cosmos DB 多 region                                |
| [9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/)        | 99.999% 跨 15 region、DynamoDB 為預設 DB                                           |
| [9.C26 PayPay](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/)             | 3 億訊息 / 天、TTL 自動清理                                                        |
| [9.C27 Disney+](/backend/09-performance-capacity/cases/disney-plus-content-metadata/)               | billions of actions daily、watchlist + 播放進度                                    |
| [9.C29 Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/)        | connection limit 才是 RDB bottleneck、改用 DynamoDB                                |

[9.C16 SeatGeek](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/) 把 DynamoDB 當 *排隊調度系統*、不只當 queue buffer：用 Counters table 控發 token 的速率、Queue table 紀錄序號、Connection table 串 WebSocket。這個架構跟 [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 的「全部塞進 DynamoDB 隱性緩衝」是兩種對立取捨 — Tixcraft 用透明度換流量吸收能力、SeatGeek 用流量吸收能力換體驗可見度。判讀重點：KV DB 不只能當 OLTP 替代品、4 張表組合就能變成業務級調度引擎、選表前要先確定業務需要哪一面。

## 下一步路由

- 上游：[0.2 State Storage Selection](/backend/00-service-selection/state-storage-selection/) — KV vs OLTP vs SearchIndex 選型
- 平行：[1.1 高併發資料存取](/backend/01-database/high-concurrency-access/)（OLTP 版本）/ [1.3 Transaction Boundary](/backend/01-database/transaction-boundary/)
- 下游：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)、[1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)
- 跨模組：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)（hot partition 量測）、[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[9.7 成本邊界](/backend/09-performance-capacity/cost-engineering/)

## 既建知識卡片

- [Hot Partition](/backend/knowledge-cards/hot-partition/)
- [Saturation Point](/backend/knowledge-cards/saturation-point/)
- [Connection Pool](/backend/knowledge-cards/connection-pool/)
- [Tail Latency](/backend/knowledge-cards/tail-latency/)
