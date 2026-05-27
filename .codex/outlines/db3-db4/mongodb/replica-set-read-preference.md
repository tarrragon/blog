# MongoDB Replica Set Read Preference：DB 層 causal session vs cache 層 freshness token

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。
>
> **校準說明**：本 outline 由 case-first audit 重寫、framing 從「primary / secondary / nearest 五擇一」推進到「DB 層 causal consistency session vs cache 層 freshness token 跨層協作」（F2.4 來源、9.C36 Coinbase 揭露 1.5M reads/sec 含 cache 是合成數字）。read preference / read concern 仍是核心機制、但讀者真正的 production 議題是 *單靠 DB 機制解不了大規模 OLTP 的 read scaling*、必須 cache + DB 跨層協作。

## 問題情境（Production pressure）

- Primary 寫入飽和、TL 提議「讀都打 secondary」想橫向擴容；改完後 user 看到「我剛下的訂單怎麼還沒出現」— write-after-read 不一致
- 跨 region replica set：app server 在 Tokyo、primary 在 Singapore，每筆讀走 70ms 跨海 RTT；改 `nearest` 後 latency 降但 stale read 出現
- Replication lag 在 backup 期間飆到分鐘級、`secondary` read 拿到幾分鐘前的資料；前端報表時間軸對不上
- Failover 期間 read preference 沒寫好、client 一直連舊 primary、`SocketTimeout` 直到 driver retry 邏輯介入
- **大規模 OLTP read scaling 撞牆**：讀者把所有 read 都打 secondary、replica 數量加到 5-7 仍撐不住 sustained 高 read（>500K reads/sec）；這時 read preference 已不夠、必須加 cache + 跨層 freshness 機制
- 讀者徵兆：`rs.printSecondaryReplicationInfo()` 顯示 lag 分鐘級、application log 出現「我剛寫的資料讀不到」客訴、failover 演練後 connection error 持續 30s+
- Case anchor: primary [9.C36 Coinbase](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/) 「document model 撐 1.5M reads/sec 靠 cache + freshness token」段（含警示「1.5M reads/sec 是 users 服務 *加上 cache* 的數字、不是 MongoDB cluster 純讀取數字」）；needs new case（跨 region read preference 改 nearest 後 stale read 的 incident）；側面引用 [Microsoft 365 Cosmos DB analytics](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) 的多 region distribution 對照

## 核心機制（Vendor-specific mechanism）

### MongoDB 內 read 機制

- Read preference 五種：`primary`（預設、強一致）、`primaryPreferred`、`secondary`、`secondaryPreferred`、`nearest`
- `nearest` 不是「最近的 secondary」、是「ping latency 最低的 member」（可能是 primary）；driver 用 latency window（預設 15ms）內隨機挑
- Read concern 跟 read preference 是兩軸：`readConcern: "majority"` 讀到「已寫到多數 member」的資料、`"local"` 讀本地最新（含未確認）；`"linearizable"` 強制最新 → 必須打 primary
- Write concern w:majority 保證寫入確認後在 majority member 上、但不保證 secondary 馬上 visible
- **Causal consistency session（DB 層機制）**：client session 帶 `clusterTime` + `operationTime`、driver 自動把 read 路由到「已 apply 該 operationTime」的 member、實現 read-your-own-write；解決的是 *單 client* 在 *MongoDB cluster 內部* 的因果一致
- Tag set：member 標 `{region: "ap-tokyo", role: "analytics"}`、read preference 帶 tag 把流量路由到特定 member
- Hidden / delayed secondary：不參與 election、不接 client read、做 backup / DR 用
- Election：primary 失聯後 majority 投票選新 primary、預設 10s 內完成；election 期間所有 primary read 失敗

### Freshness token（cache 層機制、F2.4 frame）

9.C36 Coinbase 揭露的 *跨層* 機制 — 解的是 *MongoDB + cache 跨層* 的 read-after-write、不是 cluster 內部：

- **觸發條件**：直接打 MongoDB 不可能撐 1.5M reads/sec（口徑：users 服務應用層觀察、含 cache、非 MongoDB cluster 純讀取）、Coinbase 在 users 服務前加 Memcached query cache、單 document query 先查 cache
- **跨層一致性問題**：write 進 MongoDB primary、cache 還是舊資料、client 下次 read 從 cache 拿到舊版
- **freshness token 機制**：
  1. Write 成功後、server 給 client 一個 token（包含 OCC version / clusterTime）
  2. Client 之後 read 帶這個 token
  3. Server 保證返回的資料版本 ≥ token
  4. 若 cache 的版本 < token、bypass cache 直接打 DB
- **跟 causal consistency session 的關係**：causal session 是 DB 層機制、保證在同一 cluster 內 read-your-own-write；freshness token 是 *DB + cache 兩層共用的版本協議*、保證跨層 read-your-own-write。兩者解決的是同一類問題（read-after-write）但作用範圍不同。

