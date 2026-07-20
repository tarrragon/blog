---
title: "無 SSH 環境的資料庫備份與變更管理"
date: 2026-06-26
description: "在只有 phpMyAdmin 或有限遠端連線的無 SSH 環境裡，怎麼建立可靠的資料庫備份策略、schema 變更紀律與還原演練流程"
weight: 10
tags: ["infra", "takeover", "database", "backup", "mysql", "php"]
---

程式碼可以從 Git repo 重新上傳，資料庫裡的資料一旦遺失或損壞就回不來。在無 SSH 的環境裡，資料庫的備份與變更管理比程式碼更需要紀律，因為可用的工具受限（通常只有 [phpMyAdmin](/infra/knowledge-cards/phpmyadmin/)）、沒有 point-in-time recovery（PITR）、也沒有自動化快照。本篇從工具限制出發，建立一套在這些約束條件下仍能可靠運作的備份與變更流程。

本篇是[無 SSH 的 FTP / 面板管理環境接管](/infra/takeover/legacy-ftp-no-ssh/)的延伸，聚焦在資料庫層面。程式碼與部署紀律見主文。

## phpMyAdmin 的限制與對策

phpMyAdmin 是多數無 SSH 環境預裝的資料庫管理介面，匯出功能涵蓋完整 SQL dump，但它跑在 PHP 執行環境裡，受限於 `max_execution_time` 和記憶體上限。資料庫超過 50MB 時，匯出經常在執行到一半就因 timeout 中斷，產出不完整的 SQL 檔案——而不完整的 dump 在還原時只會匯入前半段的表、後面的表靜靜消失。

### 大資料庫的匯出對策

第一個選項是分表匯出。phpMyAdmin 的匯出頁面允許選擇要匯出的資料表，把一次完整匯出拆成 3-5 批，每批在 timeout 之前完成。缺點是匯出不是原子操作——不同批次之間如果有寫入，表之間的參照關係可能不一致（例如訂單表引用的商品 ID 在商品表的那一批裡還沒匯出）。對多數讀取為主的站台，這個不一致窗口可接受；對交易密集的站台，需要在低流量時段操作。

第二個選項是調整 phpMyAdmin 的 timeout。部分主機允許在 phpMyAdmin 的設定目錄放自訂的 `config.inc.php`：

```php
$cfg['ExecTimeLimit'] = 600; // 從預設 300 秒增加到 600 秒
```

cPanel 主機通常在「軟體」區塊的 phpMyAdmin 設定裡有對應的 UI 選項。Plesk 的路徑是「資料庫」→「phpMyAdmin 設定」。能不能改取決於主機商的權限政策，改之前先確認。

第三個選項是繞過 phpMyAdmin。如果主機允許遠端 MySQL 連線（在 cPanel 的「遠端 MySQL」頁面加白名單 IP），就能用桌面工具直連資料庫匯出：

| 工具      | 平台              | 費用 | 匯出方式                |
| --------- | ----------------- | ---- | ----------------------- |
| DBeaver   | 跨平台            | 免費 | 右鍵資料庫 → 匯出 → SQL |
| TablePlus | macOS / Windows   | 付費 | Cmd+Shift+E 匯出        |
| HeidiSQL  | Windows           | 免費 | 工具 → 匯出資料庫為 SQL |
| mysqldump | CLI（需本機安裝） | 免費 | 見下方指令              |

桌面工具直連 MySQL 比 phpMyAdmin 穩定，因為匯出跑在本機、不受主機的 PHP timeout 限制。[mysqldump](/infra/knowledge-cards/mysqldump/) 是最可靠的選項：

```bash
mysqldump -h db-host.example.com -u dbuser -p \
  --single-transaction --routines --triggers \
  dbname > backup_$(date +%Y%m%d_%H%M).sql
```

`--single-transaction` 對 InnoDB 表做一致性快照，不需要鎖表。`--routines` 和 `--triggers` 確保 stored procedure 和觸發器也被包含在 dump 裡——phpMyAdmin 匯出預設也包含，但容易在手動選項時漏勾。

### 匯出後的驗證

匯出完成後檢查 SQL 檔案的結尾。完整的 mysqldump 結尾會有 `-- Dump completed on YYYY-MM-DD HH:MM:SS`。phpMyAdmin 匯出的結尾會有 `-- phpMyAdmin SQL Dump` 的對應結尾標記。如果檔案在某個 `INSERT INTO` 語句中間斷掉，這份 dump 就是不完整的，還原時會靜靜丟失後面的資料。

```bash
tail -5 backup_20260626_1430.sql
# 預期看到 "Dump completed" 或完整的結尾註解
```

## 備份策略：頻率與保留

備份頻率由資料的變更速率決定。一個每天只有幾筆訂單的小型電商，每週備份加上每次變更前備份就夠用。一個每天有數百筆交易的服務，需要每日備份。判斷依據是：如果最新的備份丟了、要用上一份還原，能接受丟失多少資料？這個時間差就是實際的 RPO（Recovery Point Objective）。

### 保留策略

