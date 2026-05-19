---
title: "MySQL Lock Contention：在 staging 重現的 deadlock、production 跑 6 個月才出現"
date: 2026-05-19
description: "MySQL InnoDB 的 lock 是 row-level、但 *為什麼某些 row 莫名其妙也被 lock* 是 gap lock / next-key lock 設計造成的隱性行為。本文從一個 production case 開場（staging 重現 deadlock / production 6 個月後突然爆）、走 5 種 InnoDB lock 類型（record / gap / next-key / insert intention / auto-inc）、isolation level 對 lock 行為的決定性影響、deadlock detection / SHOW ENGINE INNODB STATUS 解讀、5 production 踩雷（gap lock 阻塞 INSERT / auto-inc lock contention / FK lock cascading / large transaction lock holding / READ COMMITTED 跟 binlog ROW 互動）"
weight: 24
tags: ["backend", "database", "mysql", "lock", "deadlock", "deep-article"]
---

> 本文是 [MySQL](/backend/01-database/vendors/mysql/) overview 的 implementation-layer deep article。Overview 已說明 MySQL 在 OLTP 譜系的定位、本文聚焦 *lock contention* — 5 種 lock type + isolation level 互動 + production debug。

---

## 開場案例

Application 跑了 6 個月、staging 100% 重現過的 deadlock 從來沒在 production 出現。某天 traffic 上升 30%、production 開始爆 `ER_LOCK_DEADLOCK`、application retry 不夠快、order 大量失敗。

`SHOW ENGINE INNODB STATUS\G` 拉出 deadlock：

```text
*** (1) TRANSACTION:
TRANSACTION 12345, ACTIVE 1 sec starting index read
mysql tables in use 1, locked 1
LOCK WAIT 4 lock struct(s), heap size 1136, 3 row lock(s)
MySQL thread id 100, query id 5000 update orders
UPDATE orders SET status = 'shipped' WHERE id = 500

*** (1) WAITING FOR THIS LOCK TO BE GRANTED:
RECORD LOCKS space id 50 page no 5 n bits 80 index PRIMARY of table `production`.`orders`
trx id 12345 lock_mode X locks rec but not gap waiting

*** (2) TRANSACTION:
TRANSACTION 12346, ACTIVE 1 sec starting index read
mysql tables in use 1, locked 1
4 lock struct(s), heap size 1136, 4 row lock(s)
MySQL thread id 101, query id 5001 update payments
UPDATE payments SET captured = 1 WHERE order_id = 500

*** (2) HOLDS THE LOCK(S):
RECORD LOCKS space id 50 page no 5 n bits 80 index PRIMARY of table `production`.`orders`
trx id 12346 lock_mode X locks rec but not gap

*** (2) WAITING FOR THIS LOCK TO BE GRANTED:
RECORD LOCKS space id 51 page no 10 n bits 80 index idx_order_id of table `production`.`payments`
trx id 12346 lock_mode X waiting

*** WE ROLL BACK TRANSACTION (1)
```

兩個 transaction 各自拿了一邊 lock、互相等對方的、deadlock。為什麼 staging 重現過、production 6 個月才爆？因為 **lock contention 是 *可能性* 不是 *確定性*** — staging 重現等於確認「程式邏輯有 deadlock risk」、production 6 個月平安等於「concurrency 還沒撞到」。Traffic 上升把 *機率乘以 N*、原本每天 0 次變每分鐘 5 次。

這個 case 揭露 MySQL lock 教學的核心：理解 lock 不只是 *debug 跑 deadlock 報錯* 的能力、是 *讀 query 預測 lock pattern* 的能力。

## InnoDB 5 種 Lock 類型

InnoDB 不是 *簡單 row lock*、有 5 個獨立 lock concept：

### 1. Record Lock — 鎖 row

`SELECT ... FOR UPDATE` / UPDATE / DELETE 對 *被 match 的 row* 加 record lock。

