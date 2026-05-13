---
title: "SQLite"
date: 2026-05-13
description: "embedded、單檔案、test / CLI / edge 場景的標準選擇、近年因 Cloudflare D1 / Turso 等服務復興"
weight: 6
tags: ["backend", "database", "vendor", "sqlite", "embedded"]
---

SQLite 是世界上部署最多的 DB（手機、瀏覽器、car、IoT 都有）。傳統定位是 embedded、單檔案、不適合 multi-tenant 網路服務。但近年因 Cloudflare D1（serverless SQLite）、Turso（distributed SQLite）、Litestream（SQLite replication）等服務興起、出現「SQLite as production DB」的新場景。

## 定位：單檔案 embedded + 新興分散式 SQLite 生態

SQLite 跟 PostgreSQL / MySQL 是完全不同類別的工具：

- 不需要 server process（function-call API）
- 單一檔案（含 schema、data、index、metadata）
- 無 user / role / connection 概念
- 同 process 同時 read / write 受 file lock 限制

傳統定位：test fixture、CLI tool data store、mobile app（iOS / Android 內建）、edge device。

新興定位：edge serverless（Cloudflare D1）、distributed SQLite（Turso、rqlite）、replicated SQLite（Litestream）。

## 容量特性

**單檔案上限**：

- DB 最大 281 TB（理論）
- 實務上單表 > 100 GB 開始有 vacuum / index 問題

**並發寫**：

- WAL mode：可同時多 reader + 1 writer
- 不是真正多 writer concurrent
- 寫吞吐受 disk fsync 限制（通常 < 1K WPS）

**並發讀**：

- WAL mode 多 reader 可同時跑
- read-only workload 可以撐高吞吐

**Cross-process / cross-instance**：

- 不支援多個 process / instance 同時寫（會 corrupt）
- 需要分散時用 Litestream（replication）或 Turso（distributed）

## 適用場景

**1. Test fixture / CI 用 DB**：

- 整合測試需要的 fixed DB
- 比 spin up PostgreSQL container 快
- 對應 [1.4 Repository Adapter](/backend/01-database/repository-adapter/) 的 contract test 模式

**2. CLI tool / desktop app 內建 store**：

- git（.git/index）、Chrome（cookies / history）、iOS app
- 不需要 server、單檔案攜帶

**3. Mobile app（iOS / Android）**：

- iOS Core Data 底層用 SQLite
- Android 自帶 SQLite API
- offline-first app 的標準

**4. Single-instance backend（特殊場景）**：

- 流量小 + 不需要 HA
- 例：Sidekick / 個人 SaaS / family-scale app
- 配合 Litestream 做 backup / DR

**5. Edge / serverless（新興）**：

- Cloudflare D1：edge SQLite、跟 Workers 整合
- Turso：distributed SQLite、跨 region replication
- 跟傳統 SQLite 不同等級、是 *新的 product*

**6. Embedded device / IoT**：

- 沒網路 / 不能依賴 server
- SQLite 內建、無 external dependency

## 不適用場景

**1. 多 instance / 多 region web service**：

- SQLite 不能多 instance concurrent write
- 替代：PostgreSQL、Aurora、Spanner、CockroachDB

**2. 高寫入吞吐（> 1K WPS）**：

- fsync 限制
- 替代：任何 server-based RDBMS

**3. Multi-user 權限管理**：

- 無 user / role 概念
- 替代：PostgreSQL / MySQL

**4. 跨機器 transaction**：

- SQLite 是 single-machine
- 替代：分散式 SQL

**5. 大規模 production OLTP**：

- 沒人會把 GitHub 跑在 SQLite 上
- 替代：MySQL / PostgreSQL / Aurora

## 跟其他 vendor 的取捨

**vs PostgreSQL（作為 test DB）**：

