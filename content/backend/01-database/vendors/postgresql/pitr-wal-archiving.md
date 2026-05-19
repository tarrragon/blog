---
title: "PostgreSQL PITR + WAL archiving：從 base backup 到 point-in-time recovery 的完整鏈"
date: 2026-05-18
description: "Base backup + WAL archive 構成 PITR 的雙軌資料、archive_command + restore_command 配置、用 pgBackRest / WAL-G 替代手寫腳本、5 個 production 踩雷（archive 靜默失敗 / archive lag / 錯誤 target time / base backup 過期未清 / timeline 分歧 recovery 模糊）、跟 Patroni + monitoring 整合"
weight: 35
tags: ["backend", "database", "postgresql", "pitr", "backup", "wal-archive", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 backup / recovery 是 OLTP 必備能力、本文聚焦 *PITR（Point-In-Time Recovery）的雙軌資料設計 + production 5 個 failure mode*。

## 問題情境

Logical bug 在 production 部署、執行 6 小時後才發現 — 某個 batch job 把 50 萬筆 user.email 改成 NULL。此時：

- 還原最新 daily backup（昨晚）→ 丟掉今天所有正常寫入（訂單、註冊）
- 從 standby promote → standby 已同步 bug、跟 primary 同狀態
- 從 application log 重建 → 部分操作不可逆（已寄出 email）

PITR 是這類 *logical disaster* 的標準解 — 不還原到 backup 時間點、而是 *還原到 bug 發生前一刻*（例：1 分鐘前）。需要 *base backup + WAL archive* 雙軌資料：base backup 是 snapshot、WAL archive 是 snapshot 之後的所有寫入；recovery 時 replay WAL 到指定 timestamp / LSN / transaction ID。

## 核心概念：base backup + WAL archive 的雙軌設計

```text
[Base backup t0]  +  [WAL archive t0 → now]
     ↓                       ↓
  全量 snapshot          incremental log
     ↓                       ↓
     └────── recover to t_target ──→ [restored cluster at t_target]
```

兩個軌道各自獨立但必須對齊：

1. **Base backup**：某時刻整個 data dir 的 snapshot。`pg_basebackup` / `pgBackRest` / `WAL-G` 都產這個；通常 *每天 / 每週* 跑一次
2. **WAL archive**：base backup 之後每段 WAL 都 push 到外部 storage（S3 / GCS / NFS）。`archive_command` 觸發、PostgreSQL 等到 archive 成功才 *回收* 那段 WAL

兩者組合決定 RPO（recovery point objective）：

- RPO ≈ WAL archive frequency（streaming 即時、`archive_timeout` 預設 1 分鐘）
- RPO 不是 base backup frequency — daily base backup + 每分鐘 archive WAL → RPO 1 分鐘

RTO（recovery time objective）跟 *base backup size + WAL replay 量* 相關：

- Restore base backup ~ 1-4 小時（TB 級）
- WAL replay 時間 ~ archive 累積量 / replay throughput

## Step-by-step 配置

### Primary：archive_command 設好

```ini
# postgresql.conf
wal_level = replica                          # 預設 replica、PITR 需要
archive_mode = on                            # 啟用 archive
archive_command = 'wal-g wal-push %p'        # 或 pgBackRest / 自寫 script
archive_timeout = 60                         # 60s 無 WAL 時強制切 segment
max_wal_size = 4GB
checkpoint_timeout = 15min
```

`archive_command` 必須 *回 exit code 0 才算成功*；非 0 PostgreSQL retry、retry 失敗會在 `pg_wal` 堆積 WAL 直到 disk 滿。**critical：archive_command 不能寫成 silent-fail**。

### 用 pgBackRest 取代手寫 script

production 強烈不建議自寫 archive script — pgBackRest / WAL-G / Barman 處理過所有 edge case：

```ini
# pgbackrest.conf
[global]
repo1-type=s3
repo1-s3-bucket=mybucket
repo1-s3-region=us-east-1
repo1-retention-full=4                       # 留 4 個 full backup
repo1-retention-diff=8                       # 留 8 個 differential
repo1-cipher-type=aes-256-cbc                # encrypt at rest
process-max=8                                # parallel restore

[main]
pg1-path=/var/lib/postgresql/16/main
```

```bash
# 跑 full backup
pgbackrest --stanza=main backup --type=full

# archive_command 用 pgbackrest 內建
archive_command = 'pgbackrest --stanza=main archive-push %p'
```

pgBackRest 處理：parallel push、compression、encryption、checksum、archive replay timing、backup catalog、retention 自動清理。

### Restore：recovery_target_time

```bash
# 1. 從 S3 / repo 拉 base backup
pgbackrest --stanza=main --type=time \
  --target="2026-05-18 14:30:00+00" restore

# 2. PostgreSQL 進 recovery mode、自動 replay WAL 到 target time
# (pgBackRest 寫好 recovery.signal + postgresql.auto.conf)

# 3. 確認到目標 timestamp 後、promote
pg_ctl promote
```

Recovery target 三種：

- **`recovery_target_time`**：到某 timestamp
- **`recovery_target_xid`**：到某 transaction ID（log 有 xid 才好定位）
- **`recovery_target_lsn`**：到某 WAL LSN（最精確、但需要事先記下 LSN）

production 多用 timestamp、application log 有時間戳容易定位。

## 故障演練 / 邊界 case

### Case 1：archive_command 靜默失敗

**徵兆**：DBA 發現某 PITR test 時、最近 3 天的 WAL 在 S3 上沒有；但 PostgreSQL 沒 alert、`pg_wal` 也沒堆積（早就被回收？）。

**根因**：archive_command 寫成 `aws s3 cp %p s3://bucket/... 2>/dev/null` — 錯誤訊息被吞、exit code 卻是 0（cp 失敗但 redirect 後 shell wrapper 不傳 fail code）；PostgreSQL 以為成功、繼續 advance WAL pointer、舊 WAL 已回收、archive 上實際沒有。

**修法**：

1. **絕對不要靜默 exit code**：archive_command 必須 *fail loud*、exit code 非 0
2. **用 pgBackRest / WAL-G**、不自寫 shell 腳本
3. **monitoring**：對 archive lag 寫 alert

```sql
SELECT pg_last_archived_xact_time(), now() - pg_last_archived_xact_time() AS lag;
```

alert if lag > 5 minutes

4. **定期測試 restore**：每月跑一次 PITR drill、實際從 archive restore + 驗證 timestamp

### Case 2：WAL archive lag、primary disk 壓力

**徵兆**：`pg_wal` 目錄持續長大、`df -h` 90%+；`pg_stat_archiver` 顯示 `failed_count` 累積、`last_failed_time` 是 30 分鐘前；archive_command 寫不出去（S3 throttle / network 慢）。

**根因**：archive_command 寫到 S3、但 S3 rate limit / connection timeout、PostgreSQL retry；WAL 一直在 `pg_wal` 不能回收、disk 持續長。

**修法**：

1. **預防**：`archive_command` 內部 retry + parallel push（pgBackRest 自帶 `process-max`）
2. **alert**：`pg_stat_archiver.failed_count` 增長 + primary disk usage > 80%
3. **緊急**：暫時改 archive_command 寫 local NFS / 其他 storage、等 S3 恢復再同步；不要直接 disable archive（會丟資料）
4. **架構**：archive storage 至少跨 region 兩份、單一 storage 故障不影響 archive

### Case 3：recovery 跑到 wrong target time

**徵兆**：PITR 還原後資料看起來 *缺一塊*；DBA 後悔 — target time 設早了 30 分鐘、recovery 已 promote、後續 WAL 在新 timeline 上、回不去。

**根因**：recovery 過程不可逆 — 一旦 promote 開新 timeline、舊 WAL 在新 timeline 上不會被 replay；想還原到更晚 timestamp 必須 *重新 restore base backup + WAL*。

**修法**：

1. **`recovery_target_action = pause`**（PG 13+）：到 target time 後 *暫停*、不自動 promote；DBA 手動 query 確認資料對才 promote

```ini
recovery_target_time = '2026-05-18 14:30:00+00'
recovery_target_action = pause
```

2. **多次 PITR 試錯**：用 *獨立 staging cluster* restore、驗證 target time 對、再對 production 跑
3. **記錄 target time 來源**：application log / event timestamp 多比對、避免時區錯亂（`+00` UTC 跟 local time 差）

### Case 4：base backup 過期未清、storage 爆

**徵兆**：S3 backup bucket size 半年內從 200GB 漲到 5TB；DBA 才發現 retention 沒設、daily base backup 留 180 天。

**根因**：archive_command 自寫腳本沒 retention 邏輯、或 pgBackRest 設了 `repo1-retention-full=180` 漏看；DB 容量本來就成長 + 每日 full backup 累積。

**修法**：

```ini
# pgBackRest retention：4 full + auto-expire archive
repo1-retention-full=4                         # 留 4 個 full backup
repo1-retention-diff=8                         # 留 8 個 differential
repo1-retention-archive=4                      # WAL archive 跟 full 對齊
repo1-retention-archive-type=full
```

storage budgeting：

- daily full + diff + WAL archive ≈ 1-2x DB size / day
- 4-week retention → ~30-60x DB size storage
- 跨 region replication → 2-3x

### Case 5：timeline 分歧後 recovery 模糊

**徵兆**：production 經歷一次 failover（Patroni promote）+ 之後又 PITR 一次；現在要再 PITR 到 failover 前一刻、archive 上有兩個 timeline、recovery target 搞不清要哪個。

**根因**：每次 promote 開新 timeline ID（`.history` 檔）；archive storage 上同 LSN 可能對應不同 timeline；recovery target time 在分歧點附近、ambiguous。

**修法**：

1. **`recovery_target_timeline`** 明示要 follow 哪個 timeline

```ini
recovery_target_time = '2026-05-15 10:00:00+00'
recovery_target_timeline = '3'                 # 要 follow timeline 3
```

2. **熟悉 `.history` 檔**：`/wal_archive/000000XX.history` 記錄 timeline 切換點、PITR 前先看
3. **預防**：每次 promote 後 *立刻* 跑新的 base backup、簡化未來 PITR 流程（不用跨 timeline）

## 容量 / cost 規劃

| 維度              | 估算                                                        | 警戒                                   |
| ----------------- | ----------------------------------------------------------- | -------------------------------------- |
| Base backup size  | 跟 DB data dir 大小成正比（PostgreSQL 內部 compression 後） | 每 backup ~ 0.5-1x DB size             |
| WAL archive size  | ~5-50GB / day depending on write volume                     | 1TB DB / write-heavy 可能 100GB+ / day |
| Storage retention | 4-12 weeks 典型                                             | 30-60x DB size budget                  |
| Base backup time  | TB 級 1-4 小時                                              | 跑在 maintenance window                |
| Restore time      | base backup restore + WAL replay                            | TB 級 PITR 通常 2-6 小時               |
| Network bandwidth | full backup 期間 100-500 Mbps                               | 跨 region 注意 egress cost             |

實務 default：

- Daily full backup + 4 weeks retention
- WAL archive every 60s（`archive_timeout = 60`）
- 跨 region replication（S3 → S3 cross-region）
- 月度 restore drill 驗證可用

## 整合 / 下一步

### 跟 [Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/) 整合

Patroni 不管 backup，但 promotion 後 timeline 切換影響 archive：

1. archive_command 用 `%t`（timeline）+ `%f`（filename）路徑、避免不同 timeline WAL 覆蓋
2. Patroni `recovery_conf` 包含 `restore_command`、standby clone 從 archive 拉
3. 每次 Patroni failover 後跑 *full backup*、簡化未來 PITR

### 跟 [logical replication](/backend/01-database/vendors/postgresql/logical-replication-debezium/) 對位

PITR 跟 logical replication 服務不同 use case：

- PITR 是 *災難恢復*（logical bug / corruption）— 全量還原到某時刻
- Logical replication 是 *連續 sync* — Kafka / 跨 DB 即時複製

兩者 *都依賴 WAL*、但目標不同；同 PostgreSQL 可同時跑、互不衝突。

### 跟 monitoring + alert

關鍵 metric：

```sql
-- archive 健康度
SELECT * FROM pg_stat_archiver;
-- archived_count, failed_count, last_archived_wal, last_archived_time

-- WAL 在 pg_wal 等待 archive 量
SELECT count(*) FROM pg_ls_waldir() WHERE name ~ '^[0-9A-F]{24}$';

-- base backup 上次跑時間
-- (pgBackRest API 或 backup catalog)
```

Prometheus alert 三條：archive failed_count 增、archive lag > 5min、base backup > 25h 沒跑。

### 下一步議題

- **Incremental backup（PG 17+）**：base backup 不全量、只 base + incremental
- **Block-level differential**：pgBackRest 已支援
- **Cloud-native 替代**：RDS / Aurora 用 storage-layer snapshot、不走 PITR 鏈
- **`pg_dump` vs PITR**：pg_dump 是 logical backup（resume to different schema OK）、PITR 是 physical（必須同 version + same arch）

## 相關連結

- 上游 vendor 頁：[PostgreSQL](/backend/01-database/vendors/postgresql/)
- 上游 chapter：[Database Migration Playbook](/backend/01-database/database-migration-playbook/) — PITR 是 migration 的失敗回退
- 平行 deep article：[Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/) / [Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/) / [autovacuum tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)
- Methodology：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)
