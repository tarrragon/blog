---
title: "SQLite Schema Migration and Versioning"
date: 2026-05-21
description: "SQLite schema migration、user_version、table rebuild、ALTER TABLE 限制、app release compatibility 與 migration evidence"
tags: ["backend", "database", "sqlite", "migration", "schema", "deep-article"]
---

> 本文是 [SQLite](/backend/01-database/vendors/sqlite/) overview 的 implementation-layer deep article。Overview 已說明 SQLite 的 embedded / single-file 定位；本文聚焦 *schema version、ALTER TABLE boundary、table rebuild migration 與 application release compatibility*。

SQLite schema migration 的核心責任是讓單檔資料庫隨 application release 安全演進。SQLite 沒有獨立 database server，也沒有 DBA 在 server 端統一套 migration；migration 常在 application startup、CLI command、mobile app upgrade 或 desktop app launch 時發生，因此 schema version、binary compatibility、backup 與 rollback 要放在同一個 release contract 中設計。

本文的判讀錨點是：SQLite migration 同時改資料庫檔案與 application 能讀的資料格式。只要使用者或服務可能拿舊 binary 打開新 database，或新 binary 打開舊 database，migration 就要處理 forward / backward compatibility，而不只是 SQL 成功執行。

## Version model

SQLite schema versioning 的服務責任是讓 application 能判斷 database file 目前處於哪個契約。SQLite 提供 `PRAGMA user_version` 作為 application-controlled integer；更複雜的服務也可以用 migration table 記錄多步驟版本、checksum 與執行時間。

```sql
PRAGMA user_version;
PRAGMA user_version = 2026052101;
```

| 方式              | 適合情境                           | 優點                          | 邊界                                 |
| ----------------- | ---------------------------------- | ----------------------------- | ------------------------------------ |
| `user_version`    | mobile / desktop / CLI single file | 簡單、內建、開檔即可讀        | 只能存一個整數，缺 migration history |
| migration table   | small backend、多人維護 schema     | 可記錄每步 migration 與 owner | 需要先建立 table 與初始化流程        |
| external manifest | fixture、artifact、read-only DB    | 可和 release artifact 綁定    | DB file 本身不含完整 history         |

Version model 要在第一版就定義。沒有版本欄位的 SQLite file 仍可 migration，但 application 只能靠 introspection 猜 schema，會讓 upgrade / downgrade runbook 複雜化。

## ALTER TABLE boundary

SQLite ALTER TABLE 的核心責任是處理有限集合的 schema 變更。官方文件說明 SQLite 支援 rename table、rename column、add column、drop column；更複雜的變更要走 table rebuild pattern。

| 變更類型                 | SQLite 支援形態                            | 操作判讀                                     |
| ------------------------ | ------------------------------------------ | -------------------------------------------- |
| Rename table / column    | 直接 ALTER，版本差異影響 trigger / view    | 需要測 trigger、view、FK reference           |
| Add column               | 多數情境很快，受 default / constraint 限制 | 適合 expand migration                        |
| Drop column              | 需要檢查 index、constraint、trigger、view  | 可能掃資料，需 maintenance window            |
| Change type / constraint | 通常走 table rebuild                       | 需要完整 copy、foreign key check、validation |

SQLite schema 存在 `sqlite_schema` 的 SQL text 中；這讓檔案格式簡潔，但也讓 ALTER TABLE 的安全條件和 server SQL 不同。Production migration 應優先用官方建議的 rebuild procedure，而非直接修改 `sqlite_schema`。

## Table rebuild migration

Table rebuild migration 的服務責任是安全完成 SQLite 直接 ALTER 難以表達的變更。官方 ALTER TABLE 文件建議的 generalized procedure 是建立新 table、copy data、drop old、rename new、重建 index / trigger / view、跑 foreign key check、commit。

```sql
BEGIN;
PRAGMA foreign_keys = OFF;

CREATE TABLE new_orders (
  id INTEGER PRIMARY KEY,
  status TEXT NOT NULL,
  paid_at TEXT
);

INSERT INTO new_orders (id, status, paid_at)
SELECT id, status, paid_at
FROM orders;

DROP TABLE orders;
ALTER TABLE new_orders RENAME TO orders;

PRAGMA foreign_key_check;
PRAGMA user_version = 2026052101;
COMMIT;
PRAGMA foreign_keys = ON;
```

這段範例是教學骨架，而非可直接複製到所有 schema 的萬用腳本。真實 migration 要先保存 index、trigger、view 與 FK reference，再依 schema 重建；有資料量時還要考慮 copy duration、disk 空間與 rollback snapshot。

