---
title: "MySQL InnoDB Tuning：為什麼一個 100 GB DB 在 64 GB RAM server 上 query 慢 5 倍"
date: 2026-05-19
description: "InnoDB 是 MySQL 預設 storage engine、預設值給 256 MB buffer pool（早期 default）。本文從一個常見痛點開場（DB > RAM 但 server 仍 swap）、走 4 個 critical knob（buffer pool / redo log / flush method / IO capacity）、各自如何影響讀寫吞吐、配置 step-by-step、5 production 踩雷（buffer pool warm-up / log file 大小 / 設 sync_binlog=0 換速度 / IO scheduler / undo log 膨脹）、跟 SSD / NVMe / EBS 的 IO 假設"
weight: 16
tags: ["backend", "database", "mysql", "innodb", "performance", "tuning", "deep-article"]
---

> 本文是 [MySQL](/backend/01-database/vendors/mysql/) overview 的 implementation-layer deep article。Overview 已說明 MySQL 在 OLTP 譜系的定位、本文聚焦 *InnoDB engine tuning* — 4 個影響最大的 knob 跟對應 production 行為。

---

## 開場：常見痛點

一個 100 GB MySQL DB、64 GB RAM 的 server、p99 query latency 從 5ms 飆到 50ms。第一直覺是 server overload — 但 CPU < 30%、disk IO 50 IOPS。為什麼慢？

打開 `SHOW VARIABLES LIKE 'innodb_buffer_pool_size'`：`134217728`（128 MB）。對 64 GB RAM server、buffer pool 只用了 128 MB、剩 99.9% 的 working set 每次 query 都要從 disk 讀。CPU 閒、disk 沒滿、是因為 *MySQL 自己不用 RAM* — 用 InnoDB 預設值跑 100 GB DB 等於 disk-only 模式。

這個案例展示 InnoDB tuning 的核心：MySQL 預設值是 *為 16 GB RAM 設計*、production server RAM 越大、預設值離 optimal 越遠。

## 4 個 critical knob

對 90% production case、調這 4 個就解決大部分 InnoDB 性能問題：

| Knob                             | 預設             | 對 production 建議                                        | 影響                     |
| -------------------------------- | ---------------- | --------------------------------------------------------- | ------------------------ |
| `innodb_buffer_pool_size`        | 128 MB           | 系統 RAM 50-75%（dedicated server 75%）                   | 讀效能（資料能否在 RAM） |
| `innodb_log_file_size`           | 48 MB（×2 file） | 1-4 GB（依寫吞吐、8.0.30+ 改 `innodb_redo_log_capacity`） | 寫效能（flush 頻率）     |
| `innodb_flush_log_at_trx_commit` | 1 (full ACID)    | 1（金融 / 訂單）/ 2（高吞吐可容 1 秒 loss）               | 寫吞吐 vs durability     |
| `innodb_io_capacity` + `_max`    | 200 / 2000       | SSD: 2000 / 20000; NVMe: 10000 / 40000                    | flush 速度（適配儲存）   |

其他 knob（`innodb_thread_concurrency` / `innodb_buffer_pool_instances` / `innodb_read_io_threads` 等）也有影響、但對多數 case *先把這 4 個調對* 比微調其他 20 個重要。

## Knob 1：Buffer pool — 把 working set 拉進 RAM

[InnoDB buffer pool](/backend/knowledge-cards/buffer-pool/) 是 *page cache* — 從 disk 讀過的 16 KB page 快取在 RAM、下次 query 直接 RAM 讀。Buffer pool 越大、cache hit ratio 越高、disk IO 越少。

**Sizing**：

- *Dedicated MySQL server*：RAM 70-80%（剩 20-30% 給 OS / MySQL 其他結構 / connection buffer）
- *Shared server*：RAM 30-50%（看其他 process 需求）
- *Container / Kubernetes*：對 container memory limit 70%（不是 host RAM）

```ini
# 64 GB RAM dedicated server
innodb_buffer_pool_size = 48G
innodb_buffer_pool_instances = 8  # 分 8 個 instance 降 mutex contention（每 instance 6 GB）
```

**Buffer pool warm-up**：MySQL 重啟後 buffer pool 是空的、要慢慢從 disk 把熱資料拉回 RAM。預設 5.7+ MySQL 啟動時 *dump buffer pool LRU list 到 disk*、重啟時 *自動 restore*：

