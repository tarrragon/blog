---
title: "MySQL Online Schema Change：gh-ost 跟 pt-online-schema-change 兩條完全不同的 ghost table 路徑"
date: 2026-05-19
description: "MySQL ALTER TABLE 鎖整張表、production 不能直接跑。gh-ost（GitHub）跟 pt-online-schema-change（Percona）都用 ghost table 解決、但底層機制完全不同：pt-osc 用 trigger 同步、gh-ost 用 binlog stream 同步。本文走兩工具機制對照表 → trigger vs binlog 各自取捨 → 配置 step-by-step → 5 production 踩雷（trigger overhead / binlog 延遲 / FK constraint / hot trigger lock / 切換瞬間 deadlock）→ 何時用哪一個"
weight: 13
tags: ["backend", "database", "mysql", "schema-migration", "online-ddl", "deep-article"]
---

> 本文是 [MySQL](/backend/01-database/vendors/mysql/) overview 的 implementation-layer deep article。Overview 已說明 MySQL 在 OLTP 譜系的定位、本文聚焦 *online schema change* — gh-ost 跟 pt-online-schema-change 兩條工具路徑的機制對比。

---

| 機制                  | pt-online-schema-change（Percona）                          | gh-ost（GitHub）                                |
| --------------------- | ----------------------------------------------------------- | ----------------------------------------------- |
| 同步機制              | **MySQL trigger**（原表 INSERT/UPDATE/DELETE 觸發寫 ghost） | **Binlog stream**（讀 primary binlog 寫 ghost） |
| Primary 寫入 overhead | trigger 觸發成本（同 transaction 內）                       | 0（binlog 已存在）                              |
| Replica lag 影響      | trigger 在 primary 跑、replica 自然 lag                     | 從 replica 讀 binlog、可主動 throttle           |
| Foreign key           | 部分支援（drop/recreate strategy）                          | 不支援（必須先 drop FK）                        |
| Roll back（過程中）   | 困難（trigger 已建、要清乾淨）                              | 容易（drop ghost table 即可）                   |
| 暫停 / resume         | 不支援                                                      | 支援（gh-ost interactive command）              |
| 切換時 lock 持續      | rename 期間 metadata lock（毫秒級）                         | rename 期間 metadata lock（毫秒級）             |
| 工具 binary           | Perl 腳本（Percona Toolkit）                                | Go binary（單一可執行檔）                       |
| 推出年份              | 2011                                                        | 2016                                            |

兩工具最終結果一樣（ghost table 取代原表）、但 *過程中對 production 的影響非常不同*。選哪個取決於：trigger overhead 可不可接受、是否有 foreign key、是否需要 resume/throttle 能力、團隊熟悉哪條工具鏈。

## 為什麼 ALTER TABLE 不能直接跑

MySQL 8.0 之前的 `ALTER TABLE` 多數情況下 *rebuild 整張表* — 過程中 *primary key 之外的 read/write 都 block*。100 GB 表 ALTER 跑 hours、production write 全部失敗。

MySQL 8.0 加 *Instant DDL*（部分 ALTER 不 rebuild、只改 metadata、毫秒級完成）、但 *能用 instant 的 ALTER 是 subset*：

- 支援：ADD COLUMN（末尾）、DROP COLUMN（部分情境）、RENAME COLUMN
- 不支援：ADD INDEX、CHANGE COLUMN type、ADD/DROP PRIMARY KEY、ADD FOREIGN KEY

不支援 instant 的場景仍要走 ghost table。Percona 跟 GitHub 各自從 production 痛點出發、產出 pt-osc（2011）跟 gh-ost（2016）。

## pt-online-schema-change：用 trigger 同步寫入

pt-osc 流程：

1. CREATE ghost table（跟原表同 schema + 你要的 ALTER）
2. 在原表上 *建 3 個 trigger*：INSERT / UPDATE / DELETE
3. 任何寫入原表的 transaction *同時觸發 trigger* 寫對應 ghost
4. 背景 chunk-by-chunk copy 既有 row 到 ghost
5. 全部 copy 完後 `RENAME TABLE`：原表 → archive、ghost → 原表名（atomic、metadata lock 毫秒級）
6. Drop trigger、drop archive

