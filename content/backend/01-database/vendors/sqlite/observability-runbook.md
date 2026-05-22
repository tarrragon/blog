---
title: "SQLite Observability and Runbook"
date: 2026-05-21
description: "SQLite production runbook、backup evidence、WAL growth、busy errors、disk usage、restore drill 與 incident route"
tags: ["backend", "database", "sqlite", "observability", "runbook"]
---

SQLite observability and runbook 的核心責任是把低操作成本服務補成可交接的 production evidence。SQLite 的元件少，但正式服務仍需要觀測 busy errors、WAL growth、backup freshness、restore drill、disk usage、migration result、file permission 與 application-level query health。

本文的判讀錨點是：SQLite 的 observability 要貼近 file、process、filesystem 與 application。它通常沒有 server DB 那種長駐監控平面，因此 runbook 要把 signal 從 app metrics、log、scheduled job、file metadata 與 restore evidence 裡組出來。

## Signal Inventory

Signal inventory 的核心責任是列出 SQLite production 化後最能預告事故的訊號。這些訊號要放進 dashboard、log search 或 scheduled report，讓事故前後都能直接查。

| Signal                 | 來源                   | 代表風險                          | 建議反應                              |
| ---------------------- | ---------------------- | --------------------------------- | ------------------------------------- |
| `SQLITE_BUSY` count    | app log / metric       | writer contention、long reader    | 查 transaction duration、busy timeout |
| WAL file size          | filesystem metric      | checkpoint lag、long reader       | 查 checkpoint result、reader age      |
| Backup age             | scheduled job metric   | RPO 擴大                          | 重跑 backup、檢查 storage             |
| Restore drill age      | release evidence       | RTO 信心下降                      | 排程 restore drill                    |
| Disk free              | host / platform metric | write failure、checkpoint failure | 清理、擴容、降級寫入                  |
| Migration version      | app startup / metadata | schema drift                      | block release、跑 validation          |
| Integrity check result | maintenance job        | corruption / storage issue        | 進入 restore decision                 |

`SQLITE_BUSY` 是 writer boundary 的最直接訊號。它可能代表長交易、read cursor 未關、parallel test 共用 DB、checkpoint 壓力或 write burst；runbook 要先查 query duration 與 transaction boundary，再調 busy timeout。

WAL size 是 checkpoint 與 reader 壓力的綜合訊號。WAL 持續成長時，先確認是否有長 reader、backup process、未完成 transaction 或 checkpoint 失敗；接著才考慮手動 checkpoint。

Backup age 是 RPO 的可觀測版本。若目標 RPO 是 5 分鐘，dashboard 就要顯示 last successful backup / replica time 與警戒線。

## Backup Evidence

Backup evidence 的核心責任是證明資料可被拿回來。SQLite backup 的完成標準包含成功建立備份、保存 sidecar 語意、恢復到新路徑、通過 integrity check、跑 application smoke test。

| Evidence               | 最小內容                               | 失敗時路由                           |
| ---------------------- | -------------------------------------- | ------------------------------------ |
| Backup job result      | timestamp、duration、file size、target | 重跑 job、檢查 credential / disk     |
| Restore artifact       | restored path、checksum、row count     | 回前一份 backup、檢查 WAL / snapshot |
| Integrity result       | `PRAGMA integrity_check;`              | 停止寫入、進入 corruption triage     |
| Application smoke test | 啟動、讀核心頁、寫測試資料             | rollback、保留 evidence              |
| Retention note         | 保存天數、刪除策略、legal hold         | 更新 data protection policy          |