| 備份類型 | 頻率   | 保留數量 | 用途                    |
| -------- | ------ | -------- | ----------------------- |
| 每日     | 每天   | 7 份     | 近期資料遺失的還原      |
| 每週     | 每週一 | 4 份     | 一到四週前的回溯        |
| 變更前   | 每次   | 長期保留 | schema 變更的回退保險點 |

命名用時間戳避免覆蓋：`dbname_20260626_1430.sql.gz`。壓縮用 gzip（`gzip backup.sql`），50MB 的 SQL dump 通常壓到 5-10MB。

### 儲存位置

本機是第一份副本，但本機磁碟故障時備份也跟著消失。至少再推一份到雲端儲存：

```bash
# rclone 同步到 Google Drive（事先用 rclone config 設定 remote）
rclone copy /local/backups/db/ gdrive:project-backups/db/ --max-age 7d

# 或推到 S3
aws s3 sync /local/backups/db/ s3://my-project-backups/db/ --storage-class STANDARD_IA
```

### 備份驗證

備份存在不等於備份可用。每月至少做一次驗證：把最新的 dump 匯入本地 MySQL，檢查關鍵表的 row count 跟 prod 一致、應用程式能正常啟動。如果匯入報錯或 row count 差異超過預期，備份流程有問題要立刻排查。

```bash
mysql -u root -p local_testdb < backup_20260626_1430.sql
mysql -u root -p -e "SELECT COUNT(*) FROM orders;" local_testdb
```

## 自動化備份（無 SSH 環境的限制下）

無 SSH 環境的自動化受限程度取決於主機提供的能力。三個層級由好到差：

**主機有 cron + mysqldump 路徑**：部分主機在 cPanel 的「cron 工作」裡允許設定排程指令。mysqldump 通常安裝在 `/usr/bin/mysqldump`，可以直接用：

```bash
# cPanel cron job（每天凌晨 3 點）
0 3 * * * /usr/bin/mysqldump -u dbuser -p'password' dbname | gzip > /home/user/backups/db_$(date +\%Y\%m\%d).sql.gz
```

密碼寫在 cron 指令裡不理想但在無 SSH 環境選擇有限。用 `.my.cnf` 檔案存密碼（`chmod 600`）較安全，但不是所有主機都支援。

**主機有遠端 MySQL 但沒 cron**：用本機排程（macOS launchd / Windows Task Scheduler / Linux cron）跑 mysqldump 遠端連線：

```bash
#!/bin/bash
# local-backup.sh — 本機排程每天跑
BACKUP_DIR="$HOME/backups/myproject/db"
mkdir -p "$BACKUP_DIR"
mysqldump -h db-host.example.com -u dbuser -p'password' \
  --single-transaction dbname \
  | gzip > "$BACKUP_DIR/db_$(date +%Y%m%d_%H%M).sql.gz"

# 推到雲端
rclone copy "$BACKUP_DIR" gdrive:project-backups/db/ --max-age 7d

# 清理超過 30 天的本地備份
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete
```

**沒有 cron 也沒有遠端 MySQL**：只能靠手動的 phpMyAdmin 匯出，加上 cPanel 的「備份精靈」（如果主機方案包含）。cPanel 備份精靈可以設定每日或每週的完整備份（含資料庫 + 檔案），但免費方案通常不支援排程。這是最受限的情境——如果連手動匯出都嫌麻煩，最高優先的升級路徑是開通遠端 MySQL 存取。

## 資料庫變更的 migration 紀律

Schema 變更（加欄位、改索引、拆表）在沒有 migration 工具的 legacy PHP 專案裡，全靠手動在 phpMyAdmin 執行 SQL。migration 紀律的目標是讓每一次 schema 變更有紀錄、可重播、可回退。

### Migration 檔案格式

每次 schema 變更寫成一個獨立的 SQL 檔案，存在 repo 的 `migrations/` 目錄：

```sql
-- migrations/2026-06-26-001-add-users-email-verified.sql
-- 目的：新增 email 驗證欄位，支援 email 驗證流程
-- 回退：ALTER TABLE users DROP COLUMN email_verified;

-- UP
ALTER TABLE users ADD COLUMN email_verified TINYINT(1) NOT NULL DEFAULT 0 AFTER email;
CREATE INDEX idx_users_email_verified ON users (email_verified);

-- DOWN（回退用，不自動執行）
-- DROP INDEX idx_users_email_verified ON users;
-- ALTER TABLE users DROP COLUMN email_verified;
```

檔名的結構是 `日期-序號-描述`，序號處理同一天多次變更的排序。UP 段是要執行的 SQL，DOWN 段是回退 SQL（註解掉，手動需要時才用）。

### 追蹤哪些 migration 已執行

在資料庫建一張追蹤表：

```sql
CREATE TABLE IF NOT EXISTS migrations_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    applied_by VARCHAR(100)
);
```

每次在 prod 執行完一個 migration，手動插入一筆紀錄：

```sql
INSERT INTO migrations_log (filename, applied_by) VALUES ('2026-06-26-001-add-users-email-verified.sql', 'alice');
```

