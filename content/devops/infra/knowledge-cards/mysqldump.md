---
title: "mysqldump"
date: 2026-06-26
description: "MySQL / MariaDB 的 CLI 備份工具，把資料庫匯出成 SQL 語句的純文字檔"
weight: 43
tags: ["infra", "knowledge-cards", "database", "backup", "mysql"]
aliases: ["/infra/knowledge-cards/mysqldump/"]
---

mysqldump 是 [MySQL](/devops/infra/knowledge-cards/mysql/) 和 MariaDB 內建的命令列備份工具，把整個資料庫（或指定的表）匯出成一份包含 CREATE TABLE 和 INSERT 語句的 SQL 純文字檔。還原時把這份檔案餵給 `mysql` client 就能重建資料。

## 跟其他概念的關係

mysqldump 是有 SSH 存取（或 remote MySQL 存取）時的主要備份手段。比 [phpMyAdmin](/devops/infra/knowledge-cards/phpmyadmin/) 的匯出更可靠——不受 web server 的 timeout 和記憶體限制影響，可以處理數 GB 的資料庫。沒有 SSH 的環境只能退回 phpMyAdmin 匯出。

## 可觀察訊號

接手時如果 server 上有 [cron](/devops/infra/knowledge-cards/cron/) job 在跑 mysqldump，代表前任有做自動備份——確認輸出的 dump 檔案存在哪、保留幾天、有沒有被驗證過能還原。如果沒有任何 mysqldump cron，代表備份可能只靠 phpMyAdmin 手動匯出或完全沒做。

## 判斷條件與後果

常用的 flag 組合：

```bash
mysqldump -u user -p \
  --single-transaction \
  --routines \
  --triggers \
  dbname > dump-$(date +%Y%m%d).sql
```

| Flag                   | 作用                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------- |
| `--single-transaction` | InnoDB 表不鎖表匯出（用一致性快照）；不加時匯出期間表被鎖住，線上的寫入要等匯出結束 |
| `--routines`           | 含 stored procedure 和 function                                                     |
| `--triggers`           | 含 trigger                                                                          |
| `--quick`              | 逐行讀取、不把整個表載入記憶體；預設已開啟，被關掉時大表要先整張讀進記憶體才寫出    |

還原指令：

```bash
mysql -u user -p dbname < dump-20260626.sql
```

mysqldump 產出的是邏輯備份（SQL 語句），還原速度取決於資料量——幾百 MB 以內分鐘級，數 GB 可能要半小時以上。需要更快的備份/還原（物理備份），要用 Percona XtraBackup 或 MySQL Enterprise Backup。

判斷一份 mysqldump 備份是否還原得出可運作的服務，看的是 dump 還原之後的資料庫，dump 檔存在只是前提。資料庫裡有 stored procedure 或 function、而 dump 沒帶 `--routines` 時，還原出來的資料庫有表與資料，而呼叫那些 procedure 的程式會報錯，原因是 routines 不在預設的匯出範圍裡；trigger 預設會匯出，被 `--skip-triggers` 關掉時，原本由 trigger 寫入的資料在還原後不再產生。資料庫裡有 MyISAM 表時，`--single-transaction` 的一致性快照只涵蓋 InnoDB 表，MyISAM 表的內容可能跟其他表對不上某一個時間點。還原時間超過服務能接受的停機時間時，邏輯備份在資料遺失之後仍然還原得出來，但要停機到 SQL 全部重新執行完，這時物理備份才換得到較短的還原時間。這幾個條件都要實際還原一次才確認得了，所以備份流程裡要定期把 dump 還原到另一個資料庫驗證。

## 鄰卡

- [phpMyAdmin](/devops/infra/knowledge-cards/phpmyadmin/)：無 SSH 時的替代備份手段
- [cron](/devops/infra/knowledge-cards/cron/)：搭配 cron 做定期自動備份
