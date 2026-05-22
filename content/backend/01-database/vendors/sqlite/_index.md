---
title: "SQLite"
date: 2026-05-13
description: "embedded、單檔案、test / CLI / edge 場景的標準選擇、近年因 Cloudflare D1 / Turso 等服務復興"
weight: 6
tags: ["backend", "database", "vendor", "sqlite", "embedded"]
---

SQLite 是世界上部署最多的 DB（手機、瀏覽器、car、IoT 都有）。傳統定位是 embedded、單檔案與低操作成本資料庫；multi-tenant 網路服務通常會先看 PostgreSQL、MySQL 或 managed SQL。但近年因 Cloudflare D1（serverless SQLite）、Turso（distributed SQLite）、Litestream（SQLite replication）等服務興起，出現「SQLite as production DB」的新場景。

## 教學路線：單檔正式狀態與 local-first

SQLite 服務頁的教學目標是把單機、單檔案、edge、desktop、test fixture 的正式狀態責任說清楚。讀者讀完後要能判斷 SQLite 何時是 production state，何時要轉向 server database、edge KV 或分散式 SQLite 變體。

| 學習段               | 核心問題                                                                          | 對應段落                         |
| -------------------- | --------------------------------------------------------------------------------- | -------------------------------- |
| Embedded state       | 單檔案資料庫如何成為 [source of truth](/backend/knowledge-cards/source-of-truth/) | 定位、適用場景                   |
| Local-first          | device、edge、desktop、test fixture 的責任形狀                                    | 適用場景、案例對照               |
| Writer boundary      | single writer、file lock、WAL 如何決定服務上限                                    | 容量特性、容量規劃要點           |
| Distributed variants | Turso、LiteFS、rqlite、D1 解決哪類同步或 edge 問題                                | 跟其他 vendor 的取捨、章節群結構 |
| 替代路由             | 何時升級 PostgreSQL、MySQL、DynamoDB 或 edge KV                                   | 不適用場景、下一步路由           |

## 定位：單檔案 embedded + 新興分散式 SQLite 生態

SQLite 跟 PostgreSQL / MySQL 承擔不同層級的資料責任：

- 以 function-call API 使用，省掉 server process
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
- 寫入仍由 single writer boundary 控制
- 寫吞吐受 disk fsync 限制（通常 < 1K WPS）

**並發讀**：

- WAL mode 多 reader 可同時跑
- read-only workload 可以撐高吞吐

**Cross-process / cross-instance**：

- 多個 process / instance 同時寫同一檔案會破壞 single writer boundary
- 需要分散時用 Litestream（replication）或 Turso（distributed）

## 適用場景

**1. Test fixture / CI 用 DB**：

- 整合測試需要的 fixed DB
- 比 spin up PostgreSQL container 快
- 對應 [1.4 Repository Adapter](/backend/01-database/repository-adapter/) 的 contract test 模式

**2. CLI tool / desktop app 內建 store**：

- Chrome / Firefox（cookies、history、bookmark）、Fossil SCM、iOS app
- 省掉 server、單檔案攜帶

**3. Mobile app（iOS / Android）**：

- iOS Core Data 底層用 SQLite
- Android 自帶 SQLite API
- offline-first app 的標準

**4. Single-instance backend（特殊場景）**：

- 流量小 + HA 由備份 / restore / redeploy 流程承擔
- 例：Sidekick / 個人 SaaS / family-scale app
- 配合 Litestream 做 backup / DR

**5. Edge / serverless（新興）**：

- Cloudflare D1：edge SQLite、跟 Workers 整合
- Turso：distributed SQLite、跨 region replication
- 跟傳統 SQLite 不同等級、是 *新的 product*

**6. Embedded device / IoT**：

- 沒網路或要降低 server 依賴
- SQLite 內建、無 external dependency

## 不適用場景

**1. 多 instance / 多 region web service**：

- SQLite 的單檔模型以單 instance writer 為主要邊界
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

- 大規模 production OLTP 需要 server database 的 HA、replica、權限與操作邊界
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

