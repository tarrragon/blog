---
title: "SQLite Mobile / Desktop Embedded Store"
date: 2026-05-21
description: "SQLite 在 mobile、desktop、CLI、browser profile 與 embedded device 中承擔 local formal state 的資料責任、backup、privacy 與 sync boundary"
tags: ["backend", "database", "sqlite", "mobile", "embedded", "deep-article"]
---

> 本文是 [SQLite](/backend/01-database/vendors/sqlite/) overview 的 implementation-layer deep article。Overview 已說明 SQLite 適合 mobile、desktop、CLI 與 embedded device；本文聚焦 *device-local formal state 的資料責任、backup、privacy 與 sync boundary*。

SQLite embedded store 的核心責任是讓 application process 在本機持有正式狀態。Mobile app、desktop app、browser profile、CLI tool 與 embedded device 常用 SQLite 保存 local data；這些資料可能只是 cache，也可能是使用者唯一資料來源。教學上要先判斷它是否承擔 [source of truth](/backend/knowledge-cards/source-of-truth/)，再決定 backup、sync、privacy 與 migration 責任。

本文的判讀錨點是：embedded SQLite 的 production boundary 不在 database server，而在 device lifecycle。OS backup、app upgrade、device loss、profile corruption、local PII、multi-device sync 與 user export / delete 都是資料庫責任的一部分。

## Embedded state model

Embedded state model 的核心責任是把 local database file 放回 application lifecycle。SQLite file 通常跟著 app sandbox、user profile、CLI config directory 或 device storage 存在；它的 owner 是 application，而非獨立 DBA。

| 場景              | SQLite 資料角色                            | 主要風險                                                |
| ----------------- | ------------------------------------------ | ------------------------------------------------------- |
| Mobile app        | offline state、draft、cache、local profile | app upgrade、device loss、cloud backup leakage          |
| Desktop app       | user profile、history、settings            | profile corruption、manual file copy、multi-version app |
| CLI tool          | local index、metadata、state cache         | command interruption、portable file path                |
| Browser / profile | cookies、history、bookmark 類資料          | privacy、profile migration、lock collision              |
| Embedded device   | offline event、sensor / config state       | power loss、flash wear、delayed sync                    |

這張表的重點是資料角色而非產品名稱。同樣是 SQLite file，cache 可以清掉重建；draft、local-only note、sensor event 或 user history 可能需要正式 backup / export / delete。

## Backup 與 export

Embedded backup 的核心責任是讓使用者或服務能從 device / profile failure 復原。Mobile / desktop / CLI 的 backup 路徑常和 OS backup、app export、cloud sync 或手動複製混在一起；SQLite file lifecycle 要明確。

| 路徑                 | 適合資料                   | 注意事項                                       |
| -------------------- | -------------------------- | ---------------------------------------------- |
| OS / device backup   | user-owned local state     | local PII、encryption、restore compatibility   |
| App export           | 使用者可攜資料             | schema version、format stability、privacy      |
| `.backup` / snapshot | application-managed backup | live DB consistency、WAL sidecar handling      |
| Cloud sync           | multi-device state         | conflict、server authority、delete propagation |

Backup 設計要先決定 restore target。Restore 到同 app version、未來 app version、或不同 device，會帶來不同 schema compatibility 與 privacy requirement。

## Privacy 與 local PII

Embedded SQLite 的 privacy 責任是治理 device-local data。資料在 server DB 中通常有 access log、IAM、DLP 與 retention policy；進入 SQLite file 後，風險轉到 device encryption、app sandbox、backup retention、debug export 與 support bundle。

| 風險           | 真實情境                         | 控制方向                                     |
| -------------- | -------------------------------- | -------------------------------------------- |
| Local PII      | profile、token、message、draft   | 最小化欄位、加密敏感值、限制 export          |
| Backup leakage | OS cloud backup 含 database file | 設定 backup exclusion 或加密                 |
| Support bundle | 使用者回報問題附上 DB            | scrub / redaction、只匯出必要 table          |
| Delete request | server 刪除但 device local 留存  | sync delete、local purge、retention evidence |

SQLite file 要進入資料保護盤點。若 local DB 保存敏感資料，應連到 [Data Protection](/backend/07-security-data-protection/data-protection-and-masking-governance/) 與 [Audit Log](/backend/knowledge-cards/audit-log/) 的相同問題，只是控制面改在 device / app。