```ini
innodb_buffer_pool_dump_at_shutdown = 1
innodb_buffer_pool_load_at_startup = 1
innodb_buffer_pool_dump_pct = 75  # 只 dump 最 hot 的 75% page list
```

沒這個 warm-up、重啟後第 1 個小時 query latency 都偏高、application 看到 p99 spike。

## Knob 2：Redo log — flush 頻率跟寫吞吐

InnoDB 寫入 *先寫 redo log（順序寫）*、再非同步寫到 data file（隨機寫）。Redo log 滿了強迫 flush data file、flush 期間寫吞吐降。

`innodb_log_file_size` 控制每個 log file 大小（預設 2 個 file）：

- 5.7：預設 48 MB × 2 = 96 MB total
- 8.0：預設仍是 48 MB × 2、8.0.30+ 改用動態 `innodb_redo_log_capacity`（default 100 MB total）

對 5K WPS server、預設容量可能 *每分鐘 flush 一次*、寫吞吐持續 stall。提高到 1-4 GB total、flush 改成每 30 分鐘一次、寫吞吐穩定。

```ini
innodb_log_file_size = 2G       # 大寫吞吐 server 設 1-4 GB
innodb_log_files_in_group = 2   # 預設 2 個就夠
innodb_log_buffer_size = 64M    # log 寫 disk 前的 RAM buffer
```

**Trade-off**：log file 越大、recovery 時間越長（crash 後 InnoDB 要 replay 全部 log）。1 GB log 通常 < 1 分鐘 recovery、4 GB 可能 5 分鐘以上。SSD / NVMe 這個 trade-off 不嚴重、HDD 要注意。

MySQL 8.0+ 改進：log file 可動態調整（不用重啟）、且 *automatic redo log writer threads* 降低 mutex contention。

## Knob 3：Flush method — ACID vs 吞吐

`innodb_flush_log_at_trx_commit` 控制 *每個 transaction commit 時要不要 flush log 到 disk*：

- `1`（預設）：每次 commit fsync log file → *zero data loss on crash*
- `2`：每次 commit 寫 log file（但 OS-level cache、不 fsync）→ *server crash 不丟、OS crash 丟 1 秒*
- `0`：每秒 fsync 一次 → *任何 crash 丟 1 秒*

`sync_binlog` 對應 binlog（不是 InnoDB log）：

- `1`（建議）：每次 commit fsync binlog
- `0`：依賴 OS sync、容易丟 binlog → replication / CDC 風險

**Production 組合**：

| 用途                       | `innodb_flush_log_at_trx_commit` | `sync_binlog` | 寫吞吐   | Crash data loss   |
| -------------------------- | -------------------------------- | ------------- | -------- | ----------------- |
| 金融 / 訂單 / 支付         | 1                                | 1             | baseline | 0                 |
| 一般 web 應用              | 1                                | 1             | baseline | 0                 |
| 高寫吞吐 + 容忍 1 sec loss | 2                                | 1             | +30-50%  | OS crash 丟 1 秒  |
| Dev / test                 | 2                                | 0             | +50-100% | 不重要            |
| 不要這樣設                 | 0                                | 0             | +100%    | 任意 crash 丟資料 |

多數 production 用 `1 + 1`、雖然慢但 *簡單可預測*。改成 `2 + 1` 之前要明確 *能容忍 1 秒 data loss*、且通常 review 過 Disaster Recovery Plan。

## Knob 4：IO capacity — 適配儲存

InnoDB 後台 flush 速度受 `innodb_io_capacity` 限制：

- `innodb_io_capacity`（一般）：後台 flush 目標 IOPS
- `innodb_io_capacity_max`（突發）：emergency flush 上限

**對應儲存類型**：

| 儲存         | IOPS 能力       | `innodb_io_capacity` | `innodb_io_capacity_max` |
| ------------ | --------------- | -------------------- | ------------------------ |
| 7200 RPM HDD | ~80 IOPS        | 100                  | 200                      |
| SSD (SATA)   | 10K-50K IOPS    | 2000                 | 20000                    |
| NVMe SSD     | 100K-500K IOPS  | 10000                | 40000                    |
| EBS gp3      | 3000-16000 IOPS | 5000                 | 16000                    |
| EBS io2      | 50K-256K IOPS   | 20000                | 60000                    |

預設 `200 / 2000` 是 *為 HDD 設計*、SSD / NVMe server 用預設值 = InnoDB 自我限速、flush 慢、寫入瓶頸。

