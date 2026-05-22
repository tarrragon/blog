---
title: "SQLite to D1 / Turso Migration"
date: 2026-05-21
description: "SQLite 轉向 Cloudflare D1、Turso / libSQL 的 edge driver、compatibility audit、data movement 與 rollback"
tags: ["backend", "database", "sqlite", "d1", "turso", "migration"]
---

SQLite to D1 / Turso migration 的核心責任是把 local SQLite 轉成 edge / serverless / distributed SQLite-compatible product。這條路線的 driver 通常是 edge locality、Workers integration、managed operation、global read latency、embedded replica 或 serverless deployment workflow。

本文的判讀錨點是：D1 / Turso migration 是 runtime boundary 變更。Local file 直連變成 platform binding、remote endpoint 或 embedded replica；因此 migration 要同時審查 SQL support、data movement、driver API、auth、latency、freshness、backup 與 vendor exit。

## Migration Drivers

Migration drivers 的核心責任是確認 edge SQLite 產品解決的是哪個服務壓力。D1 與 Turso / libSQL 都接近 SQLite experience，但它們的採用理由應寫成具體 workload。

| Driver               | 適合產品                 | 判讀訊號                                |
| -------------------- | ------------------------ | --------------------------------------- |
| Workers integration  | Cloudflare D1            | App 已在 Workers、資料量小、query 清楚  |
| Serverless low ops   | D1 / Turso               | 不想維護 host DB、可接受 platform limit |
| Low-latency read     | Turso / embedded replica | read-heavy、freshness window 明確       |
| Edge-local app       | D1 / Turso               | 使用者分散、write rate 可控             |
| Portable SQLite base | Turso / libSQL           | 想保留 SQLite-like schema 與 local dev  |

D1 的 migration driver 要和 Cloudflare platform 綁定。若 app 已用 Workers routing、KV、Queues 或 Pages，D1 可以降低跨平台整合成本；若 app 不在 Cloudflare 生態，D1 的價值要用 latency、operation 與成本證明。

Turso / libSQL 的 migration driver 要和 replica freshness 綁定。若使用者需要 local read speed，embedded replica 有價值；若產品要求每次讀都立即看到最新 global state，就要先設計 read-after-write path。

## Compatibility Audit

