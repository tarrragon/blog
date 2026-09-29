---
title: "MySQL Backup Restore Drill"
date: 2026-05-22
description: "MySQL logical dump、physical backup frame、binlog position、restore validation 與 RPO / RTO evidence"
tags: ["backend", "database", "mysql", "hands-on", "backup"]
---

MySQL backup restore drill 的核心責任是證明資料可以從 backup 回到可用狀態。這篇承接 [PITR / Backup](../../pitr-backup/)，用 logical dump 建立最小演練框架，並保留 physical backup / binlog PITR 的 evidence 欄位。

本篇的範圍是對 local lab 的 `appdb` 做一次 logical dump 演練：產出 dump 並記下它對應的 binlog position、在 dump 之後寫入一筆、還原到隔離的 `appdb_restore` 跑 validation query，並寫下 RPO / RTO note。

## Create Backup

Create backup 的核心責任是建立可還原 artifact。

```bash
mkdir -p /tmp/mysql-backup-lab
# --source-data=2：把 dump snapshot 對應的 binlog file / position 以註解寫進 dump 開頭
# 這個選項要 RELOAD 權限，app_user 沒有，所以用 root 執行
mysqldump -h 127.0.0.1 -P 33069 -u root -proot_pw \
  --single-transaction --source-data=2 --routines --triggers appdb \
  > /tmp/mysql-backup-lab/appdb.sql
```

記錄 binlog position：從 dump 開頭取出 `--source-data=2` 寫進去的那一行。

```bash
grep -m1 'CHANGE REPLICATION SOURCE' /tmp/mysql-backup-lab/appdb.sql
# 輸出形如：-- CHANGE REPLICATION SOURCE TO SOURCE_LOG_FILE='mysql-bin.000003', SOURCE_LOG_POS=1994;
# file 名稱與 position 以自己跑出來的為準
```

dump 跑完之後才執行 `SHOW BINARY LOG STATUS`，回的是查詢那一刻的 binlog 位置；dump 期間 source 若有寫入，這個位置會落在 dump snapshot 之後，從它開始補 binlog 會漏掉那段寫入。`--source-data=2` 記下的位置與 `--single-transaction` 取的 snapshot 是同一個時間點。

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
