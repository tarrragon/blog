---
title: "MySQL PITR + Backup Strategy：備份不是「拷貝資料」、是 N 點任意 restore 的能力"
date: 2026-05-19
description: "MySQL backup 不只是 mysqldump、是 *full backup + binlog 連續流* 組合才能達成 PITR（point-in-time recovery）。本文走「PITR 是能力、不是動作」、3 種 backup tool 對比（mysqldump / Percona XtraBackup / MyDumper）、binlog-based recovery 流程、配置 step-by-step、5 production 踩雷（GTID 處理不一致 / binlog gap / backup 沒 verify / RPO 不到 1 分鐘的代價 / encryption key 沒備份）、跟 PG pitr-wal-archiving sibling 對比"
weight: 23
tags: ["backend", "database", "mysql", "backup", "pitr", "deep-article"]
---

> 本文是 [MySQL](/backend/01-database/vendors/mysql/) overview 的 implementation-layer deep article。Overview 已說明 MySQL 在 OLTP 譜系的定位、本文聚焦 *backup + PITR* — 不是「拷貝資料」、是「N 點任意 restore 的能力」。

---

「我們每天 mysqldump 一次、放 S3、沒問題吧」是個常見錯誤。問「能不能 restore 到 5 分鐘前」、答案會是 *不能*。Dump-based backup 只能 restore 到 *dump 那個瞬間*、5 分鐘前的事故無法 recover、必須等下次 dump。

**真正的 backup strategy 是 [PITR（point-in-time recovery）](/backend/knowledge-cards/point-in-time-recovery/)**：

- *能 restore 到任意過去時間點*（RPO 取決於 binlog flush 頻率、可接近 0）
- 由 *full backup 基線* + *binlog 連續流*（從 backup 點到目標時間點的 incremental delta）組成
- Restore 過程：先 restore full backup → 再 apply binlog 到目標 timestamp 或 GTID

這篇 deep article 把 backup *拆解成能力*、然後展開達到此能力需要的工具鏈跟工程紀律。

## Backup 三層責任

PITR 的 *能力* 由三層工程責任達成、任一層失效則 PITR 不成立：

```text
Layer 1: Full Backup（基線）
   ↓     (mysqldump / XtraBackup / MyDumper / LVM snapshot / EBS snapshot)
   ↓
Layer 2: Binlog Stream（incremental）
   ↓     (sync_binlog=1 + binlog 持續流到 backup storage)
   ↓
Layer 3: Restore + Replay 流程
         (能 restore full + 能 apply binlog 到目標時間點)
```

每層的 *backup* 不夠 — 必須有 *測試 restore 流程* 才算真的有 backup。「dump 在 S3」加「沒有 verified restore」= no backup。

## Tool 1：mysqldump — 邏輯備份、最廣容、最慢

```bash
mysqldump --single-transaction --master-data=2 --gtid-purged=ON \
  --triggers --routines --events \
  --all-databases > full-backup.sql
```

**輸出**：SQL statement、純文字、可 grep / 編輯。

**Trade-off**：

- 優點：跨 MySQL 版本（5.7 → 8.0 也讀）、跨 cloud / 跨 OS、可選 dump 部分 table
- 缺點：*極慢*（rebuild 整 DB 從 SQL execute）、大 DB（> 100 GB）不適用、restore 時長 hours+
- `--single-transaction`：InnoDB only、用 REPEATABLE READ 拿 consistent snapshot、不 lock 表

**適合**：

- < 100 GB DB
- Schema dump（migration / 給 dev clone DB）
- 跨版本 migrate
- 配 binlog 做 PITR baseline

**不適合**：

- > 500 GB DB（restore 跑 days）
- 高吞吐 production（dump 跑時 hold MVCC read view、bloat）

## Tool 2：Percona XtraBackup — 物理備份、快、production 標準

```bash
xtrabackup --backup --target-dir=/backup/full-2026-05-19 \
  --user=backup --password=... \
  --slave-info --safe-slave-backup
# Prepare（apply 內部 redo log、變成可 restore 狀態）
xtrabackup --prepare --target-dir=/backup/full-2026-05-19
```

**輸出**：InnoDB 資料檔案的 binary copy。

**Trade-off**：

- 優點：*極快*（直接 copy file、無 SQL execute）、適合 TB-scale DB、restore 跑時間跟 copy file 同
- 缺點：MySQL 版本綁定（XtraBackup 8.0 不能 restore 5.7 backup）、有 storage engine 限制（只 InnoDB）
- *Incremental backup* 支援：基於 LSN（log sequence number）只 copy 變更 page

