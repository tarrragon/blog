---
title: "1.3 Transaction 與一致性邊界"
date: 2026-05-13
description: "交易邊界、isolation level、retry 策略、distributed transaction（2PC、Saga）與跨 region 強一致取捨"
weight: 3
tags: ["backend", "database", "transaction"]
---

交易邊界（transaction boundary）的核心責任是定義哪些資料變更必須一起成立。資料庫交易的價值在於讓同一個業務動作可以被明確提交、明確回退、明確重試。

本章涵蓋的範圍從單一資料庫內的交易切分、isolation level 與 retry，延伸到跨服務的 2PC、Saga 與跨 region 的一致性取捨。

## 邊界先於語法

交易邊界先從業務動作切分、再回到 SQL。建立訂單、扣庫存、寫付款狀態是一個動作；更新推薦分數、寫審計摘要、送通知事件屬於不同節奏、適合拆成後續流程。

當同一個動作內同時包含高延遲外部呼叫、交易範圍會直接放大鎖持有時間。穩定做法是把交易內責任收斂在「需要同時成功」的資料集合、讓外部呼叫或延伸副作用透過 queue / outbox 交給後續流程。

## Isolation Level：從 Read Uncommitted 到 External Consistency

SQL 標準定義 Read Uncommitted、Read Committed、Repeatable Read、Serializable 四個 isolation level，Spanner 這類全球分散式資料庫另外提供比 Serializable 更強的 external consistency；實務上 PostgreSQL / MySQL / Spanner 等實作有微妙差異。理解各級的具體行為、才能在 *正確性 vs 性能* 之間做取捨。

**Read Uncommitted（dirty read 可能）**：

- 標準允許讀到別的 transaction 還沒 commit 的資料
- MySQL InnoDB 照標準實作，真的會讀到還沒 commit 的值；PostgreSQL 接受這個設定，但行為等同 Read Committed，讀不到還沒 commit 的值
- 實務不要用

**Read Committed（PostgreSQL / Oracle 預設）**：

- 只讀到 commit 的資料
- 同一個 transaction 內、多次 SELECT 同一筆資料可能讀到不同值（non-repeatable read）
- 適合：read-heavy workload、不要求同 transaction 內 read consistency

**Repeatable Read（MySQL InnoDB 預設）**：

- 同一個 transaction 裡的一般 SELECT 讀同一份快照，讀到的值一致
- 標準定義不防 phantom read；InnoDB 的一般 SELECT 讀快照、看不到別的 transaction 新 commit 的列，而同一個 transaction 裡的 `SELECT ... FOR UPDATE` 與 `UPDATE` 讀的是最新 commit 的資料，會碰到那些新列（下方區塊以 MySQL 8.4 實際跑過）
- 適合：報表類 transaction、需要 snapshot 一致性

```sql
-- seats 一開始只有 (1, 10) 一列；連線 A：
SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;
START TRANSACTION;
SELECT count(*) FROM seats WHERE event_id = 10;              -- 1
-- 此時連線 B 執行並 commit：INSERT INTO seats VALUES (2, 10);
SELECT count(*) FROM seats WHERE event_id = 10;              -- 仍是 1：讀快照
SELECT count(*) FROM seats WHERE event_id = 10 FOR UPDATE;   -- 2：locking read 讀最新 commit 的資料
UPDATE seats SET event_id = 11 WHERE event_id = 10;          -- 改到 2 列，包含連線 B 新插入的那一列
ROLLBACK;
```

**Serializable（SQL 標準裡最強的一級）**：

- 看起來像所有 transaction 序列執行
- 兩種實作：strict 2PL（lock-based、MySQL）vs SSI（snapshot isolation + 衝突檢測、PostgreSQL）
- 衝突時會 serialization failure、應用層必須 retry
- 適合：金融交易、ticketing inventory、需要絕對正確

**External Consistency / Linearizable（Spanner）**：