```sql
-- Transaction 1
BEGIN;
SELECT * FROM orders WHERE id = 100 FOR UPDATE;
-- 對 id=100 的 row 加 record lock
```

Transaction 2 試 `UPDATE orders WHERE id = 100` 必須等。

### 2. Gap Lock — 鎖 row 之間的「空隙」

InnoDB 在 *REPEATABLE READ* (預設) 下、`SELECT ... FOR UPDATE WHERE col > 100` 不只 lock 符合的 row、*也 lock 該 range 內的「空隙」*、防其他 transaction INSERT 進這個 range。

```sql
-- 已存在 orders: id=100, 200, 300
BEGIN;
SELECT * FROM orders WHERE id > 100 AND id < 300 FOR UPDATE;
-- Lock id=200 + gap lock (100, 200) + gap lock (200, 300)
```

Transaction 2 試 `INSERT INTO orders (id) VALUES (150)` 必須等 — 即使 id=150 不存在、gap lock 阻擋 INSERT。

**Gap lock 是 deadlock 最常見來源** — application logic 看 row、但 lock 卻 cover row 之外的空隙、難預測。

### 3. Next-Key Lock — Record + Gap 組合

預設 lock 行為。`SELECT ... FOR UPDATE WHERE col = 100` 對 id=100 的 record lock + id=100 之前的 gap lock。

Lock 的範圍實際是 *半開區間* (previous_id, current_id]：

```text
Records: 100, 200, 300

WHERE id = 100 FOR UPDATE → next-key lock (-inf, 100]
WHERE id = 200 FOR UPDATE → next-key lock (100, 200]
WHERE id = 300 FOR UPDATE → next-key lock (200, 300]
WHERE id BETWEEN 150 AND 250 FOR UPDATE → next-key lock (100, 200] + (200, 300]
```

### 4. Insert Intention Lock — INSERT 之前的 gap lock

`INSERT` 不直接 lock 整個 gap、而是 *insert intention lock* — 比 gap lock 弱、允許多個 INSERT 同 gap 並行（不同 id）。

```sql
-- Transaction 1
INSERT INTO orders (id) VALUES (150);
-- Transaction 2
INSERT INTO orders (id) VALUES (175);
-- 同 gap (100, 200)、兩個 INSERT 並行、不阻塞
```

但如果 Transaction 1 已 hold gap lock（through SELECT FOR UPDATE）、Transaction 2 INSERT 必須等。

### 5. Auto-Inc Lock — Auto-Increment column 專用

`INSERT INTO orders (id) VALUES (DEFAULT)` 取得 auto-increment value 時 lock。Mode：

- `innodb_autoinc_lock_mode=0`（traditional）：lock 整個 INSERT statement 期間、其他 INSERT 必須等
- `innodb_autoinc_lock_mode=1`（consecutive）：lock 短時間（取值期間）、INSERT 1 row 不會阻塞其他
- `innodb_autoinc_lock_mode=2`（interleaved、8.0+ 預設（5.7 預設仍是 1））：完全並行、auto-inc value 不保證連續但可並行

8.0+ 預設 mode=2、性能高、但 *binlog format 必須 ROW*（STATEMENT 行為錯）。

## Isolation Level 對 Lock 的決定性影響

InnoDB 4 個 isolation level、lock 行為完全不同：

| Isolation        | Read 行為                           | Lock 範圍                    | Default? |
| ---------------- | ----------------------------------- | ---------------------------- | -------- |
| READ UNCOMMITTED | 可讀 dirty data                     | 純 record lock、無 gap       | 否       |
| READ COMMITTED   | 每個 statement 看當下 committed     | 純 record lock、無 gap       | 否       |
| REPEATABLE READ  | Transaction 內 snapshot consistent  | Record + gap + next-key      | **是**   |
| SERIALIZABLE     | 強制 SELECT 變 SELECT ... FOR SHARE | Record + gap + next-key 加重 | 否       |