**Incremental flow**：

```bash
# Day 1: Full backup
xtrabackup --backup --target-dir=/backup/full-day1

# Day 2: Incremental（only changes since day 1）
xtrabackup --backup --target-dir=/backup/inc-day2 \
  --incremental-basedir=/backup/full-day1

# Restore: Apply incremental on top of full
xtrabackup --prepare --apply-log-only --target-dir=/backup/full-day1
xtrabackup --prepare --apply-log-only --target-dir=/backup/full-day1 \
  --incremental-dir=/backup/inc-day2
xtrabackup --prepare --target-dir=/backup/full-day1
```

**適合**：

- > 100 GB production DB
- 每日 incremental + 週一次 full（典型 enterprise schedule）
- 從自管 MySQL 遷 cloud（XtraBackup + rsync 到 cloud restore）

**不適合**：

- Schema-only dump（用 mysqldump 更簡單）
- 跨 major version restore

## Tool 3：MyDumper — 並行邏輯備份

```bash
mydumper --user=backup --password=... \
  --threads=8 --rows=100000 \
  --outputdir=/backup/mydumper-2026-05-19 \
  --less-locking
```

**輸出**：每張 table 一個 `.sql` file（schema） + 多個 chunked `.dat` file（資料）。

**Trade-off**：

- 優點：*並行 dump*（per-table thread）、比 mysqldump 快 5-10x、可恢復斷點（resume）
- 缺點：tooling 不如 mysqldump 普及、需要單獨裝
- 對應的 `myloader` restore：也並行、比 mysqldump restore 快 5-10x

**適合**：

- 100 GB - 1 TB 範圍
- 中型 production、想要邏輯備份的可讀性 + 並行加速

## Tool 4：LVM / EBS Snapshot — 物理 file system 層

```bash
# 1. Freeze MySQL（讓 write 暫停）
mysql> FLUSH TABLES WITH READ LOCK;
# 2. Trigger snapshot（EBS / LVM）
aws ec2 create-snapshot --volume-id vol-xxx --description "mysql-2026-05-19"
# 3. Unfreeze
mysql> UNLOCK TABLES;
```

**Trade-off**：

- 優點：超快（file system 層）、適合 *VM-based MySQL*（EC2 / on-prem）
- 缺點：必須 *暫停 write*（短時間 lock）、不能跨 OS / cloud 移植
- AWS RDS / Aurora 全部走這條路（自動 snapshot）

**適合**：

- AWS RDS / Aurora（自動）
- 自管 MySQL on EC2 with EBS（EBS snapshot 結合 mysql freeze）
- 大 DB 想要 fast backup + fast restore

## Binlog-based PITR

Full backup 加上 binlog 才能達到 PITR。Binlog 是 MySQL replication / CDC / PITR 共用的 source。

**配置**：

```ini
[mysqld]
log_bin = mysql-bin
binlog_format = ROW                  # ROW 必須
binlog_row_image = FULL              # 完整 row image
sync_binlog = 1                      # 每次 commit fsync binlog（zero loss）
binlog_expire_logs_seconds = 1209600 # 14 天 retention（依需求調）
gtid_mode = ON                       # GTID 必須、PITR 用 GTID 識別 transaction
enforce_gtid_consistency = ON
```

**Binlog backup**：

```bash
# 持續 stream binlog 到 backup storage
mysqlbinlog --read-from-remote-server --raw --stop-never \
  --user=replication --password=... \
  --host=primary.example.com \
  --result-file=/backup/binlog/ mysql-bin.000001 &
```

`--read-from-remote-server` + `--stop-never` 持續從 primary tail binlog、不間斷 stream 到 backup directory。每個 binlog file 寫滿後 close + 開新 file。

## Restore + PITR 流程

完整 PITR 流程（restore 到 2026-05-19 14:30:00）：

