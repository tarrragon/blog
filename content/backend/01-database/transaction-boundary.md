---
title: "1.3 Transaction 與一致性邊界"
date: 2026-05-13
description: "交易邊界、isolation level、retry 策略、distributed transaction（2PC、Saga）與跨 region 強一致取捨"
weight: 3
tags: ["backend", "database", "transaction"]
---

交易邊界（transaction boundary）的核心責任是定義哪些資料變更必須一起成立。資料庫交易的價值在於讓同一個業務動作可以被明確提交、明確回退、明確重試。

本章從業務邊界切分開始、進入 isolation level 工程細節、再到 retry 策略、最後處理跨服務 / 跨 region 的 distributed transaction。讀完後讀者能回答：transaction 範圍該多大、isolation 該訂多嚴、deadlock 怎麼處理、跨服務一致性怎麼設計、什麼時候該換 Saga 模式。

## 邊界先於語法

交易邊界先從業務動作切分、再回到 SQL。建立訂單、扣庫存、寫付款狀態是一個動作；更新推薦分數、寫審計摘要、送通知事件屬於不同節奏、適合拆成後續流程。

當同一個動作內同時包含高延遲外部呼叫、交易範圍會直接放大鎖持有時間。穩定做法是把交易內責任收斂在「需要同時成功」的資料集合、讓外部呼叫或延伸副作用透過 queue / outbox 交給後續流程。

## Isolation Level 五級深度

SQL 標準定義四個 isolation level、實務上 PostgreSQL / MySQL / Spanner 等實作有微妙差異。理解各級的具體行為、才能在 *正確性 vs 性能* 之間做取捨。

**0. Read Uncommitted（dirty read 可能）**：

- 可讀到別的 transaction 還沒 commit 的資料
- 多數 DB 不真的支援這級（會 fallback 到 Read Committed）
- 實務不要用

**1. Read Committed（PostgreSQL / Oracle 預設）**：

- 只讀到 commit 的資料
- 同一個 transaction 內、多次 SELECT 同一筆資料可能讀到不同值（non-repeatable read）
- 適合：read-heavy workload、不要求同 transaction 內 read consistency

**2. Repeatable Read（MySQL InnoDB 預設）**：

- 同 transaction 內 read 一致（snapshot at transaction start）
- 不防 phantom read（標準定義）、但 InnoDB 的 RR 加 gap lock 實際上防住了
- 適合：報表類 transaction、需要 snapshot 一致性

**3. Serializable（最強）**：

- 看起來像所有 transaction 序列執行
- 兩種實作：strict 2PL（lock-based、MySQL）vs SSI（snapshot isolation + 衝突檢測、PostgreSQL）
- 衝突時會 serialization failure、應用層必須 retry
- 適合：金融交易、ticketing inventory、需要絕對正確

**4. External Consistency / Linearizable（Spanner、Aurora DSQL）**：