```ini
# NVMe SSD server
innodb_io_capacity = 10000
innodb_io_capacity_max = 40000
innodb_flush_neighbors = 0  # NVMe 不需要 group flush 相鄰 page
```

## 5 個 Production 踩雷

### 1. Buffer pool 沒 warm-up — 重啟後 1 小時 p99 飆

MySQL 重啟（OS upgrade / config change / failover）後、buffer pool 是空的、所有 query 第一次都 disk 讀、p99 latency 飆 5-10x、application 看到 timeout。

修法：

- 啟用 `innodb_buffer_pool_dump_at_shutdown=1` + `innodb_buffer_pool_load_at_startup=1`
- 對 *沒 graceful shutdown* 的 crash（OOM / kernel panic）、buffer pool 沒 dump、warm-up 後第一個小時仍辛苦
- 重要 server 重啟前手動 dump：`SET GLOBAL innodb_buffer_pool_dump_now=ON`
- 對於不能容忍 cold cache 的場景、failover 前 *先 pre-warm new primary*（用 query replay 把 hot data 拉到 buffer pool）

### 2. Log file size 設太小 — checkpoint storm

`innodb_log_file_size=48M` 預設、高寫吞吐 server log 每分鐘 flush 一次、flush 期間 *checkpoint storm* — 寫吞吐降 50%、p99 暴增。錯誤訊號是 `innodb_log_waits` 持續 > 0。

修法：

- 監控 `SHOW STATUS LIKE 'Innodb_log_waits'` — 應該長期接近 0
- 提高 `innodb_log_file_size` 到 1-4 GB（依寫吞吐）
- 8.0+ 可動態調整、5.7 需要 *正常 shutdown* 後改、開啟前先 dump buffer pool（避免 cold cache）

### 3. `sync_binlog=0` 換速度 — replication 永久 broken 風險

開發 / staging 改 `sync_binlog=0`（加快寫入）、後來複製到 production 配置、production 同樣 `sync_binlog=0`。OS crash 後 binlog 缺最後幾秒 transaction、replica 跟 primary GTID set diverge、replication broken、要 *重建 replica from base backup*（小時級 recovery）。

修法：

- *Production 永遠用 `sync_binlog=1`*、不要為了寫吞吐犧牲 binlog durability
- 開發 / staging 配置跟 production 隔離、不要直接 copy config
- Replica 失聯後 *用 GTID 自動 re-attach*（不是 binlog position）— 仍然需要 binlog 完整、`sync_binlog=0` 仍是風險

### 4. IO scheduler — 不是 InnoDB tuning 但影響大

Linux `noop` / `deadline` / `cfq` IO scheduler 對 SSD / NVMe 影響大：

- `cfq`（traditional spinning disk default）：對 SSD 嚴重 bottleneck
- `deadline`：對 SSD 較好、但有 latency cap
- `noop` / `none`：對 NVMe 最好（讓 device 自己處理 queue）

**Production check**：

```bash
cat /sys/block/sda/queue/scheduler
# 應該顯示： [none] mq-deadline (NVMe)
# 或：         noop deadline [cfq] (cfq 是錯的)
```

不是 InnoDB knob、但影響 InnoDB IO behavior > 30%。InnoDB tuning 前先確認 OS-level IO scheduler 對。

### 5. Undo log 膨脹 — purge 跟不上

Undo log 紀錄 *未來可能 rollback 需要的舊版本 row*。長 transaction（hours-level）讓 undo log 持續累積、不能 purge、最後 InnoDB tablespace 膨脹幾 GB、disk 滿。

訊號：

- `SHOW ENGINE INNODB STATUS` 看 `History list length` 持續成長（正常 < 1000、異常 millions）
- `information_schema.innodb_metrics` 的 `trx_rseg_history_len`

修法：

- 找 long-running transaction：`SELECT * FROM information_schema.innodb_trx WHERE trx_started < NOW() - INTERVAL 1 HOUR`
- KILL 該 transaction（謹慎、可能 application bug）
- 8.0+ 用 separate undo tablespace（`innodb_undo_tablespaces`）、不污染 main tablespace、且可以 truncate

## 容量規劃要點

對 64 GB RAM、NVMe SSD、5K WPS、100 GB DB 的 server：

