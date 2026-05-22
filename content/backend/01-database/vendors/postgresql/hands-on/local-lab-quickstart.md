---
title: "PostgreSQL Local Lab Quickstart"
date: 2026-05-22
description: "PostgreSQL local lab 的 Docker Compose、schema seed、sample workload、basic metric 與 teardown"
tags: ["backend", "database", "postgresql", "hands-on"]
---

PostgreSQL local lab quickstart 的核心責任是建立後續 connection、migration、backup 與 failover 演練共用的本地環境。這個 lab 提供一個可重建的 PostgreSQL instance、app-facing user、baseline schema、seed data 與 basic evidence。

本文的驗收標準是：你能啟動本地 PostgreSQL，套用 schema，跑 sample workload，取得 `pg_stat_activity` / `pg_stat_database` snapshot，最後 teardown 並重建。

## Docker Compose

Docker Compose 的核心責任是讓 lab 環境可重建。建立 `docker-compose.yml`：

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: lab_admin
      POSTGRES_PASSWORD: lab_admin_pw
      POSTGRES_DB: appdb
    ports:
      - "54329:5432"
    command:
      - "postgres"
      - "-c"
      - "log_min_duration_statement=100"
      - "-c"
      - "shared_preload_libraries=pg_stat_statements"
```

啟動：

```bash
docker compose up -d
export DATABASE_URL="postgres://lab_admin:lab_admin_pw@localhost:54329/appdb?sslmode=disable"
```

## Baseline Schema

Baseline schema 的核心責任是建立可測 transaction、index、lock 與 migration 的資料模型。

```bash
psql "$DATABASE_URL" <<'SQL'
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

CREATE TABLE accounts (
  id bigserial PRIMARY KEY,
  tenant_id uuid NOT NULL,
  owner_name text NOT NULL,
  status text NOT NULL CHECK (status IN ('active', 'closed')),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ledger_entries (
  id bigserial PRIMARY KEY,
  account_id bigint NOT NULL REFERENCES accounts(id),
  amount_cents bigint NOT NULL CHECK (amount_cents <> 0),
  idempotency_key text NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_ledger_entries_account_created
ON ledger_entries(account_id, created_at DESC);
SQL
```

這組 schema 後續可用於 migration、lock、PITR 與 pool lab。

## Seed and Workload

Seed and workload 的核心責任是產生可觀察的資料與查詢。

```bash
psql "$DATABASE_URL" <<'SQL'
INSERT INTO accounts(tenant_id, owner_name, status)
VALUES
  ('00000000-0000-0000-0000-000000000001', 'Ada', 'active'),
  ('00000000-0000-0000-0000-000000000002', 'Lin', 'active');

INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key)
SELECT 1, 100, 'seed-ada-' || g
FROM generate_series(1, 100) AS g;

SELECT a.owner_name, SUM(l.amount_cents) AS balance_cents
FROM accounts a
JOIN ledger_entries l ON l.account_id = a.id
GROUP BY a.owner_name;
SQL
```

Sample workload 要保留 SQL 與輸出，作為後續 migration / restore validation 的 baseline。

## Basic Evidence

Basic evidence 的核心責任是把 lab 狀態保存成可比較 snapshot。

```bash
psql "$DATABASE_URL" <<'SQL'
SELECT current_database(), current_user, version();
SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY relname;
SELECT datname, numbackends, xact_commit, xact_rollback
FROM pg_stat_database
WHERE datname = current_database();
SELECT pid, state, wait_event_type, query
FROM pg_stat_activity
WHERE datname = current_database();
SQL
```

這些查詢是 PostgreSQL lab 的最小 evidence。正式服務要再加入 slow query、lock wait、replica lag、backup status 與 pooler metrics。

## Teardown

Teardown 的核心責任是讓 lab 可重跑。

```bash
docker compose down -v
```

重建後應能重新套用 schema 與 seed。若 lab 需要跨章節沿用資料，先用 `pg_dump` 保存 fixture，再 teardown。

## 下一步路由

完成本篇後，連線壓力進入 [Connection Pool Lab](../connection-pool-lab/)；migration evidence 進入 [Schema Migration Evidence Lab](../schema-migration-evidence-lab/)；backup / PITR 進入 [PITR Restore Drill](../pitr-restore-drill/)。
