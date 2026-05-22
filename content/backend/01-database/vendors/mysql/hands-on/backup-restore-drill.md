---
title: "MySQL Backup Restore Drill"
date: 2026-05-22
description: "MySQL logical dump、physical backup frame、binlog position、restore validation 與 RPO / RTO evidence"
tags: ["backend", "database", "mysql", "hands-on", "backup"]
---

MySQL backup restore drill 的核心責任是證明資料可以從 backup 回到可用狀態。這篇承接 [PITR / Backup](../../pitr-backup/)，用 logical dump 建立最小演練框架，並保留 physical backup / binlog PITR 的 evidence 欄位。

本文的驗收標準是：你能產出 dump、記錄 binlog position、還原到隔離 database、跑 validation query，並寫下 RPO / RTO note。

## Create Backup

Create backup 的核心責任是建立可還原 artifact。

```bash
mkdir -p /tmp/mysql-backup-lab
mysqldump -h 127.0.0.1 -P 33069 -u app_user -papp_pw \
  --single-transaction --routines --triggers appdb \
  > /tmp/mysql-backup-lab/appdb.sql
```

記錄 binlog 狀態：

```bash
mysql -h 127.0.0.1 -P 33069 -u root -proot_pw -e "SHOW BINARY LOG STATUS;"
```

`--single-transaction` 適合 InnoDB consistent dump。大型 production 要評估 physical backup、backup lock、replication lag 與 binlog retention。

## Mutate Source

Mutate source 的核心責任是讓 restore 時間點具體化。

```bash
mysql -h 127.0.0.1 -P 33069 -u app_user -papp_pw appdb \
  -e "INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key) VALUES (1, 777, 'after-backup-write');"
```

Source 現在比 backup 多一筆。這能用來討論 RPO 與 binlog PITR。

## Restore Isolated Database

Restore isolated database 的核心責任是避免覆蓋 source。

```bash
mysql -h 127.0.0.1 -P 33069 -u root -proot_pw \
  -e "DROP DATABASE IF EXISTS appdb_restore; CREATE DATABASE appdb_restore;"
mysql -h 127.0.0.1 -P 33069 -u root -proot_pw appdb_restore \
  < /tmp/mysql-backup-lab/appdb.sql
```

Validation：

```bash
mysql -h 127.0.0.1 -P 33069 -u root -proot_pw appdb_restore <<'SQL'
SELECT COUNT(*) FROM accounts;
SELECT COUNT(*) FROM ledger_entries;
SELECT a.owner_name, SUM(l.amount_cents) AS balance_cents
FROM accounts a JOIN ledger_entries l ON l.account_id = a.id
GROUP BY a.owner_name;
SQL
```

Validation query 要和 application smoke test 對齊。正式 drill 還要啟動 app 指向 restore database。

## RPO / RTO Note

RPO / RTO note 的核心責任是把演練結果轉成服務承諾。

| Evidence        | 記錄內容                        |
| --------------- | ------------------------------- |
| Backup time     | dump start / finish             |
| Binlog position | file、position 或 GTID set      |
| Restore time    | 開始 restore 到 validation 成功 |
| Data gap        | backup 後需要 binlog 補回的寫入 |
| Smoke test      | application workflow            |

完成本篇後，binlog CDC 讀 [Binlog CDC](../../binlog-cdc/)；PITR 策略讀 [PITR / Backup](../../pitr-backup/)。
