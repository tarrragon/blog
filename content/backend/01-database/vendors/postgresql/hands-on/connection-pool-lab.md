---
title: "PostgreSQL Connection Pool Lab"
date: 2026-05-22
description: "PostgreSQL application pool、PgBouncer、backend connection、pool exhaustion 與 failover reconnect 的操作說明"
tags: ["backend", "database", "postgresql", "hands-on", "connection-pool"]
---

PostgreSQL connection pool lab 的核心責任是讓讀者看到 connection pressure 如何從 application pool 傳到 PostgreSQL backend process。這篇承接 [Connection Scaling](../../connection-scaling/) 與 [PgBouncer Config](../../pgbouncer-config/)。

本篇的範圍是在 local lab 上比較 application 直連 PostgreSQL 與經過 PgBouncer transaction pooling 時的 backend 數、重現 pool exhaustion 時 client 在 pooler 排隊，並把 `pg_stat_activity` 與 PgBouncer `SHOW POOLS` 的結果寫成 failure note。

## Baseline Direct Connections

Baseline direct connections 的核心責任是先看 application 直連 PostgreSQL 時的 backend 數。

```bash
export DATABASE_URL="postgres://lab_admin:lab_admin_pw@localhost:54329/appdb?sslmode=disable"
psql "$DATABASE_URL" -c "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();"
```

用背景 psql 開五個同時在執行 `pg_sleep(10)` 的 session：

```bash
for i in 1 2 3 4 5; do
  psql "$DATABASE_URL" -c "SELECT pg_sleep(10);" &
done
psql "$DATABASE_URL" -c "SELECT state, count(*) FROM pg_stat_activity WHERE datname = current_database() GROUP BY state;"
# state 是 active 的有 6 個：五個 pg_sleep session，加上這一句查詢自己
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
      # PostgreSQL 16 的密碼以 SCRAM 儲存；image 預設 md5 時 PgBouncer 連 backend 回 wrong password type
      AUTH_TYPE: scram-sha-256
      # admin console（pgbouncer 虛擬 database）只允許這裡列的 user，image 預設只有 postgres
      ADMIN_USERS: lab_admin
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

再進 PgBouncer admin console；compose 裡的 `ADMIN_USERS: lab_admin` 讓 lab_admin 能連 `pgbouncer` 這個虛擬 database：

```bash
psql "postgres://lab_admin:lab_admin_pw@localhost:64329/pgbouncer?sslmode=disable" -c "SHOW POOLS;"
```

驗收重點是：client workload 增加時，PostgreSQL backend 數量被 pool size 控制，排隊發生在 pooler 層。

## Pool Exhaustion

Pool exhaustion 的核心責任是看過載時 client 在 pooler 排隊等待。這組參數下 50 個 client 全部成功，看得到的是 `SHOW POOLS` 的 `cl_waiting` 與 psql 印出的 `No server connection available in postgres backend, client being queued`；錯誤要等 client 在隊伍裡待超過 PgBouncer 的 `query_wait_timeout`（預設 120 秒）才出現。

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
