---
title: "CockroachDB Transaction Retry Pattern：serializable default 與 application contract 重塑"
date: 2026-05-27
description: "CockroachDB default SERIALIZABLE、application 必須包 retry loop 處理 40001 serialization_failure。本文走 PG → CockroachDB application contract 重塑視角、SAVEPOINT cockroach_restart 語法、5 種失敗模式（retry storm / 非冪等 / cross-statement state / hot row / long-running transaction）。**整篇是跨 case 合成 frame**：DoorDash case 沒揭露 retry pattern、只揭露 PG wire protocol 相容 + SQL 行為仍要 audit、本章 retry contract 重塑屬通用工程議題從 Cockroach Labs 官方 docs 合成"
weight: 50
tags: ["backend", "database", "cockroachdb", "distributed-sql", "transaction", "isolation", "serializable", "deep-article"]
---

> 本文是 [CockroachDB vendor overview](/backend/01-database/vendors/cockroachdb/) 的 implementation-layer deep article。Overview 已界定 CockroachDB 的 PostgreSQL wire 相容定位、本文聚焦 *serializable default 對 application transaction contract 的重塑*。
>
> **Scope warning（最高、F4 Frame 2）**：**本篇整篇是跨 case 合成 frame、不是單一 case 揭露**。3 個 CockroachDB direct case（[9.C39 DoorDash](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/) / [9.C40 Netflix](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/) / [9.C41 Hard Rock Digital](/backend/09-performance-capacity/cases/hard-rock-digital-cockroachdb-sports-betting/)）對 application transaction retry contract 重塑的揭露 *都偏弱* — DoorDash case 只寫 PostgreSQL wire *protocol-level* 相容、SQL 行為（serializable default / retry semantics / partial index）「仍要驗證」、**沒**直接寫 `40001 serialization_failure` / `SAVEPOINT cockroach_restart` / hot row contention / retry loop pattern。Netflix / Hard Rock case 完全沒寫 retry pattern。本章 retry pattern 議題從 Cockroach Labs 官方 SQL Layer docs + PG → CockroachDB 通用 contract 重塑視角合成、DoorDash 只作為 trigger context（撞牆訊號 + 觸發遷移）、不是 ground truth case study。讀者引用本章內容到實際系統前、應該 *自己跑 application audit* 而不是直接套合成的 pattern。

---

## 問題情境：從 PG READ COMMITTED 遷到 CockroachDB SERIALIZABLE 的 application 衝擊

團隊從 PostgreSQL（default `READ COMMITTED`）遷到 CockroachDB（default `SERIALIZABLE`）、上線後 application transaction retry 突然爆增、user-facing latency p99 高 5 倍、error rate 顯著上升。Driver 不會自動 retry — 應用層必須認得 `40001 serialization_failure` 並包 retry loop with exponential backoff。沒包就是直接拋例外給用戶。

讀者常問：

- 為什麼同樣的 transaction 在 CockroachDB 一直 retry、在 PostgreSQL 從來不會？
- `40001 serialization_failure` error 怎麼處理、能不能直接 swallow？
- 我要把所有 application transaction 都改成 retry loop 包起來嗎？
- 能不能改 isolation level 回 `READ COMMITTED`、放棄 serializable 保證？

四題的回答都依賴一個前提：CockroachDB 的 application transaction contract 跟 PostgreSQL default 不一樣、必須重塑。

### Scope warning explicit label：DoorDash case 沒揭露 retry pattern

**DoorDash case 沒直接揭露 serializable retry contract / 40001 / SAVEPOINT pattern / hot row contention**。case 只寫「PostgreSQL wire protocol 相容、實際 SQL 行為（serializable default、retry semantics、partial index）*仍要驗證*」（DoorDash 觀察段 / 策略段 3、F4.4）。

本章 retry pattern 議題是從 PG → CockroachDB 通用 contract 重塑視角合成、不是 DoorDash case 直接揭露。引用 DoorDash 時應該用：

