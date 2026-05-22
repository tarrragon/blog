---
title: "SQLite Migration Fixture Lab"
date: 2026-05-21
description: "SQLite user_version、table rebuild migration、fixture snapshot、rollback note 與 CI evidence 的操作說明"
tags: ["backend", "database", "sqlite", "hands-on", "migration", "fixture"]
---

SQLite migration fixture lab 的核心責任是把 schema migration 與 test fixture 放進同一個可重建流程。這篇承接 [Schema Migration / Versioning](/backend/01-database/vendors/sqlite/schema-migration-versioning/) 與 [Test Fixture Best Practice](/backend/01-database/vendors/sqlite/test-fixture-best-practice/)，讓 migration 有版本、snapshot、validation 與 rollback note。

本文的驗收標準是：你能建立 v1 fixture、套用 v2 migration、產生 v2 snapshot，並用 validation query 證明資料合約仍成立。

## Create Fixture

Create fixture 的核心責任是建立乾淨、可重建的 source fixture。沿用 quickstart schema，或重新建立一份 fixture DB。

```bash
mkdir -p /tmp/sqlite-fixture-lab
cd /tmp/sqlite-fixture-lab
rm -f fixture-v1.db fixture-v2.db
sqlite3 fixture-v1.db <<'SQL'
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

INSERT INTO accounts VALUES (1, 'Ada', 'active', '2026-05-21T00:00:00Z');
INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key, created_at)
VALUES (1, 1000, 'fixture-v1-ada', '2026-05-21T00:10:00Z');
SQL
```

這個 fixture 是 v1 source of truth。CI 可以每次從 SQL 重建，也可以保存 `fixture-v1.db` 作為 binary fixture；兩者都要有版本與 checksum。

## Pre-Migration Snapshot

Pre-migration snapshot 的核心責任是建立 rollback 起點。正式 migration 前應先保存 source DB。

```bash
sqlite3 fixture-v1.db ".backup 'fixture-v1-before-migration.db'"
sqlite3 fixture-v1-before-migration.db "PRAGMA integrity_check;"
```

這份 snapshot 代表 migration 失敗時的回退點。CI log 要保留 snapshot path、schema version 與 migration id。

## Apply Add Column Migration

Apply add column migration 的核心責任是展示低風險 schema change。先複製 v1，再套用 v2。

```bash
cp fixture-v1.db fixture-v2.db
sqlite3 fixture-v2.db <<'SQL'
PRAGMA foreign_keys = ON;
BEGIN;
ALTER TABLE accounts ADD COLUMN email TEXT;
PRAGMA user_version = 2;
COMMIT;
SQL
```

驗證 schema version 與新欄位：

```bash
sqlite3 fixture-v2.db <<'SQL'
PRAGMA user_version;
PRAGMA table_info(accounts);
SQL
```

Add column 是較簡單的 migration。涉及 drop column、rename、constraint 重建或資料 reshape 時，應改用 table rebuild 策略。

## Table Rebuild Example

Table rebuild 的核心責任是展示 SQLite schema migration 的高風險路徑。以下範例把 `accounts.status` 的 allowed value 加入 `suspended`，透過新表重建 constraint。

```bash
sqlite3 fixture-v2.db <<'SQL'
PRAGMA foreign_keys = OFF;
BEGIN;

CREATE TABLE accounts_new (
  id INTEGER PRIMARY KEY,
  owner_name TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'closed', 'suspended')),
  created_at TEXT NOT NULL,
  email TEXT
) STRICT;

INSERT INTO accounts_new(id, owner_name, status, created_at, email)
SELECT id, owner_name, status, created_at, email
FROM accounts;

DROP TABLE accounts;
ALTER TABLE accounts_new RENAME TO accounts;

PRAGMA user_version = 3;
COMMIT;
PRAGMA foreign_keys = ON;
SQL
```

Table rebuild 要保存 index、trigger、view 與 FK reference。這個 lab 只有小型 schema；正式 migration 要先列出所有 dependent object。

## Validation Query

Validation query 的核心責任是證明 migration 後資料仍符合 domain invariant。

```bash
sqlite3 fixture-v2.db <<'SQL'
PRAGMA integrity_check;
PRAGMA foreign_key_check;
SELECT COUNT(*) AS account_count FROM accounts;
SELECT COUNT(*) AS ledger_count FROM ledger_entries;
SELECT SUM(amount_cents) AS total_balance FROM ledger_entries;
PRAGMA user_version;
SQL
```

驗收結果應包含 integrity `ok`、foreign key check 空結果、account count `1`、ledger count `1`、total balance `1000`、user version `3`。

## Contract Test Hook

Contract test hook 的核心責任是讓 fixture 進入 CI。語言與 framework 可以不同，但測試要固定做三件事：開啟 FK、確認 schema version、跑 repository contract。

```text
test setup:
  copy fixture-v2.db to temp path
  open SQLite connection
  execute PRAGMA foreign_keys = ON
  assert PRAGMA user_version = 3
  run repository contract tests
```

每個 test 使用 temp copy 可以避免資料污染。需要測 concurrency 時，改用 [WAL busy reproduction](/backend/01-database/vendors/sqlite/hands-on/wal-busy-reproduction/)。

## Rollback Note

Rollback note 的核心責任是把 migration 失敗時的處理寫清楚。這個 lab 的 rollback 是保留 `fixture-v1-before-migration.db`，在 migration validation 失敗時停止 release 並保存 failed DB。

正式 runbook 要記錄：

1. Migration id 與 source / target `user_version`。
2. Pre-migration backup path。
3. Validation query 與結果。
4. Failed DB 保存路徑。
5. Release block / rollback 條件。

完成本篇後，下一步可以讀 [SQLite to PostgreSQL migration](/backend/01-database/vendors/sqlite/migrate-to-postgresql/) 或 [SQLite to D1 / Turso migration](/backend/01-database/vendors/sqlite/migrate-to-d1-turso/)。
