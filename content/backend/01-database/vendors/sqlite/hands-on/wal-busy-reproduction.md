---
title: "SQLite WAL Busy Reproduction"
date: 2026-05-21
description: "SQLite long transaction、SQLITE_BUSY、busy_timeout、checkpoint growth 與 writer queue 的操作說明"
tags: ["backend", "database", "sqlite", "hands-on", "wal"]
---

SQLite WAL busy reproduction 的核心責任是讓讀者親眼看到 single writer boundary。這篇承接 [WAL concurrency / locking](/backend/01-database/vendors/sqlite/wal-concurrency-locking/)，把 `SQLITE_BUSY` 從文字警告轉成可重現 timeline。

本文用兩個 sqlite3 session 重現 writer contention、比較不同 busy timeout 下的等待與失敗，並觀察 WAL size 與 checkpoint result，把它們連回 production runbook；範圍從 local file quickstart 建好的 `/tmp/sqlite-lab/app.db` 開始。

## Prepare Database

Prepare database 的核心責任是建立可重現的 WAL mode database。本篇的 insert 寫進 `ledger_entries`，而這張表與它參照的 `accounts` 由 [local file quickstart](/backend/01-database/vendors/sqlite/hands-on/local-file-quickstart/) 建立在 `/tmp/sqlite-lab/app.db`；還沒跑過那一篇，先跑完它的 Lab Directory、Baseline Schema 與 Seed Data 三節。

```bash
cd /tmp/sqlite-lab
sqlite3 app.db "PRAGMA journal_mode = WAL;"
# journal_mode 寫進資料庫檔案，之後每個 connection 都是 WAL。
# busy_timeout 則只屬於設定它的那個 connection，所以不在這裡設，
# 而是寫在後面每一條會撞上鎖的 sqlite3 指令裡。
```

確認 WAL mode：

```bash
sqlite3 app.db "PRAGMA journal_mode;"
```

預期輸出是 `wal`。

## 持鎖 session：刻意持有 writer lock

持鎖 session 的核心責任是刻意持有 write transaction，讓另一個 connection 的寫入撞上 single writer boundary。開一個 terminal，執行：

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

先保持 transaction 開啟，暫時延後 `COMMIT`。`BEGIN IMMEDIATE` 會取得 writer lock，讓其他 connection 的寫入需要等待或失敗。

## 等鎖 session：觀察 busy

等鎖 session 的核心責任是在持鎖 session 還沒 commit 時，用另一個 connection 寫入，觀察 single writer boundary。另開一個 terminal，執行：

```bash
cd /tmp/sqlite-lab
sqlite3 app.db "PRAGMA busy_timeout = 1000; INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key, created_at) VALUES (1, 22, 'busy-session-b', '2026-05-21T02:01:00Z');"
```

預期結果是等待約 1 秒（`busy_timeout = 1000` 的單位是毫秒）後失敗，sqlite3 3.51.0 印出 `Error: stepping, database is locked (5)`、exit code 為 5。錯誤文字隨 sqlite3 版本略有差異，要讀的是括號裡的 result code 5，也就是 `SQLITE_BUSY`：等鎖 session 在持鎖 session commit 前拿不到 write lock。

## Release Lock

Release lock 的核心責任是確認 contention 來自 writer transaction。回到持鎖 session，輸入：

```sql
COMMIT;
.quit
```

在等鎖 session 的 terminal 再送一次同一筆 insert，這次應成功（exit code 0）。

```bash
sqlite3 app.db "PRAGMA foreign_keys = ON; INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key, created_at) VALUES (1, 22, 'busy-session-b', '2026-05-21T02:01:00Z');"
```

前一次嘗試因為 busy 失敗，`busy-session-b` 沒有寫進資料庫，所以同一個 key 可以原樣重送；這一筆成功之後再送一次，`idempotency_key` 的 `UNIQUE` 約束會擋下它（`UNIQUE constraint failed: ledger_entries.idempotency_key`）。production write 要有 idempotency 設計的理由就在這裡：因 busy 失敗的寫入可以用同一個 key 安全重送，已經成功的不會被寫第二次。

