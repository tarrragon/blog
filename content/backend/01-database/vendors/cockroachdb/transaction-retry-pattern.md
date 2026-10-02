---
title: "CockroachDB Transaction Retry Pattern：serializable default 與 application contract 重塑"
date: 2026-05-27
description: "CockroachDB default SERIALIZABLE、application 必須包 retry loop 處理 40001 serialization_failure。本文走 PG → CockroachDB application contract 重塑、SAVEPOINT cockroach_restart 語法，以及 retry storm、retry loop 裡的副作用重複執行、cross-statement state、hot row、改 READ COMMITTED 後的業務語意、long-running transaction、distributed deadlock 等失敗模式；retry pattern 取自 Cockroach Labs 官方文件，不是案例揭露"
weight: 50
tags: ["backend", "database", "cockroachdb", "distributed-sql", "transaction", "isolation", "serializable", "deep-article"]
---

> 本文整理 CockroachDB 預設 `SERIALIZABLE` 對 application transaction contract 的影響：為什麼要包 retry loop、怎麼寫、哪些寫法在 retry 時出事。
>
> **來源**：本篇的 retry 機制與寫法取自 Cockroach Labs 官方的 SQL Layer 與 Transaction Retry 文件，不是任何一個案例的揭露。三個 CockroachDB 案例（[DoorDash](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/) / [Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/) / [Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/)）都沒有寫到 `40001 serialization_failure`、`SAVEPOINT cockroach_restart`、hot row contention 或 retry loop；DoorDash case 只寫到 PostgreSQL wire *protocol-level* 相容、SQL 行為（serializable default / retry semantics / partial index）仍要驗證。把本篇的 pattern 用到實際系統前，先對自己的 application 跑一次 audit。

---

## 問題情境：從 PG READ COMMITTED 遷到 CockroachDB SERIALIZABLE 的 application 衝擊

團隊從 PostgreSQL（default `READ COMMITTED`）遷到 CockroachDB（default `SERIALIZABLE`）、上線後 application transaction retry 突然爆增、user-facing latency p99 高 5 倍、error rate 顯著上升。Driver 不會自動 retry — 應用層必須認得 `40001 serialization_failure` 並包 retry loop with exponential backoff。沒包就是直接拋例外給用戶。

讀者常問：

- 為什麼同樣的 transaction 在 CockroachDB 一直 retry、在 PostgreSQL 從來不會？
- `40001 serialization_failure` error 怎麼處理、能不能直接 swallow？
- 我要把所有 application transaction 都改成 retry loop 包起來嗎？
- 能不能改 isolation level 回 `READ COMMITTED`、放棄 serializable 保證？

四題的回答都依賴一個前提：CockroachDB 的 application transaction contract 跟 PostgreSQL default 不一樣、必須重塑。

### DoorDash case 給的是遷移前要驗證的提醒

DoorDash case 在〈策略〉段寫的是：「CockroachDB 不是 PostgreSQL fork、是 *protocol-level 相容*、實際 SQL 行為（serializable default、retry semantics、partial index）仍要驗證」。這一句是本篇要處理的問題的來由：serializable default 與 retry semantics 正是 application transaction contract 要改寫的地方。retry contract、`40001`、`SAVEPOINT` pattern 與 hot row contention 本身，DoorDash case 都沒有寫，本篇依 Cockroach Labs 官方的 SQL Layer 與 Transaction Retry 文件整理。