## App release compatibility

SQLite migration 的 application compatibility 來自 binary 與 DB file 的同步問題。Server SQL migration 通常有 central deploy order；SQLite file 可能跟著使用者裝置、desktop profile、CLI artifact 或 edge deploy 留在不同版本。

| 相容性問題                  | 真實情境                        | 設計策略                                        |
| --------------------------- | ------------------------------- | ----------------------------------------------- |
| 新 app 打開舊 DB            | 使用者升級 app                  | startup migration、read compatibility           |
| 舊 app 打開新 DB            | 使用者 downgrade、同步舊 binary | 保留 backward-compatible column、feature gate   |
| 多裝置不同版本              | local-first / sync app          | sync protocol version、server authority         |
| fixture 與 production drift | test fixture 沒更新             | fixture version、contract test、migration smoke |

Compatibility 的核心是先決定支援範圍。Mobile app 常要支援舊版資料庫升級；internal CLI 可能只支援最新版本；test fixture 則需要每次 migration 後重新產生。

## Migration evidence

Migration evidence 的責任是證明 schema 變更已完成且資料仍可用。SQLite migration evidence 比 server DB 簡單，但更依賴 application-level validation。

| Evidence          | 目的                         | 範例                          |
| ----------------- | ---------------------------- | ----------------------------- |
| schema version    | 確認 DB file 契約            | `PRAGMA user_version`         |
| row count         | 確認 copy / rebuild 無漏資料 | `SELECT COUNT(*) FROM orders` |
| domain query      | 確認重要 business invariant  | unpaid / paid 狀態數量        |
| foreign key check | 確認 reference integrity     | `PRAGMA foreign_key_check`    |
| integrity check   | 檢查 DB 結構                 | `PRAGMA integrity_check`      |
| backup marker     | 回退點                       | pre-migration `.backup` file  |

這些 evidence 應接到 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 或 release note。SQLite migration 失敗時，最清楚的 rollback 通常是回到 migration 前 snapshot，而非在同一檔案上繼續試錯。

## Production 踩雷

### Case 1：startup migration 讓 app 啟動卡住

Startup migration 的核心風險是把長時間 table rebuild 放在使用者啟動路徑。小表新增 column 可能很快；大表 rebuild、index 重建或 vacuum 類操作會讓 app 啟動、CLI command 或 API cold start 變慢。

修正方向是先估資料量。短 migration 可在 startup；長 migration 要有 explicit command、progress、backup 與 rollback route。

### Case 2：fixture schema 升級漏掉 production gap

Fixture schema drift 的核心風險是測試 DB 和 production DB 的 dialect / constraint 不一致。SQLite fixture 很快，但 production 若是 PostgreSQL / MySQL，type、date、NULL、constraint 與 transaction 行為都可能不同。

修正方向是把 SQLite fixture 明確標成 contract test 層。Repository error mapping、domain invariant 可以用 SQLite；production-specific SQL 要用 production database container 驗證。

### Case 3：直接改 `sqlite_schema`

直接改 `sqlite_schema` 的核心風險是產生語法正確但語意破壞的 database file。SQLite 官方文件提供 writable schema route，但同時強調錯誤修改可能讓 database corrupt / unreadable。

修正方向是讓 writable schema 成為最後手段。一般 migration 優先用 ALTER TABLE 或 table rebuild；需要特殊修復時先複製原檔，在副本驗證。

## 操作檢查清單

SQLite migration runbook 至少要記錄：

1. DB file 目前 `user_version` 與 application release version。
2. Migration 是否可重入、是否可中斷後恢復。
3. Migration 前 backup / snapshot 位置。
4. 需要 table rebuild 的 table、資料量、index / trigger / view 清單。
5. Validation query、row count、foreign key check、integrity check。
6. 舊 binary / 新 binary 的相容策略。
7. Fixture DB 是否已重新產生並被 contract test 使用。

## 下一步路由

- 上游：[SQLite overview](/backend/01-database/vendors/sqlite/)
- 操作：[Migration fixture lab](/backend/01-database/vendors/sqlite/hands-on/migration-fixture-lab/)
- 平行：[Test Fixture Best Practice](/backend/01-database/vendors/sqlite/test-fixture-best-practice/)
- 遷移：[SQLite to PostgreSQL](/backend/01-database/vendors/sqlite/migrate-to-postgresql/)
- 官方：[SQLite ALTER TABLE](https://www.sqlite.org/lang_altertable.html)、[SQLite PRAGMA](https://www.sqlite.org/pragma.html)
