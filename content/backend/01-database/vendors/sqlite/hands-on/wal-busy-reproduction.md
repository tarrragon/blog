---
title: "SQLite WAL Busy Reproduction"
date: 2026-05-21
description: "SQLite long transaction、SQLITE_BUSY、busy_timeout、checkpoint growth 與 writer queue 的操作說明"
tags: ["backend", "database", "sqlite", "hands-on", "wal"]
---

SQLite WAL busy reproduction 的核心責任是讓讀者親眼看到 single writer boundary。這篇承接 [WAL concurrency / locking](/backend/01-database/vendors/sqlite/wal-concurrency-locking/)，把 `SQLITE_BUSY` 從文字警告轉成可重現 timeline。

本文的驗收標準是：你能用兩個 sqlite3 session 重現 writer contention，觀察 busy timeout 行為，並用 WAL size 與 checkpoint result 連回 production runbook。

## Prepare Database

Prepare database 的核心責任是建立可重現的 WAL mode database。若已跑過 [local file quickstart](/backend/01-database/vendors/sqlite/hands-on/local-file-quickstart/)，可以沿用 `/tmp/sqlite-lab/app.db`。

```bash
cd /tmp/sqlite-lab
sqlite3 app.db "PRAGMA journal_mode = WAL;"
sqlite3 app.db "PRAGMA busy_timeout = 1000;"
```

確認 WAL mode：

```bash
sqlite3 app.db "PRAGMA journal_mode;"
```

預期輸出是 `wal`。

## Session A: Hold Writer Lock

Session A 的核心責任是刻意持有 write transaction。開第一個 terminal，執行：

```bash
sqlite3 app.db
```

在 sqlite prompt 內輸入：

```sql
PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;
INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key, created_at)
VALUES (1, 11, 'busy-session-a', '2026-05-21T02:00:00Z');
```

先保持 transaction 開啟，暫時延後 `COMMIT`。`BEGIN IMMEDIATE` 會取得 writer lock，讓第二個 writer 需要等待或失敗。

## Session B: Observe Busy

Session B 的核心責任是用第二個 connection 觀察 single writer boundary。開第二個 terminal，執行：

```bash
cd /tmp/sqlite-lab
sqlite3 app.db "PRAGMA busy_timeout = 1000; INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key, created_at) VALUES (1, 22, 'busy-session-b', '2026-05-21T02:01:00Z');"
```

預期結果是等待約 1 秒後出現 busy / locked 類錯誤。不同 sqlite3 版本的錯誤文字可能略有差異，核心訊號是第二個 writer 在 Session A commit 前拿不到 write lock。

## Release Lock

Release lock 的核心責任是確認 contention 來自 writer transaction。回到 Session A，輸入：

```sql
COMMIT;
.quit
```

再次執行 Session B 的 insert，這次應成功。

```bash
sqlite3 app.db "PRAGMA foreign_keys = ON; INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key, created_at) VALUES (1, 22, 'busy-session-b', '2026-05-21T02:01:00Z');"
```

若 idempotency key 已在前一次嘗試中寫入，改成新的 key。這個細節也提醒 production write 要有 idempotency 設計。

## Busy Timeout Comparison

Busy timeout comparison 的核心責任是區分「等一下」和「解決 writer contention」。Timeout 可以讓短暫鎖等待更平滑，但長交易仍會造成延遲或失敗。

重開 Session A 並持有 transaction：

```sql
BEGIN IMMEDIATE;
INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key, created_at)
VALUES (1, 33, 'busy-session-a-long', '2026-05-21T02:10:00Z');
```

在 Session B 測不同 timeout：

```bash
time sqlite3 app.db "PRAGMA busy_timeout = 5000; INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key, created_at) VALUES (1, 44, 'busy-session-b-long', '2026-05-21T02:11:00Z');"
```

若 Session A 在 5 秒內 commit，Session B 可能成功；若持續持有 transaction，Session B 會在 timeout 後失敗。這就是 production 裡 busy timeout 的邊界：它緩衝短鎖，長 transaction 仍要被設計移除。

## WAL and Checkpoint

WAL and checkpoint 的核心責任是把 writer activity 和 file artifact 連起來。多做幾次寫入後觀察 sidecar。

```bash
ls -lh app.db app.db-wal app.db-shm
sqlite3 app.db "PRAGMA wal_checkpoint(PASSIVE);"
```

`wal_checkpoint` 會回傳 checkpoint 狀態。正式 runbook 要記錄 WAL size、checkpoint duration、reader age 與 checkpoint failure。

可以手動觸發 truncate checkpoint：

```bash
sqlite3 app.db "PRAGMA wal_checkpoint(TRUNCATE);"
ls -lh app.db app.db-wal app.db-shm
```

TRUNCATE 適合 lab 觀察。Production 使用時要評估 reader、latency 與維護窗口。

## Mitigation Note

Mitigation note 的核心責任是把 lab 結果轉成設計策略。看到 `SQLITE_BUSY` 後，優先檢查 long transaction、未關閉 cursor、背景 job、write burst、parallel test 共用 DB 與 checkpoint pressure。

常見策略包含：

1. 縮短 transaction，將外部 API call 移到 transaction 外。
2. 設定合理 busy timeout 與 retry backoff。
3. 把 write queue 序列化，讓高風險 workflow 先排隊。
4. 將 heavy read 移到 snapshot 或 replica。
5. 當 concurrent writer 成為常態，評估 PostgreSQL / MySQL。

完成本篇後，下一步讀 [observability / runbook](/backend/01-database/vendors/sqlite/observability-runbook/) 把 busy、WAL 與 checkpoint 變成正式監控訊號。
