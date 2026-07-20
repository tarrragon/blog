---
title: "Database Migration"
date: 2026-06-26
description: "用版本化的 SQL 腳本管理資料庫 schema 的變更歷程，讓 schema 變更可追蹤、可重現、可回退"
weight: 45
tags: ["infra", "knowledge-cards", "database", "migration"]
---

Database migration 是用版本化的腳本管理資料庫 schema 變更的做法。每次 schema 變更（加欄位、改索引、拆表、改資料型別）寫成一份獨立的 migration 檔案，按順序套用。這讓 schema 的演進跟程式碼一樣有版本歷史、可追蹤、可在新環境重現。在 [RDS](/infra/knowledge-cards/rds/) 等受管資料庫上執行時，schema 變更仍需注意鎖表與停機風險。

## 概念位置

migration 解決的問題是「資料庫的 schema 怎麼從 A 狀態安全地變成 B 狀態」。沒有 migration 時，schema 變更靠在 [phpMyAdmin](/infra/knowledge-cards/phpmyadmin/) 或 CLI 手動執行 SQL，改了什麼只存在操作者的記憶裡。有 migration 時，每次變更都是 repo 裡的一份檔案，跟程式碼一起 commit、一起 review。

## 可觀察訊號

接手專案時，如果 repo 裡有 `migrations/` 目錄（或框架特定的路徑如 Laravel 的 `database/migrations/`、Rails 的 `db/migrate/`），代表專案使用 migration。如果 repo 裡只有一份 `schema.sql` 或完全沒有 schema 相關檔案，代表 schema 變更是手動的——這時候建立 migration 紀律是接手後的優先事項之一。

## 設計責任

每份 migration 檔案包含兩個方向：

- **UP**（套用）：執行 schema 變更的 SQL
- **DOWN**（回退）：撤銷這次變更的 SQL（不是所有變更都能完美回退，如刪除欄位後資料就沒了）

```sql
-- migrations/2026-06-26-001-add-users-email-verified.sql

-- UP
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;

-- DOWN
ALTER TABLE users DROP COLUMN email_verified;
```

常用的 migration 工具：

| 工具              | 語言 / 框架                       |
| ----------------- | --------------------------------- |
| Laravel Migration | PHP / Laravel                     |
| Rails Migration   | Ruby / Rails                      |
| Flyway            | Java / 跨語言（純 SQL）           |
| Liquibase         | Java / 跨語言（XML / YAML / SQL） |
| golang-migrate    | Go                                |
| 手動 SQL 檔案     | 無框架時的最低限度方案            |

沒有框架時，用日期 + 序號命名 SQL 檔案（`2026-06-26-001-描述.sql`），搭配一張 `migration_log` 表記錄哪些已經套用過，就是最低限度的 migration 系統。

## 鄰卡

- [RDS](/infra/knowledge-cards/rds/)：migration 在 production 資料庫上執行時要格外小心——大表的 ALTER TABLE 可能鎖表
- [mysqldump](/infra/knowledge-cards/mysqldump/)：執行 migration 前先做一次完整備份
