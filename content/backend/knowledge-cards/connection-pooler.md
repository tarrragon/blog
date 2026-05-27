---
title: "Connection Pooler"
date: 2026-05-27
description: "應用層跟資料庫之間的連線複用中介層、解水平擴展時的連線數放大問題"
weight: 353
---

Connection pooler 的核心責任是讓部署在應用層跟資料庫之間的中介層、把多個應用層連線複用到少數 DB backend 連線上。解水平擴展應用層時「100 臺機器 × 每臺 10 連線 = 1000 個 DB 連線、超過 `max_connections` 十倍」這個常見問題。跟 [connection pool](/backend/knowledge-cards/connection-pool/) 是不同層 — 後者在 application instance 內、本卡是跨 instance 共享層。

## 概念位置

Connection pooler 在 DB topology 中是「應用層跟 DB 之間的 multiplexer 層」、跟 [connection pool](/backend/knowledge-cards/connection-pool/) 是不同層。常見實作：

- **PgBouncer**（PostgreSQL）：輕量 single-process、三種 pool_mode（session / transaction / statement）
- **AWS RDS Proxy**（PostgreSQL / MySQL）：managed 版本、整合 IAM auth、failover 加速
- **ProxySQL**（MySQL）：規則型 routing + connection pooling + query rewriting
- **PgCat**（PostgreSQL）：Rust 寫的 PgBouncer 替代、支援 sharding

PgBouncer 的 `pool_mode` 是核心配置：session mode 嚴格說屬 connection caching（單 client 跟 backend 1:1 綁定整個 session）；transaction mode 是多數場景的 default、但限於不依賴 transaction-scoped state 的應用（`SET LOCAL`、prepared statement、temp table 在 transaction mode 下會丟失）；statement mode 限於純無狀態 query workload、極少用。

## 可觀察訊號與例子

該裝 pooler 的訊號：應用層機器數 ≥ 20、每臺機器連線數 ≥ 10、DB `max_connections` 使用率 ≥ 70%、P99 connection wait time 升高。`pg_stat_activity` 顯示大量 idle 連線是裝 pooler 的明確指標。中型 PostgreSQL 服務裝 PgBouncer 後、DB 連線數常從 1000+ 壓到 50-100。

## 設計責任

選 PgBouncer 自管要付 HA / failover / 監控的運維成本；選 RDS Proxy 換掉運維、付 per vCPU 計價。Transaction mode 配置前要 audit ORM / driver 行為 — JDBC / asyncpg 的 default prepared statement 跟 transaction mode 衝突、要明示配置 protocol-level prepared statement 或改寫成 inline parameter。Pooler 解的是連線數放大、N+1 query 屬另一層議題 — 兩個問題正交、各自要解。