## App upgrade 與 schema compatibility

App upgrade 的核心責任是保證新版 binary 能安全打開舊 database file。Mobile / desktop app 的使用者不會按照 backend deployment order 升級；同一時間可能存在多個 app version 與多個 DB schema version。

| 問題           | 設計策略                                                            |
| -------------- | ------------------------------------------------------------------- |
| 新 app 打舊 DB | startup migration、`user_version`、backup before migration          |
| 舊 app 打新 DB | backward-compatible column、feature gate、minimum supported version |
| 使用者降版     | export / import、read-only fallback、no-downgrade notice            |
| 多裝置不同版本 | sync protocol version、server-side compatibility                    |

這些策略要和 [Schema Migration / Versioning](/backend/01-database/vendors/sqlite/schema-migration-versioning/) 對齊。Embedded app 的 migration failure 通常直接影響使用者啟動體驗，因此 migration 要能快速、可恢復、可診斷。

## Sync boundary

Sync boundary 的核心責任是把 single-device SQLite 和 multi-device state 分開。SQLite 保存本地狀態；跨裝置同步需要 transport、identity、conflict resolution、delete propagation 與 server authority。

| Sync 需求        | SQLite 角色             | 下一步路由                                                                                  |
| ---------------- | ----------------------- | ------------------------------------------------------------------------------------------- |
| 單裝置 offline   | local source of truth   | SQLite + backup / export                                                                    |
| 多裝置同步       | local replica / cache   | [Local-first sync boundary](/backend/01-database/vendors/sqlite/local-first-sync-boundary/) |
| 即時多人協作     | local working copy      | server authority、CRDT、event log                                                           |
| Server reporting | local data upload / ETL | API sync、queue、analytics store                                                            |

當 sync 需求出現時，SQLite 仍可作為 local store，但不再單獨承擔完整資料一致性。完整性要由 sync protocol 與 server-side validation 補上。

## Production 踩雷

### Case 1：把 cache 當正式資料

Cache 被誤當正式資料的核心風險是清除 local DB 會造成不可恢復資料損失。許多 app 初期把 SQLite 當 cache；後來加入 draft、offline action 或 local-only setting，資料責任就改變了。

修正方向是逐 table 標示資料角色。Cache table 可清；formal state table 要 backup、migration、export 與 delete policy。

### Case 2：OS backup 帶走敏感資料

OS backup 的核心風險是 device-local PII 進入使用者或平台雲端備份。Server 端已刪除的資料，可能仍存在 device backup。

修正方向是決定哪些資料可被備份。Token、secret、敏感 PII 可排除或加密；user-owned content 則要提供 export / restore 語意。

### Case 3：App upgrade migration 失敗讓使用者卡在啟動頁

Startup migration 失敗的核心風險是使用者卡在 app 啟動前，且修復能力有限。SQLite file 在使用者裝置上，SRE 通常需要透過 app update、support bundle 或 restore flow 處理。

修正方向是保留 pre-migration snapshot、提供 safe mode、收集匿名 schema / error evidence，並避免長 migration 放在 cold start。

## 操作檢查清單

Embedded SQLite 設計要回答：

1. 每張 table 是 cache、formal state、derived state 還是 sync queue。
2. Database file 在 app / OS 的哪個 storage boundary。
3. OS backup 是否包含 database file。
4. 敏感欄位是否加密、排除或可清除。
5. App upgrade migration 是否有 pre-migration backup。
6. 使用者 export / delete / support bundle 如何處理 SQLite data。
7. Multi-device sync 是否有 conflict 與 server authority 設計。

## 下一步路由

- 上游：[SQLite overview](/backend/01-database/vendors/sqlite/)
- Sibling：[Local-first Sync Boundary](/backend/01-database/vendors/sqlite/local-first-sync-boundary/)、[Schema Migration / Versioning](/backend/01-database/vendors/sqlite/schema-migration-versioning/)
- 操作：[SQLite Hands-on](/backend/01-database/vendors/sqlite/hands-on/)
- 跨模組：[Data Protection](/backend/07-security-data-protection/data-protection-and-masking-governance/)
- 官方：[SQLite Appropriate Uses](https://www.sqlite.org/whentouse.html)、[SQLite Backup API](https://www.sqlite.org/backup.html)
