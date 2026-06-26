---
title: "mysqldump"
date: 2026-06-26
description: "MySQL / MariaDB 的 CLI 備份工具，把資料庫匯出成 SQL 語句的純文字檔"
weight: 43
tags: ["infra", "knowledge-cards", "database", "backup", "mysql"]
---

mysqldump 是 MySQL 和 MariaDB 內建的命令列備份工具，把整個資料庫（或指定的表）匯出成一份包含 CREATE TABLE 和 INSERT 語句的 SQL 純文字檔。還原時把這份檔案餵給 `mysql` client 就能重建資料。

## 概念位置

mysqldump 是有 SSH 存取（或 remote MySQL 存取）時的主要備份手段。比 [phpMyAdmin](/infra/knowledge-cards/phpmyadmin/) 的匯出更可靠——不受 web server 的 timeout 和記憶體限制影響，可以處理數 GB 的資料庫。沒有 SSH 的環境只能退回 phpMyAdmin 匯出。

## 可觀察訊號

接手時如果 server 上有 [cron](/infra/knowledge-cards/cron/) job 在跑 mysqldump，代表前任有做自動備份——確認輸出的 dump 檔案存在哪、保留幾天、有沒有被驗證過能還原。如果沒有任何 mysqldump cron，代表備份可能只靠 phpMyAdmin 手動匯出或完全沒做。

## 設計責任

常用的 flag 組合：

```bash
mysqldump -u user -p \
  --single-transaction \
  --routines \
  --triggers \
  dbname > dump-$(date +%Y%m%d).sql
```

| Flag                   | 作用                                              |
| ---------------------- | ------------------------------------------------- |
| `--single-transaction` | InnoDB 表不鎖表匯出（用一致性快照），生產備份必備 |
| `--routines`           | 含 stored procedure 和 function                   |
| `--triggers`           | 含 trigger                                        |
| `--quick`              | 逐行讀取、不把整個表載入記憶體，大表必備          |

還原指令：

```bash
mysql -u user -p dbname < dump-20260626.sql
```

mysqldump 產出的是邏輯備份（SQL 語句），還原速度取決於資料量——幾百 MB 以內分鐘級，數 GB 可能要半小時以上。需要更快的備份/還原（物理備份），要用 Percona XtraBackup 或 MySQL Enterprise Backup。

## 鄰卡

- [phpMyAdmin](/infra/knowledge-cards/phpmyadmin/)：無 SSH 時的替代備份手段
- [cron](/infra/knowledge-cards/cron/)：搭配 cron 做定期自動備份
