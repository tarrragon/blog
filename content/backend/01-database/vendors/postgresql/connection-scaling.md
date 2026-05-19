---
title: "PostgreSQL Connection Scaling：connection-per-process model 跟為什麼 pooler 是必裝"
date: 2026-05-19
description: "PG 每個 client connection fork 一個 backend process（不是 thread）、RAM 成本 5-15MB/connection、context switch 跟 fork() cost 在 100+ connection 後線性放大、所以 pooler 不是 *optional optimization* 而是 *production prerequisite*。本文走 connection-per-process model 跟 MySQL thread-per-connection 對比、max_connections + shared_buffers + work_mem 三 GUC 互動、application-side pool vs middleware pool vs RDS Proxy 三層選擇、5 production 踩雷（connection storm / fork() cost 在 burst 流量 / shared_buffers 跟 connection 數壓縮 / double-pool 配置錯誤 / max_connections 設太大反而慢）、跟 PgBouncer config 互補不重複"
weight: 14
tags: ["backend", "database", "postgresql", "connection", "pooler", "scaling", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 PG 在 OLTP 譜系的定位、本文聚焦 *connection scaling 的根因* — 為什麼 PG 比多數 DB 更需要 pooler、跟 [pgbouncer-config](/backend/01-database/vendors/postgresql/pgbouncer-config/) 是 *根因 vs 配置* 的關係。

---

## Connection-per-Process Model 是 PG 的結構性選擇

PG 接受 client connection 時的行為跟多數現代 DB 不同：每個 connection 由 postmaster `fork()` 一個獨立的 OS process（backend）來服務。這個 process 在 connection lifetime 內專屬該 client、不跟其他 client 共享。

對比常見 DB 的 connection model：

| Vendor                 | Connection model               | 每 connection 資源             |
| ---------------------- | ------------------------------ | ------------------------------ |
| PostgreSQL             | Process-per-connection（fork） | 5-15MB RAM、獨立 PID           |
| MySQL                  | Thread-per-connection          | 256KB-2MB RAM、共享 process    |
| Oracle                 | Shared server / dedicated 可選 | 配置決定                       |
| SQL Server             | Thread-per-connection（pooled）| ~512KB                         |
| MongoDB                | Thread-per-connection          | ~1MB                           |

PG 選 process 不選 thread 是 1990s 設計決定 — 當時 thread library 在多 UNIX 平台不穩定、process 隔離性更好（一個 backend crash 不會帶倒整個 DB）。這個 trade-off 一路保留到今天、是 PG 在 high-connection-count workload 的 *結構性負擔*。

## 量化：connection 數量對 RAM 跟 CPU 的壓力

一個 PG backend process 的 RAM footprint 由三部分組成：

```text
backend_rss ≈ shared_buffers_attach + process_private + work_mem 高水位
```

`shared_buffers` 是所有 backend 共享的、不重複計、但 `process_private`（catalog cache / plan cache / temp buffer）跟 `work_mem` 是 per-backend：

| Workload 類型              | process_private | work_mem 高水位 | 單 backend RAM |
| -------------------------- | --------------- | --------------- | -------------- |
| Idle / 簡單 OLTP           | 3-5MB           | 4MB             | 7-9MB          |
| 中等 query（join / sort）  | 5-8MB           | 16-64MB         | 21-72MB        |
| Heavy analytical（CTE / window）| 8-15MB     | 256MB+          | 264MB+         |

500 個 connection、平均 30MB 各 ≈ 15GB RAM 給 backend processes（還沒算 shared_buffers）。這是 PG 在 cloud instance 上很快撞到 RAM ceiling 的根因。

CPU 層面、`fork()` 系統呼叫在 Linux 通常 1-3ms、context switch ~3-5μs。100 connection burst 在 1 秒內進來、accumulated fork cost 100-300ms、加 query 本身的 CPU 跟 scheduler latency、平均 query 延遲會跳 2-5x。

## 三個 GUC 互動：max_connections / shared_buffers / work_mem

PG 的 memory 規劃由這三個 GUC 互動決定、不能獨立調：

```text
total_RAM ≈ shared_buffers + (max_connections × work_mem 高水位) + OS overhead
```

實務 sizing 規則（16GB instance、OLTP workload）：

| GUC                | 建議值                            | 理由                                                                |
| ------------------ | --------------------------------- | ------------------------------------------------------------------- |
| `shared_buffers`   | 25% RAM（4GB）                    | 太大 OS file cache 收益遞減、< 25% wastes RAM                       |
| `work_mem`         | 8-32MB                            | 每 query operation 用一份、不是每 connection 一份                   |
| `max_connections`  | 100-200                           | 超過 200 需 pooler、不是調更大                                      |
| `effective_cache_size` | 50-75% RAM                    | planner 估 cost 用、不是實際配置                                    |
| `maintenance_work_mem` | 64-512MB                      | VACUUM / CREATE INDEX 用                                            |

`max_connections = 1000` 是常見 anti-pattern — 真實 active query 可能只 50-100、剩下都 idle、但每個還是吃 RAM 跟 process slot、context switch overhead 還在。

## Pooler 為什麼是 *production prerequisite*

> 本段是「為什麼必裝」、實際 PgBouncer 配置看 [pgbouncer-config](/backend/01-database/vendors/postgresql/pgbouncer-config/)。

Pooler 的核心責任是 *把 N 個 application connection multiplex 成 M 個 PG backend（M ≪ N）*：

```text
Application (3000 connection)
   ↓
Pooler（PgBouncer / Pgcat）
   ↓
PostgreSQL (50 backend process)
```

Application 看到的是 *無限 connection 池*、PG 看到的是 *穩定 50 個 backend*。三個層次的效益：

1. **RAM 節省**：3000 connection × 30MB = 90GB → 50 backend × 30MB = 1.5GB
2. **Fork() cost 攤平**：backend 重用、不是每個 client 都 fork
3. **Connection storm 緩衝**：application 重啟 / scaling event 不會直接打到 PG

Pooler 有三種 pool mode、各有 application 層相容性 trade-off：

| Pool mode    | Session 隔離              | 適用 application                          | PG feature 限制                    |
| ------------ | ------------------------- | ----------------------------------------- | ---------------------------------- |
| Session      | 每 client 獨佔 1 backend  | 用 prepared statement、SET、temp table    | 等同沒 pool、僅救 fork cost        |
| Transaction  | 每 transaction 換 backend | 多數 stateless API（最常用）              | 不能用 session-level state         |
| Statement    | 每 statement 換 backend   | Read-only / analytical                    | 不能用 transaction                 |

Production 多數選 transaction pool — 救 RAM 又保留 transaction semantics、代價是 application 不能用 session-level `SET`、`LISTEN/NOTIFY`、prepared statement（部分 pooler 已支援）。

## Application-side Pool vs Middleware Pool vs RDS Proxy

三層 pool 都能解 connection 問題、但解的問題不同：

| 層級                       | 代表                              | 解的問題                                              | 限制                                          |
| -------------------------- | --------------------------------- | ----------------------------------------------------- | --------------------------------------------- |
| Application-side（driver） | HikariCP（Java）/ pgx pool（Go）/ asyncpg / Sequelize | Connection 重用 + lifecycle 管理 | 仍每 app instance 開 N 個到 PG、總量沒收斂    |
| Middleware pooler          | PgBouncer / Pgcat                 | Multiplex 所有 application instance 到少數 backend    | 多一跳 latency 0.1-1ms、需自管 HA             |
| Cloud-managed proxy        | RDS Proxy / Cloud SQL Proxy       | Multiplex + IAM auth + Secrets Manager integration    | Latency 1-3ms、cost premium、PG feature 受限  |

**典型 production 拓撲**：

```text
Application (HikariCP pool 10/instance × 50 instance = 500)
   ↓
PgBouncer transaction pool（50 backend）
   ↓
PostgreSQL primary
```

Application pool 救 fork cost、PgBouncer 救 backend 總量、兩層各做各的事不衝突。

**雙層 pool 配置容易出錯**：application pool size 5 + PgBouncer default_pool_size 50 + 100 個 app instance、application 願意開 500 connection、PgBouncer 只給 50 個 backend — 多 450 個 application connection wait、看起來像「DB 慢」但實際是 pool 不足。

## 5 個 Production 踩雷

### Case 1：Connection storm（重啟 / autoscale 同時打進來）

**情境**：Kubernetes rolling restart、200 個 pod 同時重連、每 pod 開 20 個 connection、瞬間 4000 個 connection 嘗試打到 PG。

PG `max_connections = 500` 直接拒絕 3500 個、application 看到 `FATAL: sorry, too many clients already`、retry storm 雪上加霜。

修法：

- PgBouncer 在前面、application 連 PgBouncer 不直連 PG
- `reserve_pool_size = 5` 給管理流量留 buffer
- Application 端加 jittered exponential backoff、避免 retry 同步

### Case 2：fork() cost 在 burst 流量

**情境**：Cron job 每分鐘整點觸發、500 個 worker 同時開 short-lived connection 跑 30ms query、結束關閉。

每分鐘 500 次 `fork()` + 500 次 `exit()`、fork cost 500-1500ms、CPU spike、其他 OLTP query 延遲飆。

修法：

- Worker 改 connect 到 PgBouncer transaction pool、backend 重用、fork 只在 PgBouncer 首次拓展時
- 或 worker 改成 long-lived process + 內部 task queue、避免每分鐘重 fork

### Case 3：shared_buffers 跟 max_connections 互相壓縮

**情境**：16GB instance、`shared_buffers = 8GB`（50%）、`max_connections = 800`、`work_mem = 16MB`。

預估 RAM：8GB + 800 × ~30MB = 32GB ≫ 16GB instance、OOM kill 來訪。

修法（重新分配）：

```ini
shared_buffers = 4GB           # 25%
max_connections = 200          # 透過 PgBouncer multiplex
work_mem = 16MB
effective_cache_size = 12GB
maintenance_work_mem = 512MB
```

關鍵：`max_connections` 不是調更大救 connection 不足、是調 *PgBouncer pool size* 拓展 application 容量。

### Case 4：Double-pool 配置失敗

**情境**：Application HikariCP pool size = 50、50 個 instance、PgBouncer `default_pool_size = 20`、PG `max_connections = 100`。

Application 願意開 2500 個 connection、PgBouncer 只給 20 個 backend、application thread 大量 block 在 PgBouncer 等 backend 釋出。

修法：

- 計算 *application 願意的並發* vs *PgBouncer 允許的 backend* vs *PG max_connections* 三層匹配
- 通常 `application_total_connection ≪ pgbouncer_max_client_conn` + `pgbouncer_default_pool_size + reserve ≪ pg_max_connections`
- Monitor PgBouncer `SHOW POOLS` 的 `cl_waiting`、長期 > 0 表示 pool 不足

### Case 5：max_connections 設太大反而慢

**情境**：team 看到 `connection refused`、把 `max_connections` 從 200 調到 2000、想說「給更多 connection 應該更好」。

調完 throughput 反而降 30% — context switch overhead、planner cache 競爭、lock manager 競爭都跟 connection 數線性放大。

修法：

- `max_connections` 上限通常 200-500、超過要靠 pooler multiplex
- 用 `pg_stat_activity` 看真實 active connection（state != 'idle'）、通常 < 100
- 真實上限 = active 高水位 × 安全係數 1.5、不是「未來可能會用到的數量」

## 跟 MySQL connection model 對比

| 維度                  | PostgreSQL                          | MySQL                                  |
| --------------------- | ----------------------------------- | -------------------------------------- |
| Connection 模型       | Process-per-connection（fork）      | Thread-per-connection                  |
| 單 connection RAM     | 5-15MB（idle）/ 30-200MB（heavy）   | 256KB-2MB                              |
| Fork / spawn cost     | 1-3ms                               | < 100μs                                |
| Pooler 必要性         | **強烈必要**（300+ connection 必裝）| 中等（ProxySQL 對特定 case 有用）      |
| 主流 pooler           | PgBouncer / Pgcat                   | ProxySQL / MySQL Router                |

MySQL thread-per-connection model 讓它在 high-connection-count workload 上 *看起來* 更省 — 但 PG 透過 PgBouncer 達到的 application 看到的容量跟 MySQL 直連是一樣的、只是多一層 indirection。

實務影響：

- MySQL 直連 1000 connection 還 OK、PG 直連 1000 connection 通常 OOM
- PG + PgBouncer 1000 application connection、後端 50 backend、表現跟 MySQL 1000 直連相當
- 沒有 *PG 更耗 RAM* 的本質結論、是 *PG 預設不 multiplex、需要外掛 multiplex 層*

## PG 17+ 的 connection 進展

PG 17（2024）對 connection 仍維持 process-per-connection、但有幾個減壓改進：

- **Per-process memory 降低**：catalog cache 改 generational allocator、idle backend RAM 降 ~20%
- **Subscriber-side parallel apply**：logical replication 減少 connection 開銷
- **`io_combine_limit`**：buffered read 合併、降 syscall overhead

但 *connection-per-process model 本身* 沒換 — 短期內 PG 仍需 pooler。長期方向（PG 18+ 討論）可能引入 thread-based backend、但目前是 experimental patch。

## 相關連結

- [pgbouncer-config](/backend/01-database/vendors/postgresql/pgbouncer-config/)：PgBouncer 操作配置 + 5 case
- [replication-topology](/backend/01-database/vendors/postgresql/replication-topology/)：Read replica + connection 分流
- [query-optimization](/backend/01-database/vendors/postgresql/query-optimization/)：`work_mem` 影響 plan
- [mvcc-lock-model](/backend/01-database/vendors/postgresql/mvcc-lock-model/)：connection idle in transaction 卡 vacuum
- [autovacuum-tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)：autovacuum 也吃 connection slot

## 下一步

- 連到 [pgbouncer-config](/backend/01-database/vendors/postgresql/pgbouncer-config/) 學配置細節
- 看 [PostgreSQL overview](/backend/01-database/vendors/postgresql/) 回到全圖