Compatibility audit 的核心責任是確認 local SQLite schema、query 與 migration workflow 可在 target product 上運作。官方文件要作為 limits 與 feature 的單一來源：D1 參考 [Cloudflare D1 docs](https://developers.cloudflare.com/d1/) 與 [D1 limits](https://developers.cloudflare.com/d1/platform/limits/)；Turso 參考 [Turso docs](https://docs.turso.tech/) 與 libSQL client reference。

| 面向         | 審查問題                                | Evidence                       |
| ------------ | --------------------------------------- | ------------------------------ |
| SQL support  | schema、trigger、index、JSON、FK        | migration dry run、query suite |
| Size / batch | import file、query duration、batch size | limit review、sample import    |
| Driver API   | local file path 變成 binding / endpoint | repository adapter test        |
| Auth         | token、binding、environment secret      | staging deployment             |
| Transaction  | request boundary、retry、write location | failure injection              |
| Backup       | export、restore、retention              | restore drill                  |

Compatibility audit 要以 production query 為單位。只跑 `CREATE TABLE` 會漏掉最重要的差異；query suite 要包含 list page、pagination、unique violation、FK violation、transaction rollback、large batch 與 slow query。

## Data Movement

Data movement 的核心責任是把 SQLite file 轉成 target platform 可接受的 seed。Local SQLite 可以先 export 成 SQL dump、CSV 或 platform CLI 支援的 import format，再進 target product。

```bash
sqlite3 app.db ".dump" > seed.sql
```

這段命令只是 seed 起點。正式流程要處理 schema ordering、unsupported SQL、large transaction、batch split、sensitive data masking、import duration、row count 與 checksum。

D1 migration 要把 Wrangler / platform workflow 納入 runbook。Cloudflare D1 的 limits 文件列出 import 與 query 限制；大型資料變更應切 batch，並在 preview / staging database 跑完整 dry run。

Turso migration 要把 remote database 與 embedded replica 分開驗證。Seed 完 remote primary 後，要測 local embedded replica 的 bootstrap、sync、read freshness、write delegation 與 offline behavior。

## Application Change

Application change 的核心責任是把 database access 從 file path 改成可替換 adapter。Local SQLite 常用 file path 與 process-local connection；D1 / Turso 會加入 binding、endpoint、token、client SDK、network failure 與 platform runtime。

| 改動層        | Local SQLite            | D1 / Turso route                         |
| ------------- | ----------------------- | ---------------------------------------- |
| Connection    | file path               | Workers binding、HTTP / libSQL endpoint  |
| Auth          | filesystem permission   | platform secret、token、binding          |
| Error model   | SQLite error code       | SDK / platform error + SQLite-like error |
| Retry         | local busy / lock retry | network retry、idempotency、timeout      |
| Observability | app log + file metric   | app log + platform metric                |

Repository adapter 要承擔 driver 差異。Domain layer 應看到穩定的 repository contract，例如 duplicate key、stale read、temporary unavailable、retryable write；底層才處理 D1 binding 或 libSQL client。

Idempotency 是 edge migration 的關鍵。Write request 進入 network / serverless runtime 後，retry 可能在 client、platform 或 application 層發生；每個 critical write 都應有 idempotency key 或 natural unique key。

## Evidence

Evidence 的核心責任是證明 edge migration 帶來的收益大於新風險。D1 / Turso 的成功要同時看功能可用、region latency、freshness、error rate、cost、migration time 與 exit route。

| Evidence                | 最小驗證方式                          |
| ----------------------- | ------------------------------------- |
| Latency by region       | 從主要 user region 跑 read/write test |
| Freshness               | write 後在 replica / edge read 檢查   |
| Migration repeatability | staging database 從空庫重跑 seed      |
| Error mapping           | duplicate、constraint、timeout、auth  |
| Cost                    | request、storage、egress、operation   |
| Exit route              | export file + restore to local SQLite |

Freshness evidence 要用產品語言寫。若 UI 可以顯示「同步中」，freshness window 可被使用者理解；若是付款、庫存、權限決策，讀舊資料會直接造成業務錯誤，這類 workflow 要走 primary read 或 server SQL。

Exit route 要被演練。Edge product 的 adoption cost 低，exit cost 會出現在 driver API、migration workflow、platform binding 與 data export；至少要能把 staging data export 回 SQLite file 並通過 smoke test。

## Rollback

Rollback 的核心責任是保留 local SQLite snapshot 與 read-only fallback。Edge migration 若在 cutover 後遇到 auth、latency、limit 或 query error，團隊要能快速回到上一個可用資料狀態。

| Rollback 觸發           | 回退策略                              |
| ----------------------- | ------------------------------------- |
| Import / migration 失敗 | 清空 target、修 migration、重跑 seed  |
| Query error spike       | 切回 local SQLite / previous endpoint |
| Freshness issue         | critical read 改 primary path         |
| Cost / limit spike      | 降低 traffic、batch migration、重評估 |
| Vendor incident         | read-only mode、fallback endpoint     |

Local snapshot 要保存到 cutover 後的觀察窗口結束。若 cutover 期間已有 target-only writes，要設計回放或 reconciliation；高風險 workflow 可以先進 read-only cutover，再逐步開寫。

## Decision Route

Decision route 的核心責任是把 edge migration 和 server DB migration 分開。D1 / Turso 適合 edge runtime 與 SQLite-like workflow；當需求轉向 central audit、server role、high-write OLTP 或 distributed transaction，應改走 PostgreSQL / CockroachDB / Spanner。

| 需求                                 | 路由                                                                                      |
| ------------------------------------ | ----------------------------------------------------------------------------------------- |
| Workers app + small relational data  | D1                                                                                        |
| Read-heavy app + local replica value | Turso / libSQL                                                                            |
| Backup / restore 是主要問題          | [Litestream / LiteFS](/backend/01-database/vendors/sqlite/litestream-litefs-replication/) |
| 多 tenant + permission + audit       | [SQLite to PostgreSQL](/backend/01-database/vendors/sqlite/migrate-to-postgresql/)        |
| Global write transaction             | [Global Distributed OLTP](/backend/01-database/global-distributed-oltp/)                  |

## 下一步路由

SQLite to D1 / Turso migration 完成後，先讀 [D1 / Turso / libSQL comparison](/backend/01-database/vendors/sqlite/d1-turso-libsql-comparison/) 釐清 product boundary；再用 [SQL dialect and index limits](/backend/01-database/vendors/sqlite/sql-dialect-index-limits/) 做 compatibility audit；需要操作演練時讀 [D1 / Turso preview lab](/backend/01-database/vendors/sqlite/hands-on/d1-turso-preview-lab/)。