查哪些 migration 還沒跑：比對 `migrations/` 目錄的檔案清單跟 `migrations_log` 表的 filename 欄。這不是自動化的 migration runner（像 Laravel 的 artisan migrate），但在沒有框架支援的 legacy 專案裡，一張表加一個目錄就能達到可追蹤的最低標準。

### 執行流程

| 步驟 | 動作                                   | 失敗時                   |
| ---- | -------------------------------------- | ------------------------ |
| 1    | 在本地 DB 執行 migration、確認語法正確 | 修正 SQL 再試            |
| 2    | 備份 prod DB（完整 dump 或受影響的表） | 如果備份失敗、不繼續     |
| 3    | 在 prod 的 phpMyAdmin 執行 UP 段       | 用 DOWN 段回退、還原備份 |
| 4    | 驗證：檢查表結構、跑應用程式確認正常   | 用 DOWN 段回退、還原備份 |
| 5    | 插入 migrations_log 紀錄               | —                        |

高風險的 migration（改大表結構、刪欄位、改資料類型）在步驟 2 要做完整的資料庫 dump 而非只備份受影響的表，因為外鍵和觸發器可能讓影響範圍超出目標表。

## 還原演練

備份的價值在還原成功的那一刻才被驗證。沒有演練過的備份等同於不存在——匯出可能不完整、SQL 版本可能不相容、匯入順序可能因為外鍵而失敗。

### 演練流程

在本地用最新的備份還原一次完整的資料庫：

```bash
# 建一個測試用的空資料庫
mysql -u root -p -e "CREATE DATABASE restore_test;"

# 匯入備份
mysql -u root -p restore_test < backup_20260626_1430.sql

# 驗證
mysql -u root -p -e "SHOW TABLES;" restore_test
mysql -u root -p -e "SELECT COUNT(*) FROM orders;" restore_test
```

驗證三件事：表結構完整（`SHOW TABLES` 的表數量跟 prod 一致）、資料完整（關鍵表的 row count 一致）、應用程式能跑（把本地應用指向 restore_test 資料庫、打開首頁和幾個關鍵流程）。

### 還原時間的量測

記錄從開始匯入到驗證完成的時間。這個數字就是事故時的最快恢復時間。如果一個 500MB 的資料庫匯入需要 40 分鐘，加上排查原因和決策的時間，實際恢復可能超過一小時。知道這個數字，才能在事故時給管理層一個實際的時間預期。

### 無 SSH 環境沒有 PITR

無 SSH 的主機環境的 MySQL 通常不提供 binlog 層級的 point-in-time recovery。能還原到的最近時間點就是最新備份的時間點——備份是每天凌晨做的、下午三點出事，那就是丟失當天的所有寫入。這是備份頻率需要跟資料變更速率對齊的根本原因。交易密集的站台如果無法接受一天的資料丟失，升級到有 binlog / PITR 的環境（VPS 或 managed MySQL）是必要的投資。

## 大資料庫的特殊處理

資料庫超過 500MB 時，備份和還原的操作時間和失敗風險都會上升。需要針對大表做特殊處理。

超過 1GB 的單表通常是 log 表、歷史紀錄表、或含有二進位大物件（BLOB）的表。對這類表的備份策略跟業務表不同：

- **log / 歷史表**：備份時可以加 `--where="created_at > DATE_SUB(NOW(), INTERVAL 90 DAY)"` 只匯出近期資料，歷史資料另做一次性歸檔
- **BLOB 欄位**（圖片、PDF）：用 `--no-data` 單獨匯出 schema，BLOB 內容如果已經搬到檔案系統或 CDN，資料庫裡只需要保留路徑參考
- **InnoDB 大表**：`--single-transaction` 避免鎖表，但匯出期間的記憶體消耗跟表大小成正比，本機如果記憶體不足可以加 `--quick`（逐行讀取、不緩衝整張表）

```bash
# 大表匯出：逐行讀取 + 一致性快照 + 壓縮
mysqldump -h db-host.example.com -u dbuser -p \
  --single-transaction --quick \
  dbname large_table | gzip > large_table_$(date +%Y%m%d).sql.gz
```

資料庫規模成長到備份時間超過維護視窗（例如匯出要兩小時但只有一小時的低流量時段），代表這類環境的備份能力已經到頂，需要評估升級到有 automated snapshot 的 managed MySQL 或 VPS。

## 跨分類引用

- → [無 SSH 的 FTP / 面板管理環境接管](/infra/takeover/legacy-ftp-no-ssh/)：主文，涵蓋程式碼備份、部署紀律與整體接管流程
- → [程式碼版控與 FTP 部署紀律](/infra/takeover/legacy-code-versioning-deployment/)：DB migration 跟 code deploy 要同步——schema 改了但 code 沒跟上會讓服務壞掉
- → [Legacy PHP 的安全盤點](/infra/takeover/legacy-php-security-audit/)：DB credential 的掃描與保護、SQL injection 風險評估
- → [Stateful 資源保護與跨服務依賴](/infra/05-core-services/stateful-protection-dependency/)：IaC 環境裡的備份、deletion protection 與 PITR 設計
- → [治理好習慣](/infra/08-governance-habits/)：tagging、secret 管理與成本可見性的長期治理
