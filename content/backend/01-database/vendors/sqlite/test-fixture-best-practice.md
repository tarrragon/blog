---
title: "SQLite Test Fixture Best Practice"
date: 2026-05-21
description: "SQLite 作為 test fixture、repository contract test、production dialect gap、seed data、fixture snapshot 與 CI evidence 的操作判準"
tags: ["backend", "database", "sqlite", "testing", "fixture", "deep-article"]
---

> 本文是 [SQLite](/backend/01-database/vendors/sqlite/) overview 的 implementation-layer deep article。Overview 已說明 SQLite 適合作為 test fixture；本文聚焦 *如何用 SQLite 加速測試，同時保留 production database 的語意邊界*。

SQLite test fixture 的核心責任是讓 repository / adapter 測試快速、可重複、可攜帶。SQLite 的單檔特性讓 CI 可以快速建立 DB、載入 seed、跑 contract test；但它的 type affinity、SQL dialect、locking 與 constraint behavior 和 PostgreSQL / MySQL 不完全相同，因此 fixture 要被定位為一層測試工具，而非 production equivalence。

本文的判讀錨點是：SQLite fixture 適合驗證 application contract，不適合取代 production database compatibility test。若測試目標是 repository error mapping、domain invariant、migration fixture 或 deterministic seed，SQLite 很划算；若測試目標是 PostgreSQL extension、MySQL lock、query planner 或 SQL dialect，應使用 production-like container。

## Test fixture 的位置

SQLite fixture 的服務責任是提供快、穩定、可重建的本地資料狀態。它通常位於 unit test 與 full integration test 之間，承擔 repository adapter 的 contract test。

| 測試層級                 | SQLite 適合度 | 判讀                                                |
| ------------------------ | ------------- | --------------------------------------------------- |
| Pure unit test           | 低            | fake / in-memory object 通常更快                    |
| Repository contract      | 高            | 驗證 CRUD、constraint mapping、transaction behavior |
| Service integration      | 中            | 適合簡單流程，不覆蓋 production-specific SQL        |
| Production compatibility | 低            | 用 PostgreSQL / MySQL container 或 staging DB       |
| Migration smoke          | 中            | 適合 fixture migration，不代表 production DDL       |

這張表的重點是把測試目的說清楚。SQLite fixture 讓語言教材與 backend 教材接起來；語言端測 interface / adapter，backend 端保留 production database 的深度文章與 migration playbook。

## Fixture lifecycle

Fixture lifecycle 的核心責任是讓每次測試拿到已知資料狀態。常見策略有三種：每 test 建新 in-memory DB、每 suite 複製 template file、每 CI job 產生 versioned fixture。

| 策略                | 適合情境                           | 優點                      | 邊界                         |
| ------------------- | ---------------------------------- | ------------------------- | ---------------------------- |
| `:memory:` per test | 小 schema、快速 unit-like contract | 隔離最好、清理簡單        | 跨 connection / WAL 行為不同 |
| template file copy  | 中等 seed、需要真實檔案行為        | 快速、可測 file lifecycle | 要避免多 test 共用同一檔案   |
| generated fixture   | migration / seed 驗證              | 和 migration 同步         | CI 時間較長                  |
| read-only fixture   | 查詢 / report 測試                 | 避免 writer collision     | 不測 mutation                |

Fixture file 應和 schema version 綁定。檔名、metadata 或 `user_version` 要能回答「這個 fixture 對應哪個 migration 版本」，避免測試資料在多次 schema 變更後變成隱性技術債。

## Production dialect gap

Production dialect gap 的核心責任是避免 SQLite 測試通過後，PostgreSQL / MySQL production 出現不同語意。SQLite 的 dynamic typing、date / time representation、foreign key pragma、ALTER TABLE 支援與 lock model 都會影響測試可信度。

| Gap 類型      | SQLite 行為                               | Production 風險                                |
| ------------- | ----------------------------------------- | ---------------------------------------------- |
| Type affinity | 欄位有 affinity，值本身仍有 storage class | PostgreSQL / MySQL type error 沒被測到         |
| Date / time   | 常以 TEXT / REAL / INTEGER 表示           | timezone、precision、function 差異             |
| Foreign key   | 需要 `PRAGMA foreign_keys=ON`             | fixture 忘記開 FK，constraint bug 漏掉         |
| ALTER TABLE   | 支援 subset，複雜變更需 rebuild           | production migration 工具行為不同              |
| Locking       | single-file lock / single writer          | server DB connection / lock model 不同         |
| SQL feature   | extension / JSON / index 差異             | vendor-specific query 需要 production evidence |