### 跨層協作三選一

讀者真實系統的 read 一致性需求要選哪層處理：

| 路徑                             | 適用情境                                                    | 代價                                   |
| -------------------------------- | ----------------------------------------------------------- | -------------------------------------- |
| 只用 DB 層（causal session）     | 無 cache 層、讀寫都直接打 MongoDB cluster                   | replica scaling 上限約幾十萬 reads/sec |
| 只用 cache 層（freshness token） | 有 cache、跨層一致性要求高、application 願改                | 需設計 token 協議 + cache bypass 邏輯  |
| 兩層並用                         | 大規模 OLTP、cluster 內也要 causal、跨 cache 也要 freshness | 複雜度最高、但 Coinbase 規模必走此路   |

- 對應 knowledge card: [stale-read](/backend/knowledge-cards/stale-read/)、[replication-lag](/backend/knowledge-cards/replication-lag/)、[session-consistency](/backend/knowledge-cards/session-consistency/)、[eventual-consistency](/backend/knowledge-cards/eventual-consistency/)

## 操作流程（Operations）

- Step 1：read shape 分類 — 把所有 read 分成 (a) 強一致必須 read-your-own-write (b) 容忍秒級 lag (c) 容忍分鐘級 lag (d) 大規模 read scaling 需 cache + freshness token
- Step 2：依分類對映 read preference + read concern + 跨層機制
  - (a) → primary + readConcern majority + causal consistency session（DB 層）
  - (b) → secondaryPreferred + readConcern local + monitoring lag alarm
  - (c) → analytical secondary（tag set 路由）+ readConcern available
  - (d) → cache 前置 + freshness token + bypass-on-stale 機制（DB 層 fallback 仍配 causal session）
- Step 3：driver config（Node.js / Java / Python 都類似）：
  - `readPreference: "secondaryPreferred"`
  - `readPreferenceTags: [{region: "ap-tokyo"}, {}]`（先 tokyo 失敗 fallback 任意）
  - `maxStalenessSeconds: 90`（拒絕 lag > 90s 的 secondary）
  - `session.startTransaction({readPreference: "primary"})` 強制 transaction 走 primary
- Step 4：causal consistency session 程式碼：

  ```text
  with client.start_session(causal_consistency=True) as s:
      coll.insert_one(doc, session=s)
      coll.find_one({...}, session=s)  # 自動路由到能讀到剛才寫的 member
  ```

- Step 5：freshness token 設計（9.C36 Coinbase 模式）：
  - Write API 返回 `{result, version_token}` — token 含 OCC version 或 MongoDB clusterTime
  - Read API 接受 optional `If-Version-≥` header / parameter
  - Cache lookup 比對 cache entry version 跟 token、低於 token 就 invalidate + bypass 到 MongoDB
  - DB 層 read 用 `readConcern: "majority"` 保證返回的 version ≥ token
- Step 6：在 staging 灌入 replication lag（暫停 secondary apply）驗證 application 行為；灌入 stale cache 驗證 token bypass 邏輯
- 驗證點：`rs.printSecondaryReplicationInfo()` lag < SLO、driver metric `readPreferenceUsageCount` 分布符合預期、failover drill 後 read recovery < 15s、cache hit rate vs freshness bypass rate 比例監控
- Rollback boundary：read preference 是 driver-side config、可以 hot-swap；causal consistency session 需 application code 改、需灰度；freshness token 是 application + cache + DB 三方協議、回退需協調

## 失敗模式（Failure modes）

- **Read-after-write 不一致（DB 層）**：寫 primary → 立刻 secondary read、應用 race condition 顯示「資料消失」；用 causal consistency session 解
- **Read-after-write 不一致（跨層）**：寫 primary → cache 還是舊資料 → user 看到舊資料；causal session 解不了（cache 在 MongoDB 外）、必須走 freshness token 跨層協議
- **Stale read 在 lag 高峰**：backup / DDL / 大量寫入導致 secondary lag 分鐘級、`secondary` read 拿到舊資料；設 `maxStalenessSeconds` 拒舊 member
- **`nearest` 在跨 region 不穩**：latency 抖動讓 driver 在 primary / secondary 跳、寫一致性與 read latency 同時惡化
- **Failover 期間 primary read 全失敗**：election 10s 內所有 primary read 拋錯；改 `primaryPreferred` + driver retry 邏輯吃掉短暫失敗
- **Tag set 失準**：把 `region: "ap-tokyo"` 的流量路由到 tag 為 tokyo 的 member、但該 member 故障時沒 fallback、流量直接停
- **Analytical query 跑 OLTP secondary**：`secondaryPreferred` 把報表打 OLTP secondary、報表 query 拖垮 OLTP read latency
- **Freshness token 漏寫**：write 沒帶 token 給 client / client 沒帶 token、token 機制 silently 失效、read 走 cache 拿舊資料；token 必須 e2e 強制（協議 + middleware）
- **Cache bypass 比例失控**：所有 read 都 bypass cache、cache 等於沒裝；token 失敗率要監控、過高表示 cache invalidation 設計有問題
- Anti-recommendation：
  - read-heavy 但有強一致需求的場景不要為了 scale 改 secondary read；該換 SQL + read replica 加 application-level cache、或加 sharding 把 primary 寫散開
  - 大規模 OLTP（>500K reads/sec）想單靠 MongoDB read preference 撐 = 拿不到那個量級；Coinbase 案明示「直接打 MongoDB 不可能撐 1.5M reads/sec」、必須 cache + freshness token

