---
title: "PostgreSQL MVCC + Lock Model：為什麼 PG 比 MySQL 少 deadlock、但 vacuum 是別的代價"
date: 2026-05-19
description: "PG 用 *MVCC-heavy + 少 explicit lock* 的並行控制、跟 MySQL InnoDB 的 *lock-based*（record / gap / next-key）相反。本文走 MVCC 機制（tuple version + xmin/xmax + visibility）、PG 4 種 lock（row-level / table-level / advisory / predicate）、預測 SERIALIZABLE 行為、5 production 踩雷（idle transaction 卡 vacuum / SELECT FOR UPDATE 跨 transaction / advisory lock 沒釋放 / bloat 不是 vacuum 問題 / predicate lock 在 SSI 下 rollback）、跟 MySQL lock-contention sibling 對比"
weight: 24
tags: ["backend", "database", "postgresql", "lock", "mvcc", "concurrency", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 PG 在 OLTP 譜系的定位、本文聚焦 *MVCC + lock model* — PG 並行控制機制跟跟 MySQL lock-based 不同。

---

## PG MVCC：每次更新都 *新增 tuple*、不改舊版

PG 的並行控制核心是 *Multi-Version Concurrency Control* — UPDATE 不修改原 row、是 *新增* 一個 tuple version、舊 version 留在 table 直到 VACUUM 清理：

```text
原 row:    (id=1, status='pending', xmin=100, xmax=NULL)
                 ↓ UPDATE status='shipped'
新 tuple:  (id=1, status='shipped', xmin=200, xmax=NULL)
舊 tuple 標 xmax=200（不刪、給其他 transaction 看舊 version）
```

`xmin` / `xmax` 是 *creator transaction id* / *destroyer transaction id*。每個 SELECT 用 *snapshot*（含當下 active transaction list）判斷哪些 tuple 對自己可見：

- 自己 transaction id > tuple.xmin 且 (tuple.xmax = NULL 或自己 transaction id < tuple.xmax) → 可見
- 否則 → 看不到（過去 / 未來版本）

**結果**：

- *Readers 不 lock writers*：SELECT 看 snapshot、不 block UPDATE
- *Writers 不 lock readers*：UPDATE 寫新 tuple、不影響正在跑的 SELECT snapshot
- *Writers 只 lock 同一 row 的 writers*：兩個 UPDATE 同 row 才 conflict

跟 MySQL InnoDB *lock-based*（[Lock Contention](/backend/01-database/vendors/mysql/lock-contention/)）對比：

- MySQL：SELECT FOR UPDATE 用 gap lock 防 phantom、deadlock 機率高
- PG：MVCC + snapshot 自然防 phantom（read 看 snapshot）、deadlock 少

但 PG 代價是 *VACUUM 治理* — dead tuple 不清理會佔 disk + 影響 query 效率。詳見 [Autovacuum Tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)。

## PG 4 種 lock

PG 仍有 lock、但場景跟 MySQL 不同：

### 1. Row-level lock — 主要由 UPDATE / DELETE / SELECT FOR UPDATE 取

```sql
BEGIN;
SELECT * FROM orders WHERE id = 100 FOR UPDATE;
-- 對 id=100 row 加 ROW EXCLUSIVE lock
-- 其他 transaction 試 UPDATE / DELETE id=100 必須等
```

Row-level lock *不 block reader*（SELECT 看 snapshot、不檢查 lock）。

### 2. Table-level lock — DDL 跟少數 SELECT FOR 場景

PG 有 8 種 table lock mode、嚴重程度遞增：

| Mode                   | 行為                                         | 衝突                     |
| ---------------------- | -------------------------------------------- | ------------------------ |
| ACCESS SHARE           | SELECT 跑                                    | 跟 ACCESS EXCLUSIVE 衝突 |
| ROW SHARE              | SELECT FOR UPDATE / FOR SHARE                | 跟 EXCLUSIVE 衝突        |
| ROW EXCLUSIVE          | UPDATE / DELETE / INSERT                     | 跟 SHARE 衝突            |
| SHARE UPDATE EXCLUSIVE | VACUUM / ANALYZE / CREATE INDEX CONCURRENTLY | 跟同 mode + 高 mode 衝突 |
| SHARE                  | CREATE INDEX（non-concurrent）               | 跟 ROW EXCLUSIVE 衝突    |
| SHARE ROW EXCLUSIVE    | CREATE TRIGGER / 某些 ALTER                  | 跟 ROW EXCLUSIVE 衝突    |
| EXCLUSIVE              | REFRESH MATERIALIZED VIEW                    | 跟所有 + 自身衝突        |
| ACCESS EXCLUSIVE       | DROP / ALTER TABLE / VACUUM FULL             | 跟所有衝突               |

DDL（ALTER / DROP）拿 ACCESS EXCLUSIVE、跟所有衝突。Production 跑 ALTER 必須短時間或走 [Online Schema Change](/backend/01-database/vendors/postgresql/online-schema-change/)。

### 3. Advisory lock — Application 自己控

PG 提供 *advisory lock* 給 application 用、不關 row / table 結構：

```sql
-- Session 1
SELECT pg_advisory_lock(12345);
-- 跑 critical section
SELECT pg_advisory_unlock(12345);

-- Session 2
SELECT pg_try_advisory_lock(12345);  -- 試取、不阻塞、返回 false
```

用途：

- Application-level 互斥（如：cron job 同時只跑一個）
- 跨 connection 同步（PG-managed mutex）
- Distributed transaction coordinator（lightweight）

跟 row lock 不同：advisory lock 不關 row、application 自定義 lock ID 語義。

### 4. Predicate lock — SERIALIZABLE isolation 才用

PG SERIALIZABLE 用 *Serializable Snapshot Isolation (SSI)*、追蹤 *predicate*（query 條件）而不是 *row*：

```sql
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
BEGIN;
-- Predicate lock 紀錄這個 query 看了哪些 predicate
SELECT * FROM orders WHERE status = 'pending';
-- 其他 transaction INSERT pending order
-- 提交時：PG 偵測 anomaly、rollback 之一
COMMIT;
```

跟 MySQL gap lock 不同：

- MySQL gap lock：*pre-lock*、防 phantom 在 query 期間
- PG predicate lock：*post-detect*、commit 時偵測 anomaly、退回 transaction

PG SSI 對 *寫入吞吐影響低*（不 pre-lock）、但 *transaction rollback 機率高*（要 application retry）。

## PG 預設 isolation：READ COMMITTED

PG 預設 READ COMMITTED、跟 MySQL InnoDB 預設 REPEATABLE READ 不同：

| Isolation        | PG 行為                                           | MySQL InnoDB 對應                                                                                                                              |
| ---------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| READ UNCOMMITTED | PG 視為 READ COMMITTED（不真的支援 dirty read）   | MySQL 真支援                                                                                                                                   |
| READ COMMITTED   | 每 statement 看當下 committed snapshot（PG 預設） | 一致                                                                                                                                           |
| REPEATABLE READ  | Transaction 內 fixed snapshot（純 MVCC）          | MVCC snapshot + gap lock 防 phantom（兩者都 MVCC、差在 phantom 防護機制：PG 靠 snapshot version visibility、InnoDB 加 gap lock pre-lock 範圍） |
| SERIALIZABLE     | SSI、commit 時偵測 anomaly                        | 強 lock + gap                                                                                                                                  |

**對 application code 含意**：

- PG REPEATABLE READ 對 *寫入吞吐* 影響低（不 pre-lock、只 retry）
- 沒 gap lock → INSERT 不被 lock-induced 阻塞
- Deadlock 機率比 MySQL 低數量級

實務 PG production：用預設 READ COMMITTED 即可、SERIALIZABLE 留給 *strict consistency 需求*（金融 / 訂單）但接受 retry。

## 5 個 Production 踩雷

### 1. Idle transaction 卡 vacuum — Bloat 暴增

PG MVCC 仰賴 *VACUUM 清理 dead tuple*。VACUUM 只清理 *沒 active transaction 看得到的 dead tuple*。如果有 *idle in transaction* session 持續開著（application connection pool 連線忘關 transaction）、VACUUM 看不到 *該 transaction snapshot 之後的 dead tuple*、累積 bloat。

修法：

- 監控 `pg_stat_activity` 看 `state = 'idle in transaction'` 持續時間
- 設 `idle_in_transaction_session_timeout = '5min'` — 超時 PG 自動 kill 該 session
- Application connection pool 配置 *不留 transaction 開著*（如：pgBouncer transaction pool 自動 commit / rollback）

### 2. SELECT FOR UPDATE 跨 transaction — Application retry 麻煩

跟 MySQL 不同：PG SELECT FOR UPDATE 不會 *block 其他 SELECT*（讀仍可繼續）、但 *block 其他 UPDATE / FOR UPDATE*。若 application 在 transaction 內 SELECT FOR UPDATE、其他 transaction 等。

如果 application 設計 *跨 transaction 持 lock*（如：取 lock + return UI + 等用戶操作 + commit）、容易撞 idle in transaction 跟其他 transaction wait。

修法：

- *Transaction 短*：取 FOR UPDATE → 立刻處理 → commit、不跨 user interaction
- 跨 user interaction 用 *advisory lock* 或 application-level state machine、不依賴 row lock

### 3. Advisory lock 沒釋放 — Session 結束才自動釋放

`pg_advisory_lock()` 拿了、沒 `pg_advisory_unlock()`、lock 直到 *session 結束* 才自動釋放。Connection pool 重複使用同 connection、可能繼承前面留的 lock。

修法：

- 用 `pg_advisory_lock` 必 `try/finally pg_advisory_unlock`
- 或用 *session-level* 用 transaction-scoped：`pg_advisory_xact_lock()` — commit / rollback 自動釋放
- 監控 `pg_locks` 看 advisory lock count、長期累積是警訊

### 4. Bloat 不只是 vacuum 沒跑、是 *active transaction 阻擋 vacuum*

第 #1 點延伸：vacuum 已跑、但 bloat 仍持續成長、原因不是 vacuum 不夠、是 *active transaction 阻擋 vacuum 看 dead tuple*。

修法：

- 不只看 `last_vacuum`、看 *VACUUM 跑了但沒收回多少*
- `SELECT * FROM pg_stat_progress_vacuum` 看 VACUUM 進度
- `SELECT * FROM pg_stat_activity WHERE backend_xmin IS NOT NULL ORDER BY backend_xmin` — 看誰阻擋 vacuum
- 詳見 [Autovacuum Tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)

### 5. SERIALIZABLE 下 transaction rollback — Application 必須 retry

`SET TRANSACTION ISOLATION LEVEL SERIALIZABLE` 後、PG SSI 偵測到 anomaly 會 *rollback transaction*、application 看到 `serialization failure`、必須 retry。

對 *不知道要 retry* 的 application、SERIALIZABLE 變 production bug。

修法：

- Application code 加 *retry middleware*：catch `SQLSTATE 40001 (serialization_failure)` → exponential backoff retry
- 不必所有 transaction 走 SERIALIZABLE — 只對 *strict consistency 需求* 場景 set
- 高並發 SERIALIZABLE workload 容易 rollback storm、考慮拆 transaction 縮短時間

## 觀測 metric

Production 監控：

- `pg_stat_activity`：active session / idle in transaction / wait_event
- `pg_locks`：當前 lock 列表、用 join 看誰 block 誰
- `pg_stat_database.deadlocks`：deadlock 計數（PG 較低、但仍要監控）
- `pg_stat_user_tables.n_dead_tup` / `n_live_tup`：dead tuple 比例 — bloat 指標
- `pg_stat_progress_vacuum`：VACUUM 進度

## 跟 MySQL Lock Model 對比

| 維度               | PG MVCC                              | MySQL InnoDB Lock          |
| ------------------ | ------------------------------------ | -------------------------- |
| 主要機制           | MVCC + snapshot                      | Lock-based + MVCC mixed    |
| Readers vs Writers | 不互 block                           | 預設 RR 下 gap lock 影響   |
| Deadlock 機率      | 低（無 gap lock）                    | 中-高（gap lock 主要來源） |
| Phantom 防護       | Snapshot 自然防 + SSI predicate lock | Gap lock 預先 lock         |
| 預設 isolation     | READ COMMITTED                       | REPEATABLE READ            |
| 成本               | Dead tuple + VACUUM 治理             | Lock contention 治理       |
| Application code   | SERIALIZABLE 需 retry                | 寫得不錯多數時 OK          |

兩者解決同一問題（並行控制）、用不同策略。PG 用 *空間換時間*（保留多版本 tuple、讀寫不互鎖、但需 VACUUM 清理）、MySQL 用 *時間換空間*（lock 等待、但不必清舊版本）。

**選擇判讀**：

- High 並發 OLTP、寫 / 讀都重：PG MVCC 通常更好（讀不 block 寫）
- 簡單 OLTP + 不想管 VACUUM：MySQL InnoDB 對 ops 簡單
- 需要 SERIALIZABLE 強一致：PG SSI 對寫吞吐影響低
- 已有 MySQL 生態 / 工具鏈：MySQL Lock 知識可繼續用

詳見 [MySQL Lock Contention](/backend/01-database/vendors/mysql/lock-contention/) — 完整 MySQL lock 機制。

## 跟其他模組整合

### 跟 Autovacuum Tuning

MVCC 仰賴 VACUUM、autovacuum 是 PG 並行控制的 *維護成本*。VACUUM 跑慢 / 沒跑 → bloat → query 慢。詳見 [Autovacuum Tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)。

### 跟 Replication Topology

`hot_standby_feedback = on` 讓 standby 上 long-running query 不被 vacuum 取消、但 *standby 把 oldest xmin 推回 primary*、primary autovacuum 變保守、增加 bloat。詳見 [Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)。

### 跟 Connection Pool

pgBouncer transaction pooling 模式下、advisory lock / SELECT FOR UPDATE 跨 transaction 行為 *broken*（不同 transaction 可能進不同 backend connection）。詳見 [pgBouncer Config](/backend/01-database/vendors/postgresql/pgbouncer-config/)。

### 跟 Query Optimization

長 transaction 跑慢 query 期間、其他 transaction 看到 snapshot bloat、planner 估錯 dead tuple ratio。詳見 [Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/)。

## 相關連結

- [PostgreSQL vendor overview](/backend/01-database/vendors/postgresql/)
- [PG Autovacuum Tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)（VACUUM 是 MVCC 必要成本）
- [PG Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)（hot_standby_feedback 影響）
- [PG pgBouncer](/backend/01-database/vendors/postgresql/pgbouncer-config/)（transaction pooling 跟 lock 互動）
- [PG Online Schema Change](/backend/01-database/vendors/postgresql/online-schema-change/)（DDL lock 議題）
- [PG Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/)（snapshot bloat 影響 planner）
- [MySQL Lock Contention](/backend/01-database/vendors/mysql/lock-contention/)（sibling、不同模型）
- [Isolation Level 卡片](/backend/knowledge-cards/isolation-level/)
- 官方：[PG MVCC](https://www.postgresql.org/docs/current/mvcc.html) / [PG Concurrency Control](https://www.postgresql.org/docs/current/transaction-iso.html) / [Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html)
