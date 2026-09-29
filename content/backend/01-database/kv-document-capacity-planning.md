---
title: "1.10 KV / Document DB 容量規劃"
date: 2026-05-13
description: "DynamoDB / Cosmos DB / Bigtable / MongoDB 等 KV / Document DB 的容量設計、partition key 取捨、capacity mode 選擇，以及加 region 之後寫入容量怎麼跟著乘上去"
weight: 10
tags: ["backend", "database", "kv", "capacity"]
---

## 概念定位

這篇整理 DynamoDB、Azure Cosmos DB、Google Cloud Bigtable、MongoDB Atlas 這類 KV / Document DB 的容量規劃：容量模型與連線模型、partition key 怎麼設計才不會 hot partition、on-demand 與 provisioned 怎麼選、一致性等級、加 region 之後的容量代價與 multi-model 的取捨，以及把 KV 當寫入緩衝與限流的用法。範圍是資料庫這一端的容量；OLTP 的高併發存取在 [高併發資料存取](/backend/01-database/high-concurrency-access/)，從 workload 出發找飽和點與建容量模型在 [Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 與 [容量規劃模型](/backend/09-performance-capacity/capacity-planning/)。

KV / Document DB 的容量規劃跟傳統 OLTP 不同。OLTP 容量靠「instance type 升級 + read replica」、KV 靠「partition 切分 + capacity unit 配置」。兩者瓶頸不同、可擴範圍不同、設計取捨也不同。

## KV / Document DB 的容量模型

KV 容量模型可以簡化成一條公式：**總容量 = partition 數量 × 每 partition 上限**。

vendor 不同、細節不同，但都遵循這個邏輯。

### HTTP API DB vs connection-based DB 的本質差異

KV DB 在 surge 場景比 OLTP 有結構性優勢的主因、不只是 partition 設計、是 *連線模型* 的本質差異。

**Connection-based DB**（PostgreSQL、MySQL、MongoDB、Cassandra）：

- 用戶端跟 DB 維持 TCP connection、connection 有 state（authenticated session）
- 每個 connection 在 DB server 端佔記憶體 + 一個 process/thread
- connection 上限由 DB 設定決定（PostgreSQL 的 `max_connections` 預設 100、MySQL 預設 151），調高也受每條連線佔用的記憶體限制
- application 想開更多 connection、DB 直接拒絕

**HTTP API DB**（DynamoDB、Cosmos DB、Bigtable、Firestore）：

- 用戶端每次 request 開新 HTTP connection（或用 keep-alive 池）
- DB 端沒有「per-user connection state」、是 stateless API server
- 沒有 connection 上限概念、能力上限是 *每 partition 的 RU / RCU*
- application 加多少 instance 都不會碰到 DB 端的連線上限；請求量仍然消耗 RCU / RU

對應 [9.C29 Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) — NTT DOCOMO 串流服務選 DynamoDB 而非 RDB 的關鍵原因是 RDB 的 connection limit 在 surge 場景變成 bottleneck、HTTP API 模型沒這個問題。

判讀含義：選 KV DB 不只是「擴容容易」、是 *連線模型* 適合無 state HTTP 服務的天然契合。微服務數量增加時、HTTP API DB 不需要每次都 review connection pool 設定。但若 application 仍以 SQL transaction 為主流程設計、改 KV 需要 *改 application 架構*、不是換 driver 而已。

### 各 vendor 的容量單位

容量公式裡的「每 partition 上限」在各 vendor 用不同的單位計：

**Amazon DynamoDB**：

- 容量單位是 RCU（Read Capacity Unit）跟 WCU（Write Capacity Unit）
- 1 RCU = 1 strongly consistent read of 4KB / sec、2 eventually consistent reads
- 1 WCU = 1 write of 1KB / sec
- 每個 partition 上限：3000 RCU / 1000 WCU、底層 partition 數量透明

**Azure Cosmos DB**：

- 容量單位是 RU（Request Unit）— 把 read / write / query 統一抽象
- 1 RU = 用 id 與 partition key 讀一筆約 1KB 的 item（point read）；strong 與 bounded staleness 一致性下的讀取約耗兩倍 RU
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

**共通點**：容量上限是「partition / shard 數量 × 每 partition 上限」。擴容有兩條路：加 partition / shard，或提高每個 partition / shard 的上限。DynamoDB 與 Cosmos DB 的單 partition 上限固定，只能靠加 partition；Bigtable 靠加 node；MongoDB Atlas 升 cluster tier 就是替每個 shard 換更大的 instance，換完之後容量仍按 shard 數量相乘。

## Partition key 設計：容量的命脈

partition key 設計不均勻、實際容量遠低於名義。這是 KV DB 最常見的 production issue。

**Hot partition 的成因**：

- 名義容量 = partition 數量 × 每 partition 上限
- 分布不均時，實際容量 = 最熱 partition 的上限 ÷ 最熱 partition 分到的流量比例
- 名義容量 100K reads/sec 的表，若 80% 的讀取集中在 1 個 partition，那個 partition 到 3,000 RCU（DynamoDB 單 partition 上限）就開始 throttle，整張表 *實際只承受得了約 3,750 reads/sec*（3,000 ÷ 0.8，以每筆 4KB 以內的 strongly consistent read 計）

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

### 彈性來自 partition key 均勻分布

KV DB 的吞吐彈性等於 partition key 均勻分布的結果。partition key 均勻時、實際容量接近名義容量；partition key 不均時、實際容量由最熱 partition 的上限（DynamoDB 每 partition 3000 RCU / 1000 WCU）與它分到的流量比例決定、加再多 partition 也分不走同一個 key 的流量。

對應 [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — 售票 IOPS 從 20 衝到 135K 的 6,750 倍彈性、前提是 partition key 把流量分散到大量 partition（合理做法是 composite key `event_id + user_id_hash` 或 write sharding `event_id + random_suffix`）。若用裸 `event_id` 當 partition key、同一場演唱會所有訂單擠進同一個 partition、實際 IOPS 上限被鎖在 1000 WCU、跟 partition 總數無關。

判讀重點：讀「Amazon Ads 9000 萬 reads/sec」、「DynamoDB 1.51 億 RPS」這類數字、要追問「partition 設計是什麼」、再判斷自己的服務能否複製。換成 DynamoDB 這類按 partition 擴容的資料庫，只讓容量有機會隨 partition 數量成長；partition key 把流量分散到足夠多的 partition，那份容量才用得上，兩個條件缺一不可。只換 DB 而沒解決 partition key、會出「換了 DB 但 hot partition 依舊」的事故。

## Capacity mode：on-demand vs provisioned

DynamoDB / Cosmos DB 都提供兩種容量模式、各有適用場景。

**On-demand（pay-per-use）**：

- 不需事前配置 RCU / WCU / RU
- 自動 scale up / down、處理突發流量
- 單位請求的價格高於 provisioned；差距隨 AWS 調價改變（2024 年 11 月 on-demand throughput 降價 50%），比較前查當下的價目表
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

### 計費粒度 vs 工程顆粒

KV / Document DB 的計費單位（DynamoDB 的 RCU/WCU、Cosmos DB 的 RU、Spanner 的 processing unit）決定容量規劃可以從多小開始。計費粒度太大、中小規模負載付過多錢；計費粒度太小、大規模負載要管理很多細項。

對應 [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) — Spanner 早期最小單位是 1 node（等於 1000 processing units，pu）、對中小負載門檻過高。後來推出 100 pu 起跳的 granular sizing、讓容量規劃可以從小開始、降低 onboarding 門檻。

**選型含義**：

- **新服務 / 中小規模**：選計費粒度小的選項（Cosmos DB serverless、Spanner granular sizing、DynamoDB on-demand）、避免一開始就為了「未來會用到」過配。中小規模付過配成本、實際就是替「不確定的未來」付保險費、保險費過高代表選錯產品。
- **穩定大規模**：計費粒度可大（DynamoDB provisioned with reserved capacity、Spanner full-node provisioning）、單價較低。Reserved capacity 通常綁 1-3 年合約、要看業務 *未來 12-24 月需求是否穩定*、若業務量可能下降或遷移、Reserved 反成沉沒成本；若業務量穩定上升、Reserved 是合理 hedging。
- **POC / 測試**：選 on-demand 或 serverless、付實際用量、別為了未實際 production 的 workload 付 reserved 成本。

判讀重點：計費粒度同時是 *vendor 商業策略* 跟 *工程顆粒*、選 vendor 時要看 *min sizing* 跟 *增量 granularity*、不只看 max throughput。

### 業務邏輯變化 → 讀寫比跳量級

讀寫比變化是容量規劃的早期警訊、但常被忽略。原始容量規劃通常基於某個讀寫比（例如 1:1 或 5:1）、業務邏輯改變可能讓比例跳一個量級、原容量規劃失效。

對應 [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) — 廣告事件量測讀寫比 18:1（曝光發生 1 次、後續查詢 18 次）。如果業務新增即時報表功能、讀次數從 18 跳到 180、容量規劃要重做、不是「再加一點 capacity」。

**常見業務變化導致讀寫比跳量級**：

- 新增即時 dashboard：每筆資料被查詢頻率從 1 次跳到 N 次
- 新增推薦演算法：每用戶 read profile 從每次登入 1 次變成每次推薦 1 次（× 推薦頻率）
- 新增 audit / compliance 查詢：每筆敏感資料額外被查 5-10 次
- 新增 cache：讀次數從 100 降到 5（cache hit rate 95%）— 跟其他變化方向相反、是 *capacity 該縮容* 的訊號、若沒同步 review 反而會繼續按舊容量付錢
- 新增 anti-fraud 檢測：每寫入觸發 N 次 read 驗證

判讀重點：容量規劃 review cadence 不只看流量、要 review *讀寫比* 是否漂移。比例跳量級是設計需要重做的訊號、不是單純 capacity 增加（或減少）的訊號。

## 一致性模型：strong vs eventual vs session

KV / Document DB 通常提供多個 [consistency level](/backend/knowledge-cards/consistency-level/)、不同 level 對應不同延遲跟可用性。

**DynamoDB**：

- Eventually consistent reads（預設、便宜）：1 sec 內收斂、cost = 0.5 RCU
- Strongly consistent reads：跨 AZ [quorum](/backend/knowledge-cards/quorum/)、cost = 1 RCU；global table 預設的 multi-Region eventual consistency（MREC）模式下，那一筆資料若最後在別的 region 更新，strong read 可能讀到舊值，要跨 region 讀到最新值得在建表時選 multi-Region strong consistency（MRSC）模式（AWS 文件〈How DynamoDB global tables work〉）
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

## 加一個 region，寫入容量要在每個 region 各付一份

從 single-region 升到 multi-region 的決定由三件事驅動：可用性目標要不要撐過整個 region 失效、使用者分布在多遠的地方、法規要不要資料留在境內。三件都不是容量問題，判斷方法在 [全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 的〈可用性目標的成本曲線〉〈延遲代價：跨 region quorum 不可壓縮〉〈跨地理合規：法規限制下的 global OLTP〉三節，那些判斷對 SQL 與 KV 都成立。這一節處理的是決定做了之後，KV / Document DB 的容量規劃跟著改變的地方。

改變的核心是 **replicated write**：一筆寫入在一個 region 發生之後，要在其餘每個 replica region 再寫一次，而那一次寫入消耗的是目的地 region 的寫入容量。所以 multi-region 的每個 region 各自要容納全部 region 加總的寫入量，同一份寫入容量沒辦法攤給多個 region 共用。

- **DynamoDB global tables**：replication 消耗 write capacity，provisioned 模式下應用程式的寫入加上 replication 的寫入超過配置的 WCU 就會 throttle。global table 的寫入容量設定在所有 replica 之間強制同步、不能逐 region 調整，讀取容量可以逐 region override（AWS 文件〈How DynamoDB global tables work〉）。
- **Cosmos DB**：container 配置的 RU/s 在帳號的每一個 region 都保留一份，帳號配置 `T` RU/s、關聯 `N` 個 region，每小時計費的是 `T × N` RU/s，storage 也在每個 region 各存一份（Microsoft Learn〈Optimize cost for multi-region deployments〉）。

Microsoft Learn 的計費範例把這個乘法寫成具體數字：

```text
# 一個 container 配置 10,000 RU/s、存 0.5 TB，從 1 個可寫 region 加到 2 個可寫 region
throughput 計費（1 個 region）：10,000 RU/s × 730 小時
throughput 計費（2 個 region）：2 × 10,000 RU/s × 730 小時
storage 計費（1 個 region）：0.5 TB
storage 計費（2 個 region）：2 × 0.5 TB = 1 TB
```

replicated write 也把 partition key 的設計結果複製到每個 region：寫入集中在少數幾個 partition key 時，每個 replica region 裡的同一批 partition 收到的是同樣集中的 replication 寫入，熱點不會因為多了 region 而分散。所以 hot partition 要在 single-region 階段就修掉，加 region 只會把同一個熱點乘上 region 數。

一致性模式的選擇同時決定容量與可用的功能，而 DynamoDB 的模式在建表時就定死、之後不能改：

- **Multi-Region eventual consistency（MREC）**：預設模式。replication 非同步、通常一秒內到達，同一筆資料在兩個 region 同時被改時以 last writer wins 收斂。寫入與 strong read 的延遲都比 MRSC 低，而 strong read 在資料最後由別的 region 更新時可能讀到舊值。
- **Multi-Region strong consistency（MRSC）**：寫入同步複製到至少另一個 region 才回成功，任何 replica 上的 strong read 都讀到最新版本，RPO 是零。代價寫在限制裡：必須恰好部署在三個 region（三個 replica，或兩個 replica 加一個 witness）、寫入與 strong read 的延遲隨 region 間的距離增加、不支援 transaction 操作、TTL 與 LSI，而且只能從一張空表轉換。

Cosmos DB 的對應選擇是單一寫入 region 還是 multi-region writes：單一寫入 region 只有一個 region 接受寫入，其餘 region 服務讀取；multi-region writes 讓每個 region 都能寫，同一筆資料在兩個 region 被同時改寫時要靠 conflict resolution 收斂，機制與 Strong 跟 multi-region writes 的互斥在 [Cosmos DB Multi-Region Write](/backend/01-database/vendors/cosmosdb/multi-region-write-conflict/)。DynamoDB 的 LWW 衝突與跨裝置同步的用法在 [DynamoDB Global Tables](/backend/01-database/vendors/dynamodb/global-tables-conflict/)，MongoDB 加 region 同時改 sharding 與 replication topology 的流程在 [MongoDB Shard Expansion + Multi-DC](/backend/01-database/vendors/mongodb/shard-expansion-multi-dc/)。

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

- 優勢：同一團隊不必管多個 vendor、ops 簡化
- 優勢：不同 use case 用同一 datastore、減少 data sync
- 限制：vendor lock-in 加深、難換
- 限制：每個 API 都不是 *最好* 的（compromise）— MongoDB API 跟 native MongoDB 有 behavior 差異

**選型建議**：

- 已用 single model → 不必為 multi-model 而換
- 多種 use case 同時上 → 評估 Cosmos DB（特別是 MongoDB workload + 新需求）
- 純 KV 高吞吐 → DynamoDB / Bigtable 比 Cosmos DB 通常便宜

**對應案例**：

- [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — MongoDB → Cosmos DB MongoDB API、應用層幾乎不改、底層改用 Cosmos 分散式架構
- [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) — 用 SQL API、不需要 MongoDB compat

## KV DB 作為寫入緩衝的特殊用法

flash-sale 架構可以把 KV 當寫入緩衝：前端先把請求寫進 KV，後端再按自己的處理速度消費。broker 與 queue 本身的設計在 [03 訊息佇列模組](/backend/03-message-queue/)，高峰事件前的整體準備在 [9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/)；這一節只談把 KV 當 buffer 的取捨。

[9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 揭露一個非傳統用法：DynamoDB 不當 OLTP、當 *durable queue*。

**模式**：前端把訂單塞進 DynamoDB（高吞吐、partition 均勻）、後端 legacy server 按自己能承受的速度從 DynamoDB 消費。

**為什麼用 DynamoDB 而非 SQS / Kafka**：

- DynamoDB Stream 提供 change data capture、後端可以 stream 消費
- 寫入後立即可查（OLTP-like）、不是純 fire-and-forget
- partition 設計讓單一事件可以分散到多個 partition
- 訂單已經寫在 DynamoDB，不必另起一個 broker 服務

**適用場景**：

- 突發流量遠超後端處理能力
- 後端是 legacy、不容易擴
- 需要寫入後立即可查（用戶看「我下單成功了」）

**不適用場景**：

- 純 fire-and-forget（用 SQS 更便宜）
- 高吞吐 stream processing（用 Kafka 更專業）
- 順序性嚴格要求（DynamoDB Streams 只在 partition 內保證順序）

詳見 [9.C15 Tixcraft 案例](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 的詳細分析。

## 連線管理：connection pool 要不要跟著 instance 數量算

連線模型的差異（見〈HTTP API DB vs connection-based DB 的本質差異〉）落到應用層架構上，是 connection pool 的總量要不要跟著 application instance 數量一起算。

**OLTP（PostgreSQL / MySQL）**：每個 application instance 維護自己的 connection pool（10-100 connections），connection 帶著 transaction 與 session variable 這類狀態，所以 pool size × instance 數量要小於 DB 的連線上限；PgBouncer 這類 connection pooler 讓應用層開出的連線數可以超過這個上限。

**KV（DynamoDB / Cosmos DB）**：每個 request 各自走 HTTP / gRPC，沒有要預先建立的 stateful connection，應用層加 instance 不會碰到 DB 端的連線上限，要算的只有請求量消耗的 RCU / RU。

## 隱性限流 vs 明確限流

flash-sale 或極端負載場景的限流可能分散在多層元件、不是單一「rate limiter」。同一架構可能同時包含 *隱性* 限流（用 DB / LB 上限自然攔截）跟 *明確* 限流（用排隊系統精確控速）。

對應 [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — 售票架構圖上看不到明確「rate limiter」元件、但限流發生在多層：

- **DynamoDB 寫入排隊**：前端把訂單寫進 DynamoDB、傳統 server 按自己的處理能力從 DynamoDB 消費 — DynamoDB 表的 throughput 上限就是隱性限流
- **ELB max connection**：load balancer 上限自動拒絕超量請求
- **Application 層 connection pool**：超過 pool size 的 request 排隊或被拒
- **付款層獨立**：搶票流量塞爆時、付款不受影響、低頻路徑「自然限流」

對比 [9.C16 SeatGeek Virtual Waiting Room](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/) 的 *明確限流*：用 Counters table 精確控發 token 速率、用戶看得到排隊位置。

**選擇取捨**：

| 維度         | 隱性限流（Tixcraft）        | 明確限流（SeatGeek）   |
| ------------ | --------------------------- | ---------------------- |
| 用戶體驗     | 用戶以為成功、實際排隊      | 用戶看得到等待時間     |
| 流量吸收能力 | 極高（DB 直接吸）           | 受限於 token 發放速度  |
| 開發複雜度   | 低（用 DB 自帶 throughput） | 高（需要 token 系統）  |
| 失敗模式     | DB 滿了用戶才被拒           | 排隊系統爆了用戶被拒   |
| 適合業務     | 流量瞬間到頂、要全收        | 流量持續高、要排序公平 |

**失敗模式延伸**：隱性限流的失敗特徵是「provisioned capacity / connection pool 飽和、用戶看到 5xx / timeout、沒人收到排隊位置」— 監控訊號是 DynamoDB throttling event 或 ELB queue length 飆。明確限流的失敗特徵是「排隊系統本身的 DB / counter 飽和、token 發不出來、所有用戶包含 VIP 都被擋」— 監控訊號是 token issuance success rate 掉。兩種失敗對應不同 runbook、混在同一 alert dashboard 會誤判。

**適合業務延伸**：隱性限流適合「流量瞬間到頂、業務願意接受用戶看不見排隊」的場景（演唱會搶票、Black Friday 開賣瞬間、限量商品）— 業務優先收住流量、用戶體驗可以事後解釋。明確限流適合「流量持續高、用戶等待時間長、需要顯示進度減少跳離」的場景（IPO 開盤、長期熱門商品上架、跨小時的搶購事件）— 用戶能看到「我還有 30 分鐘」會繼續等。

判讀重點：選哪種限流取決於業務願意接受什麼用戶體驗、不是工程偏好。隱性限流用透明度換流量吸收能力、明確限流用流量吸收能力換體驗可見度。兩者並存、沒有「best practice」。

## 案例對照

| 案例                                                                                                | 教學重點                                                                            |
| --------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| [9.C1 AWS Prime Day 2025](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) | DynamoDB 24 小時 1.51 億 RPS、毫秒級延遲、可預期峰值上限參考                        |
| [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)           | 9000 萬 RPS + 99.999% 可用 — partition 均勻設計典範                                 |
| [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/)   | Cosmos DB 1M RU/s + multi-model + global distribution                               |
| [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)       | DynamoDB 當 durable queue、IOPS 20→135K                                             |
| [9.C16 SeatGeek](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/)             | DynamoDB 4 表 + Lambda 實作 virtual waiting room、跟 Tixcraft 的隱性緩衝形成姊妹案  |
| [9.C18 Zoom](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/)                     | 30x DAU surge、DynamoDB 撐 [control plane](/backend/knowledge-cards/control-plane/) |
| [9.C19 Capcom](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/)                  | 遊戲後端 KV、billions of requests + single-digit ms                                 |
| [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)           | TiDB → DynamoDB、50% 成本下降的取捨                                                 |
| [9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/)                   | Black Friday 1.67 億請求 / 24h、Cosmos DB 多 region                                 |
| [9.C24 Genesys](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/)        | 99.999% 跨 15 region、DynamoDB 為預設 DB                                            |
| [9.C26 PayPay](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/)             | 3 億訊息 / 天、TTL 自動清理                                                         |
| [9.C27 Disney+](/backend/09-performance-capacity/cases/disney-plus-content-metadata/)               | billions of actions daily、watchlist + 播放進度                                     |
| [9.C29 Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/)        | connection limit 才是 RDB bottleneck、改用 DynamoDB                                 |

[9.C16 SeatGeek](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/) 把 DynamoDB 當 *排隊調度系統*、不只當 queue buffer：用 Protected Zone table 記錄哪個 event 受 waiting room 保護、Counters table 控發 token 的速率、Queue table 紀錄序號、User Connection table 串 WebSocket。這個架構跟 [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 的「全部塞進 DynamoDB 隱性緩衝」是兩種對立取捨 — Tixcraft 用透明度換流量吸收能力、SeatGeek 用流量吸收能力換體驗可見度。判讀重點：KV DB 不只能當 OLTP 替代品、這四張表組合就能變成業務級調度引擎、選表前要先確定業務要的是流量吸收能力還是排隊位置的可見度。

## 下一步路由

- 上游：[0.2 State Storage Selection](/backend/00-service-selection/state-storage-selection/) — KV vs OLTP vs SearchIndex 選型
- 平行：[1.1 高併發資料存取](/backend/01-database/high-concurrency-access/)（OLTP 版本）/ [1.3 Transaction Boundary](/backend/01-database/transaction-boundary/)
- 下游：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)、[1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)（含「預設 DB 治理 pattern」— KV 在大規模平台的選型治理）
- 跨模組：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)（hot partition 量測）、[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[9.7 成本邊界](/backend/09-performance-capacity/cost-engineering/)
- DynamoDB 深入：[partition key 反模式](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/)、[on-demand vs provisioned 切換](/backend/01-database/vendors/dynamodb/on-demand-vs-provisioned/)、[single-table design](/backend/01-database/vendors/dynamodb/single-table-design-pattern/)、[GSI / LSI 設計](/backend/01-database/vendors/dynamodb/gsi-lsi-design/)
- Cosmos DB 深入：[partition key 設計](/backend/01-database/vendors/cosmosdb/partition-key-design/)、[RU 成本模型](/backend/01-database/vendors/cosmosdb/ru-cost-model-sizing/)、[一致性層次工程](/backend/01-database/vendors/cosmosdb/consistency-levels-engineering/)
- MongoDB 深入：[shard key 選型](/backend/01-database/vendors/mongodb/shard-key-selection/)、[schema design pattern](/backend/01-database/vendors/mongodb/schema-design-pattern/)、[connection 管理與 cache 層](/backend/01-database/vendors/mongodb/connection-management-and-cache-layer/)

## 既建知識卡片

- [Hot Partition](/backend/knowledge-cards/hot-partition/)
- [Saturation Point](/backend/knowledge-cards/saturation-point/)
- [Connection Pool](/backend/knowledge-cards/connection-pool/)
- [Tail Latency](/backend/knowledge-cards/tail-latency/)