## 容量與觀測（Capacity & observability）

- 關鍵 metric：每個 member 的 `opcounters` 分布、`rs.status().members[].optimeDate` 推算 lag、driver-side `readPreferenceTags` 命中率、stale read 比例（causal consistency 拒絕重試次數）、**cache hit rate vs freshness bypass rate**（跨層）
- Mongo command：`rs.status()`、`rs.printSecondaryReplicationInfo()`、`db.serverStatus().repl`、`db.adminCommand({replSetGetStatus:1})`
- Application observability：APM 看「同一 session 內 write + read 順序對 latency / error 的影響」、SLO 是 read-your-own-write 命中率；跨層還要看 freshness token 流動完整性（write 是否發 token、read 是否帶 token、cache 是否驗 token）
- Lag alarm：lag > 30s 預警、> 90s 觸發 driver `maxStalenessSeconds` 自動拒讀
- 回到 [4.20 observability evidence](/backend/04-observability/observability-evidence-package/)：把 read preference 命中分布、replication lag time series、failover drill recovery time、freshness token bypass rate 列為 evidence
- 回到 [9.5 bottleneck localization](/backend/09-performance-capacity/bottleneck-localization/)：read latency 異常時要區分 (a) primary 飽和 (b) secondary lag 高 (c) tag routing 把流量集中到單一 member (d) cache hit rate 下降 / bypass 率上升

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：
  - [shard key selection](./shard-key-selection.md)（read preference 解決不了 write 飽和、要切 shard）
  - [change streams + Kafka](./change-streams-kafka.md)（change stream 預設打 primary、放 secondary 的 trade-off）
  - [aggregation pipeline optimization](./aggregation-pipeline-optimization.md)（把 analytical aggregation 路由到專屬 secondary）
  - [connection management and cache layer](./connection-management-and-cache-layer.md)（freshness token 是該篇的核心議題之一、本文聚焦 DB 層 vs cache 層機制對照、不展開 cache 部署架構）
- Migration playbook：跨 region 強 consistency 需求 → [→ Cosmos DB MongoDB API](/backend/01-database/vendors/mongodb/)（5 consistency level）；跨 region 想保留原生 MongoDB → [→ Atlas global cluster](/backend/01-database/vendors/mongodb/migrate-to-atlas/)
- 跟 1.x 互引：[1.1 高併發資料存取](/backend/01-database/high-concurrency-access/) 處理 read scaling pattern；[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 處理跨 region 一致性升級路徑

## 寫作前置 checklist

- [ ] Case anchor：primary 9.C36 Coinbase（1.5M reads/sec + cache + freshness token + mongobetween）已充分；跨 region nearest + stale read 的具體 incident 強烈需要新建 case（含時區、SLO 數字、修法）
- [ ] Knowledge card 雙引用：stale-read + replication-lag + session-consistency 三張都已存在、eventual-consistency 補充
- [ ] Sibling 對比清楚：跟 PostgreSQL streaming replication + hot_standby_feedback 對比、跟 DynamoDB consistent / eventually consistent read 對比、跟 Cosmos DB 5 consistency level 對比；本文是 MongoDB-specific（per-query read preference + causal consistency session + 跨層 freshness token）
- [ ] Fact vs derive 分層：「Coinbase 用 freshness token 撐 1.5M reads/sec」是 case 明示（口徑：users 服務應用層觀察、含 cache、非 MongoDB 純讀取）、寫進文章時必須明示口徑、不能寫成「MongoDB 撐 1.5M reads/sec」；「DB 層 vs cache 層三選一框架」是本章合成 frame、case 原文沒這個 frame、明示「本章合成」
- [ ] Scope warning：1.5M reads/sec 明示是合成數字（含 cache）、避免讀者把這當 MongoDB cluster 純讀取 benchmark
- [ ] 預估寫作長度：280-340 行（DB 層 + cache 層跨層機制是新主軸、需多花篇幅鋪 freshness token 協議 + Coinbase case 對應）
