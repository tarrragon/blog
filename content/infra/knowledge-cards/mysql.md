---
title: "MySQL"
date: 2026-06-26
description: "最廣泛使用的開源關聯式資料庫。MariaDB 是其社群分支。大版本升級（5.7→8.0）有認證方式和查詢行為的 breaking change"
weight: 34
tags: ["infra", "knowledge-cards"]
---

MySQL 是最廣泛使用的開源關聯式資料庫，多數 PHP 應用、WordPress、以及大量 web 服務的資料層都跑在 MySQL 上，維運上常搭配 [phpMyAdmin](/infra/knowledge-cards/phpmyadmin/) 或 CLI 工具管理。MariaDB 是 MySQL 被 Oracle 收購後社群分支出來的相容實作，多數 Linux 發行版已經把預設的 mysql 套件指向 MariaDB。

## 概念位置

MySQL 在 infra 裡是典型的 stateful 資源——資料不可重建、備份和刪除保護是 day-1 需求。接手維運時，MySQL 的版本、備份設定、認證方式是第一批要確認的項目。雲端環境裡 MySQL 常以 [RDS](/infra/knowledge-cards/rds/) 形式運行（受管服務、代管備份與 failover）。

## 大版本升級的關鍵差異

MySQL 5.7 → 8.0 的 breaking change 在接手和升級情境裡經常遇到：

| 變更項               | 5.7 行為                | 8.0 行為                        |
| -------------------- | ----------------------- | ------------------------------- |
| 預設認證方式         | `mysql_native_password` | `caching_sha2_password`         |
| `GROUP BY` 隱式排序  | 有（按 group 欄位排）   | 無（需要明確 `ORDER BY`）       |
| 預設字元集           | `utf8`（3 byte）        | `utf8mb4`（4 byte、支援 emoji） |
| `GRANT` 同時建使用者 | 允許                    | 必須先 `CREATE USER`            |

## 可觀察訊號

接手維運時的確認清單：`SELECT VERSION();` 查版本、`SHOW DATABASES;` 看有哪些資料庫、`SHOW VARIABLES LIKE 'character_set%';` 確認字元集、`SHOW VARIABLES LIKE 'max_connections';` 看連線上限。

## CLI 工具

| 工具          | 功能                    |
| ------------- | ----------------------- |
| `mysql`       | 互動式 SQL 查詢         |
| `mysqldump`   | 匯出資料庫為 SQL 文字檔 |
| `mysqlcheck`  | 檢查、修復、優化資料表  |
| `mysqlimport` | 匯入 CSV / TSV 資料     |

`mysqldump` 是備份的核心工具——一行指令把整個資料庫匯出成可還原的 SQL。phpMyAdmin 的匯出功能底層也是類似的邏輯，但受 web server timeout 限制，大資料庫更適合用 CLI。

## 設計責任

MySQL 的 infra 設計要決定：備份頻率和保留天數（RDS 預設 7 天自動備份）、是否開 multi-AZ（failover 保護）、連線池設定（RDS Proxy 或應用層 pool）、慢查詢日誌是否開啟。

## 鄰卡

- [RDS](/infra/knowledge-cards/rds/) — AWS 的受管 MySQL 服務
- [phpMyAdmin](/infra/knowledge-cards/phpmyadmin/) — Web 介面的 MySQL 管理工具
