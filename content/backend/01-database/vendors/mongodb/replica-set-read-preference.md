---
title: "MongoDB Replica Set Read Preference：DB 層 causal session vs cache 層 freshness token"
date: 2026-05-27
description: "MongoDB read preference 五擇一 + read concern + causal consistency session 機制；DB 層機制解 cluster 內 read-your-own-write、cache 層 freshness token 解跨層 read-after-write、大規模 OLTP 必須兩層合用"
weight: 32
tags: ["backend", "database", "mongodb", "replication", "read-preference", "consistency", "deep-article"]
---

MongoDB replica set 在小規模時 read preference 五擇一就夠用、`primary` 走預設、想分擔 primary 改 `secondary` — 直觀但會在 production 反噬。讀者真正撞到的議題分兩層：DB 層的 read-your-own-write（同 client 寫完馬上讀讀不到）跟跨層的 read-after-write（write 進 MongoDB、cache 還是舊資料）。前者用 causal consistency session 解、後者要走 freshness token 跨層協議。Coinbase 1.5M reads/sec 不是純 MongoDB 撐出來、是 DB + cache 跨層合成。本文把 read preference 機制 + 跨層協作講清楚。

本文不重複 [MongoDB vendor overview](/backend/01-database/vendors/mongodb/) 已寫過的 replica set 簡介 — 而是 production 部署 + 跨層協作 + 失敗修復的實作層教學。