**Trade-off**：

- *寫入 overhead*：每個 primary 寫入 transaction 都多一次 trigger 執行、寫吞吐降 10-30%
- *Replica lag*：trigger 跟原寫入同 transaction、replica 上每個 row 也跑 trigger、replica lag 可能暴增（不能主動 throttle）
- *Roll back 困難*：tool 跑到一半失敗、trigger 已建、要手動清掉才能 retry
- *FK 處理*：原表有 FK 指向時、ghost table 要先 drop FK 再 recreate、操作複雜

**適用**：

- 寫吞吐 < 50% capacity（有 buffer 撐 trigger overhead）
- 無 FK 或 FK 簡單
- 沒有 replica lag 敏感的 read（trigger 在 replica 也跑）

**不適用**：

- 高寫吞吐（> 80% capacity）— trigger overhead 直接 saturate
- 大量 FK 結構
- 需要 throttle / pause / resume

## gh-ost：用 binlog stream 同步寫入

gh-ost 流程：

1. CREATE ghost table
2. *從 replica 讀 binlog*（不在 primary 加 trigger）
3. 同步 *primary 上的寫入* 透過 binlog event 寫到 ghost
4. 背景 chunk-by-chunk copy 既有 row 到 ghost
5. 全部 copy 完後 swap：`RENAME TABLE`
6. Drop archive

**Trade-off**：

- *寫入 overhead*：0（binlog 已經寫了、gh-ost 只是 consumer）
- *Replica lag 影響*：gh-ost 可監測 replica lag、超過 threshold 自動 throttle copy（不影響 primary 寫入）
- *Roll back 容易*：失敗 / 不要了直接 drop ghost table、原表完全沒被改動
- *FK 不支援*：gh-ost 設計上不處理 FK、有 FK 必須先 drop / restructure

**適用**：

- 高寫吞吐 production（trigger overhead 不可接受）
- 需要 throttle / pause / resume（gh-ost interactive command 可動態調 chunk size、cut-over 時點）
- 已用 GitHub-flavored MySQL operations workflow

**不適用**：

- 有複雜 FK 結構、不想動 schema
- Replica 跑不了 binlog（極少數場景）

## 配置 step-by-step（gh-ost）

實務 production 多用 gh-ost（GitHub / Slack / Booking.com 等）。pt-osc 用於有 FK 或舊系統。

### gh-ost 一個 ALTER 命令

```bash
gh-ost \
  --host=replica.example.com \           # 從 replica 讀 binlog
  --user=ghost \
  --password=... \
  --database=production \
  --table=orders \
  --alter='ADD COLUMN status VARCHAR(20) DEFAULT NULL, ADD INDEX idx_status (status)' \
  --allow-on-master=false \              # 不直接連 primary 讀 binlog
  --chunk-size=1000 \                    # 每批 copy 1000 row
  --max-load='Threads_running=50' \      # primary load 限制
  --critical-load='Threads_running=200' \ # 超過直接 abort
  --max-lag-millis=1500 \                # replica lag 限制
  --throttle-additional-flag-file=/tmp/throttle \  # touch 此檔 throttle
  --postpone-cut-over-flag-file=/tmp/postpone \    # touch 此檔延後 cut-over
  --execute                              # 真的執行（沒這個只 dry-run）
```

### Interactive command（gh-ost 跑起來後）

```bash
# 連 gh-ost socket（同 directory）
echo "status" | nc -U /tmp/gh-ost.production.orders.sock
# 動態調 chunk size
echo "chunk-size=500" | nc -U /tmp/gh-ost.production.orders.sock
# 立即觸發 cut-over（不再等）
echo "unpostpone" | nc -U /tmp/gh-ost.production.orders.sock
# Abort 並 drop ghost
echo "panic" | nc -U /tmp/gh-ost.production.orders.sock
```

## 配置 step-by-step（pt-osc）

對比 gh-ost 的 binlog reader、pt-osc 命令更短但配置義務同樣多：