- SQLite：快 spin up、SQL dialect 接近但有差異
- PostgreSQL：跟 production 一致、發現的 bug 真實
- 選 SQLite：speed of iteration、簡單 query
- 選 PostgreSQL：catch production-like bug、PostgreSQL-specific 特性測試

**vs Cloudflare D1**：

- SQLite（local）：單機、自管
- D1：edge serverless、跟 Workers 整合
- 選 SQLite：embedded / CLI / app 場景
- 選 D1：edge web service、跟 Cloudflare 生態整合

**vs Turso（distributed SQLite）**：

- SQLite：單機、單檔案
- Turso：distributed、跨 region replication、SQLite-compatible
- 選 SQLite：simple use case
- 選 Turso：需要 SQLite simplicity + 全球分散

**vs Litestream（replicated SQLite）**：

- SQLite：單檔案
- Litestream：把 SQLite 變成 streaming replicated 到 S3
- 選 Litestream：想要 SQLite simplicity + DR

**vs Firebase / Firestore（mobile app）**：

- SQLite：embedded、offline-first、無 sync
- Firestore：realtime、自動 sync、雲端 store
- 選 SQLite：offline-first、單機
- 選 Firestore：multi-device sync、realtime

## 容量規劃要點

**1. WAL mode 必須開**：

- default journal mode 是 rollback journal（每寫都 lock）
- WAL（Write-Ahead Log）讓多 reader 可同時跑
- `PRAGMA journal_mode = WAL`

**2. fsync 配置**：

- `PRAGMA synchronous = FULL`（durable、慢）
- `PRAGMA synchronous = NORMAL`（faster、少數情況可能掉資料）
- `PRAGMA synchronous = OFF`（最快、不安全）

**3. mmap 加速 read**：

- `PRAGMA mmap_size = 268435456`（256 MB）
- 把 DB 部分內容 mmap 進 RAM、加速 read

**4. Cache size**：

- `PRAGMA cache_size = -64000`（64 MB cache）
- 大 cache 對 read-heavy workload 有幫助

**5. Auto-vacuum**：

- 預設 off、delete 後檔案不縮小
- `PRAGMA auto_vacuum = INCREMENTAL` + 定期 `PRAGMA incremental_vacuum`

## 預計實作話題（後續擴充）

- WAL mode 工作原理
- Litestream + S3 replication 配置
- Cloudflare D1 適用判斷
- Turso distributed SQLite 模型
- iOS Core Data 底層 SQLite 細節
- SQLite as test fixture best practice
- SQLite migration（Alembic、Atlas、原生）

## 案例對照

SQLite 不在 09 case 庫的「規模化 vendor」類別、但作為 *embedded 跟 test* 廣泛使用：

- iOS Core Data：所有 iOS app 的 default DB
- Chrome / Firefox：cookie、history、bookmark
- Git：`.git/index`
- Cloudflare D1：edge serverless（新興 production 場景）
- Turso：distributed SQLite（新興 production 場景）

## 常見陷阱

- **default journal mode 不改 WAL**：read 跟 write 互相 block、performance 差
- **多 process / instance 同時寫同檔**：corruption
- **delete 後檔案沒縮小**：忘了 vacuum
- **synchronous=OFF 給 production**：power loss 可能掉資料
- **SQLite 跟 PostgreSQL 行為差異測試不足**：SQLite test 過、PostgreSQL production 出 bug（特別是 date / time、NULL 處理、type coercion）

## 下一步路由

- 平行：[PostgreSQL vendor](/backend/01-database/vendors/postgresql/) / [MySQL vendor](/backend/01-database/vendors/mysql/)（production server-based RDBMS）
- 上游：[1.4 Repository Adapter](/backend/01-database/repository-adapter/)（test fixture 模式）
- 官方：[SQLite Documentation](https://sqlite.org/docs.html)、[Litestream](https://litestream.io/)、[Turso](https://turso.tech/)、[Cloudflare D1](https://developers.cloudflare.com/d1/)
