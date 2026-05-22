---
title: "SQLite Hands-on 操作路線"
date: 2026-05-21
description: "SQLite local file lab、backup / restore drill、WAL busy reproduction、migration fixture、D1 / Turso preview 的操作型章節設計"
tags: ["backend", "database", "sqlite", "hands-on"]
---

SQLite hands-on 操作路線的核心責任是把單檔正式狀態轉成可演練流程。這一層對齊 LLM `hands-on/`：讀者能建立一個 SQLite 檔案、製造 WAL / lock 訊號、跑 backup / restore、套 migration，並知道何時該升級到 server SQL 或 edge SQLite。

## 章節列表

| 章節                                            | 主題                                                         | 產出 artifact                                 |
| ----------------------------------------------- | ------------------------------------------------------------ | --------------------------------------------- |
| [Local file quickstart](local-file-quickstart/) | 建立 `.db`、schema、seed data、basic query                   | database file、schema version、query sample   |
| [Backup restore drill](backup-restore-drill/)   | `.backup` / `VACUUM INTO` / restore validation               | backup file、restore record、validation query |
| [WAL busy reproduction](wal-busy-reproduction/) | long transaction、`SQLITE_BUSY`、checkpoint growth           | busy error sample、WAL size evidence          |
| [Migration fixture lab](migration-fixture-lab/) | `user_version`、table rebuild、fixture snapshot              | migration log、fixture DB、rollback note      |
| [D1 / Turso preview lab](d1-turso-preview-lab/) | local SQLite 到 edge SQLite product 的 compatibility preview | export / import note、compatibility gap       |

## 設計原則

SQLite hands-on 章節要以檔案生命週期為中心。操作指令只在能產出 evidence 時出現；每篇都要回答 database file 在哪裡、sidecar file 如何處理、restore 如何驗證，以及 application release 如何知道它仍相容。

## 引用路徑

- 上游：[SQLite overview](/backend/01-database/vendors/sqlite/)
- Structure：[SQLite Teaching Structure](/backend/01-database/vendors/sqlite/teaching-structure/)
- Deep article：[File lifecycle / backup boundary](/backend/01-database/vendors/sqlite/file-lifecycle-backup-boundary/)
