---
title: "PostgreSQL MVCC + Lock Model：為什麼 PG 比 MySQL 少 deadlock、但 vacuum 是別的代價"
date: 2026-05-19
description: "PG 用 *MVCC-heavy + 少 explicit lock* 的並行控制、跟 MySQL InnoDB 的 *lock-based*（record / gap / next-key）相反。本文走 MVCC 機制（tuple version + xmin/xmax + visibility）、PG 4 種 lock（row-level / table-level / advisory / predicate）、預測 SERIALIZABLE 行為、5 production 踩雷（idle transaction 卡 vacuum / SELECT FOR UPDATE 跨 transaction / advisory lock 沒釋放 / bloat 不是 vacuum 問題 / predicate lock 在 SSI 下 rollback）、跟 MySQL lock-contention sibling 對比"
weight: 24
tags: ["backend", "database", "postgresql", "lock", "mvcc", "concurrency", "deep-article"]
---

本文的範圍是 PostgreSQL 的並行控制：MVCC 每次更新新增 tuple 的做法，row-level、table-level、advisory 與 predicate lock，預設的 READ COMMITTED isolation，production 踩雷與觀測 metric，以及跟 MySQL lock-based 模型的對比。

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

- tuple.xmin 在 snapshot 建立前已經 commit（不在 active transaction list 裡、也不比 snapshot 新），而且 tuple.xmax 是 NULL、或 xmax 的 transaction 對這個 snapshot 還不算數（仍在 active list 裡、比 snapshot 新、或已 abort）→ 可見
- 否則 → 看不到（還沒 commit 或比 snapshot 新的版本，以及已經被 commit 的 UPDATE / DELETE 取代的舊版本）

**MVCC 對讀寫並行的效果**：

- *Readers 不 lock writers*：SELECT 看 snapshot、不 block UPDATE
- *Writers 不 lock readers*：UPDATE 寫新 tuple、不影響正在跑的 SELECT snapshot
- *Writers 只 lock 同一 row 的 writers*：兩個 UPDATE 同 row 才 conflict

跟 MySQL InnoDB *lock-based*（[Lock Contention](/backend/01-database/vendors/mysql/lock-contention/)）對比：

- MySQL：SELECT FOR UPDATE 用 gap lock 防 phantom、deadlock 機率高
- PG：REPEATABLE READ 以上的 transaction 整段讀同一個 snapshot，看不到別人新 commit 的列，phantom 不出現；預設的 READ COMMITTED 每個 statement 拿新的 snapshot，同一個 transaction 裡兩次查詢可以看到不同的列。deadlock 少

但 PG 代價是 *VACUUM 治理* — dead tuple 不清理會佔 disk + 影響 query 效率。詳見 [Autovacuum Tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)。

## PG 的 lock：row-level、table-level、advisory、predicate

PG 仍有 lock、但場景跟 MySQL 不同：

### Row-level lock — 主要由 UPDATE / DELETE / SELECT FOR UPDATE 取

```sql
BEGIN;
SELECT * FROM orders WHERE id = 100 FOR UPDATE;
-- 對 id=100 這一列加 row-level 的 FOR UPDATE lock；table 層級拿的是 ROW SHARE（pg_locks 裡的 RowShareLock）
-- 其他 transaction 試 UPDATE / DELETE id=100 必須等
```

Row-level lock *不 block reader*（SELECT 看 snapshot、不檢查 lock）。

### Table-level lock — DDL 跟少數 SELECT FOR 場景

PG 有 8 種 table lock mode、嚴重程度遞增：