```bash
# Step 1: Restore full backup
xtrabackup --copy-back --target-dir=/backup/full-2026-05-18  # 前一天 full

# Step 2: 啟動 MySQL（會看到 backup 拿那刻的 GTID set）
systemctl start mysqld

# Step 3: 查 full backup 結束時的 GTID
mysql> SHOW MASTER STATUS;
+------------------+----------+------------------------------------------+
| File             | Position | Executed_Gtid_Set                        |
+------------------+----------+------------------------------------------+
| mysql-bin.000150 |     1234 | server-uuid:1-12345                      |
+------------------+----------+------------------------------------------+

# Step 4: Apply binlog 從 backup 之後到目標時間
mysqlbinlog --start-datetime="2026-05-18 03:00:00" \
            --stop-datetime="2026-05-19 14:30:00" \
            /backup/binlog/mysql-bin.000150 \
            /backup/binlog/mysql-bin.000151 \
            ...                                # 列所有需要的 binlog
            | mysql -u root -p

# Step 5: 驗證 GTID set 到目標時間點對應的位置
mysql> SHOW MASTER STATUS;
# Executed_Gtid_Set 應包含到目標時間點的 transaction
```

對 *精確 GTID-based PITR*（停在特定 transaction、不是 timestamp）：

```bash
mysqlbinlog --include-gtids='server-uuid:1-50000' \
            /backup/binlog/mysql-bin.000150 ... | mysql -u root -p
```

## 5 個 Production 踩雷

### 1. GTID 處理不一致 — Restore 後 replication broken

XtraBackup restore 時 `--slave-info` 紀錄 GTID purged set、mysqldump 用 `--gtid-purged=ON`。如果 restore 後沒正確 set `gtid_purged`、replica re-attach 時 GTID gap error。

修法：

- XtraBackup restore：用 `xtrabackup_binlog_info` 內的 GTID set 設 `SET GLOBAL gtid_purged='...';`
- mysqldump：dump file 內已有 `SET @@GLOBAL.GTID_PURGED='...';`、執行 dump 自動 set
- Restore 後 *先驗證 `Executed_Gtid_Set`* 跟 source 預期對齊、再 START SLAVE

### 2. Binlog gap — 中間遺漏 file 直接 restore fail

Binlog stream 失聯（network blip / disk full）+ binlog rotate、`mysql-bin.000156` 不在 backup storage 內。PITR 試圖跨過該 file restore、跳過已 commit transaction、結果 *資料不一致*（不是錯誤、是 *silently incorrect*）。

修法：

- *Binlog stream 必須持續*、失聯 → alert
- 監控 backup storage 內 binlog 連續性（file name 連號、無 gap）
- Restore 前 *先驗證 binlog 完整性*：`mysqlbinlog --verify-binlog-checksum *.bin > /dev/null`
- 對 missing binlog *中止 PITR*、不繼續 partial restore

### 3. Backup 沒 verify — 真事故時才發現 restore broken

每天備份成功、storage 用了 5 TB、實際 *從未 restore 過*。事故發生 restore 才知道 backup file corrupt / GTID 錯 / binlog gap、整套無用。

修法：

- *自動化 restore test*：每週 / 每月在 staging server 跑完整 restore + PITR、跑完 SELECT 比對 production
- 驗證 restore 後 row count 跟 production 接近、`CHECKSUM TABLE` 比對主要 table
- 真的事故時 RTO 才不會 surprise

### 4. RPO 不到 1 分鐘的代價

「我要 RPO < 1 分鐘」聽起來合理、但實現需要：

- `sync_binlog=1`（每 commit fsync、寫吞吐降 10-30%）
- Binlog stream 到 *獨立 storage*（不只是 primary local disk）、cross-region replication（額外 network cost）
- Replica 也用 semi-sync 配合（zero binlog loss）
- 監控 + alert RPO 違反（< 1 分鐘 stream lag）

**TCO**：~30% 寫吞吐 penalty + 額外 storage / network cost + 7x24 on-call。考慮 *real RPO requirement* — 多數 application 5 分鐘 RPO 已足夠、追求 1 分鐘 RPO 不划算。

修法：

- 跟 product / business 確認 *真 RPO 要求*
- *RPO budget = 寫吞吐 trade-off + ops cost*、不是 free
- 用 [Aurora](/backend/01-database/vendors/aurora/) / managed offering 把 RPO 議題 outsource（Aurora < 1 秒 RPO + 自動 cross-AZ）

### 5. Encryption key 沒備份 — Restore 後解不開資料

啟用 *encryption at rest*（MySQL 8.0+ `default_table_encryption=ON` + keyring plugin / component；MariaDB 用 `innodb_encrypt_tables`）後、所有 InnoDB tablespace 都加密。Master key 在 *keyring file* 或 KMS-backed component。如果 backup 只 backup MySQL data file、沒備 keyring、restore 後資料 *encrypted 但無 key、無法讀*。

修法：

