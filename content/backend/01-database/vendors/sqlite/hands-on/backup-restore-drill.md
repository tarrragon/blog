---
title: "SQLite Backup Restore Drill"
date: 2026-05-21
description: "SQLite .backup、VACUUM INTO、restore validation、sidecar file handling 與 RPO / RTO note 的操作說明"
tags: ["backend", "database", "sqlite", "hands-on", "backup"]
---

SQLite backup restore drill 的核心責任是證明單檔 database 可以被一致備份並還原。這篇承接 [File lifecycle / backup boundary](/backend/01-database/vendors/sqlite/file-lifecycle-backup-boundary/)，把備份從概念轉成 artifact、validation query 與 RPO / RTO note。

本文的驗收標準是：你能從 live `app.db` 建立 backup，將它還原到隔離路徑，通過 `integrity_check` 與核心查詢，並記錄 restore duration。

## Prepare Source

Prepare source 的核心責任是建立一個有 WAL 與資料變化的 live database。若你已跑過 [local file quickstart](/backend/01-database/vendors/sqlite/hands-on/local-file-quickstart/)，可以直接沿用 `/tmp/sqlite-lab/app.db`。

```bash
mkdir -p /tmp/sqlite-lab/backup /tmp/sqlite-lab/restore
cd /tmp/sqlite-lab
sqlite3 app.db "PRAGMA journal_mode = WAL;"
sqlite3 app.db "INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key, created_at) VALUES (2, 100, 'backup-drill-1', '2026-05-21T01:00:00Z');"
```

這一步讓 source database 有新的資料。後續會用 backup snapshot 和 source 後續寫入做對照。

## Create Backup

Create backup 的核心責任是用 SQLite-aware 方法建立一致 snapshot。SQLite CLI `.backup` 會透過 SQLite backup API 產出目標檔案。

```bash
sqlite3 app.db ".backup 'backup/app-backup.db'"
sqlite3 backup/app-backup.db "PRAGMA integrity_check;"
```

預期 `integrity_check` 輸出 `ok`。這是最小 backup evidence。

`VACUUM INTO` 也可以產出 compact copy，適合想順便整理檔案大小的情境。

```bash
sqlite3 app.db "VACUUM INTO 'backup/app-vacuum-copy.db';"
sqlite3 backup/app-vacuum-copy.db "PRAGMA integrity_check;"
```

`.backup` 與 `VACUUM INTO` 都要在 runbook 中標明使用條件、耗時、目標路徑與失敗處理。正式環境還要記錄檔案大小、checksum 與 storage retention。

## Mutate Source After Backup

Mutate source 的核心責任是確認 backup 是時間點 snapshot。備份後對 source 寫入新資料，再用 restore 驗證 backup 保持原時間點。

```bash
sqlite3 app.db "INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key, created_at) VALUES (1, 777, 'after-backup-write', '2026-05-21T01:05:00Z');"
sqlite3 app.db "SELECT COUNT(*) FROM ledger_entries;"
sqlite3 backup/app-backup.db "SELECT COUNT(*) FROM ledger_entries;"
```

Source count 應比 backup count 多一筆。這個差異讓 RPO 討論具體化：backup 只保護到它建立的時間點。

## Restore Isolated Copy

Restore isolated copy 的核心責任是避免把演練和 source 混在一起。把 backup 複製到 restore path，所有 validation 都對 restore file 執行。

```bash
cp backup/app-backup.db restore/app-restored.db
sqlite3 restore/app-restored.db "PRAGMA integrity_check;"
sqlite3 restore/app-restored.db <<'SQL'
.headers on
.mode column
SELECT account_id, SUM(amount_cents) AS balance_cents
FROM ledger_entries
GROUP BY account_id
ORDER BY account_id;
SQL
```

正式 restore drill 還要啟動 application 指向 `restore/app-restored.db`，跑核心 read/write smoke test。若 application 需要 migration，也要確認 restore file 的 `PRAGMA user_version` 與 app version 相容。

## RPO / RTO Note

RPO / RTO note 的核心責任是把演練結果轉成服務承諾。RPO 是可接受資料遺失窗口，RTO 是可接受恢復時間。

| 指標 | 本 lab 記錄方式                          |
| ---- | ---------------------------------------- |
| RPO  | backup 建立時間到事故時間的資料差距      |
| RTO  | 從取得 backup 到 app smoke test 成功耗時 |

可以用 shell 的 `time` 記錄 restore duration。

```bash
time sqlite3 restore/app-restored.db "PRAGMA integrity_check;"
```

正式服務要把 RPO / RTO 寫進 [observability / runbook](/backend/01-database/vendors/sqlite/observability-runbook/)。

## Known Gap

Known gap 的核心責任是讓 lab 結果誠實。這個 drill 驗證 SQLite-aware backup 與 restore path；它尚未覆蓋 object storage credential、remote retention、large database restore time、encrypted disk、user device support flow 與 legal retention。

完成本篇後，下一步可以進入 [WAL busy reproduction](/backend/01-database/vendors/sqlite/hands-on/wal-busy-reproduction/) 觀察 writer boundary，或進入 [migration fixture lab](/backend/01-database/vendors/sqlite/hands-on/migration-fixture-lab/) 建立 schema change evidence。