> **MongoDB 適用度前置判讀**：進到 read preference 設計前先確認 workload 在 MongoDB 適用區（document shape 主導 / contract layer 該放哪 / 跨雲 hedging 是否需要）— 詳見 [schema-design-pattern 開頭 3 軸前置判讀](../schema-design-pattern/#問題情境document-自由的後座力)、本篇不重複展開。Read scaling 是 *已選 MongoDB 後* 的容量決策。

## 問題情境：read scaling 撞牆的兩種長相

典型觸發場景：primary 寫入飽和、TL 提議「讀都打 secondary」想橫向擴容。改完後幾個 production 徵兆連環出現：

- User 看到「我剛下的訂單怎麼還沒出現」— write 進 primary、立刻 read 打 secondary、secondary 還沒 apply 該寫入、user 看到 stale data
- 跨 region replica set：app server 在 Tokyo、primary 在 Singapore、每筆讀走 70ms 跨海 RTT；改 `nearest` 後 latency 降但 stale read 出現
- Replication lag 在 backup 期間飆到分鐘級、`secondary` read 拿到幾分鐘前的資料、前端報表時間軸對不上
- Failover 期間 read preference 沒寫好、client 一直連舊 primary、`SocketTimeout` 直到 driver retry 邏輯介入

**第二類議題、規模更大**：把所有 read 打 secondary、replica 數量加到 5-7 仍撐不住 sustained 高 read（>500K reads/sec）；replication lag 升 + secondary CPU 飽和。這時 read preference 已不夠、必須加 cache + 跨層 freshness 機制。

讀者徵兆：`rs.printSecondaryReplicationInfo()` 顯示 lag 分鐘級、application log 出現「我剛寫的資料讀不到」客訴、failover 演練後 connection error 持續 30s+、cache hit rate 跟 read latency 反向相關。

Case anchor：[9.C36 Coinbase](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/) 揭露「document model 撐 1.5M reads/sec 靠 cache + freshness token」、含警示「1.5M reads/sec 是 users 服務 *加上 cache* 的數字、不是 MongoDB cluster 純讀取數字」。跨 region read preference 改 `nearest` 後 stale read 的具體 incident 細節需未來 case 補完、本文以「常見 failure pattern」處理。

## 核心機制

### MongoDB read preference + read concern 兩軸

Read preference 五種：

- **`primary`**（預設）：只打 primary、強一致、primary 飽和時無路可走
- **`primaryPreferred`**：先 primary、primary 不可用 fallback secondary
- **`secondary`**：只打 secondary、永遠拒 primary、failover 期間若所有 secondary 都不行就拋錯
- **`secondaryPreferred`**：先 secondary、secondary 不可用 fallback primary
- **`nearest`**：不是「最近的 secondary」、是「ping latency 最低的 member」（可能是 primary）；driver 用 latency window（預設 15ms）內隨機挑

Read concern 是另一軸：

- **`local`**：讀本地最新（含未確認）、效能最佳、可能讀到後來 rollback 的資料
- **`available`**：跟 `local` 類似但對 sharded cluster 有差異
- **`majority`**：讀到「已寫到多數 member」的資料、寫入 commit 後在多數 member 確認後才看得到
- **`linearizable`**：強制最新、必須打 primary、最高 latency

Write concern `w: "majority"` 保證寫入確認後在多數 member 上、但不保證 secondary 馬上 visible — 兩個概念分開。

### Causal consistency session（DB 層機制）

Causal consistency session 解的是 *單 client* 在 *MongoDB cluster 內部* 的因果一致：

- Client session 帶 `clusterTime` + `operationTime`
- Driver 把 read 路由到「已 apply 該 operationTime」的 member
- 實現 read-your-own-write（自己剛寫的、自己讀得到）

機制只在「同一 client session」內生效。跨 client 的因果一致（A 寫 → B 讀）不在範圍內。

其他輔助機制：

- **Tag set**：member 標 `{region: "ap-tokyo", role: "analytics"}`、read preference 帶 tag 把流量路由到特定 member
- **Hidden / delayed secondary**：不參與 election、不接 client read、做 backup / DR 用
- **Election**：primary 失聯後 majority 投票選新 primary、預設 10s 內完成；election 期間所有 primary read 失敗

### Freshness token（cache 層機制）

9.C36 Coinbase 揭露的 *跨層* 機制 — 解的是 *MongoDB + cache 跨層* 的 read-after-write、不是 cluster 內部：

**觸發條件**：直接打 MongoDB 不可能撐 1.5M reads/sec（口徑：users 服務應用層觀察、含 cache、非 MongoDB cluster 純讀取）。Coinbase 在 users 服務前加 Memcached query cache、單 document query 先查 cache。

**跨層一致性問題**：write 進 MongoDB primary、cache 還是舊資料、client 下次 read 從 cache 拿到舊版。

**freshness token 機制**：

1. Write 成功後、server 給 client 一個 token（包含 OCC version / clusterTime）
2. Client 之後 read 帶這個 token
3. Server 保證返回的資料版本 ≥ token
4. 若 cache 的版本 < token、bypass cache 直接打 DB

**跟 causal consistency session 的關係**：兩者解決同一類問題（read-after-write）但作用範圍不同。Causal session 是 DB 層、保證在同一 cluster 內 read-your-own-write；freshness token 是 *DB + cache 兩層共用的版本協議*、保證跨層 read-your-own-write。

### 跨層協作三選一

讀者真實系統的 read 一致性需求要選哪層處理：

| 路徑                             | 適用情境                                                    | 代價                                   |
| -------------------------------- | ----------------------------------------------------------- | -------------------------------------- |
| 只用 DB 層（causal session）     | 無 cache 層、讀寫都直接打 MongoDB cluster                   | replica scaling 上限約幾十萬 reads/sec |
| 只用 cache 層（freshness token） | 有 cache、跨層一致性要求高、application 願改                | 需設計 token 協議 + cache bypass 邏輯  |
| 兩層並用                         | 大規模 OLTP、cluster 內也要 causal、跨 cache 也要 freshness | 複雜度最高、但 Coinbase 規模必走此路   |

對應 knowledge card：[stale-read](/backend/knowledge-cards/stale-read/)、[replication-lag](/backend/knowledge-cards/replication-lag/)、[session-consistency](/backend/knowledge-cards/session-consistency/)、[eventual-consistency](/backend/knowledge-cards/eventual-consistency/)。

## 操作流程

**Step 1：read shape 分類**。把所有 read 分成四類：

- (a) 強一致必須 read-your-own-write（訂單詳情、帳戶餘額）
- (b) 容忍秒級 lag（個人資料、商品詳情）
- (c) 容忍分鐘級 lag（報表、analytics）
- (d) 大規模 read scaling 需 cache + freshness token（用戶資料 / 高頻 product query）

**Step 2：依分類對映機制**。

| 分類 | Read preference      | Read concern | 跨層機制                         |
| ---- | -------------------- | ------------ | -------------------------------- |
| (a)  | primary              | majority     | causal consistency session       |
| (b)  | secondaryPreferred   | local        | monitoring lag alarm             |
| (c)  | secondary（tag set） | available    | 無                               |
| (d)  | secondaryPreferred   | majority     | cache + freshness token + bypass |

**Step 3：driver config**（Node.js / Java / Python 都類似）：

```text
mongodb://host1:27017,host2:27017,host3:27017/db?
  replicaSet=rs0&
  readPreference=secondaryPreferred&
  readPreferenceTags=region:ap-tokyo&
  readPreferenceTags=&
  maxStalenessSeconds=90&
  readConcernLevel=majority
```

`readPreferenceTags` 寫多個 = fallback chain（先 tokyo 失敗 fallback 任意）。`maxStalenessSeconds=90` 拒絕 lag > 90s 的 secondary。

**Step 4：causal consistency session**：

```python
with client.start_session(causal_consistency=True) as s:
    coll.insert_one(doc, session=s)
    # 下面這個 find 自動路由到能讀到剛才寫的 member
    coll.find_one({"_id": doc["_id"]}, session=s)
```

Session 結束後因果關係結束、下個 session 不繼承。

**Step 5：freshness token 設計**（9.C36 Coinbase 模式）：

- Write API 返回 `{result, version_token}` — token 含 OCC version 或 MongoDB clusterTime
- Read API 接受 optional `If-Version-≥` header / parameter
- Cache lookup 比對 cache entry version 跟 token、低於 token 就 invalidate + bypass 到 MongoDB
- DB 層 read 用 `readConcern: "majority"` 保證返回的 version ≥ token

**Step 6：staging 驗證**。灌入 replication lag（暫停 secondary apply）驗證 application 行為；灌入 stale cache 驗證 token bypass 邏輯；模擬 failover 驗證 driver retry。

驗證點：

- `rs.printSecondaryReplicationInfo()` lag < SLO
- driver metric `readPreferenceUsageCount` 分布符合預期
- failover drill 後 read recovery < 15s
- cache hit rate vs freshness bypass rate 比例監控

Rollback boundary：read preference 是 driver-side config、可以 hot-swap；causal consistency session 需 application code 改、需灰度；freshness token 是 application + cache + DB 三方協議、回退需協調。

## 失敗模式

**Read-after-write 不一致（DB 層）**：寫 primary → 立刻 secondary read、應用 race condition 顯示「資料消失」。修法是 causal consistency session、driver 自動路由到已 apply 該寫入的 member。

**Read-after-write 不一致（跨層）**：寫 primary → cache 還是舊資料 → user 看到舊資料。causal session 解不了（cache 在 MongoDB 外）、必須走 freshness token 跨層協議。

**Stale read 在 lag 高峰**：backup / DDL / 大量寫入導致 secondary lag 分鐘級、`secondary` read 拿到舊資料。修法設 `maxStalenessSeconds` 拒舊 member、driver 自動轉到較新的 member 或 primary。

**`nearest` 在跨 region 不穩**：latency 抖動讓 driver 在 primary / secondary 跳、寫一致性與 read latency 同時惡化。修法是不要用 `nearest` 解跨 region 議題、應該用 tag set 明確路由。

**Failover 期間 primary read 全失敗**：election 10s 內所有 primary read 拋錯。修法改 `primaryPreferred` + driver retry 邏輯吃掉短暫失敗、application 端配 retry policy。

**Tag set 失準**：把 `region: "ap-tokyo"` 的流量路由到 tag 為 tokyo 的 member、但該 member 故障時沒 fallback、流量直接停。修法是 tag 設多層 fallback chain、最後一層留空 tag 表示「任意 member」。

**Analytical query 跑 OLTP secondary**：`secondaryPreferred` 把報表打 OLTP secondary、報表 query 拖垮 OLTP read latency。修法是 analytical workload 用 tag set 路由到專屬 analytics secondary、跟 OLTP read 隔離。

**Freshness token 漏寫**：write 沒帶 token 給 client / client 沒帶 token、token 機制 silently 失效、read 走 cache 拿舊資料。修法 token 必須 e2e 強制（middleware 自動帶 / 自動驗證）、不能靠 application 自覺。

**Cache bypass 比例失控**：所有 read 都 bypass cache、cache 等於沒裝。修法是 token 失敗率要監控、過高表示 cache invalidation 設計有問題（cache 沒在 write 後 update / invalidate）。

Anti-recommendation：

- read-heavy 但有強一致需求的場景不要為了 scale 改 secondary read；該換 SQL + read replica 加 application-level cache、或加 sharding 把 primary 寫散開
- 大規模 OLTP（>500K reads/sec）想單靠 MongoDB read preference 撐 = 拿不到那個量級。Coinbase 案明示「直接打 MongoDB 不可能撐 1.5M reads/sec」、必須 cache + freshness token

## 容量與觀測

關鍵 metric：

- **Replica health**：每個 member 的 `opcounters` 分布、`rs.status().members[].optimeDate` 推算 lag
- **Read preference 命中**：driver-side `readPreferenceTags` 命中率
- **一致性 SLO**：stale read 比例（causal consistency 拒絕重試次數）
- **跨層 freshness**：cache hit rate vs freshness bypass rate

Mongo command：

- `rs.status()`：replica set 整體
- `rs.printSecondaryReplicationInfo()`：lag 概況
- `db.serverStatus().repl`：詳細 replication metric
- `db.adminCommand({replSetGetStatus:1})`：完整 status

Application observability：APM 看「同一 session 內 write + read 順序對 latency / error 的影響」、SLO 是 read-your-own-write 命中率；跨層還要看 freshness token 流動完整性（write 是否發 token、read 是否帶 token、cache 是否驗 token）。

Lag alarm：lag > 30s 預警、> 90s 觸發 driver `maxStalenessSeconds` 自動拒讀。

回到 [4.20 observability evidence](/backend/04-observability/observability-evidence-package/)：把 read preference 命中分布、replication lag time series、failover drill recovery time、freshness token bypass rate 列為 evidence。

回到 [9.5 bottleneck localization](/backend/09-performance-capacity/bottleneck-localization/)：read latency 異常時要區分 (a) primary 飽和 (b) secondary lag 高 (c) tag routing 把流量集中到單一 member (d) cache hit rate 下降 / bypass 率上升。

## 邊界與整合

### Frame 5：合規邊界 — MongoDB 用 cluster-per-region 吸收

MongoDB / Atlas 沒有 *row-level locality* 機制（不像 CockroachDB 可把單 row pin 在合規 region）— 跨境合規必須以 *cluster-per-region* 拓樸吸收：每個合規市場開獨立 cluster、application 層做 routing、不靠 replica set / sharded cluster 機制跨 region。

跨 vendor 對照（[模組 outline Section B Frame 5](../../../_index.md)）：

| Vendor              | 合規吸收機制                                                            | 拓樸特性                                             |
| ------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------- |
| MongoDB / Cosmos DB | cluster-per-region（無 row-level locality 等價物）                      | 各 region 獨立 cluster、application 層做市場 routing |
| Aurora              | fleet 拓樸（每市場獨立 cluster、Global Database 在合規場景反指標）      | active-passive per market、跨市場不複製              |
| CockroachDB         | locality + placement（邏輯一個 cluster + region pinning + Outposts）    | 單 logical cluster、physical row 鎖在合規 region     |
| DynamoDB            | region-pinned Global Tables（按 region 開關 replication、各市場可分離） | 仍 active-active、但 replication 範圍可控            |

**MongoDB 在這 frame 的退化點**：read preference 機制本身不解合規 — 即使 `readPreferenceTags={region:eu}` 把流量路由到歐洲 secondary、但 primary 在亞洲時跨境 replication 仍在跑、合規 audit 不會放行 *路由層* 控制當作 *資料邊界* 控制。合規市場必須整 cluster 分離、再用 application 層 routing 把 user 帶到對應 cluster。

**Atlas 在合規場景的 fit**：Atlas global cluster（zone sharding 把 shard 鎖在 region）是「跨 region 但 *資料 pin 在 zone*」的中介選項、適合 GDPR 軟條款（資料在歐洲 EEA 內可流動）；strict 條款（資料不能離開單一國家）仍須走 cluster-per-region。

### Sibling 與 cross-link

Sibling deep articles：

- [shard key selection](../shard-key-selection/) — read preference 解決不了 write 飽和、要切 shard
- [change streams + Kafka](../change-streams-kafka/) — change stream 預設打 primary、放 secondary 的 trade-off
- [aggregation pipeline optimization](../aggregation-pipeline-optimization/) — 把 analytical aggregation 路由到專屬 secondary
- [connection management and cache layer](../connection-management-and-cache-layer/) — freshness token 是該篇的核心議題之一、本文聚焦 DB 層 vs cache 層機制對照、不展開 cache 部署架構

Migration playbook：

- 跨 region 強 consistency 需求 → [→ Cosmos DB MongoDB API](/backend/01-database/vendors/cosmosdb/)（5 consistency level）
- 跨 region 想保留原生 MongoDB → [→ Atlas global cluster](/backend/01-database/vendors/mongodb/migrate-to-atlas/)

跟 1.x 互引：[1.1 高併發資料存取](/backend/01-database/high-concurrency-access/) 處理 read scaling pattern；[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 處理跨 region 一致性升級路徑。

## 相關連結

- [MongoDB vendor overview](/backend/01-database/vendors/mongodb/) — 本文是該頁尾「replica set + read preference」backlog 的深度展開
- [Vendor 深度技術文章方法論](/posts/vendor-deep-article-methodology/)
- [9.C36 Coinbase](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/) — freshness token + 1.5M reads/sec（含 cache）
- 官方：[MongoDB Read Preference](https://www.mongodb.com/docs/manual/core/read-preference/)、[Read Concern](https://www.mongodb.com/docs/manual/reference/read-concern/)、[Causal Consistency](https://www.mongodb.com/docs/manual/core/causal-consistency-read-write-concerns/)