| Mode                   | 行為                                                                            | 衝突                                                                                    |
| ---------------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| ACCESS SHARE           | SELECT 跑                                                                       | ACCESS EXCLUSIVE                                                                        |
| ROW SHARE              | SELECT FOR UPDATE / FOR SHARE                                                   | EXCLUSIVE、ACCESS EXCLUSIVE                                                             |
| ROW EXCLUSIVE          | UPDATE / DELETE / INSERT                                                        | SHARE、SHARE ROW EXCLUSIVE、EXCLUSIVE、ACCESS EXCLUSIVE                                 |
| SHARE UPDATE EXCLUSIVE | VACUUM / ANALYZE / CREATE INDEX CONCURRENTLY                                    | SHARE UPDATE EXCLUSIVE、SHARE、SHARE ROW EXCLUSIVE、EXCLUSIVE、ACCESS EXCLUSIVE         |
| SHARE                  | CREATE INDEX（non-concurrent）                                                  | ROW EXCLUSIVE、SHARE UPDATE EXCLUSIVE、SHARE ROW EXCLUSIVE、EXCLUSIVE、ACCESS EXCLUSIVE |
| SHARE ROW EXCLUSIVE    | CREATE TRIGGER / 某些 ALTER                                                     | ACCESS SHARE 與 ROW SHARE 以外的所有 mode（含自身）                                     |
| EXCLUSIVE              | REFRESH MATERIALIZED VIEW CONCURRENTLY                                          | ACCESS SHARE 以外的所有 mode（含自身）                                                  |
| ACCESS EXCLUSIVE       | DROP / ALTER TABLE / VACUUM FULL / REFRESH MATERIALIZED VIEW（非 CONCURRENTLY） | 所有 mode（含 ACCESS SHARE）                                                            |

DDL（ALTER / DROP）拿 ACCESS EXCLUSIVE、跟所有衝突。Production 跑 ALTER 必須短時間或走 [Online Schema Change](/backend/01-database/vendors/postgresql/online-schema-change/)。

### Advisory lock — Application 自己控

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

### Predicate lock — SERIALIZABLE isolation 才用

PG SERIALIZABLE 用 *Serializable Snapshot Isolation (SSI)*、追蹤 *predicate*（query 條件）而不是 *row*：

