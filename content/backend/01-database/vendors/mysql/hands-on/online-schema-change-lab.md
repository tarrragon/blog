---
title: "MySQL Online Schema Change Lab"
date: 2026-05-22
description: "MySQL ALTER TABLE、metadata lock、gh-ost / pt-osc frame、cutover evidence 與 rollback note"
tags: ["backend", "database", "mysql", "hands-on", "schema-migration"]
---

MySQL online schema change lab 的核心責任是讓讀者看到 schema change 的 metadata lock、algorithm、copy / cutover 與 validation evidence。這篇承接 [Online Schema Change Tools](../../online-schema-change-tools/) 與 [Metadata Lock Deep Dive](../../metadata-lock-deep-dive/)。

本篇的範圍是在 local lab 的 `accounts` 上跑一次直接 `ALTER TABLE`、另開 session 重現 long transaction 讓 DDL 卡在 metadata lock、跑 validation query；gh-ost / pt-osc 只整理 cutover 要留的 evidence，不安裝工具。

## Direct ALTER Baseline

Direct ALTER baseline 的核心責任是先看 MySQL 原生 DDL 的行為。

```bash
mysql -h 127.0.0.1 -P 33069 -u app_user -papp_pw appdb <<'SQL'
ALTER TABLE accounts ADD COLUMN email VARCHAR(255) NULL;
SHOW CREATE TABLE accounts\G
SQL
```

記錄 ALTER duration、algorithm、lock impact 與 table size。不同 MySQL 版本與 DDL 類型會有不同行為，production 要在 staging dry run。

## Metadata Lock Observation

Metadata lock observation 的核心責任是看到 blocker。

這段 lab 開三個 terminal，各自扮演一個角色：持有 transaction 的讀取 session、執行 ALTER 的 DDL session、查 `performance_schema` 的觀察 session。

讀取 session 用 app_user 連線，開 transaction 讀一列之後不 commit：

```sql
-- 讀取 session（app_user）
START TRANSACTION;
SELECT * FROM accounts WHERE id = 1;
-- 讀到之後停在這裡，transaction 保持開啟
```

DDL session 同樣用 app_user 連線執行 ALTER，這一句會停住不回：

```sql
-- DDL session（app_user）
ALTER TABLE accounts ADD COLUMN note VARCHAR(255) NULL;
```

觀察 session 要用 root 連線：`performance_schema.metadata_locks` 需要 SELECT 權限，app_user 只有 `appdb` 的權限，用它查會回 `ERROR 1142`。

```sql
-- 觀察 session（root）
SELECT OBJECT_SCHEMA, OBJECT_NAME, LOCK_TYPE, LOCK_STATUS, OWNER_THREAD_ID
FROM performance_schema.metadata_locks
WHERE OBJECT_SCHEMA = 'appdb';
-- accounts  SHARED_READ  GRANTED：讀取 session 持有
-- accounts  EXCLUSIVE    PENDING：DDL session 在等讀取 session 放掉
```

完成觀察後，在讀取 session 執行 `COMMIT`，DDL session 的 ALTER 隨即完成。這段 lab 展示 long transaction 如何讓 DDL 等待。

## OSC Frame

OSC frame 的核心責任是理解 gh-ost / pt-online-schema-change 的證據，而非要求每個 lab 都安裝工具。

OSC runbook 要記錄：

1. Source table、ghost table、migration statement。
2. Copy progress、chunk size、throttle condition。
3. Replication lag / load threshold。
4. Cutover pre-check：long transaction、metadata lock、traffic。
5. Cutover duration 與 validation query。
6. Rollback / drop ghost table policy。

Cutover 前最重要的是 metadata lock pre-check。工具能降低大部分 copy 風險，但最後 rename / swap 仍需要短暫鎖。

## Validation

Validation 的核心責任是證明 schema change 後資料與 query 仍正確。

```bash
mysql -h 127.0.0.1 -P 33069 -u app_user -papp_pw appdb <<'SQL'
SELECT COUNT(*) FROM accounts;
SELECT COUNT(*) FROM ledger_entries;
EXPLAIN SELECT * FROM accounts WHERE tenant_id = 'tenant-a';
SQL
```

正式 migration 要補 row checksum、null rate、index usage、replication lag 與 application smoke test。

## Release Gate

Release gate 的核心責任是形成交付 artifact。

```text
Migration:
DDL / OSC command:
Table size:
MDL pre-check:
Duration:
Validation:
Rollback:
Owner:
```

完成本篇後，MDL 事故讀 [Metadata Lock Deep Dive](../../metadata-lock-deep-dive/)；工具選型讀 [Online Schema Change Tools](../../online-schema-change-tools/)。
