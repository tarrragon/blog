---
title: "Connection Pooler"
date: 2026-05-27
description: "應用層跟資料庫之間的連線複用中介層、解水平擴展時的連線數放大問題"
weight: 353
---

Connection pooler 是部署在應用層跟資料庫之間的中介層、把多個應用層連線複用到少數 DB backend 連線上。解的是「水平擴展應用層、DB 連線數爆掉」這個常見問題 — 100 臺機器 × 每臺 10 連線 = 1000 個 DB 連線、超過 PostgreSQL `max_connections` default 十倍。Pooler 把 application-side 看到的 1000 個連線、複用到 DB 真實的 50-100 個 backend 上。跟 [connection pool](/backend/knowledge-cards/connection-pool/) 的差別是後者在 application instance 內、本卡是跨 instance 共享層。

## 概念位置

Connection pooler 在 DB topology 中是「應用層跟 DB 之間的 multiplexer 層」、跟應用層內部的 [connection pool](/backend/knowledge-cards/connection-pool/) 是不同層 — 後者在 application instance 內、本卡是跨 instance 共享。常見實作：

- **PgBouncer**（PostgreSQL）：輕量 single-process、三種 pool_mode（session / transaction / statement）取捨
- **AWS RDS Proxy**（PostgreSQL / MySQL）：managed 版本、整合 IAM auth、failover 加速
- **ProxySQL**（MySQL）：規則型 routing + connection pooling + query rewriting
- **PgCat**（PostgreSQL）：Rust 寫的 PgBouncer 替代、支援 sharding

## 三種 pool_mode 取捨

PgBouncer 的 `pool_mode` 是 connection pooler 設計的核心抽象：

- **Session mode**：應用層 client 拿到的連線、跟 DB backend 1:1 綁定、整個 session 結束才釋放。其實沒做 multiplexing、只是 connection caching。
- **Transaction mode**：每個 transaction 結束、應用層 client 連線釋放回 pool。multiplexing 強、但**不支援 transaction-scoped state**（`SET LOCAL`、prepared statement、temp table）
- **Statement mode**：每 statement 結束就釋放、最強 multiplexing 但**不支援 transaction**、極少用

Transaction mode 是多數場景的 default、但要對齊 ORM / driver 行為（PostgreSQL 14+ protocol-level prepared statement 才相容）。

## 何時需要

該裝 pooler 的訊號：

- 應用層機器數 ≥ 20
- 每臺機器連線數 ≥ 10
- DB `max_connections` 使用率 ≥ 70%
- P99 connection wait time 升高

不需要 pooler 的場景：

- 應用層機器數 < 10
- DB 規格大、`max_connections` 充裕
- Workload 全是長 transaction（pool 跟 session mode 沒差）

## 反模式

- **把 pooler 當 N+1 解藥**：Pooler 解的是「連線數放大」、不是「query 數量過多」。N+1 在裝完 pooler 後仍然慢、只是 DB 不會因為連線爆掉而當機
- **Transaction mode 配置不審 ORM**：Prepared statement / SET LOCAL / temp table 跟 transaction mode 衝突、ORM 預設行為要 audit、否則 production 出現「query 隨機失敗」