**REPEATABLE READ + Gap lock 是 deadlock 主要來源**：

- 預設 isolation level
- 為了 *保證 repeatable read*（同 transaction 內讀同樣資料）、強制 gap lock 防 phantom row
- 但 gap lock 經常 lock 比預期廣的範圍、deadlock 機率上升

**改成 READ COMMITTED 的取捨**：

- 優點：無 gap lock、deadlock 大降、寫吞吐上升
- 缺點：transaction 內讀同 query 結果可能不同（non-repeatable read）
- 重要：*binlog format 必須 ROW*（STATEMENT 在 READ COMMITTED 下 replication 行為不一致）
- 多數 MySQL production 用 READ COMMITTED 跑 OLTP、REPEATABLE READ 留給特殊 case

**對比 PostgreSQL**：

- PG 預設 isolation 是 *READ COMMITTED*（不是 RR）
- PG 的 RR 用 *snapshot isolation*（不靠 gap lock）、deadlock 少
- 這是 MySQL 跟 PG 在 *並行控制 model* 的根本差異 — MySQL 用 lock-based、PG 用 MVCC-heavy

## 用 SHOW ENGINE INNODB STATUS 讀 lock 狀態

`SHOW ENGINE INNODB STATUS\G` 是 production debug lock contention 的主要工具：

```text
------------
TRANSACTIONS
------------
Trx id counter 12350
Purge done for trx's n:o < 12340 undo n:o < 0 state: running but idle
History list length 5

---TRANSACTION 12345, ACTIVE 30 sec  -- 長 transaction、警訊
3 lock struct(s), heap size 1136, 5 row lock(s)
MySQL thread id 100, OS thread handle ..., query id ...
SELECT * FROM orders WHERE id > 100 FOR UPDATE
------- TRX HAS BEEN WAITING 5 SEC FOR THIS LOCK:
RECORD LOCKS space id 50 page no 5 n bits 80 index PRIMARY of table `production`.`orders`
trx id 12345 lock_mode X locks gap before rec  -- gap lock
```

關鍵欄位：

- `ACTIVE N sec`：transaction 跑多久（長 transaction 嫌疑）
- `lock_mode X / S`：exclusive / shared lock
- `locks rec but not gap` / `locks gap before rec` / `locks rec`：是 record / gap / next-key
- `TRX HAS BEEN WAITING N SEC FOR THIS LOCK`：等多久、超過幾秒就是 lock contention

`SELECT * FROM information_schema.INNODB_TRX` / `INNODB_LOCKS` (5.7) / `performance_schema.data_locks` (8.0) 給 *structured* lock 視圖。

## 5 個 Production 踩雷

### 1. Gap lock 阻塞 INSERT — 「Lock 不存在的 row」

```sql
-- Transaction 1
BEGIN;
SELECT * FROM orders WHERE user_id = 100 FOR UPDATE;
-- 假設 user_id=100 沒任何 order、預期沒 lock 任何 row

-- Transaction 2
INSERT INTO orders (user_id, amount) VALUES (100, 50);
-- 等！為什麼？
```

問題：`WHERE user_id = 100` *沒有 record* 時、InnoDB 仍 lock *user_id=100 應該在的 gap*（防 phantom）、Transaction 2 INSERT 進這個 gap 被阻擋。

修法：

- 改 READ COMMITTED isolation
- 或不用 `SELECT ... FOR UPDATE` on empty result、改 *application 層 check + INSERT* pattern
- 用 `INSERT ... ON DUPLICATE KEY UPDATE` 或 `INSERT IGNORE` 避免 SELECT FOR UPDATE

### 2. Auto-Inc Lock Contention — 大量並行 INSERT

`innodb_autoinc_lock_mode=0` 或 `=1` 模式下、大量並行 INSERT 撞 auto-inc lock、寫吞吐 cap。

修法：