## Busy Timeout Comparison

Busy timeout comparison 的核心責任是區分「等一下」和「解決 writer contention」。Timeout 可以讓短暫鎖等待更平滑，但長交易仍會造成延遲或失敗。

重開持鎖 session 並持有 transaction：

```sql
BEGIN IMMEDIATE;
INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key, created_at)
VALUES (1, 33, 'busy-session-a-long', '2026-05-21T02:10:00Z');
```

在等鎖 session 把 timeout 拉長到 5000 ms 再寫一次：

```bash
time sqlite3 app.db "PRAGMA busy_timeout = 5000; INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key, created_at) VALUES (1, 44, 'busy-session-b-long', '2026-05-21T02:11:00Z');"
```

若持鎖 session 在 5 秒內 commit，等鎖 session 的 insert 會在那次 commit 之後成功；若持鎖 session 一直不 commit，等鎖 session 會在約 5 秒後以同樣的 `database is locked (5)` 失敗。這就是 production 裡 busy timeout 的邊界：它緩衝短鎖，長 transaction 仍要被設計移除。

## WAL and Checkpoint

WAL and checkpoint 的核心責任是把 writer activity 和 file artifact 連起來。先回持鎖 session 輸入 `COMMIT;`，但不要 `.quit`，讓這個 connection 保持開著；再從另一個 terminal 多寫幾筆後觀察 sidecar。

```bash
# 持鎖 session 必須保持開著：最後一個 connection 關閉時 SQLite 會做 checkpoint，
# 並移除（或清空）-wal 與 -shm，下面的 ls 就看不到 WAL 成長
for i in 1 2 3 4 5; do
  sqlite3 app.db "INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key, created_at) VALUES (1, $i, 'wal-demo-$i', '2026-05-21T03:00:00Z');"
done
ls -lh app.db app.db-wal app.db-shm
# app.db-wal 不是 0：這幾筆寫入還在 WAL 裡，沒有合併回 app.db

sqlite3 app.db "PRAGMA wal_checkpoint(PASSIVE);"
# 輸出三欄依序是：checkpoint 是否被擋住（0 是沒有，1 是遇到 busy）、
# WAL 裡的 frame 數、已合併回 app.db 的 frame 數；後兩欄相等代表 WAL 已全部合併
```

正式 runbook 要記錄 WAL size、checkpoint duration、reader age 與 checkpoint failure。

可以手動觸發 truncate checkpoint：

```bash
sqlite3 app.db "PRAGMA wal_checkpoint(TRUNCATE);"
# 0|0|0：WAL 內容已全部合併，檔案被截斷
ls -lh app.db app.db-wal app.db-shm
# app.db-wal 變成 0B；持鎖 session 仍開著，所以檔案還在、只是被截斷
```

TRUNCATE 適合 lab 觀察。Production 使用時要評估 reader、latency 與維護窗口。

## Mitigation Note

Mitigation note 的核心責任是把 lab 結果轉成設計策略。看到 `SQLITE_BUSY` 後，優先檢查 long transaction、未關閉的查詢結果的讀取物件（cursor）、背景 job、write burst、parallel test 共用 DB 與 checkpoint pressure。

常見策略包含：

1. 縮短 transaction，將外部 API call 移到 transaction 外。
2. 設定合理 busy timeout 與 retry backoff。
3. 把 write queue 序列化，讓高風險 workflow 先排隊。
4. 將 heavy read 移到 snapshot 或 replica。
5. 當 concurrent writer 成為常態，評估 PostgreSQL / MySQL。

完成本篇後，下一步讀 [observability / runbook](/backend/01-database/vendors/sqlite/observability-runbook/) 把 busy、WAL 與 checkpoint 變成正式監控訊號。