SQLite 官方 [backup API](https://www.sqlite.org/backup.html) 與 CLI `.backup` 是備份設計的基礎路由。WAL mode 下，直接複製單一 `.db` 檔容易漏掉 sidecar file 的時序；runbook 應使用 SQLite-aware backup 或經過 checkpoint / stop-the-world 的 snapshot。

```bash
sqlite3 app.db ".backup 'backup/app-2026-05-21.db'"
sqlite3 backup/app-2026-05-21.db "PRAGMA integrity_check;"
```

這段命令提供最小 restore evidence 的起點。正式演練要把備份檔複製到隔離路徑，使用相同 application version 啟動，跑核心 read/write smoke test，再記錄耗時與失敗條件。

## Migration Evidence

Migration evidence 的核心責任是讓 SQLite schema change 可回退、可審查、可交接。單檔 DB 在使用者裝置或服務節點上升級時，migration 失敗會直接影響啟動、資料讀取與同步。

| Evidence               | 內容                                     | Release gate                      |
| ---------------------- | ---------------------------------------- | --------------------------------- |
| Schema version         | `PRAGMA user_version` 或 migration table | app startup 比對 expected version |
| Pre-migration snapshot | backup path、size、checksum              | migration 前完成                  |
| Validation query       | row count、FK check、domain invariant    | migration 後立即執行              |
| Smoke test             | 核心 read/write workflow                 | app release gate                  |
| Rollback route         | restore snapshot 或 block startup        | migration 失敗時啟動              |

Migration log 要包含版本、耗時、row count、錯誤、validation result 與 rollback decision。若 SQLite file 位於 end-user device，log 還要能被使用者支援流程收集，避免事故只停在「app 開不起來」。

```sql
PRAGMA user_version;
PRAGMA foreign_key_check;
SELECT COUNT(*) FROM orders;
```

這些 query 是 migration 後的最小 evidence。正式服務要再補 domain-specific invariant，例如「所有 active subscription 都有 owner」、「所有 pending mutation 都有 idempotency key」。

## Incident Runbook

Incident runbook 的核心責任是把 SQLite 事故分流到正確處置。SQLite 常見事故包含 disk full、busy storm、WAL growth、bad migration、corruption suspicion、backup failure 與 permission error。

| Incident          | 第一個判讀問題                            | 立即處置                                       |
| ----------------- | ----------------------------------------- | ---------------------------------------------- |
| Busy storm        | 有長 transaction 或 write burst 嗎        | 暫停非必要寫入、查 transaction duration        |
| Disk full         | DB / WAL / backup 哪個吃掉空間            | 停止寫入、清理 backup、擴容                    |
| WAL growth        | checkpoint 被誰阻擋                       | 查 reader、跑 checkpoint evidence              |
| Bad migration     | schema version 與 app version 是否一致    | 停止 rollout、restore snapshot、保留 failed DB |
| Corruption signal | integrity check 是否失敗                  | 進入 read-only、restore last good backup       |
| Backup failure    | credential、network、destination 是否可用 | 切換 destination、補跑 restore drill           |

Busy storm 要先保護使用者操作。可以降低 write endpoint、停用背景 job、延長 retry backoff，然後用 log 查最長 transaction 與最多重試的 query。

Disk full 要先停止寫入。SQLite 在 disk full 時可能讓 write / checkpoint / backup 同時失敗；runbook 要保留剩餘空間、DB file、WAL file、backup directory 與 tmp directory 的大小。

Bad migration 要保留 failed artifact。先複製 failed DB 到 evidence path，記錄 schema version、app version、migration id、validation error，再執行 rollback。

## Dashboard and Alert Route

Dashboard and alert route 的核心責任是讓 SQLite 被納入正式服務的可觀測系統。SQLite signal 常來自 application，因此 metric 命名要接近操作問題。

| Metric name example             | 類型      | 用途                          |
| ------------------------------- | --------- | ----------------------------- |
| `sqlite_busy_total`             | counter   | writer contention             |
| `sqlite_query_duration_ms`      | histogram | slow query / long transaction |
| `sqlite_wal_size_bytes`         | gauge     | checkpoint pressure           |
| `sqlite_backup_age_seconds`     | gauge     | RPO evidence                  |
| `sqlite_restore_drill_age_days` | gauge     | RTO confidence                |
| `sqlite_disk_free_bytes`        | gauge     | disk full prevention          |
| `sqlite_migration_version`      | gauge     | schema drift                  |

Alert 要連到 runbook，並提供可執行的第一步。每個 alert 至少要有 owner、severity、first query、rollback condition 與 escalation route。

Log schema 要保留 query category，而非只記原始 SQL。正式服務通常應避免把完整 SQL 與 PII 直接寫入 log；可以記 operation name、duration、row count、error code、busy retry count 與 correlation id。

## Handoff

Handoff 的核心責任是讓下一個維護者知道 SQLite service 的邊界。交接文件要把「誰負責檔案」、「誰負責備份」、「誰能執行 restore」、「何時升級資料庫」寫清楚。

最小 handoff 包含：

1. Database file path、sidecar file policy、journal mode 與 PRAGMA baseline。
2. Backup command、destination、retention、last restore drill。
3. Migration command、schema version、rollback route。
4. Alert list、dashboard link、incident owner。
5. Known limits：writer concurrency、file size、edge / sync boundary。
6. Next route：PostgreSQL、D1 / Turso、Litestream / LiteFS 的評估條件。

Handoff 的重點是把低操作成本保留下來。SQLite 的好處來自少元件；可交接文件讓少元件不等於少 evidence。

## 下一步路由

Observability / runbook 完成後，下一步要接到具體演練。Backup 與 restore 讀 [SQLite backup restore drill](/backend/01-database/vendors/sqlite/hands-on/backup-restore-drill/)；WAL 與 busy 讀 [WAL busy reproduction](/backend/01-database/vendors/sqlite/hands-on/wal-busy-reproduction/)；正式服務的 evidence 可對齊 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 與 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。