- 設 `innodb_autoinc_lock_mode=2`（interleaved、8.0+ 預設（5.7 預設仍是 1））
- 確認 `binlog_format=ROW`（mode=2 必須）
- 接受 auto-inc value 不連續（id 可能跳號）

### 3. FK Lock Cascading — 父子 transaction 互鎖

```sql
-- orders 表有 customer_id FK → customers.id
-- Transaction 1
UPDATE customers SET name = '...' WHERE id = 100;  -- lock customers row

-- Transaction 2
INSERT INTO orders (customer_id, amount) VALUES (100, 50);
-- FK check 需要 lock customers row id=100、等 Transaction 1
```

FK 強制 *每個 INSERT child 都要 shared lock parent*、parent 的任何 UPDATE 都會 lock 所有 child INSERT。

修法：

- 評估 FK 是否真的需要（high-write 場景考慮 application-level enforcement）
- 短 transaction 縮短 lock 時間
- FK 設計時讓 *parent UPDATE 少* / *child INSERT 多*（parent 是穩定資料）

### 4. Large Transaction Lock Holding — 1 個 transaction 拖全 cluster

```sql
BEGIN;
-- 100K row 的 batch UPDATE
UPDATE orders SET status = 'archived' WHERE created_at < '2024-01-01';
-- 跑 5 分鐘、持 100K row 的 lock
-- 其他 transaction 撞到任何被 lock 的 row 都等 5 分鐘
COMMIT;
```

長 transaction 是 *lock contention 災難*。

修法：

- 把 batch operation *拆 chunk*（每 chunk 1000 row、commit、繼續）：

    ```sql
    DO {
      START TRANSACTION;
      UPDATE orders SET status = 'archived'
      WHERE created_at < '2024-01-01' AND status != 'archived'
      LIMIT 1000;
      COMMIT;
    } WHILE rows_affected > 0;
    ```

- 用 *pt-archiver* tool（Percona）對 batch UPDATE / DELETE 自動 chunked
- 監控 `information_schema.innodb_trx` 找出 long-running transaction

### 5. READ COMMITTED + Binlog ROW Interaction

READ COMMITTED isolation 改善 deadlock、但對 *binlog format* 有要求：

- `binlog_format=STATEMENT`：READ COMMITTED 下 transaction 看到不同 snapshot、replicate 後 replica 結果可能 *不同於 primary*（broken replication semantically）
- `binlog_format=ROW`：每個 row event 都 explicit、READ COMMITTED 跟 ROW 兼容、replica 結果一致
- `binlog_format=MIXED`：部分 case 仍可能 fall back STATEMENT、不推薦

修法：

- 用 READ COMMITTED 時、強制 `binlog_format=ROW`
- 全 cluster server（primary + replica + Group Replication members）統一 binlog_format
- Migration 5.7 STATEMENT → 8.0 ROW 時、isolation 跟 binlog format 一起 review

## 跟其他模組整合

### 跟 Replication

`binlog_format=ROW` 跟 isolation level 互動已述。Replica apply ROW binlog 時、replica 上 *也 acquire 同樣 lock*、replica 上的 long query 跟 replication lag 互動。詳見 [Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)。

### 跟 Group Replication

GR certification phase 跟 row lock 衝突 — write conflict 檢測在 certification、不是 lock。但 *local row lock* 仍存在、影響 single-instance write throughput。詳見 [Group Replication](/backend/01-database/vendors/mysql/group-replication/)。

### 跟 Online Schema Change

gh-ost / pt-osc 在 cut-over 階段需要 metadata lock、跟 long-running transaction 衝突。Lock contention deep dive 跟 OSC cut-over 議題密切。詳見 [Online Schema Change Tools](/backend/01-database/vendors/mysql/online-schema-change-tools/)。

### 跟 Query Optimization