**1. WAL mode 是 production baseline**：

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

## 章節群結構

SQLite 章節群的責任是把單檔正式狀態、embedded process、writer boundary、backup / restore、test fixture、local-first 與 edge SQLite 變體拆成可教學路線。完整結構見 [SQLite Teaching Structure](teaching-structure/)；下表列出目前已建立的 deep article、hands-on 與 migration route。

| 層級              | 文件                                                                           | 狀態     | 教學責任                                                  |
| ----------------- | ------------------------------------------------------------------------------ | -------- | --------------------------------------------------------- |
| 結構總覽          | [Teaching Structure](teaching-structure/)                                      | 已有正文 | 對齊 PG / MySQL 與 LLM 架構，固定 SQLite 後續讀法         |
| Core deep         | [File lifecycle / backup boundary](file-lifecycle-backup-boundary/)            | 已有正文 | WAL sidecar、backup API、restore drill、corruption route  |
| Hands-on          | [Hands-on 操作路線](hands-on/)                                                 | 已有正文 | local file、backup restore、WAL busy、migration fixture   |
| Concurrency       | [WAL concurrency / locking](wal-concurrency-locking/)                          | 已有正文 | single writer、file lock、`SQLITE_BUSY`、checkpoint       |
| Performance       | [PRAGMA tuning / performance](pragma-tuning-performance/)                      | 已有正文 | journal、sync、cache、mmap、vacuum 的取捨                 |
| Migration         | [Schema migration / versioning](schema-migration-versioning/)                  | 已有正文 | app release、schema version、rollback、migration evidence |
| Testing           | [Test fixture best practice](test-fixture-best-practice/)                      | 已有正文 | SQLite 測試便利性與 production dialect gap                |
| Embedded app      | [Mobile / desktop embedded store](mobile-desktop-embedded-store/)              | 已有正文 | device local state、privacy、backup、app version          |
| Sync              | [Local-first sync boundary](local-first-sync-boundary/)                        | 已有正文 | 多裝置同步、conflict、server authority                    |
| Edge variant      | [D1 / Turso / libSQL comparison](d1-turso-libsql-comparison/)                  | 已有正文 | edge SQLite 產品與 local SQLite 的責任差異                |
| Replication       | [Litestream / LiteFS replication](litestream-litefs-replication/)              | 已有正文 | continuous backup、read replica、failover boundary        |
| SQL compatibility | [SQL dialect and index limits](sql-dialect-index-limits/)                      | 已有正文 | type affinity、index、constraint、PostgreSQL / MySQL gap  |
| Operations        | [Observability / runbook](observability-runbook/)                              | 已有正文 | busy errors、WAL growth、backup evidence、incident route  |
| Migration route   | [SQLite to PostgreSQL](migrate-to-postgresql/)                                 | 已有正文 | 多 tenant、權限、HA、audit 出現時的升級路線               |
| Migration route   | [SQLite to D1 / Turso](migrate-to-d1-turso/)                                   | 已有正文 | edge / serverless 化路線                                  |
| Migration route   | [PostgreSQL to SQLite simplification](migrate-from-postgresql-simplification/) | 已有正文 | single-user / embedded 工具的反向簡化路線                 |

章節群的讀法是先讀 file lifecycle，再按壓力選 deep article。若問題是 write contention，讀 WAL locking；若問題是測試，讀 test fixture；若問題是 edge / serverless，讀 D1 / Turso comparison；若問題是服務長大，讀 SQLite to PostgreSQL migration。

## Anti-recommendation 與升級路由

SQLite 的低操作成本容易讓團隊忽略它的 writer boundary。這一段先說何時維持 SQLite，再說何時升級到 server SQL、edge SQLite 變體或 managed KV。

