---
title: "PostgreSQL Schema Migration Evidence Lab"
date: 2026-05-22
description: "PostgreSQL expand / contract migration、validation query、rollback condition 與 release gate evidence 的操作說明"
tags: ["backend", "database", "postgresql", "hands-on", "migration"]
---

PostgreSQL schema migration evidence lab 的核心責任是把 schema change 轉成 release gate 可使用的 evidence。這篇承接 [Online Schema Change](../../online-schema-change/) 與 [Database Migration Playbook](/backend/01-database/database-migration-playbook/)。

本文的驗收標準是：你能設計 expand migration、量測 lock、跑 backfill validation、建立 contract migration 的 [fail-forward](/backend/knowledge-cards/fail-forward/) / rollback 判準。

## Expand Migration

Expand migration 的核心責任是先加入向後相容 schema。以下範例新增 `accounts.email`，先允許 null。

```bash
psql "$DATABASE_URL" <<'SQL'
\timing on
BEGIN;
ALTER TABLE accounts ADD COLUMN email text;
COMMIT;
SQL
```

新增 nullable column 通常是低風險操作，但仍要記錄 timing 與 lock。正式服務要在低流量窗口或 staging 上先測。

## Lock Evidence

Lock evidence 的核心責任是讓 migration 的阻塞風險可見。開另一個 terminal，在 migration 前後查 lock。

```bash
psql "$DATABASE_URL" <<'SQL'
SELECT locktype, relation::regclass, mode, granted, pid
FROM pg_locks
WHERE relation IN ('accounts'::regclass, 'ledger_entries'::regclass)
ORDER BY granted, mode;
SQL
```

Release gate 要保存 lock mode、duration、blocked session 與 application impact。高風險 DDL 要先改成 expand / backfill / contract。

## Backfill and Validation

Backfill and validation 的核心責任是把資料補齊並證明結果符合 domain。

```bash
psql "$DATABASE_URL" <<'SQL'
UPDATE accounts
SET email = lower(owner_name) || '@example.test'
WHERE email IS NULL;

SELECT count(*) AS missing_email
FROM accounts
WHERE email IS NULL;
SQL
```

大型表要分 batch backfill，避免 WAL、replica lag、autovacuum 與 lock 壓力。每個 batch 要記錄 row count、duration、error 與 lag。

## Add Constraint Safely

Add constraint safely 的核心責任是把資料驗證和 constraint 生效拆開。

```bash
psql "$DATABASE_URL" <<'SQL'
ALTER TABLE accounts
ADD CONSTRAINT accounts_email_present
CHECK (email IS NOT NULL) NOT VALID;

ALTER TABLE accounts
VALIDATE CONSTRAINT accounts_email_present;
SQL
```

`NOT VALID` 讓 constraint 先約束新資料，再用 validation 掃既有資料。這是 PostgreSQL online migration 常用技巧。

## Query Plan Evidence

Query plan evidence 的核心責任是確認 migration 後 query 仍走正確路徑。

```bash
psql "$DATABASE_URL" <<'SQL'
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM accounts
WHERE email = 'ada@example.test';
SQL
```

若 email 查詢成為正式 path，要新增 index，並用 `CREATE INDEX CONCURRENTLY` 評估 lock 與時間。

## Contract Migration

Contract migration 的核心責任是在 application 都改用新欄位後，收斂舊欄位或舊 constraint。Contract migration 要比 expand 更謹慎，因為 rollback 空間更小。

Contract release gate：

1. 所有 app version 已停止讀舊欄位 / 舊行為。
2. Backfill validation 為零缺口。
3. Query plan 與 index evidence 已保存。
4. Rollback path 是 fail-forward 或 restore，兩者擇一寫清楚。
5. PITR / backup window 符合風險。

## Release Gate Note

Release gate note 的核心責任是形成可交付 artifact。

```text
Migration: add accounts.email
Expand DDL duration:
Backfill rows:
Validation query:
Lock evidence:
Query plan:
Rollback / fail-forward:
Owner:
```

完成本篇後，複雜 migration 回到 [Online Schema Change](../../online-schema-change/)；需要跨 DB 遷移則讀 [Database Migration Playbook](/backend/01-database/database-migration-playbook/)。