- 比 Serializable 更強：跨 transaction 的順序跟 wall clock 一致
- Aurora DSQL 常跟 Spanner 並列為全球分散式 SQL，而它的交易隔離是 snapshot isolation：沒有鎖，兩筆交易改到同一列時後 commit 的那一筆收到 SQLSTATE `40001`（AWS 文件〈Concurrency control in Aurora DSQL〉），不屬於這一級
- 全球分散式系統的特殊取捨
- 詳見 [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 的 Spanner TrueTime 段
- 詳見 [9.C10 Spanner case](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)

**選擇原則**：

- 90% 業務用 Read Committed 夠
- 報表 / 對帳用 Repeatable Read
- 金融交易 / inventory 用 Serializable
- 跨 region 的交易之間也要有全域順序時，用 Spanner 這類提供 external consistency 的系統

## Isolation 跟 Retry 的關係

[isolation level](/backend/knowledge-cards/isolation-level/) 的責任是定義交易彼此可見性。`Read Committed` 在高併發寫入下可維持一般業務一致性；`Repeatable Read` 與 `Serializable` 提供更強約束、同時提高鎖競爭與重試頻率。

併發交易的常見結果是 deadlock 或 serialization failure。這些結果代表資料庫在保護一致性、應用層需要把它視為可重試路徑：

- **重試次數有上限**（通常 3-5 次）— 避免 retry storm
- **重試間隔有抖動**（exponential backoff + jitter）— 避免同步衝突
- **重試前提是動作可重入**（idempotent）— 不會放大副作用

對應 [Exponential Backoff](/backend/knowledge-cards/exponential-backoff/) 跟 [Idempotency](/backend/knowledge-cards/idempotency/) 卡片。

## Optimistic vs Pessimistic Locking

當多個 transaction 同時操作同一筆資料、有兩種防衝突策略：

**Pessimistic locking（悲觀鎖）**：讀取時就鎖住要改的列，其他 transaction 要改同一列得等這個 transaction 結束。

```sql
BEGIN;
-- 鎖住 id = 1 這一列，直到 COMMIT 或 ROLLBACK
SELECT balance FROM accounts WHERE id = 1 FOR UPDATE;
UPDATE accounts SET balance = 80 WHERE id = 1;
COMMIT;
-- 鎖持有期間，另一個連線對同一列的 UPDATE 會等待；設了 lock_timeout 就在逾時後報錯：
--   ERROR:  canceling statement due to lock timeout
```

- 適合：衝突機率高、retry 成本高
- 缺點：lock 期間其他 transaction 等待、容易 deadlock

**Optimistic locking（樂觀鎖）**：讀取時不鎖，寫回時把讀到的版本號當條件；版本號對不上，這次 UPDATE 就改不到任何列。

```sql
-- 兩個請求都讀到 version = 7
SELECT balance, version FROM accounts WHERE id = 1;   -- 100 | 7

-- 先寫回的請求：條件成立，版本號跟著加一
UPDATE accounts SET balance = 80, version = version + 1
WHERE id = 1 AND version = 7;                          -- UPDATE 1

-- 後寫回的請求：version 已經是 8，條件不成立
UPDATE accounts SET balance = 50, version = version + 1
WHERE id = 1 AND version = 7;                          -- UPDATE 0
```

- 版本號對不上時資料庫不報錯、transaction 也不會失敗，訊號只有 UPDATE 改到 0 列；應用層要檢查受影響的列數，是 0 就重讀、重算、再寫一次
- 適合：衝突機率低、性能優先
- 缺點：高衝突場景 retry 多、整體吞吐反而低

**選擇邏輯**：

- 衝突 < 5% → optimistic（更高吞吐）
- 衝突 > 30% → pessimistic（避免 retry waste）
- 中間區 → 量測再決定

對應 [hot row contention 處理](/backend/01-database/high-concurrency-access/)（[1.1 高併發下的 SQL 讀寫邊界](/backend/01-database/high-concurrency-access/)）— 高衝突 hot row 通常該換 KV / cache、不該硬擴 SQL。

## 服務情境：Checkout 多層邊界

電商 checkout 是典型的 transaction boundary 設計題，切分依據是這個步驟能不能晚一點完成：必須跟訂單同時成立的步驟放進交易層，晚一點完成也不影響訂單成立的步驟放進延伸層。

**交易層（即時一致）**：

- 建立訂單主表
- 寫入訂單項目
- 扣減可售庫存
- 寫入付款待確認狀態

**延伸層（最終可達）**：

- 寄訂單確認 email
- 同步 CRM 系統
- 觸發 analytics event
- 更新推薦模型

這種切法讓交易層跟延伸層各自穩定：

- 交易層關注 *鎖、隔離與回退*
- 延伸層關注 *投遞、重試與補償*

對應案例：

- [9.C4 DraftKings Aurora](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) — 體育博彩 ledger、200 個獨立 cluster 處理 transaction、後續 settlement 跑非同步
- [9.C14 Standard Chartered](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/) — 跨市場銀行 transaction、各市場獨立、跨市場結算非同步

## Distributed Transaction：2PC vs Saga

當業務動作跨越 *多個服務 / 資料庫*、傳統 ACID transaction 不夠用、需要 distributed transaction 模式。

**Two-Phase Commit (2PC)**：

- Commit-request 階段（又稱 voting / prepare phase）：coordinator 詢問所有 participant「能不能 commit？」
- Commit 階段：所有 participant 都回 yes → coordinator 廣播 commit；任一回 no → 廣播 abort
- **優點**：強一致、ACID 保證
- **缺點**：coordinator failure 會 block 所有 participant、性能差、跨服務複雜
- 適合：少數高一致性需求的場景（金融交易、跨多 DB 一致性）

**Saga Pattern**：

- 把長 transaction 拆成多個 local transaction + compensating transaction
- 每個 step 成功 → 進下個；任一失敗 → 倒回去跑 compensation
- 例：訂單流程依序是扣庫存、收款、送貨。收款失敗時，已經成功的只有扣庫存，所以跑扣庫存的 compensation（把庫存補回去）
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

- 每個 region 的讀取都看得到最新 commit 的資料；交易隔離各家不同：Spanner 是 external consistency、CockroachDB 預設 Serializable、Aurora DSQL 是 snapshot isolation
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

這個案例主要支撐的是「提交與副作用切分」判讀、不直接支撐 schema naming 或 cache freshness；若問題落在資料命名或快取新鮮度、應回到 [1.2 schema design 與資料建模](/backend/01-database/schema-design/) 或 [02 快取模組](/backend/02-cache-redis/)。

若事件出現資料已寫入但外部流程落後、或重試後副作用重複、先收斂本章的邊界切分與重試前提、再同步更新 [3.3 outbox pattern](/backend/03-message-queue/outbox-pattern/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 跨模組路由

交易邊界設計會直接影響後續模組的可操作性。

1. 與 [訊息佇列模組](/backend/03-message-queue/) 的交接：交易外副作用透過 [outbox pattern](/backend/knowledge-cards/outbox-pattern/) 與 consumer 落地。
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