Sibling 對照 [DraftKings Aurora financial ledger](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 走的是 *PostgreSQL READ COMMITTED + Aurora* 的另一條路徑 — 用 application-level sharding（200 個獨立 Aurora cluster）解 Aurora single-primary 的寫入上限，沒有走到 serializable retry 這一步。DraftKings case 沒有寫 retry pattern；同樣的 ledger 若改走 CockroachDB，才需要處理本篇描述的 retry loop 與 application 改寫。

## 核心機制：serializable default 跟 PostgreSQL 的差異

### Serializable 是 CockroachDB 的 default

CockroachDB 預設 `SERIALIZABLE` — 最強 isolation level、保證 transaction 結果等同某個 serial order（即所有 transaction 像逐個按順序執行）。對比：

| 維度         | PostgreSQL default | CockroachDB default               |
| ------------ | ------------------ | --------------------------------- |
| Isolation    | READ COMMITTED     | SERIALIZABLE                      |
| 衝突處理     | 後 writer 等 lock  | 衝突即 abort、丟 40001            |
| 機制         | row lock + MVCC    | timestamp ordering + write intent |
| Retry 必要性 | 通常不需要         | application 必須有 retry loop     |
| SSI 對應     | PG SSI（opt-in）   | 預設啟用                          |

### Conflict detection：read / write set 衝突就 abort

CockroachDB 追蹤每個 transaction 的 read set 跟 write set。當兩個並行 transaction 的 read / write set 衝突、CockroachDB abort 後到的那個、發 [Serialization Failure](/backend/knowledge-cards/serialization-failure/)（`40001 serialization_failure`）。

對比 PostgreSQL serializable（SSI）：兩者都不靠預先上鎖來擋住衝突，差別在 *衝突偵測時機* 跟 *成本*：

- PostgreSQL SSI：用 predicate lock 追蹤 query 條件、commit 時偵測
- CockroachDB：用 timestamp ordering + write intent、衝突 *當下* 就 abort

CockroachDB 的成本在「衝突立刻 abort 不等 commit」、好處是「retry window 較短、不會跑完整個 transaction 才發現衝突」。

### Application 端 retry：driver 不自動處理

關鍵：**CockroachDB driver 不自動 retry**。application 收到 `40001 serialization_failure` 必須自己決定怎麼處理 — exponential backoff retry、circuit break、或拋給上層。

對比 PostgreSQL：PostgreSQL READ COMMITTED 幾乎不會丟 serialization failure（後 writer 等 lock 不 abort）、SERIALIZABLE 才會、但多數 application 沒走 SERIALIZABLE。CockroachDB *預設* 就是 SERIALIZABLE、所以 retry loop 是 *必要*、不是 optional。

### Savepoint pattern：官方推薦寫法

Cockroach Labs 官方推薦的 retry pattern 用 `SAVEPOINT cockroach_restart`：

```sql
BEGIN;
SAVEPOINT cockroach_restart;

-- 做正常 transaction 工作
SELECT balance FROM accounts WHERE id = 1;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
UPDATE accounts SET balance = balance + 100 WHERE id = 2;

RELEASE SAVEPOINT cockroach_restart;
COMMIT;

-- 如果中途 40001：
-- ROLLBACK TO SAVEPOINT cockroach_restart;
-- 重新跑 transaction body、再 RELEASE + COMMIT
```

`cockroach_restart` 是特殊保留 savepoint name — CockroachDB 認得這個名字、會把 `ROLLBACK TO SAVEPOINT cockroach_restart` 視為「重啟整個 transaction」而不是部分 rollback。

### READ COMMITTED 是 v23.2+ 可選降級

CockroachDB v23.2+ 新增 `READ COMMITTED` isolation level — application 可選擇用 weaker isolation 換少 retry。但這是「降級」、失去 serializable 保證 — 反例見〈改 READ COMMITTED 後忘了驗證業務語意〉（金融 ledger 走 READ COMMITTED 可能讓 balance 變負）。

對應 [isolation level 卡](/backend/knowledge-cards/isolation-level/) 跟 [transaction boundary 卡](/backend/knowledge-cards/transaction-boundary/)。

## 操作流程：retry loop 設計

### Retry loop 偽碼

```go
for attempt := 0; attempt < MAX_RETRIES; attempt++ {
    tx, err := db.Begin()
    if err != nil { return err }

    _, err = tx.Exec("SAVEPOINT cockroach_restart")
    if err != nil { tx.Rollback(); return err }

    // ... 跑 transaction body ...

    _, err = tx.Exec("RELEASE SAVEPOINT cockroach_restart")
    if err == nil {
        err = tx.Commit()
        if err == nil { return nil } // 成功
    }

    if isSerializationFailure(err) { // SQLSTATE == "40001"
        tx.Rollback()
        backoff := time.Duration(math.Pow(2, float64(attempt))) * 10 * time.Millisecond
        time.Sleep(backoff + jitter())
        continue
    }

    tx.Rollback()
    return err // 非 retry-able error
}
return ErrMaxRetriesExceeded
```

關鍵點：

- exponential backoff with jitter（避免 retry storm 同步）
- max retry 上限（避免無限 loop、要有 circuit breaker）
- 只 retry serialization failure、其他 error 直接拋
- retry loop 裡資料庫之外的動作必須冪等，或移到 COMMIT 成功之後（見〈Idempotency 設計：retry 會重做的是 transaction 外的副作用〉）

### 配置

```sql
-- 單一 transaction 改用 READ COMMITTED（v23.2+）
BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;
SHOW transaction_isolation;   -- read committed
COMMIT;

-- 改這個 session 之後所有 transaction 的預設
SET default_transaction_isolation = 'read committed';

-- 看當前 session 預設
SHOW default_transaction_isolation;
```

### 驗證點

```sql
-- crdb_internal 在 v26.3 預設禁止查詢，要先開這個 session 變數（官方標示為不支援的內部介面）
SET allow_unsafe_internals = true;

-- 看 transaction retry 統計：每種 transaction 指紋一列，maxRetries 是觀察到的最多重試次數
SELECT fingerprint_id,
       (statistics->'statistics'->>'cnt')::INT        AS executions,
       (statistics->'statistics'->>'maxRetries')::INT AS max_retries
FROM crdb_internal.transaction_statistics
ORDER BY max_retries DESC LIMIT 10;

-- 看哪些 table / key 衝突最多
SELECT * FROM crdb_internal.cluster_contention_events ORDER BY count DESC LIMIT 10;
```

### Idempotency 設計：retry 會重做的是 transaction 外的副作用

`ROLLBACK TO SAVEPOINT cockroach_restart` 會丟掉這一次嘗試寫進資料庫的全部變更，所以 transaction body 裡的 SQL 在 retry 時重跑一次，不會在資料庫裡留下兩份結果：

```sql
-- 共用資料：accounts(id, balance)，id = 1 的 balance = 900；logs(id 自動產生, msg) 是空表
BEGIN;
SAVEPOINT cockroach_restart;
INSERT INTO logs (msg) VALUES ('attempt');                -- 第一次嘗試
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
ROLLBACK TO SAVEPOINT cockroach_restart;                 -- 模擬收到 40001 之後重來
INSERT INTO logs (msg) VALUES ('attempt');                -- 重跑同一段 body
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
RELEASE SAVEPOINT cockroach_restart;
COMMIT;
-- logs 只有 1 列；balance 是 800，只扣了一次 100
```

retry 會重複發生的是資料庫之外的動作：在 retry loop 裡呼叫付款 API、送通知、改 application 記憶體裡的狀態，每重試一次就多做一次。另一個需要 [idempotency](/backend/knowledge-cards/idempotency/) 的位置是 COMMIT 的結果不確定時——例如連線在 COMMIT 途中斷掉，application 不知道這筆有沒有寫進去，整筆重送就可能寫兩次，要靠 idempotency key 或 UNIQUE constraint 讓重送的那一筆被擋下。這兩件事都是 application 設計議題、不是 CockroachDB 配置可解的 — application contract 重塑的核心成本就在這。

### Rollback 邊界

transaction 自身有 `SAVEPOINT cockroach_restart` 邊界、`ROLLBACK TO SAVEPOINT` 後可重試整個 transaction body。但：

- commit 後不可回滾 — 業務狀態還原只能新交易補償
- application 端如果在 transaction *外* cache state、retry 後 state 不一致（見〈Cross-statement state 假設〉）

## 失敗模式

### Retry storm：contention 嚴重時 CPU 雪崩

當高頻寫入撞同一 row（例：全局 counter、熱門商品 inventory）、serializable 衝突率可能 100%、application 端 retry loop 不斷重跑、CPU 雪崩。

修法：

- Max retry 上限 + circuit breaker：超過就放棄、回 5xx 給 client、避免 retry storm 拖垮 cluster
- 改 schema 避開 hot row（partition by region、shard counter、用 sequence 代替全局 counter）
- 監控 `crdb_internal.cluster_contention_events`、針對 top-N table 改設計

### retry loop 裡的副作用重複執行：double-count

最危險的 production bug：retry loop 裡除了 SQL 還有資料庫之外的動作（呼叫付款 API、送通知、寫外部 log），每次 retry 都再做一次；或 COMMIT 結果不確定時整筆重送。後果是 payment 重複扣款、通知重複送出。

修法：

- 資料庫之外的動作移到 COMMIT 成功之後，或讓外部系統用 idempotency key 去重
- `INSERT` 加 UNIQUE constraint + `ON CONFLICT DO NOTHING`，讓重送的那一筆被擋下
- 用 idempotency key（client 帶 UUID、server 端 dedupe）

### Cross-statement state 假設

application 在 transaction *外* cache state（例：開 transaction 前 read 一個值、跑 transaction 期間用 cached 值）— retry 從 SAVEPOINT 重來時、cached state 不會重新讀、retry 後 state 不一致。

修法：

- 把 cached state 改成在 transaction 內 read
- retry loop 內 reset 所有 cached state
- 用 closure / scope 限制 cache 的生命週期到 transaction 內

### Hot row contention

高頻 update 同一 row（例：全局計數器、熱門商品庫存、世界冠軍直播觀眾數）— serializable 衝突率接近 100%、無論 retry 多少次都繼續衝突。

修法（schema-level、不是 application-level）：

- 用 sequence 或 distributed counter（每節點本地 + 定期 aggregate）
- partition by hash key、把單一 row 拆成 N 個 sub-row
- 改 *append-only* + 定期 aggregate（事件流 + materialized view）

### 改 READ COMMITTED 後忘了驗證業務語意

v23.2+ 可改 `READ COMMITTED`、少 retry 但失去 serializable 保證。對金融 ledger：READ COMMITTED 可能讓 balance 變負——兩個並行 withdraw 都讀到 balance=100、各自判斷餘額足夠而扣 80：

```sql
-- 共用資料：wallet 表 id = 1 的 balance = 100
-- 兩個 session 同時執行這一段；isolation 換成 SERIALIZABLE 再各跑一次對照
BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;
SELECT balance FROM wallet WHERE id = 1;                 -- 兩個 session 都讀到 100，application 判斷餘額足夠
SELECT pg_sleep(2);                                      -- 模擬 application 判斷的時間，讓兩個 transaction 重疊
UPDATE wallet SET balance = balance - 80 WHERE id = 1;
COMMIT;
-- READ COMMITTED：兩個 session 都 COMMIT 成功，balance = -60
-- SERIALIZABLE：後寫的那個 session 收到 40001（restart transaction），balance = 20
```

修法：

- 金融 / 庫存 / 配額這類 *strict consistency* 場景必須留 SERIALIZABLE
- READ COMMITTED 只用在 *容忍 stale read* 的場景（搜尋結果 / 分析 dashboard）
- 改 isolation level 前 *跑 application audit*、確認業務語意能容忍

### Long-running transaction：retry 機率隨時間線性上升

transaction read 開始時間早、commit 時 conflict window 大、retry 機率隨 transaction duration 線性上升。

修法：

- transaction scope 縮小 — 只包必要 read / write、不要把 RPC call / external API 放 transaction 內
- kill long-running query（`SHOW SESSIONS` + `CANCEL QUERY`）
- 把 batch update 拆成多個小 transaction、加 idempotency key

### Distributed deadlock 跟 retry 互動

CockroachDB 用 distributed deadlock detection（每個 node 維護 wait-for graph、定期跨 node 交換）跟 PostgreSQL local lock 表的 deadlock detection 不同。一般情況下、被 detector 選為 victim 的 transaction 會直接 abort、application retry loop 應該收到 `40001` 後重跑。但在三種 corner case 下會跟 retry loop 形成雪崩 pattern：

- 多 transaction 同時撞同一組熱 row、deadlock detector 跨節點時間窗有 lag、多個 victim 同時 abort 後同時 retry、撞回同一個 deadlock window
- 跨節點的 distributed deadlock 偵測週期（預設 200ms+）放大 application retry latency、application 的 retry backoff 沒對齊偵測週期、形成「detect → abort → 快速 retry → 再 deadlock」迴圈
- Application 把 deadlock victim 當 `40001` 直接 retry、不分流出來看、就難以從 metric 區分「serialization conflict retry」跟「distributed deadlock retry」、調 schema / contention 的策略會用錯方向

修法（屬通用工程議題、case 未直接揭露）：

- Retry backoff 至少對齊 distributed deadlock 偵測週期、避免在偵測窗內快速 retry
- 加 jitter、不同 session 的 retry 不同步
- Application metric 分桶記錄 `serialization_conflict_retry` vs `distributed_deadlock_retry`、避免 contention 改善方向判錯
- Schema 設計階段避免「跨節點熱 row 環形依賴」（例：兩個服務交叉 update 對方的 counter row）

## 容量與觀測

### 必看 metric

- `Transaction retry rate`：per table、per session
- `Serialization failure rate`：絕對值 + ratio
- `Transaction duration p99`：long-running 是 retry 的根因之一
- `Hot ranges by retry count`：top contention 來源
- Application metric：retry count per request、retry-induced latency p99、circuit breaker trip count

### 容量公式

- 基底 QPS × (1 + avg retry count) = 實際 transaction load
- 例：1000 QPS、avg retry = 0.3 → 實際 cluster 處理 1300 transaction/s

retry rate 是 *容量規劃必納入* 的變數 — 沒算 retry 就會 underestimate 真實 load。

### Tuning

- reduce transaction scope：transaction 越短、conflict window 越小
- kill long-running query：transaction 過長要主動截斷
- partition hot rows：schema-level 解 hot contention
- 改 isolation 到 READ COMMITTED（如果業務語意允許）

### 回路徑

- [9.5 瓶頸定位流程](/backend/09-performance-capacity/) 判斷 retry-bound vs CPU-bound
- [9.6 容量規劃模型](/backend/09-performance-capacity/) retry rate × baseline QPS
- [transaction boundary 卡](/backend/knowledge-cards/transaction-boundary/)
- [isolation level 卡](/backend/knowledge-cards/isolation-level/)

## 邊界與整合

### 同 vendor 的其他文章

- [HLC + Raft consensus](../hlc-raft-consensus/)：為什麼 serializable 是 distributed SQL 的合理 default
- [locality-aware schema](../locality-aware-schema/)：partition 降低 hot row contention
- [survival goals](../survival-goals/)：cross-region latency 加長 retry window

### 跟 PostgreSQL 對照

PostgreSQL READ COMMITTED 是 default、application 沒 retry loop 是 acceptable。遷 CockroachDB *必須* 重塑 application transaction contract — 這是 migration 階段最容易 underestimate 的成本。

對應 PostgreSQL MVCC + SSI 機制細節、見 [PostgreSQL MVCC + Lock Model](/backend/01-database/vendors/postgresql/mvcc-lock-model/)。

### Migration playbook

PG → CockroachDB 的 application audit 必看 transaction shape：

- 每個 transaction 的 read / write set 預估衝突率
- 是否冪等（retry-safe）
- transaction duration（long-running 是 retry 放大器）
- 業務語意能否容忍 READ COMMITTED（避開 retry 的 fallback）

### 1.x 章節互引

- [1.3 Transaction Boundary](/backend/01-database/transaction-boundary/) 上游 — distributed transaction 邊界
- [isolation level 卡](/backend/knowledge-cards/isolation-level/)

### 何時不用本文

- 純 read-only workload、無 contention
- 已用 PostgreSQL serializable（application contract 相似、遷移衝擊小）
- 用 CockroachDB v23.2+ READ COMMITTED 且業務允許 stale read

## 相關連結

- [CockroachDB vendor overview](/backend/01-database/vendors/cockroachdb/)
- [HLC + Raft consensus](../hlc-raft-consensus/)
- [DoorDash](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/)（trigger context — PG wire 相容警語）
- [DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)（合成對照 — Aurora sharding 路徑）
- [PostgreSQL MVCC + Lock Model](/backend/01-database/vendors/postgresql/mvcc-lock-model/)
- [isolation level 卡](/backend/knowledge-cards/isolation-level/) / [transaction boundary 卡](/backend/knowledge-cards/transaction-boundary/)
- 官方：[CockroachDB Transactions](https://www.cockroachlabs.com/docs/stable/transactions.html) / [Transaction Retry Error Reference](https://www.cockroachlabs.com/docs/stable/transaction-retry-error-reference.html) / [READ COMMITTED v23.2 announcement](https://www.cockroachlabs.com/docs/stable/read-committed.html)