- 比 Serializable 更強：跨 transaction 的順序跟 wall clock 一致
- 全球分散式系統的特殊取捨
- 詳見 [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 的 Spanner TrueTime 段
- 詳見 [9.C10 Spanner case](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)

**選擇原則**：

- 90% 業務用 Read Committed 夠
- 報表 / 對帳用 Repeatable Read
- 金融交易 / inventory 用 Serializable
- 全球強一致用 Spanner / Aurora DSQL 等 linearizable 系統

## Isolation 跟 Retry 的關係

[isolation level](/backend/knowledge-cards/isolation-level/) 的責任是定義交易彼此可見性。`Read Committed` 在高併發寫入下可維持一般業務一致性；`Repeatable Read` 與 `Serializable` 提供更強約束、同時提高鎖競爭與重試頻率。

併發交易的常見結果是 deadlock 或 serialization failure。這些結果代表資料庫在保護一致性、應用層需要把它視為可重試路徑：

- **重試次數有上限**（通常 3-5 次）— 避免 retry storm
- **重試間隔有抖動**（exponential backoff + jitter）— 避免同步衝突
- **重試前提是動作可重入**（idempotent）— 不會放大副作用

對應 [Exponential Backoff](/backend/knowledge-cards/exponential-backoff/) 跟 [Idempotency](/backend/knowledge-cards/idempotency/) 卡片。

## Optimistic vs Pessimistic Locking

當多個 transaction 同時操作同一筆資料、有兩種防衝突策略：

**Pessimistic locking（悲觀鎖）**：

- `SELECT ... FOR UPDATE`、提前 lock 行
- 適合：衝突機率高、retry 成本高
- 缺點：lock 期間其他 transaction 等待、容易 deadlock

**Optimistic locking（樂觀鎖）**：

- 不 lock、用 version column 或 `WHERE old_value = ?`
- commit 時若 version 不對、整個 transaction 失敗、應用層 retry
- 適合：衝突機率低、性能優先
- 缺點：高衝突場景 retry 多、整體吞吐反而低

**選擇邏輯**：

- 衝突 < 5% → optimistic（更高吞吐）
- 衝突 > 30% → pessimistic（避免 retry waste）
- 中間區 → 量測再決定

對應 [hot row contention 處理](/backend/01-database/high-concurrency-access/)（[1.1](/backend/01-database/high-concurrency-access/)）— 高衝突 hot row 通常該換 KV / cache、不該硬擴 SQL。

## 服務情境：Checkout 多層邊界

電商 checkout 是典型的 transaction boundary 設計題、可拆成兩層邊界。

**第一層：交易層（即時一致）**：

- 建立訂單主表
- 寫入訂單項目
- 扣減可售庫存
- 寫入付款待確認狀態

**第二層：延伸層（最終可達）**：

- 寄訂單確認 email
- 同步 CRM 系統
- 觸發 analytics event
- 更新推薦模型

這種切法讓交易控制面跟非同步控制面各自穩定：

- 交易層關注 *鎖、隔離與回退*
- 非同步層關注 *投遞、重試與補償*

對應案例：

- [9.C4 DraftKings Aurora](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) — 體育博彩 ledger、200 個獨立 cluster 處理 transaction、後續 settlement 跑非同步
- [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) — 跨市場銀行 transaction、各市場獨立、跨市場結算非同步

## Distributed Transaction：2PC vs Saga

當業務動作跨越 *多個服務 / 資料庫*、傳統 ACID transaction 不夠用、需要 distributed transaction 模式。

**Two-Phase Commit (2PC)**：

- 階段 1：coordinator 詢問所有 participant「你能 commit 嗎？」
- 階段 2：所有都說 yes → coordinator 廣播 commit；任一說 no → 廣播 abort
- **優點**：強一致、ACID 保證
- **缺點**：coordinator failure 會 block 所有 participant、性能差、跨服務複雜
- 適合：少數高一致性需求的場景（金融交易、跨多 DB 一致性）

**Saga Pattern**：

- 把長 transaction 拆成多個 local transaction + compensating transaction
- 每個 step 成功 → 進下個；任一失敗 → 倒回去跑 compensation
- 例：訂單 step1 扣庫存、step2 收款、step3 送貨。step2 失敗 → 跑 step1 的 compensation（補庫存）
- **優點**：高可用、性能好、容易擴展
- **缺點**：不是強一致、中間狀態可見、compensation 必須設計
- 適合：multi-service 業務流程、可接受 [eventual consistency](/backend/knowledge-cards/eventual-consistency/)

**Choreography vs Orchestration**：

- Choreography：每個 service 自己決定下一步（event-driven）
- Orchestration：中央 orchestrator 控制流程（state machine）
- 大規模傾向 orchestration（容易追蹤、debug）、小規模 choreography 足夠

**對應案例**：

- [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — 售票 + 付款分開：DynamoDB 接搶單（local transaction）、legacy server 跑付款（compensation 處理庫存回退）
- [9.C28 FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) — 投注 → 結算的 saga 流程

詳見 [Outbox Pattern 卡片](/backend/knowledge-cards/outbox-pattern/) 跟 [3.3 Outbox Pattern](/backend/03-message-queue/outbox-pattern/)。

## 跨 Region Transaction：[CAP](/backend/knowledge-cards/cap/) 取捨

當 transaction 必須跨 region 同時成立、CAP 定理開始作用。

**Single-region transaction**（PostgreSQL / MySQL / Aurora）：

- ACID within region
- 跨 region 用 async replication、不是 transaction

**Multi-region eventual consistency**（DynamoDB Global Tables、Cosmos DB session/eventual）：

- 各 region 都能寫
- LWW 或 application-level conflict resolution
- 不是 ACID、是 BASE

**Multi-region strong consistency**（Spanner、Aurora DSQL、CockroachDB）：

- 跨 region linearizable transaction
- 代價是 latency（跨洲 100-200ms [quorum](/backend/knowledge-cards/quorum/)）
- 對應 [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)

**決策邏輯**：

- 業務不需要跨 region 強一致 → single-region OLTP + eventual replication
- 需要跨 region 強一致 + 接受 latency → Spanner / Aurora DSQL
- 需要跨 region 寫但接受最終一致 → Cosmos DB session / DynamoDB Global Tables

## 判讀訊號

| 訊號                                     | 判讀重點                       | 對應動作                                |
| ---------------------------------------- | ------------------------------ | --------------------------------------- |
| deadlock rate 升高                       | 交易範圍過大或鎖順序不一致     | 統一更新順序、縮小 transaction 範圍     |
| transaction duration 在尖峰時段上升      | 交易內含慢查詢或外部依賴       | 將外部呼叫移出交易、補索引與查詢計畫    |
| retry 成功率下降                         | 重試條件與業務冪等假設不一致   | 補 idempotency key、調整 retry 邏輯     |
| rollback 後仍出現業務狀態殘留            | 邊界切分和副作用落點未對齊     | 將副作用統一移到 outbox / consumer 路徑 |
| 交易內讀寫跨多資料域導致 contention 爆發 | 業務聚合邊界與資料模型邊界衝突 | 重新切 aggregate 與拆分熱點資料結構     |
| Serializable retry 率 > 10%              | isolation 太嚴或業務衝突高     | 降到 Repeatable Read 或拆 hot row       |
| 跨服務 transaction 用 2PC 卡住           | coordinator failure 阻塞       | 改 Saga + compensation                  |

## 常見誤區

交易保護的是一致性、不是吞吐量最大化。把過多步驟包進單一交易、會同時放大鎖競爭與回退成本。把交易切成可驗證的業務單位、能讓高併發下的可預期性更高。

重試保護的是暫時性失敗、不是所有失敗。沒有冪等保護的重試會放大副作用、特別是金流、庫存、配額這類正式狀態。

isolation level 不是「越強越好」。Serializable 比 Read Committed 慢數倍、且 retry rate 上升。只在 *必要* 場景用最強 isolation、其他場景用最低可接受 isolation。

distributed transaction 不是「跨服務就要 2PC」。多數 multi-service 業務用 Saga 更可靠、2PC 是少數場景的特殊工具。

## 案例對照

| 案例                                                                                                  | Transaction 相關重點                                                     |
| ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| [9.C4 DraftKings Aurora](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)  | Aurora MySQL ACID transaction、200 個獨立 cluster 隔離 transaction scope |
| [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)         | External consistency（linearizable）跨 region transaction、TrueTime      |
| [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) | 跨市場 transaction 各市場獨立 cluster、合規限制                          |
| [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)         | 搶票 + 付款 saga 模式、DynamoDB queue + legacy SQL                       |

## 案例回寫

交易邊界可用 [GitHub 2018 Oct21 MySQL Topology Incident](/backend/08-incident-response/cases/github/2018-oct21-mysql-topology-incident/) 做回寫。先看事件中的主從切換與恢復順序、再回到本章判讀三件事：哪些變更必須同交易成功、哪些副作用應拆到 outbox、哪些錯誤屬於可重試而非立即回退。

這個案例主要支撐的是「提交與副作用切分」判讀、不直接支撐 schema naming 或 cache freshness；若問題落在資料命名或快取新鮮度、應回到 1.2 或 2.x。

若事件出現資料已寫入但外部流程落後、或重試後副作用重複、先收斂本章的邊界切分與重試前提、再同步更新 [3.3 outbox pattern](/backend/03-message-queue/outbox-pattern/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 跨模組路由

交易邊界設計會直接影響後續模組的可操作性。

1. 與 03 的交接：交易外副作用透過 [outbox pattern](/backend/knowledge-cards/outbox-pattern/) 與 consumer 落地。
2. 與 1.7 的交接：付款狀態拆欄位、雙寫與回呼更新要進入 [Schema Migration Rollout 證據](/backend/01-database/schema-migration-rollout-evidence/) 的驗證流程。
3. 與 1.10 / 1.11 的交接：KV 跟全球分散式 OLTP 的 transaction model 不同、選型時要回到本章邊界判讀。
4. 與 04 的交接：交易失敗需要對齊 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 的查詢與證據欄位。
5. 與 06 的交接：高風險交易變更納入 [Release Gate](/backend/06-reliability/release-gate/) 與 [Migration Safety](/backend/06-reliability/migration-safety/)。
6. 與 08 的交接：交易層回退或 [fail-forward](/backend/knowledge-cards/fail-forward/) 判斷記錄到 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 下一步路由

- 平行：[1.1 高併發資料存取](/backend/01-database/high-concurrency-access/)（connection pool / hot row）
- 下游：[1.6 資料庫轉換實作](/backend/01-database/database-migration-playbook/) / [1.7 Schema Migration Rollout 證據](/backend/01-database/schema-migration-rollout-evidence/) / [1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) / [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)
- 跨模組：[3.3 outbox pattern](/backend/03-message-queue/outbox-pattern/) / [6.11 Migration Safety](/backend/06-reliability/migration-safety/) / [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)
- 卡片：[Isolation Level](/backend/knowledge-cards/isolation-level/) / [Transaction Boundary](/backend/knowledge-cards/transaction-boundary/) / [Idempotency](/backend/knowledge-cards/idempotency/) / [Outbox Pattern](/backend/knowledge-cards/outbox-pattern/) / [Exponential Backoff](/backend/knowledge-cards/exponential-backoff/)
- Spanner 一致性深入：[TrueTime API 深入](/backend/01-database/vendors/spanner/truetime-api-depth/) / [Spanner 一致性模型對照](/backend/01-database/vendors/spanner/consistency-models-comparison/)
- CockroachDB retry / 隔離深入：[CockroachDB transaction retry pattern](/backend/01-database/vendors/cockroachdb/transaction-retry-pattern/) / [Aurora DSQL / Spanner / CockroachDB 決策樹](/backend/01-database/vendors/cockroachdb/aurora-dsql-spanner-decision-tree/)
- Aurora 寫入語意深入：[Aurora 儲存層架構](/backend/01-database/vendors/aurora/storage-architecture/)（6 寫 / 4 讀 quorum 對 transaction 的影響）
