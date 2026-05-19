---
title: "PostgreSQL pgBouncer 配置 + 連線池治理"
date: 2026-05-18
description: "pgBouncer transaction pooling 配置、跟 application connection pool 的分層、production 故障演練（pool exhaustion / stale connection / DNS failover）跟容量規劃"
weight: 100
tags: ["backend", "database", "postgresql", "connection-pool", "pgbouncer", "deep-article"]
---

PostgreSQL 的 connection 是 *昂貴的 process*、每個 connection ~10MB RAM、idle connection 也吃 backend slot。當 application instance 數量爆炸（K8s replica × 多 deployment × pool size）、直接連 PostgreSQL 會把 backend slot 耗盡、新 connection 全 refuse — 即使 active query 不多。pgBouncer 是 *connection pool proxy*、把幾千個 application connection 收斂成幾百個 PostgreSQL backend connection、production-grade PostgreSQL 部署的標配。

本文不是 pgBouncer overview（請看 [PostgreSQL vendor 頁](/backend/01-database/vendors/postgresql/) 中 connection pool 段）— 而是 *production 部署 + 故障演練* 的實作層教學。覆蓋三層 pool（application → pgBouncer → PostgreSQL）的對齊、transaction pooling 跟 session pooling 的選擇陷阱、跟 HA failover 的整合、容量規劃。

## 問題情境

典型觸發場景：團隊規模從 50 人爬到 200 人、microservice 從 20 個爬到 100 個、K8s replica 從 3 個爬到每服務 5-10 個。直連 PostgreSQL 的 connection 計算：

```text
100 service × 6 replica × 30 application pool = 18000 connection
```

PostgreSQL 預設 `max_connections = 100`、production 設 `max_connections = 500-1000` 已經是上限（每多一個都加 memory + context switch cost）。18000 連線打 PostgreSQL 直接打爆。

進一步問題：

- 一半 connection 是 *idle*（application pool 預留、實際沒查詢）— 浪費 backend slot
- Cold start 時所有 replica 同時建 connection、瞬間 spike
- DB failover 時所有 application 同時 reconnect、prod-test pattern 跑不通
- DNS-based failover 時 application connection pool 不知道 backend 換了

pgBouncer 解這四個問題。但 *引入 pgBouncer* 後又會引入新的問題層（pgBouncer 跟 application pool 不對齊、transaction pooling 的 session state 限制、HA 故障時 pgBouncer 也要 failover）— 本文討論這些。

## 核心概念：pool mode + sizing

pgBouncer 的 first-class concept 是 *pool mode*、決定 application connection 跟 PostgreSQL backend connection 的綁定方式：

- **Session pooling**：application connection 拿到 backend connection 後、整個 session 期間都綁同一個 backend。tear-down 才釋放。語義跟「直連」一樣、不破壞 session state。但 *idle connection 仍占 backend slot*、收斂效率低、適合 *連線數不多但要保留 session state*（用了 prepared statement、temporary table、advisory lock 等）的場景。
- **Transaction pooling**：application connection 在 *transaction 邊界* 才綁 backend、commit / rollback 後立即釋放。同一個 application connection 不同 transaction 可能拿到不同 backend。收斂效率高（idle connection 完全不占 backend slot）、但 *session state 限制嚴* — 不能用 `SET` 改 session-level setting、不能用 prepared statement（除非 application 端禁用）、不能用 advisory lock 跨 transaction。
- **Statement pooling**：每個 statement 完就釋放 backend。極端高收斂但 *連 transaction 都不能跨 statement*、絕大多數 application 用不了、只在 batch query 場景。