```sql
-- 兩個 session 照同一條規則下單：先數 pending 訂單，再新增一張 pending 訂單
-- Session A
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT count(*) FROM orders WHERE status = 'pending';  -- SSI 記下這個 query 讀過的範圍（pg_locks 裡的 SIReadLock）
INSERT INTO orders VALUES (200, 'pending');
COMMIT;                                                -- 先 commit 的 A 成功

-- Session B：在 A commit 之前開始，數到的是同一個舊的 count
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT count(*) FROM orders WHERE status = 'pending';
INSERT INTO orders VALUES (201, 'pending');
COMMIT;
-- ERROR:  could not serialize access due to read/write dependencies among transactions
-- SQLSTATE 40001：兩邊各自讀了對方寫入的範圍，沒有任何一種先後順序能得到這個結果，B 被 rollback、要整段重試
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

## Production 踩雷

### Idle transaction 卡 vacuum — Bloat 暴增

PG MVCC 仰賴 *VACUUM 清理 dead tuple*。VACUUM 只清理 *已經沒有任何 transaction 看得到的 dead tuple*。如果有 *idle in transaction* session 持續開著（application connection pool 連線忘關 transaction），而這個 transaction 已經寫過資料（持有 transaction ID）或跑在 REPEATABLE READ 以上（持有 snapshot），VACUUM 就不能清掉在它開始之後才變成 dead 的 tuple，bloat 跟著累積。只讀過資料的 READ COMMITTED transaction 在兩個 statement 之間不持有 snapshot，閒置時不擋 vacuum。

修法：

- 監控 `pg_stat_activity` 看 `state = 'idle in transaction'` 持續時間
- 設 `idle_in_transaction_session_timeout = '5min'` — 超時 PG 自動 kill 該 session
- Application 在每條程式路徑的結尾都 commit 或 rollback；經過 pgBouncer 時可再設 `idle_transaction_timeout`，client 在 transaction 裡閒置超過這個秒數就被 pgBouncer 斷線

### SELECT FOR UPDATE 的 transaction 跨過使用者操作 — lock 等待與 idle in transaction

PG 的 SELECT FOR UPDATE 不會 *block 其他普通 SELECT*（讀仍可繼續）、但 *block 其他 UPDATE / FOR UPDATE*。若 application 在 transaction 內 SELECT FOR UPDATE、其他 transaction 等。

如果 application 設計 *跨 transaction 持 lock*（如：取 lock + return UI + 等用戶操作 + commit）、容易撞 idle in transaction 跟其他 transaction wait。

修法：

- *Transaction 短*：取 FOR UPDATE → 立刻處理 → commit、不跨 user interaction
- 跨 user interaction 用 *advisory lock* 或 application-level state machine、不依賴 row lock

### Advisory lock 沒釋放 — Session 結束才自動釋放

`pg_advisory_lock()` 拿了、沒 `pg_advisory_unlock()`、lock 直到 *session 結束* 才自動釋放。Connection pool 重複使用同 connection、可能繼承前面留的 lock。

修法：

- 用 `pg_advisory_lock` 必 `try/finally pg_advisory_unlock`
- 或把 session-level 的 `pg_advisory_lock()` 換成 transaction-level 的 `pg_advisory_xact_lock()`：lock 在 commit / rollback 時自動釋放
- 監控 `pg_locks` 看 advisory lock count、長期累積是警訊

### Bloat 的成因是 xmin horizon 擋住 vacuum、不只是 vacuum 沒跑

這是〈Idle transaction 卡 vacuum〉的一般形態：vacuum 已經跑過、bloat 仍持續成長，原因是某個 session 的 xmin horizon 停在舊位置。xmin horizon 是官方文件對 `pg_stat_activity.backend_xmin` 的稱呼，指這個 session 還需要的最舊 transaction；比它新才變成 dead 的 tuple，vacuum 一律不能清。

修法：

- 不只看 `last_vacuum`、看 *VACUUM 跑了但沒收回多少*
- `SELECT * FROM pg_stat_progress_vacuum` 看 VACUUM 進度
- `SELECT pid, state, backend_xid, backend_xmin FROM pg_stat_activity WHERE backend_xid IS NOT NULL OR backend_xmin IS NOT NULL ORDER BY greatest(age(backend_xid), age(backend_xmin)) DESC` — 看誰阻擋 vacuum：排最前面的 session 持有最舊的 transaction ID 或 snapshot。`xid` 型別沒有排序運算子，直接 `ORDER BY backend_xmin` 會報錯，所以用 `age()` 換成數字再排；寫過資料的 transaction 只有 `backend_xid` 有值，兩欄都要看
- 詳見 [Autovacuum Tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)

### SERIALIZABLE 下 transaction rollback — Application 必須 retry

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

兩者解決同一問題（並行控制）、用不同策略。PG 把舊版本 tuple 留在 table 裡：讀寫不互鎖，代價是要靠 VACUUM 清理。InnoDB 把舊版本放在 undo log、由背景的 purge 清掉，REPEATABLE READ 下的 locking read 用 gap lock 擋 phantom，代價是 lock 等待。

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

pgBouncer transaction pooling 模式下、session-level advisory lock（`pg_advisory_lock`）會失效：lock 綁在 backend connection 上，同一個 client 的下一個 transaction 可能進不同的 backend，unlock 落在沒有持有 lock 的 connection 上。`pg_advisory_xact_lock` 與 SELECT FOR UPDATE 的 lock 都在 transaction 結束時釋放，不受 pool mode 影響。詳見 [pgBouncer Config](/backend/01-database/vendors/postgresql/pgbouncer-config/)。

### 跟 Query Optimization

長 transaction 持有的 xmin horizon 讓 vacuum 清不掉 dead tuple，table 與 index 裡累積的 dead tuple 讓 query 要多讀 page。詳見 [Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/)。

## 相關連結

- [PostgreSQL vendor overview](/backend/01-database/vendors/postgresql/)
- [PG Autovacuum Tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)（VACUUM 是 MVCC 必要成本）
- [PG Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)（hot_standby_feedback 影響）
- [PG pgBouncer](/backend/01-database/vendors/postgresql/pgbouncer-config/)（transaction pooling 跟 lock 互動）
- [PG Online Schema Change](/backend/01-database/vendors/postgresql/online-schema-change/)（DDL lock 議題）
- [PG Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/)（xmin horizon 造成的 dead tuple 讓 query 變慢）
- [MySQL Lock Contention](/backend/01-database/vendors/mysql/lock-contention/)（sibling、不同模型）
- [Isolation Level 卡片](/backend/knowledge-cards/isolation-level/)
- 官方：[PG MVCC](https://www.postgresql.org/docs/current/mvcc.html) / [PG Concurrency Control](https://www.postgresql.org/docs/current/transaction-iso.html) / [Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html)
