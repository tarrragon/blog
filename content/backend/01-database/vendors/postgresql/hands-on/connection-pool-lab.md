---
title: "PostgreSQL Connection Pool Lab"
date: 2026-05-22
description: "PostgreSQL application pool、PgBouncer、backend connection、pool exhaustion 與 failover reconnect 的操作說明"
tags: ["backend", "database", "postgresql", "hands-on", "connection-pool"]
---

PostgreSQL connection pool lab 的核心責任是讓讀者看到 connection pressure 如何從 application pool 傳到 PostgreSQL backend process。這篇承接 [Connection Scaling](../../connection-scaling/) 與 [PgBouncer Config](../../pgbouncer-config/)。

本文的驗收標準是：你能比較 direct connection 與 PgBouncer transaction pooling，取得 `pg_stat_activity`、PgBouncer `SHOW POOLS`、latency / error sample 與 failure note。

## Baseline Direct Connections

Baseline direct connections 的核心責任是先看 application 直連 PostgreSQL 時的 backend 數。

```bash
export DATABASE_URL="postgres://lab_admin:lab_admin_pw@localhost:54329/appdb?sslmode=disable"
psql "$DATABASE_URL" -c "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();"
```

用多個 terminal 或簡單 workload 產生 idle connection：

```bash
for i in 1 2 3 4 5; do
  psql "$DATABASE_URL" -c "SELECT pg_sleep(10);" &
done
psql "$DATABASE_URL" -c "SELECT state, count(*) FROM pg_stat_activity WHERE datname = current_database() GROUP BY state;"
```

這一步證明每個 client session 會占用 PostgreSQL backend process。

## Add PgBouncer

Add PgBouncer 的核心責任是把 client connection 與 server connection 拆開。以下 compose fragment 可加入 local lab：

```yaml
  pgbouncer:
    image: edoburu/pgbouncer:latest
    environment:
      DB_HOST: postgres
      DB_USER: lab_admin
      DB_PASSWORD: lab_admin_pw
      DB_NAME: appdb
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 100
      DEFAULT_POOL_SIZE: 5
    ports:
      - "64329:5432"
```

啟動後設定 pooler URL：

```bash
export POOL_URL="postgres://lab_admin:lab_admin_pw@localhost:64329/appdb?sslmode=disable"
```

## Compare Pool Behavior

Compare pool behavior 的核心責任是觀察 client 多、server 少的效果。

```bash
for i in $(seq 1 20); do
  psql "$POOL_URL" -c "SELECT pg_sleep(1);" &
done
psql "$DATABASE_URL" -c "SELECT state, count(*) FROM pg_stat_activity WHERE datname = current_database() GROUP BY state;"
```

再進 PgBouncer admin console，實際命令依 image 設定調整：

```bash
psql "postgres://lab_admin:lab_admin_pw@localhost:64329/pgbouncer?sslmode=disable" -c "SHOW POOLS;"
```

驗收重點是：client workload 增加時，PostgreSQL backend 數量被 pool size 控制，排隊發生在 pooler 層。

## Pool Exhaustion

Pool exhaustion 的核心責任是看過載時的錯誤與等待。

```bash
for i in $(seq 1 50); do
  psql "$POOL_URL" -c "BEGIN; SELECT pg_sleep(5); COMMIT;" &
done
```

觀察：

```bash
psql "$DATABASE_URL" -c "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();"
psql "postgres://lab_admin:lab_admin_pw@localhost:64329/pgbouncer?sslmode=disable" -c "SHOW POOLS;"
```

Pool exhaustion 的 evidence 包含 waiting clients、timeout、application latency 與 error message。這些要接到 production alert。

## Failure Note

Failure note 的核心責任是把 lab 結果轉成 runbook。記錄三件事：

1. Direct connection baseline backend 數。
2. PgBouncer transaction pooling 下 server connection 數。
3. Pool exhaustion 時的 latency / error / queue。

若 application 使用 session state、prepared statement、temp table 或 advisory lock，還要補 transaction pooling compatibility matrix。

## 下一步路由

完成本篇後，回到 [Connection Pooler Comparison](../../connection-pooler-comparison/) 做選型；要看 PgBouncer production 設定讀 [PgBouncer Config](../../pgbouncer-config/)。