**Production 預設選 transaction pooling**、application 端禁用 prepared statement（或用 [PgBouncer-supported prepared statement](https://www.pgbouncer.org/config.html#max_prepared_statements)、需 pgBouncer 1.21+）。例外場景才開 session pooling。

**Pool sizing 公式**：

```text
PostgreSQL max_connections     = pgBouncer N × default_pool_size + reserve
pgBouncer default_pool_size    = per-database backend connection 上限
Application pool size          = 每 application instance 拿幾個 pgBouncer connection
```

實例：50 個 application replica、每 instance pool 30 個、pgBouncer 後 default_pool_size = 20（per database）、3 個 database。

```text
Total application → pgBouncer = 50 × 30 = 1500 connection
pgBouncer → PostgreSQL        = 3 × 20 = 60 connection
PostgreSQL max_connections    = 60 + reserve (50 預留 admin / migration) = 110
```

1500 → 110 收斂 13.6 倍、PostgreSQL 還在合理上限內。

## Step-by-step 配置

**pgBouncer.ini**：

```ini
[databases]
mydb = host=postgres-primary.internal port=5432 dbname=mydb auth_user=pgbouncer

[pgbouncer]
listen_port = 6432
listen_addr = 0.0.0.0
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
auth_query = SELECT usename, passwd FROM pg_shadow WHERE usename=$1

pool_mode = transaction
default_pool_size = 20
min_pool_size = 5
reserve_pool_size = 10
reserve_pool_timeout = 5

max_client_conn = 2000
max_db_connections = 100

server_idle_timeout = 600
server_lifetime = 3600
server_connect_timeout = 15
server_login_retry = 5

client_idle_timeout = 0
client_login_timeout = 60

stats_period = 60
log_connections = 0
log_disconnections = 0
log_pooler_errors = 1

admin_users = pgbouncer_admin
stats_users = pgbouncer_stats
```

關鍵欄位解釋：

- `pool_mode = transaction`：絕大多數 production 場景
- `default_pool_size = 20`：每 database 對 PostgreSQL 的 backend connection 上限、調整時要算進 PostgreSQL `max_connections`
- `reserve_pool_size = 10` + `reserve_pool_timeout = 5`：當 default_pool_size 用滿、等 5 秒還拿不到 connection 才用 reserve pool — 是 *突發 spike* 的 buffer、不是 baseline
- `max_client_conn = 2000`：application 端能連 pgBouncer 的最大數
- `server_lifetime = 3600`：每 1 小時強制 recycle backend connection、避免 long-lived connection 累積 memory bloat（PostgreSQL `pg_stat_activity` 看 connection age）
- `auth_query`：pgBouncer 直接從 PostgreSQL `pg_shadow` 拉密碼、不需要在 pgBouncer 本地維護 userlist — production 推薦做法

**Application 端 pool 設定**：

```yaml
# 例：Spring Boot HikariCP
spring.datasource.url: jdbc:postgresql://pgbouncer.internal:6432/mydb
spring.datasource.hikari.maximum-pool-size: 30
spring.datasource.hikari.minimum-idle: 5
spring.datasource.hikari.connection-timeout: 30000
spring.datasource.hikari.idle-timeout: 600000
spring.datasource.hikari.max-lifetime: 1800000  # 30 min < pgBouncer server_lifetime 60 min

# 例：SQLAlchemy
engine = create_engine(
    "postgresql://pgbouncer.internal:6432/mydb",
    pool_size=30,
    max_overflow=5,
    pool_pre_ping=True,        # 必開、檢測 stale connection
    pool_recycle=1800,         # 30 min、跟 pgBouncer server_lifetime 對齊
)
```

**Application 跟 pgBouncer 對齊**：

- application `max-lifetime` < pgBouncer `server_lifetime`：避免 application 拿到已被 pgBouncer recycle 的 connection
- `pool_pre_ping = True`：每次 checkout 前 send `SELECT 1`、檢測 stale connection — 對 transaction pooling 是必要的
- application 端 *不要* 用 prepared statement（除非 pgBouncer 1.21+ 設 `max_prepared_statements`）

## 故障演練 / 邊界 case

### Case 1：Pool exhaustion（default_pool_size 用滿）

徵兆：application log `ERROR: no more connections allowed`、pgBouncer log `pool is full`、pgBouncer admin console `SHOW POOLS` 顯示 `cl_waiting > 0`。

Debug：

```sql
-- 連 pgBouncer admin
\c pgbouncer
SHOW POOLS;
-- 看 cl_active / cl_waiting / sv_active / sv_idle
SHOW SERVERS;
-- 看 server connection state（active / idle / used）
```

修：

- 短期：調高 `default_pool_size` 跟 PostgreSQL `max_connections`、配合 reserve pool
- 中期：找 *long-running query*（PostgreSQL `pg_stat_activity` 看 `query_start`、kill 過長 query）
- 長期：拆 database / 改 read replica / 移 OLAP query 到 data warehouse

### Case 2：Transaction pooling 下 session state 漏洞

徵兆：random 失敗 `prepared statement "S_3" does not exist`、`relation "tmp_xxx" does not exist`、advisory lock 不釋放。

原因：application 用了 prepared statement / temporary table / advisory lock、但 transaction commit 後 backend connection 釋放、下一個 transaction 拿到不同 backend、session state 不存在。

修：

- Application 框架禁用 prepared statement（JDBC `prepareThreshold=0`、SQLAlchemy `use_native_prepared_statements=False`）
- temporary table 改 [unlogged table](https://www.postgresql.org/docs/current/sql-createtable.html#SQL-CREATETABLE-UNLOGGED-TABLES) + cleanup
- advisory lock 改 row-level lock 或 application-level lock（Redis）
- 或：切到 session pooling、犧牲收斂效率

### Case 3：DNS-based failover 後 application 連到舊 master

徵兆：PostgreSQL 切換 master 後、application 寫操作 *時好時壞*（看連到哪台）。

原因：pgBouncer 在 application 跟 PostgreSQL 之間、application 不知道 backend 換了；pgBouncer 自己也需要 reload config 才會連新 master。

修：

- pgBouncer 用 `RECONNECT` admin command 強制 close all backend connection、重連
- 配 Patroni / Stolon 等 HA 工具自動 trigger pgBouncer reconnect
- application 端 `pool_pre_ping` 開啟、stale connection 自動踢

### Case 4：Server lifetime recycle 跟 in-flight transaction 衝突

徵兆：偶發 `server closed the connection unexpectedly`、跟 long-running transaction 重疊。

原因：pgBouncer `server_lifetime = 3600` 強制 recycle、但有 transaction 在跑時 pgBouncer 不會切、超過時間後仍會切。

修：

- 確認沒有 *超過 1 小時* 的 transaction（PostgreSQL `pg_stat_activity` 看 `xact_start`）
- 必要時調高 `server_lifetime`、但 memory bloat 風險上升
- application 端做 transaction timeout

### Case 5：pgBouncer 自己 crash / OOM

徵兆：所有 application 同時失去 PostgreSQL 連線。

原因：pgBouncer 是 single-process（除非 1.21+ 用 `so_reuseport` 多 process）、memory leak / OOM / 部署事件都會打掉整個 connection layer。

修：

- 多 pgBouncer instance + load balancer（HAProxy / Envoy）前置、application 連 LB
- `so_reuseport = 1`（1.21+）讓多個 pgBouncer process 共用 port
- Resource limit 跟 alert：RSS > N、connection count > M
- HA mode：active-passive 配 keepalived

## 容量 / cost 規劃

**單一 pgBouncer 容量上限**：

- `max_client_conn`：實務 < 5000 per instance（再高 CPU 跟 file descriptor 緊）
- `default_pool_size × database 數`：實務 < 200 per instance
- single process CPU bound：在 10K QPS 等級已經是瓶頸、要橫向 scale

**何時加 pgBouncer instance**：

- application connection 數突破 3000 / pgBouncer instance
- pgBouncer CPU usage > 60%（baseline、不算 spike）
- 跨 region application 需要 region-local pgBouncer

**何時改架構（pgBouncer 不夠用）**：

- PostgreSQL backend connection 數突破 500（即使有 pgBouncer 也撐不住）→ 改 read replica / partitioning / sharding
- write 量太大（每秒 50K+ TPS）→ 改 sharding（[Vitess](https://vitess.io) / [Citus](https://www.citusdata.com)）或全球分散式 SQL（[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)）
- application 大量 prepared statement / session state 需求 → 改 [PgCat](https://github.com/postgresml/pgcat)（Rust 寫、支援更完整的 session feature）或回 session pooling

## 整合 / 下一步

**跟 HA failover 整合**（[Patroni](https://github.com/zalando/patroni)）：

- Patroni 切換 master 後 trigger pgBouncer `RECONNECT`
- pgBouncer 透過 service discovery（Consul / etcd）拿新 master 位址、不是寫死在 config
- application 不需感知 failover、connection 從 pgBouncer 拿到新 master 的 backend

**跟監控整合**：

- pgBouncer admin console `SHOW STATS` / `SHOW POOLS` / `SHOW SERVERS` 拉到 Prometheus（[pgbouncer_exporter](https://github.com/jbub/pgbouncer_exporter)）
- 必看 metric：`cl_waiting`（等 backend 的 client 數）、`sv_active`（active backend 數）、`avg_query_time`、`avg_xact_time`
- Alert：`cl_waiting > 0 持續 30s`、`server connection error rate > 0`

**跟 application observability 整合**：

- Application APM（[Datadog](/backend/04-observability/vendors/datadog/) / Honeycomb / OpenTelemetry）的 DB span 顯示 *application 看到的 latency*、pgBouncer metric 顯示 *pgBouncer ↔ PostgreSQL latency* — 兩者差異揭露 connection wait time

**何時 revisit 這個配置**：

- application 數量倍增（trigger pool sizing 重算）
- PostgreSQL 升級（pgBouncer 跟 PostgreSQL 版本相容性）
- 跨 region 部署（要不要 region-local pgBouncer）
- 切換到 RDS Proxy / Aurora Cluster Endpoint（managed alternative）

## 相關連結

- [PostgreSQL vendor overview](/backend/01-database/vendors/postgresql/) — 本文是該頁尾「pgBouncer / PgCat 配置 best practice」backlog 的深度展開
- [Connection Scaling Deep Dive](/backend/01-database/vendors/postgresql/connection-scaling/) — connection-per-process model 跟為什麼 pooler 是必裝（根因 vs 配置）
- [1.1 高併發資料存取](/backend/01-database/high-concurrency-access/) — 上游：什麼時候需要 connection pool
- [Connection Pool 卡片](/backend/knowledge-cards/connection-pool/) — 概念基底
- [Vendor 深度技術文章方法論](/posts/vendor-deep-article-methodology/) — 本文是該方法論的 demo #1
- [9.C29 Lemino RDB connection limit case](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) — connection 爆是 streaming surge 場景的 vendor-switch 主因
- 官方：[pgBouncer Documentation](https://www.pgbouncer.org/usage.html)