| 機制 / 路線           | 維持簡單設計的條件                                      | 升級訊號                                               | 主要引用路徑                                                                                                       |
| --------------------- | ------------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| Local SQLite          | 單 process、單 writer、資料可用檔案備份保護             | 多 instance 寫入、需要 HA、需要資料層權限              | [Database](/backend/knowledge-cards/database/)、[Source of Truth](/backend/knowledge-cards/source-of-truth/)       |
| WAL + file backup     | read-heavy、寫入量低、RPO 可接受定期 snapshot           | restore 演練失敗、WAL growth 失控、RPO / RTO 變嚴格    | [RPO](/backend/knowledge-cards/rpo/)、[RTO](/backend/knowledge-cards/rto/)                                         |
| Litestream / LiteFS   | 單 primary 寫入清楚、主要需求是 backup 或 read replica  | 需要多地 active write、跨 region transaction           | [Replication Lag](/backend/knowledge-cards/replication-lag/)、[Stale Read](/backend/knowledge-cards/stale-read/)   |
| Cloudflare D1 / Turso | edge / serverless 生態已是主平台                        | SQL 特性、migration、observability 或 vendor 限制卡住  | [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)                                              |
| PostgreSQL / MySQL    | application 已進入多服務、多 tenant、權限與備份治理需求 | schema migration、connection、audit 與 failover 成主題 | [PostgreSQL vendor](/backend/01-database/vendors/postgresql/)、[MySQL vendor](/backend/01-database/vendors/mysql/) |

SQLite 的簡單路徑是讓檔案生命週期成為正式操作流程。只要單一 writer、備份、restore、migration 與 file ownership 都能被 runbook 控制，SQLite 可以是正式狀態，而非臨時 cache。

升級到 server SQL 的訊號是操作責任超過檔案邊界。當團隊需要資料庫帳號、權限分層、read replica、線上 schema migration、集中 audit 或跨 instance failover 時，PostgreSQL / MySQL / Aurora 會比繼續包裝 SQLite 更清楚。

## 已知 limitation 與後續路由

SQLite overview 目前已完成服務判斷與章節群正文路由。File lifecycle、WAL locking、PRAGMA tuning、schema migration、test fixture、local-first sync、edge product 差異、observability、hands-on 與 migration route 都已有對應正文；下一輪審查可集中在案例補強、引用精度與跨章重複整理。

## 案例對照

SQLite 不在 09 case 庫的「規模化 vendor」類別、但作為 *embedded 跟 test* 廣泛使用：

- iOS Core Data：所有 iOS app 的 default DB
- Chrome / Firefox：cookie、history、bookmark
- Fossil SCM：repository metadata 與 application-file use case
- Cloudflare D1：edge serverless（新興 production 場景）
- Turso：distributed SQLite（新興 production 場景）

## 常見陷阱

- **default journal mode 不改 WAL**：read 跟 write 互相 block、performance 差
- **多 process / instance 同時寫同檔**：corruption
- **delete 後檔案沒縮小**：忘了 vacuum
- **synchronous=OFF 給 production**：power loss 可能掉資料
- **SQLite 跟 PostgreSQL 行為差異測試不足**：SQLite test 過、PostgreSQL production 出 bug（特別是 date / time、NULL 處理、type coercion）

## 下一步路由

- 完整 T1 對照：[01-database vendors index](/backend/01-database/vendors/)
- 平行：[PostgreSQL vendor](/backend/01-database/vendors/postgresql/) / [MySQL vendor](/backend/01-database/vendors/mysql/)（production server-based RDBMS）
- 上游：[1.4 Repository Adapter](/backend/01-database/repository-adapter/)（test fixture 模式）
- 結構：[SQLite Teaching Structure](/backend/01-database/vendors/sqlite/teaching-structure/)（完整章節群與寫作順序）
- 操作：[SQLite Hands-on](/backend/01-database/vendors/sqlite/hands-on/)（local file、backup restore、WAL busy reproduction、migration fixture、D1 / Turso preview）
- 深入：[SQLite file lifecycle 與 backup boundary](/backend/01-database/vendors/sqlite/file-lifecycle-backup-boundary/)（WAL、backup、restore、file ownership）
- 官方：[SQLite Documentation](https://sqlite.org/docs.html)、[Litestream](https://litestream.io/)、[Turso](https://turso.tech/)、[Cloudflare D1](https://developers.cloudflare.com/d1/)