- *Keyring file 跟 data file 分開儲存*、但兩者 *都要 backup*
- 用 *KMS-based keyring*（AWS KMS / HashiCorp Vault）取代 file-based、key 不在 MySQL server 上
- Disaster recovery runbook 紀錄 *key recovery 流程*、不要假設「重 install MySQL」就能解

## 容量規劃要點

| 項目              | 建議                                              |
| ----------------- | ------------------------------------------------- |
| Full backup 頻率  | 週一次（XtraBackup）或日一次（小 DB）             |
| Incremental 頻率  | 每日（XtraBackup incremental）                    |
| Binlog retention  | 14 天（給 PITR window）                           |
| Backup retention  | Full × 4 週 + 月度 archive × 12 個月              |
| Storage cost      | 約 2-3x DB size（full + incremental + binlog）    |
| Cross-region copy | 必要（local backup 失效時還有 disaster recovery） |
| Restore test 頻率 | 每週 staging 上跑、每月 production-like 跑        |

## 跟其他模組整合

### 跟 Replication topology

Replication replica 不能取代 backup — replica 上的 DROP TABLE 也會被 replicate、replica 上資料同樣消失。Backup 是 *獨立保險*。詳見 [Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)。

### 跟 InnoDB Tuning

`innodb_flush_log_at_trx_commit=1` + `sync_binlog=1` 是 backup-friendly 的設定（zero loss）、但寫吞吐降。如果為了寫吞吐放寬 durability、必須接受 *PITR window* 也 widening。詳見 [InnoDB Tuning](/backend/01-database/vendors/mysql/innodb-tuning/)。

### 跟 Aurora MySQL

Aurora 完全 outsource backup — automatic continuous backup + PITR < 1 秒、不必管 mysqldump / XtraBackup / binlog stream。從 Aurora 遷出時、需要重新建 self-managed backup chain。詳見 [migrate-to-aurora](/backend/01-database/vendors/mysql/migrate-to-aurora/)。

### 跟 PostgreSQL PITR

| 維度            | MySQL PITR                            | PostgreSQL PITR                         |
| --------------- | ------------------------------------- | --------------------------------------- |
| Logical backup  | mysqldump / MyDumper                  | pg_dump / pg_dumpall                    |
| Physical backup | XtraBackup                            | pg_basebackup / pgBackRest              |
| Incremental log | Binary log（binlog）                  | WAL (Write-Ahead Log)                   |
| Stream tool     | mysqlbinlog --read-from-remote-server | pg_receivewal                           |
| PITR command    | mysqlbinlog --stop-datetime           | pg_ctl + recovery.conf / standby.signal |
| Identifier      | GTID 或 file:position                 | LSN（Log Sequence Number）              |
| Cross-version   | mysqldump（廣容）                     | pg_dump（廣容）                         |

兩家 PITR 概念類似（full + log replay）、tool name 不同、概念對等。詳見 [PostgreSQL PITR + WAL Archiving](/backend/01-database/vendors/postgresql/pitr-wal-archiving/)。

## 何時 outsource backup

| 場景                         | 建議                                         |
| ---------------------------- | -------------------------------------------- |
| AWS 生態 + 不想管 backup ops | Aurora MySQL（內建 PITR）                    |
| GCP 生態                     | Cloud SQL（內建 PITR）                       |
| Azure 生態                   | Azure DB for MySQL                           |
| 跨雲 + 想自管                | XtraBackup + binlog stream + S3              |
| 規模小、可接受 mysqldump     | mysqldump cron + S3                          |
| 規模大、無 cloud             | Percona XtraBackup Enterprise + tape archive |
| 強合規（HIPAA / PCI-DSS）    | 自管 + air-gap backup + audit trail          |

## 相關連結

- [MySQL vendor overview](/backend/01-database/vendors/mysql/)
- [MySQL Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)（binlog 跟 PITR 共用 source）
- [MySQL InnoDB Tuning](/backend/01-database/vendors/mysql/innodb-tuning/)（durability + backup 互動）
- [migrate-to-aurora](/backend/01-database/vendors/mysql/migrate-to-aurora/)（backup outsource）
- [PostgreSQL PITR + WAL Archiving](/backend/01-database/vendors/postgresql/pitr-wal-archiving/)（PG sibling）
- 官方：[Percona XtraBackup](https://docs.percona.com/percona-xtrabackup/8.0/) / [MyDumper](https://github.com/mydumper/mydumper) / [mysqldump](https://dev.mysql.com/doc/refman/8.0/en/mysqldump.html)