Slow query 持 lock 久、放大 contention。`EXPLAIN ANALYZE` 看實際執行時間、跟 lock holding time 直接相關。詳見 [Query Optimization](/backend/01-database/vendors/mysql/query-optimization/)。

### 跟 InnoDB Tuning

`innodb_lock_wait_timeout=50`（預設 50 秒）— lock wait 超時 transaction 自動 rollback、避免無限等。production 建議調短（10-20 秒）、快 fail 給 application retry。詳見 [InnoDB Tuning](/backend/01-database/vendors/mysql/innodb-tuning/)。

## 跟 PostgreSQL Lock model 對比

| 維度               | MySQL InnoDB                       | PostgreSQL                                      |
| ------------------ | ---------------------------------- | ----------------------------------------------- |
| Concurrency model  | Lock-based（rec / gap / next-key） | MVCC-heavy（few explicit lock）                 |
| 預設 isolation     | REPEATABLE READ                    | READ COMMITTED                                  |
| Gap lock           | 有                                 | 無對應（PG 用 predicate lock for SERIALIZABLE） |
| Deadlock 機率      | 中-高                              | 低                                              |
| Auto-inc           | 內建 + auto-inc lock               | SEQUENCE（無對應 lock 議題）                    |
| Snapshot isolation | 部分（RR 內）                      | 完整（MVCC 跑全 stack）                         |

PG 用 MVCC 跑大部分並行 control、少數 case 才用 explicit lock、整體 deadlock 機率低。MySQL 用 lock-based + MVCC mixed、production 必須懂 lock pattern。

## 觀測 metric

Production 持續 monitor：

- `Innodb_row_lock_waits` / `_time` → lock wait 累計
- `Innodb_deadlocks` → deadlock 次數（5.7+ 有、之前要 parse SHOW ENGINE）
- `performance_schema.data_lock_waits` → 即時 lock wait 視圖（8.0+）
- `information_schema.innodb_trx` → long-running transaction
- `slow_query_log` → 看 query 是否花太多 time 在 lock wait

對 deadlock：把 `innodb_print_all_deadlocks=ON`、所有 deadlock 寫 error log、不用 `SHOW ENGINE` 才看到。

## 何時改 isolation level

| 場景                                    | 建議 isolation                                        |
| --------------------------------------- | ----------------------------------------------------- |
| 典型 web OLTP、低-中寫吞吐              | REPEATABLE READ（預設）                               |
| 高寫吞吐、deadlock 頻繁                 | READ COMMITTED                                        |
| 金融 transaction、需要 strict isolation | REPEATABLE READ + 仔細 review                         |
| 嚴格 serializable（小 case）            | SERIALIZABLE（performance penalty）                   |
| 跨 region replication + 強一致          | 用 Group Replication / Spanner 而不是 isolation level |

## 相關連結

- [MySQL vendor overview](/backend/01-database/vendors/mysql/)
- [MySQL Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)（binlog format + isolation 互動）
- [MySQL Query Optimization](/backend/01-database/vendors/mysql/query-optimization/)（slow query → lock contention）
- [MySQL InnoDB Tuning](/backend/01-database/vendors/mysql/innodb-tuning/)（lock_wait_timeout）
- [MySQL Group Replication](/backend/01-database/vendors/mysql/group-replication/)（cert vs lock）
- [MySQL Online Schema Change](/backend/01-database/vendors/mysql/online-schema-change-tools/)（metadata lock）
- [PostgreSQL MVCC + Lock Model](/backend/01-database/vendors/postgresql/mvcc-lock-model/)（PG sibling、為什麼 PG 比 MySQL 少 deadlock — pure MVCC vs MVCC + gap lock）
- [PostgreSQL vendor page](/backend/01-database/vendors/postgresql/)（MVCC vs lock model）
- [Isolation Level 卡片](/backend/knowledge-cards/isolation-level/)
- 官方：[InnoDB Locking](https://dev.mysql.com/doc/refman/8.0/en/innodb-locking.html)