- **正確口徑**：「DoorDash 揭露 Aurora Postgres 1.636 M QPS 撞牆 → 引出 distributed SQL retry contract 需求、本章 retry pattern 議題是從 PostgreSQL → CockroachDB 通用 contract 重塑視角合成、不是 DoorDash case 直接揭露」
- **不要寫成**：「DoorDash retry pattern」、「DoorDash 揭露 40001 處理」之類把合成包成 case fact 的語法

### Case anchor（trigger context、不是 ground truth）

- [9.C39 DoorDash](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/)：提供「PG wire 相容、SQL 行為仍要 audit」的 case 警語（F4.4）、作為本章 *為什麼 retry contract 要重塑* 的觸發訊號。retry pattern 本體走 standard-driven（Cockroach Labs 官方 SQL Layer docs + Transaction Retry docs）

Sibling 對照 [9.C4 DraftKings Aurora financial ledger](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 提供 *PostgreSQL READ COMMITTED + Aurora* 的另一條路徑 — 用 application-level sharding（200 個獨立 Aurora cluster）避開 retry、而不是處理 retry。**Scope warning**：DraftKings case *沒* 寫 PostgreSQL READ COMMITTED retry pattern、case 是 Aurora 內 business sharding 路徑。本章引用 DraftKings 為「假想若把 DraftKings 遷 CockroachDB 會撞到 retry contract 重塑」合成對照、不是 case 直接揭露。

## 核心機制：serializable default 跟 PostgreSQL 的差異

> **來源分層**：本段機制來源是 Cockroach Labs 官方 SQL Layer docs + Transaction Retry docs（standard-driven）、*不是* 從 case 抽取。3 個 direct case 都沒揭露這些機制細節。

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

CockroachDB 追蹤每個 transaction 的 read set 跟 write set。當兩個並行 transaction 的 read / write set 衝突、CockroachDB abort 後到的那個、發 `40001 serialization_failure`。

對比 PostgreSQL serializable（SSI）：兩者都是「post-detect」、commit 時偵測 anomaly、不是 pre-lock。差別在 *衝突偵測時機* 跟 *成本*：

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

CockroachDB v23.2+ 新增 `READ COMMITTED` isolation level — application 可選擇用 weaker isolation 換少 retry。但這是「降級」、失去 serializable 保證 — 對應的反例段在失敗模式段展開（金融 ledger 走 READ COMMITTED 可能讓 balance 變負）。

對應 [isolation level 卡](/backend/knowledge-cards/isolation-level/) 跟 [transaction boundary 卡](/backend/knowledge-cards/transaction-boundary/)。

### DoorDash case 對接點（trigger context only）

DoorDash case 揭露 PG wire *protocol-level* 相容、明示 SQL 行為（serializable default / retry semantics / partial index）「仍要驗證」（F4.4）。本章機制段就是回答「audit 什麼」的具體展開 — 但 audit checklist 本體屬通用工程知識、case 沒 ground truth。

引用紀律：「DoorDash 揭露 PG wire 相容、SQL 行為仍要 audit、其中 serializable default 跟 retry semantics 是 application contract 重塑的核心議題」— 把 case 揭露的 fact 跟本章合成的 frame 分開講。

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
- transaction body 必須是 *冪等* 的（同樣 input 多次執行結果一致）

### 配置

```sql
-- 改 transaction isolation level（v23.2+ 才支援 READ COMMITTED）
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;

-- 看當前 session 預設
SHOW SESSION default_transaction_isolation;
```

### 驗證點

```sql
-- 看 transaction retry 統計
SELECT * FROM crdb_internal.txn_stats;

-- 看哪些 query / table 衝突最多
SELECT * FROM crdb_internal.cluster_contention_events ORDER BY count DESC LIMIT 10;
```

### Idempotency 設計：transaction body 必須冪等

retry-safe transaction body 必須冪等 — 同樣 input 多次執行結果一致：

| Transaction body                             | 是否冪等       | 為什麼                                 |
| -------------------------------------------- | -------------- | -------------------------------------- |
| `UPDATE balance SET balance = balance - 100` | 是             | 同樣 input 每次都減 100                |
| `UPDATE balance SET balance = 900`           | 是             | 設成絕對值、retry 不影響               |
| `INSERT INTO logs VALUES (...)`              | 否             | retry 後重複寫、要加 UNIQUE constraint |
| `INSERT ON CONFLICT (id) DO NOTHING`         | 是             | 用 ON CONFLICT 處理重複                |
| `UPDATE counter SET val = val + 1`           | 否（語意問題） | retry 後加超過預期次數                 |

冪等性是 application 設計議題、不是 CockroachDB 配置可解的 — application contract 重塑的核心成本就在這。

### Rollback 邊界

transaction 自身有 `SAVEPOINT cockroach_restart` 邊界、`ROLLBACK TO SAVEPOINT` 後可重試整個 transaction body。但：

- commit 後不可回滾 — 業務狀態還原只能新交易補償
- application 端如果在 transaction *外* cache state、retry 後 state 不一致（見失敗模式段）

## 失敗模式

### Retry storm：contention 嚴重時 CPU 雪崩

當高頻寫入撞同一 row（例：全局 counter、熱門商品 inventory）、serializable 衝突率可能 100%、application 端 retry loop 不斷重跑、CPU 雪崩。

修法：

- Max retry 上限 + circuit breaker：超過就放棄、回 5xx 給 client、避免 retry storm 拖垮 cluster
- 改 schema 避開 hot row（partition by region、shard counter、用 sequence 代替全局 counter）
- 監控 `crdb_internal.cluster_contention_events`、針對 top-N table 改設計

### 非冪等 transaction 重試：double-count

最危險的 production bug：transaction body 不是冪等的、retry 後資料重複寫。ledger double-count、payment 重複扣款、log 重複記錄。

修法：

- transaction body 寫成 `UPDATE balance SET balance = balance - X`（相對運算）、不寫 `UPDATE balance SET balance = Y`（絕對賦值依賴 read 結果）
- `INSERT` 加 UNIQUE constraint + `ON CONFLICT DO NOTHING`
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

v23.2+ 可改 `READ COMMITTED`、少 retry 但失去 serializable 保證。對金融 ledger：READ COMMITTED 可能讓 balance 變負（兩個並行 withdraw 都看到 balance=100、都扣 50、結果 balance=-50）。

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

### 跨 case 合成 Scope warning：DraftKings 對照

DraftKings ledger 對照 — **DraftKings case 沒寫 PostgreSQL READ COMMITTED retry pattern**、case 內容是「Aurora 內 business sharding 路徑」、用 200 個獨立 cluster 解 Aurora single-primary 撞牆。本章把 DraftKings 拿來當「假想若遷 CockroachDB 需改 SERIALIZABLE + retry loop」的合成對照、不是 case 揭露的 fact。

實際 DraftKings 走 Aurora + application sharding 而非 CockroachDB、所以「DraftKings retry pattern」這個說法本身就是合成 — 應該寫成「DraftKings 走 Aurora sharding 避開 retry contract 重塑、若改走 CockroachDB 則需處理本章描述的 application 改寫」。

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

### Sibling deep articles

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
- [9.C39 DoorDash](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/)（trigger context — PG wire 相容警語）
- [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)（合成對照 — Aurora sharding 路徑）
- [PostgreSQL MVCC + Lock Model](/backend/01-database/vendors/postgresql/mvcc-lock-model/)
- [isolation level 卡](/backend/knowledge-cards/isolation-level/) / [transaction boundary 卡](/backend/knowledge-cards/transaction-boundary/)
- 官方：[CockroachDB Transactions](https://www.cockroachlabs.com/docs/stable/transactions.html) / [Transaction Retry Error Reference](https://www.cockroachlabs.com/docs/stable/transaction-retry-error-reference.html) / [READ COMMITTED v23.2 announcement](https://www.cockroachlabs.com/docs/stable/read-committed.html)
