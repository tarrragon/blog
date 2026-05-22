---
title: "SQLite Local File Quickstart"
date: 2026-05-21
description: "SQLite local .db file、schema、seed data、PRAGMA baseline、query sample 與 cleanup 的操作說明"
tags: ["backend", "database", "sqlite", "hands-on"]
---

SQLite local file quickstart 的核心責任是建立後續 backup、WAL、migration 與 fixture lab 共用的 database file。這個 lab 把 SQLite 從抽象服務選型轉成可觀察的檔案、schema、PRAGMA、transaction 與 sidecar artifact。

本文的驗收標準是：你能建立一個可重建的 `app.db`，知道它的 schema version、journal mode、foreign key 設定、seed data 與 cleanup 路徑。

## Lab Directory

Lab directory 的核心責任是把 SQLite artifact 放在隔離資料夾，避免和正式檔案混淆。以下命令建立一個可刪除的本地工作區。

```bash
mkdir -p /tmp/sqlite-lab
cd /tmp/sqlite-lab
rm -f app.db app.db-wal app.db-shm
```

驗收 artifact 是 `/tmp/sqlite-lab/app.db`。後續 lab 可以沿用這個路徑，也可以每次從頭建立。

## Baseline Schema

Baseline schema 的核心責任是建立一組能測 transaction、constraint、index 與 query 的小型資料模型。這裡使用 `accounts` 與 `ledger_entries`，因為它們能清楚展示 foreign key 與金額 invariant。

```bash
sqlite3 app.db <<'SQL'
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;

CREATE TABLE accounts (
  id INTEGER PRIMARY KEY,
  owner_name TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'closed')),
  created_at TEXT NOT NULL
) STRICT;

CREATE TABLE ledger_entries (
  id INTEGER PRIMARY KEY,
  account_id INTEGER NOT NULL REFERENCES accounts(id),
  amount_cents INTEGER NOT NULL CHECK (amount_cents != 0),
  idempotency_key TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
) STRICT;

CREATE INDEX idx_ledger_entries_account_created
ON ledger_entries(account_id, created_at);
SQL
```

這段 schema 的重點是明確資料合約。`STRICT`、`CHECK`、`FOREIGN KEY` 與 `UNIQUE` 讓 fixture 更接近正式資料責任，也讓後續 migration lab 有可驗證的 invariant。

## Seed Data

Seed data 的核心責任是建立可重跑的測試資料。每筆 ledger entry 都有 idempotency key，讓後續 edge / retry 設計可以沿用。

```bash
sqlite3 app.db <<'SQL'
PRAGMA foreign_keys = ON;

BEGIN;
INSERT INTO accounts(id, owner_name, status, created_at)
VALUES
  (1, 'Ada', 'active', '2026-05-21T00:00:00Z'),
  (2, 'Lin', 'active', '2026-05-21T00:05:00Z');

INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key, created_at)
VALUES
  (1, 1200, 'seed-ada-credit-1', '2026-05-21T00:10:00Z'),
  (1, -200, 'seed-ada-debit-1', '2026-05-21T00:12:00Z'),
  (2, 900, 'seed-lin-credit-1', '2026-05-21T00:15:00Z');
COMMIT;
SQL
```

Seed 完成後先跑基本查詢。這一步確認 schema、constraint 與 index 入口都可用。

```bash
sqlite3 app.db <<'SQL'
.headers on
.mode column
SELECT a.id, a.owner_name, SUM(l.amount_cents) AS balance_cents
FROM accounts a
JOIN ledger_entries l ON l.account_id = a.id
GROUP BY a.id, a.owner_name
ORDER BY a.id;
SQL
```

預期輸出應顯示 Ada 餘額 `1000`，Lin 餘額 `900`。

## PRAGMA Snapshot

PRAGMA snapshot 的核心責任是把連線設定變成 evidence。SQLite 的部分設定與 connection 有關，因此 lab 要明確查出當前狀態。

```bash
sqlite3 app.db <<'SQL'
.headers on
.mode column
PRAGMA journal_mode;
PRAGMA foreign_keys;
PRAGMA user_version;
PRAGMA integrity_check;
SQL
```

驗收重點如下：

| 欄位           | 期望結果 | 意義                      |
| -------------- | -------- | ------------------------- |
| `journal_mode` | `wal`    | 後續可觀察 `-wal` sidecar |
| `foreign_keys` | `1`      | constraint 在連線上已啟用 |
| `user_version` | `1`      | migration 起點清楚        |
| integrity      | `ok`     | database file 基本健康    |

## Transaction Sample

Transaction sample 的核心責任是建立後續 busy / migration lab 的共同語言。SQLite transaction 成功時要同時更新資料與保護 invariant。

```bash
sqlite3 app.db <<'SQL'
PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;
INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key, created_at)
VALUES (1, 300, 'manual-ada-credit-1', '2026-05-21T00:20:00Z');
COMMIT;
SQL
```

`BEGIN IMMEDIATE` 會提早取得 write lock。這讓後續 [WAL busy reproduction](/backend/01-database/vendors/sqlite/hands-on/wal-busy-reproduction/) 可以直接展示 single writer boundary。

## File Artifact Check

File artifact check 的核心責任是讓讀者看到 SQLite 由 `.db` 與可能存在的 sidecar 共同構成。WAL mode 可能建立 `-wal` 與 `-shm` sidecar，backup / copy / restore runbook 要理解這些檔案。

```bash
ls -lh app.db app.db-wal app.db-shm
```

若 sidecar 暫時未出現，可以再寫入一筆資料或保持連線開啟。Sidecar 是否存在取決於 WAL 狀態、checkpoint 與 connection lifecycle。

## Cleanup

Cleanup 的核心責任是讓 lab 可以重跑。若要重新開始，刪除 database 與 sidecar。

```bash
rm -f /tmp/sqlite-lab/app.db /tmp/sqlite-lab/app.db-wal /tmp/sqlite-lab/app.db-shm
```

完成本篇後，下一步可以進入 [backup restore drill](/backend/01-database/vendors/sqlite/hands-on/backup-restore-drill/) 或 [WAL busy reproduction](/backend/01-database/vendors/sqlite/hands-on/wal-busy-reproduction/)。