這張表的用法是決定哪些測試留在 SQLite，哪些要升級到 production-like DB。Repository contract 可用 SQLite；query optimization、vendor SQL、online schema change、CDC、replication、pooling 都應回到 PostgreSQL / MySQL 章節。

## Contract test 設計

Contract test 的核心責任是讓不同 DB adapter 對 application 呈現同一組語意。SQLite fixture 測的是 application port 的行為，例如 duplicate key、not found、transaction rollback、pagination、domain invariant，而非底層 engine 的所有細節。

```text
Repository contract
├── Create / read / update / delete
├── Unique conflict → ErrAlreadyExists
├── Missing row → ErrNotFound
├── Transaction rollback restores domain invariant
├── Pagination order stable
└── Migration version matches fixture
```

如果 production adapter 是 PostgreSQL / MySQL，contract test 應至少在 nightly 或 CI matrix 裡跑一輪 production-like database。SQLite 提供快速回饋，production-like test 提供 dialect confidence。

## CI evidence

SQLite fixture 的 CI evidence 要證明資料狀態和 schema version 一致。測試失敗時，讀者要能知道是 application contract 失效、fixture 過期、migration 漏跑，還是 SQLite / production dialect gap。

| Evidence             | 目的                             |
| -------------------- | -------------------------------- |
| fixture version      | 對齊 migration / app release     |
| seed checksum        | 確認測試資料穩定                 |
| migration log        | 確認 fixture 可由 migration 重建 |
| contract test output | 確認 repository behavior         |
| dialect gap note     | 標示未覆蓋 production behavior   |

CI 產物不一定要很複雜，但要能被下一個維護者重建。SQLite fixture 的優勢是可攜帶；若 fixture 只能靠某個人的本機狀態生成，就失去教學與維護價值。

## Production 踩雷

### Case 1：共用同一個 `.db` 檔跑平行測試

平行測試共用檔案的核心風險是 test runner 製造和 production 不同的 writer collision。測試偶發 `SQLITE_BUSY`，團隊可能以為 application 有 race；實際上是測試隔離不足。

修正方向是 per-test temp DB 或 read-only template copy。需要測 WAL / busy 行為時，用專門 hands-on lab，讓一般 contract test 專注在 repository contract。

### Case 2：忘記開 foreign keys

Foreign key pragma 漏開的核心風險是 constraint bug 被 fixture 隱藏。SQLite foreign key enforcement 需要明確啟用；若 production DB 一定 enforce FK，fixture 也要在 connection initialization 中開啟。

修正方向是 baseline PRAGMA 和 startup assertion。每個 test DB open 後都跑 `PRAGMA foreign_keys` 並驗證結果。

### Case 3：SQLite fixture 掩蓋 vendor-specific SQL

Vendor-specific SQL 被 SQLite 掩蓋的核心風險是 query 到 production 才失敗。例如 PostgreSQL JSONB、partial index、full-text search 或 MySQL generated column、optimizer hint 都應在 vendor DB 測。

修正方向是把 SQL 分層。Portable repository contract 可以用 SQLite；vendor-specific query 要有 PostgreSQL / MySQL test container。

## 操作檢查清單

SQLite fixture 設計前要回答：

1. 這個測試驗證 application contract 還是 production dialect。
2. Fixture 是 in-memory、template copy、generated file 還是 read-only。
3. `PRAGMA foreign_keys`、`journal_mode`、`busy_timeout` 是否固定。
4. Fixture version 如何對齊 migration version。
5. Parallel test 是否每個 worker 有獨立 DB file。
6. 哪些 query 必須在 PostgreSQL / MySQL container 再跑。
7. CI artifact 是否保留 migration log 與 dialect gap note。

## 下一步路由

- 上游：[Repository Adapter](/backend/01-database/repository-adapter/)
- Sibling：[Schema Migration / Versioning](/backend/01-database/vendors/sqlite/schema-migration-versioning/)、[SQL Dialect and Index Limits](/backend/01-database/vendors/sqlite/sql-dialect-index-limits/)
- 操作：[Migration Fixture Lab](/backend/01-database/vendors/sqlite/hands-on/migration-fixture-lab/)
- 平行：[PostgreSQL](/backend/01-database/vendors/postgresql/)、[MySQL](/backend/01-database/vendors/mysql/)
- 官方：[SQLite Datatypes](https://www.sqlite.org/datatype3.html)、[SQLite STRICT Tables](https://www.sqlite.org/stricttables.html)、[SQLite PRAGMA](https://www.sqlite.org/pragma.html)