```bash
pt-online-schema-change \
  --host=primary.example.com \
  --user=ghost \
  --password=... \
  --alter='ADD COLUMN status VARCHAR(20) DEFAULT NULL, ADD INDEX idx_status (status)' \
  D=production,t=orders \
  --chunk-size=1000 \
  --max-load='Threads_running=50' \
  --critical-load='Threads_running=200' \
  --max-lag=1.5 \
  --check-replication-filters \           # 防 binlog filter 漏 trigger
  --alter-foreign-keys-method=auto \      # auto / rebuild_constraints / drop_swap / none
  --execute
```

`--alter-foreign-keys-method` 是 pt-osc 對 FK 處理的策略選項、四種選擇對 production 影響非常不同（rebuild 重建 FK / drop_swap 用更快但少了 atomic、none 是不處理）。

## 5 個 Production 踩雷

### 1. pt-osc trigger overhead 不可預期

`--max-load='Threads_running=50'` 看起來保護了 server、但 trigger 在 transaction 內、production 的 *每個寫入* 都加 trigger 開銷。`Threads_running` 是 *當下* 數字、看不到 trigger 累積 latency。常見場景：高峰時段下 pt-osc、預期 30% overhead、實際 60%、p99 飆 5x。

修法：

- 高峰時段不跑 pt-osc、排 off-peak window
- 用 *staging environment* 跑 production-like load 預估 trigger overhead
- 對寫吞吐 > 50% capacity 的 server 改用 gh-ost

### 2. gh-ost binlog lag 跟 primary 寫入率追不上

gh-ost 從 replica 讀 binlog、binlog event 進來速度有上限。如果 *primary 寫入率超過 gh-ost binlog consume 速度*（每秒幾千 transaction 對某些 server 已是 ceiling）、gh-ost 永遠追不上、cut-over 永遠不能觸發。

修法：

- gh-ost 預設用 *replica binlog*、改用 `--allow-on-master` 直接從 primary 讀（如果 primary 容量夠）
- 提高 `--chunk-size` 加快 copy（同時用 `--max-load` 防過載）
- 真的追不上、考慮 *暫停部分寫入流量*（throttle traffic、不是 throttle tool）

### 3. Foreign key constraint — 兩工具都尷尬

原表有 FK 指向（其他 table FK references 這張表）、ghost table 切換時 *新 ghost 沒有那些 FK 指向*。Cut-over 一瞬間、FK 從指向「原表」變成指向「archive 表」、外部 constraint 失效。

修法（pt-osc）：

- 用 `--alter-foreign-keys-method=rebuild_constraints`：先 ALTER 外部 table FK 指向 ghost、再 cut-over
- 或 `drop_swap`：cut-over 前 drop FK、cut-over 後 recreate（更快但 cut-over 期間 FK 失效）

修法（gh-ost）：

- gh-ost 不支援 — 手動 drop FK / 重 setup FK
- 或維護 schema 改 FK 結構（FK 改在 application 層 enforce）

### 4. pt-osc trigger 跟 application 既有 trigger 衝突

原表上已經有 application 自建 trigger、pt-osc 在原表 *再加 3 個 trigger*、新舊 trigger 執行順序 MySQL 不保證（多 trigger 同事件按 *未定義順序*）。Application 行為可能 subtly broken。

修法：

- 跑 pt-osc 前 audit 原表 trigger（`SHOW TRIGGERS FROM production LIKE 'orders'`）
- 如果有 application trigger、考慮 *暫時 disable 再 ALTER* 或改 gh-ost
- gh-ost 不在原表加 trigger、不會碰到這個問題

### 5. Cut-over 瞬間 deadlock — 兩工具都有但表現不同

Cut-over 用 `RENAME TABLE original TO archive, ghost TO original`（atomic operation）。但 cut-over 瞬間需要 *metadata lock*、跟 *進行中的 long-running transaction* 衝突會 wait。Long-running transaction 持續、cut-over 永遠 wait、最後 timeout 失敗。

修法（gh-ost）：

- `--cut-over-lock-timeout-seconds=3`、超時 abort、稍後 retry
- `--postpone-cut-over-flag-file`：先把 copy 跑完、等流量空檔再觸發 cut-over

修法（pt-osc）：

- `--set-vars="lock_wait_timeout=60"`、cut-over 等更久（風險：long transaction 撐住更久 server 更多 lock wait）
- 或排在 long transaction 已知不會跑的時段（nightly backup 後）

