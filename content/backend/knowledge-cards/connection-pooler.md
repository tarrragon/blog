---
title: "Connection Pooler"
date: 2026-05-27
description: "應用層跟資料庫之間的連線複用中介層、解水平擴展時的連線數放大問題"
weight: 354
---

連線池代理（connection pooler）的核心責任是讓部署在應用層跟資料庫之間的中介層、把多個應用層連線複用到少數 DB backend 連線上。解水平擴展應用層時「100 臺機器 × 每臺 10 連線 = 1000 個 DB 連線、超過 `max_connections` 十倍」這個常見問題。跟 [connection pool](/backend/knowledge-cards/connection-pool/) 是不同層 — 後者在 application instance 內、本卡是跨 instance 共享層。

## 跟其他概念的關係

Connection pooler 在 DB topology 中是「應用層跟 DB 之間的 multiplexer 層」、跟 [connection pool](/backend/knowledge-cards/connection-pool/) 是不同層。常見實作：

- **PgBouncer**（PostgreSQL）：輕量 single-process、三種 pool_mode（session / transaction / statement）
- **AWS RDS Proxy**（PostgreSQL / MySQL）：managed 版本、整合 IAM auth、failover 加速
- **ProxySQL**（MySQL）：規則型 routing + connection pooling + query rewriting
- **PgCat**（PostgreSQL）：Rust 寫的 PgBouncer 替代、支援 sharding

PgBouncer 的 `pool_mode` 是核心配置：session mode 嚴格說屬 connection caching（單 client 跟 backend 1:1 綁定整個 session）；transaction mode 是多數場景的 default、但限於不依賴跨 transaction 的 session 層級狀態的應用（session 層級的 `SET`、prepared statement、temp table 在 transaction mode 下會丟失，`SET LOCAL` 只在單一 transaction 內生效、不受影響；PgBouncer 1.21 起可用 `max_prepared_statements` 追蹤 prepared statement，1.24 起預設開啟，見 [Prepared Statement](/backend/knowledge-cards/prepared-statement/)）；statement mode 限於純無狀態 query workload、極少用。

## 可觀察訊號與例子

該裝 pooler 的訊號：應用層機器數 ≥ 20、每臺機器連線數 ≥ 10、DB `max_connections` 使用率 ≥ 70%、P99 connection wait time 升高。`pg_stat_activity` 顯示大量 idle 連線是裝 pooler 的明確指標。中型 PostgreSQL 服務裝 PgBouncer 後、DB 連線數常從 1000+ 壓到 50-100。

## 判斷條件與後果

自管 PgBouncer 與 RDS Proxy 的差別在成本的形態：自管 PgBouncer 付的是 HA、failover 與監控的運維工作；RDS Proxy 把這些運維交給 AWS，付的是依 vCPU 計價的費用。Transaction mode 下，同一個 client 的連續 transaction 可能分配到不同的 backend 連線，JDBC、asyncpg 與 Go 的 pgx 預設使用的 prepared statement 在另一條 backend 連線上不存在，在沒有開啟 `max_prepared_statements` 的 PgBouncer 上，查詢會失敗；所以切到 transaction mode 之前先查 ORM 與 driver 的行為，改成明示配置 protocol-level prepared statement 或 inline parameter。Pooler 減少的是連線數的放大，N+1 query 造成的查詢次數放大不受它影響，兩者是彼此獨立的兩件事。