```ini
# my.cnf production-ready baseline
[mysqld]
# Buffer pool (75% RAM)
innodb_buffer_pool_size = 48G
innodb_buffer_pool_instances = 8
innodb_buffer_pool_dump_at_shutdown = 1
innodb_buffer_pool_load_at_startup = 1

# Redo log
innodb_log_file_size = 2G
innodb_log_files_in_group = 2
innodb_log_buffer_size = 64M

# Flush behavior
innodb_flush_log_at_trx_commit = 1
sync_binlog = 1
innodb_flush_method = O_DIRECT  # 跳過 OS page cache 避免 double cache

# IO capacity (NVMe)
innodb_io_capacity = 10000
innodb_io_capacity_max = 40000
innodb_flush_neighbors = 0
innodb_lru_scan_depth = 1024

# Concurrency
innodb_thread_concurrency = 0  # 0 = no limit (8.0+ 推薦)
innodb_read_io_threads = 8
innodb_write_io_threads = 8

# 額外
innodb_file_per_table = 1
innodb_strict_mode = 1
```

跨不同 server spec、`buffer_pool_size` / `io_capacity` 隨硬體調整、其他 knob 變動小。

## 跟其他模組整合

### 跟 Replication topology

`sync_binlog=1` + `innodb_flush_log_at_trx_commit=1` 是 *durability baseline*、影響 [Replication Topology](/backend/01-database/vendors/mysql/replication-topology/) 的 *primary durability*。Semi-sync 加在這基礎上提供 *跨 server durability*。

### 跟 ProxySQL

ProxySQL connection pool 降低 *MySQL connection 開銷*、但 *每個 connection* 仍消耗 8-10 MB RAM（thread stack + session buffer）。Buffer pool 設 75% RAM 後、剩 25% 給 connection / temporary buffer / OS。Connection 太多會擠掉 buffer pool。

詳見 [ProxySQL 配置](/backend/01-database/vendors/mysql/proxysql-config/)。

### 跟 Aurora MySQL

Aurora 改寫 InnoDB storage layer、上方 knob 大多 *Aurora 自動管理*：

- Buffer pool size：Aurora compute instance 自動配
- Redo log：Aurora 自己的 distributed log、不用 `innodb_log_file_size`
- `sync_binlog` / `innodb_flush_log_at_trx_commit`：Aurora storage layer 保證 durability、應用層 knob 影響小

Aurora user 仍可 tune `innodb_buffer_pool_size` 等、但操作面從 InnoDB 內部議題變成 *Aurora instance class 選擇*。詳見 [Aurora vendor page](/backend/01-database/vendors/aurora/)。

### 跟 OSC tool

InnoDB tuning 不直接影響 OSC 工具行為、但 *log file size 太小* 時 gh-ost / pt-osc 寫 ghost table 容易 trigger checkpoint storm、放慢整個 schema migration。詳見 [Online Schema Change Tools](/backend/01-database/vendors/mysql/online-schema-change-tools/)。

## 觀測 metric

`SHOW STATUS LIKE` + Performance Schema 提供：

- `Innodb_buffer_pool_read_requests` / `_reads` → cache hit ratio = `1 - reads/read_requests`、應該 > 99%
- `Innodb_log_waits` → checkpoint pressure、應該 = 0
- `Innodb_log_write_requests` / `_writes` → log buffer 效率
- `Innodb_rows_inserted` / `_updated` / `_read` → workload 形狀
- `Innodb_row_lock_waits` / `_time` → lock contention

把這些丟進 [Datadog](/backend/04-observability/vendors/datadog/) / [Prometheus](/backend/04-observability/vendors/prometheus/) 透過 [mysqld_exporter](https://github.com/prometheus/mysqld_exporter) / [Percona Monitoring](https://www.percona.com/software/database-tools/percona-monitoring-and-management) 持續 trend。

## 相關連結

- [MySQL vendor overview](/backend/01-database/vendors/mysql/)
- [MySQL Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)（`sync_binlog` 跟 replication 互動）
- [MySQL ProxySQL 配置](/backend/01-database/vendors/mysql/proxysql-config/)（connection 跟 buffer pool 爭 RAM）
- [Aurora vendor page](/backend/01-database/vendors/aurora/)（managed MySQL、InnoDB tuning 部分轉手）
- [PostgreSQL Autovacuum Tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)（PG sibling、不同 engine 內部 tuning）
- 官方：[InnoDB Configuration](https://dev.mysql.com/doc/refman/8.0/en/innodb-default-se.html) / [Percona Tuning Guide](https://www.percona.com/blog/mysql-101-tuning-mysql-after-installation/)