## 容量 / 時間估算

對 100 GB 表、ALTER 加 column + 加 index 為例：

| 維度          | pt-osc                            | gh-ost                        |
| ------------- | --------------------------------- | ----------------------------- |
| 估算總時間    | 6-12 小時（依 chunk size + load） | 5-10 小時（同上、可動態調整） |
| 寫吞吐影響    | -10% ~ -30%（trigger overhead）   | < 5%（binlog 已存在）         |
| Replica lag   | 1-10 秒（trigger 在 replica 跑）  | 自動 throttle 在 threshold 內 |
| Disk 額外需求 | ~原表大小 + index（ghost 用）     | 同左                          |
| Rollback 成本 | 中（清 trigger）                  | 低（drop ghost）              |

兩工具總時間接近、*影響 production 的差異大*。

## 跟其他模組整合

### 跟 GTID / Replication topology

兩工具都 *依賴 replication* — pt-osc 透過 trigger 確保 replica 同步、gh-ost 直接從 replica 讀 binlog。Pre-requisite：

- Binlog `ROW` format（兩工具都要）
- GTID 啟用（gh-ost 更需要、binlog re-pointing 容易）
- 詳見 [Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)

### 跟 Vitess

Vitess 有自己的 *VReplication-based online DDL*、不用 gh-ost 或 pt-osc。Vitess online DDL 在 shard 內部用類似 gh-ost 的 binlog stream 機制、但有 Vitess-aware schema management。詳見 *Vitess sharding 設計* 篇（待寫）。

### 跟 Aurora MySQL

Aurora MySQL 仍支援 gh-ost / pt-osc、但 *Aurora 自己的 fast DDL*（部分 ALTER） 比 8.0 Instant DDL 更廣。先檢查 Aurora 文件、能用 native fast DDL 就不用 ghost table tool。詳見 [Aurora vendor page](/backend/01-database/vendors/aurora/)。

### 跟 PlanetScale

PlanetScale（managed Vitess）走 *branch-based schema migration* — 建 schema branch、跑 schema change、deploy 時 atomic merge。不用 gh-ost / pt-osc、用 PlanetScale 內建。詳見 *→ PlanetScale migration playbook* 篇（待寫）。

## 何時用哪一個

| 情境                                                         | 選擇              | 原因                                   |
| ------------------------------------------------------------ | ----------------- | -------------------------------------- |
| 標準 production write < 50% capacity                         | gh-ost（預設）    | 寫入 overhead 0、控制更細              |
| 高寫吞吐 (> 80% capacity)                                    | gh-ost（必須）    | pt-osc trigger overhead 直接 OOM       |
| 有 FK constraint 不能改                                      | pt-osc            | gh-ost 不處理 FK                       |
| 有 application-side trigger 在原表                           | gh-ost            | pt-osc trigger 跟既有 trigger 不可預期 |
| 需要 pause / resume 能力                                     | gh-ost            | pt-osc 不支援                          |
| 已用 Percona Toolkit 整套（pt-table-checksum / pt-archiver） | pt-osc            | 工具鏈一致                             |
| 已用 Vitess                                                  | Vitess online DDL | 不要 gh-ost / pt-osc                   |
| 已用 PlanetScale                                             | branch-based      | 不要 gh-ost / pt-osc                   |
| 已用 Aurora MySQL + native fast DDL OK                       | 不用 ghost table  | 直接 ALTER                             |

## 相關連結

- [MySQL vendor overview](/backend/01-database/vendors/mysql/)
- [MySQL Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)（binlog ROW format + GTID 是 pre-requisite）
- [Aurora vendor page](/backend/01-database/vendors/aurora/)（managed MySQL fast DDL）
- [PlanetScale](https://planetscale.com/)（branch-based 不用 ghost table）
- [1.6 Database Migration Playbook](/backend/01-database/database-migration-playbook/)（schema migration 治理）
- [Expand / Contract 卡片](/backend/knowledge-cards/expand-contract/)（schema migration 設計原則）
- 官方：[gh-ost](https://github.com/github/gh-ost) / [pt-online-schema-change](https://docs.percona.com/percona-toolkit/pt-online-schema-change.html)
