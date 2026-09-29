---
title: "PostgreSQL major version upgrade（14 → 17）：upgrade audit、升級方法與故障演練"
date: 2026-05-19
description: "PostgreSQL 同 vendor major version upgrade 涵蓋升級前的 audit（extension 相容性、breaking change、replication slot、config 預設值、statistics 重建）、pg_upgrade / logical replication / blue-green 的選擇與執行步驟，以及升級後常見的故障與處置"
weight: 40
tags: ["backend", "database", "postgresql", "version-upgrade", "deep-article"]
---

> 這篇整理 PostgreSQL 14 → 17 同 vendor major version upgrade 的升級前 audit、升級方法選擇、執行步驟與故障演練。

## Major version upgrade 的工作量集中在 upgrade audit

跟換 vendor 的 migration 相比，PostgreSQL 14 → 17 的 wire protocol、SQL syntax、operational tooling 與元件數量幾乎不變，多數 application 不用改 code。工作量集中在同 vendor 升級才有的幾件事：

- **Extension 相容性**：pg14 的 extension 不一定能在 pg17 直接用（API 變動 / ABI break）
- **Breaking change**：每個 major version 有 release-specific behavior change（例：pg15 起新建的 database 裡，一般使用者預設不能在 `public` schema 建物件；pg_upgrade 與 dump-restore 會保留舊 database 原本的權限，所以這一項在升級後新建的 database 上才出現）
- **Storage format**：major version 之間 *data dir 不向後相容*、必須 `pg_upgrade` 或 dump-restore
- **Statistics 重建**：upgrade 後 `pg_statistic` 失效、必須跑 `ANALYZE`、否則 query plan 退化
- **Replication slot**：logical replication slot 不跨 major version

這幾件事在〈Upgrade audit〉逐項展開。

## 問題情境：major version 不只是 minor bump

PostgreSQL major version（14 / 15 / 16 / 17）一年一版、每版含 *breaking change*、不是 minor bump。常見升級驅動：

- **EOL pressure**：PostgreSQL 每版 maintained 5 年、pg14 EOL 2026-11；pg13 EOL 2025-11 已過、production 仍跑 pg13 是 risk
- **新 feature 需求**：pg15 MERGE / pg16 `pg_stat_io`（I/O 統計 view）/ pg17 incremental backup
- **Cloud provider 強制**：Aurora / RDS 對 EOL 版本停 minor patch、planned upgrade 不能拖

不升級的代價：security patch 停發、新功能不能用、跟新 client / extension 漸增不相容。

## Upgrade audit

升級前的硬閘門 audit、跳過任一個 production 必踩：

### Extension 相容性

```sql
SELECT extname, extversion FROM pg_extension WHERE extname != 'plpgsql';
```

對每個 extension 跑：

1. 對應 target version (pg17) 是否有 release？
2. ABI break？（如 PostGIS major version 對應 PG major version）
3. 是否有 maintainer 持續更新？（TimescaleDB 已不 cover pg17 部分 feature）

常見 pg14 → pg17 需要 *先升 extension* 的：PostGIS / TimescaleDB / pgaudit / pg_partman / pg_repack。

### Breaking change pull

```bash
# 查 release note 累積 breaking change（pg14 → pg17 跨 3 個 major）
# pg15: deprecated public schema 預設 write 權限變嚴
# pg16: regrole removed implicit casts
# pg17: removed several deprecated columns from system catalogs
```

對每個 breaking change：

1. 用 SQL grep / static analysis 找 application code 影響範圍
2. 評估修改工作量（多數命中是 false alarm，逐條確認哪些是真實影響）
3. 列出無法立刻修的、規劃 *逐 major 升* 而不是 *一次升 3 major*

### Replication / logical slot

```sql
SELECT slot_name, plugin, slot_type, active FROM pg_replication_slots;
```

major version upgrade 後：

- **Physical replication slot**：standby 必須先升級到 *相同 major version* 才能跟新 primary
- **Logical replication slot**：**不跨 major version**、必須在 upgrade 前 drop、之後重建（消費者重 init load）
- 對應 [Debezium CDC](/backend/01-database/vendors/postgresql/logical-replication-debezium/) consumer 必須重 init

### Config 參數變更

```bash
# diff postgresql.conf default 14 vs 17
# 重點: shared_preload_libraries / autovacuum_* / wal_level / synchronous_commit
```

新 major version 會改預設值或移除參數，自定 config 需逐項 review。pg14 → 17 之間的例子：pg15 把 `hash_mem_multiplier` 預設從 1 改成 2；pg16 移除 `promote_trigger_file` 與 `vacuum_defer_cleanup_age`，設定裡還帶著它們時新版本啟動會以 unrecognized configuration parameter 失敗。

### Statistics 重建計畫

`pg_upgrade` 後 `pg_statistic` 重置、第一次跑 query plan 用空 stats、production 性能會塌；upgrade 計畫必須含：

- `ANALYZE` 跑全 DB（小 DB ~10 分鐘、大 DB 1-3 小時）
- 多 stage `vacuumdb --analyze-in-stages` 先快速跑 baseline、再跑 full
- Maintenance window 內預留 statistics 重建時間

## 升級方法選擇

三種主流方法、依 downtime 容忍跟 DB 大小：

| 方法                  | Downtime             | 風險                                          | 適用                               |
| --------------------- | -------------------- | --------------------------------------------- | ---------------------------------- |
| `pg_upgrade --link`   | 10-30 分鐘           | data dir 跟 OS package 同 host、回退複雜      | < 500GB、可接受 30 分鐘 downtime   |
| Logical replication   | 切換瞬間（< 1 分鐘） | 設定複雜、long-running migration window       | TB 級、低 downtime 需求            |
| Blue-green deployment | 切換瞬間             | 雙倍硬體、cutover 期間需嚴格 traffic shifting | Cloud-managed（Aurora / RDS 內建） |

### `pg_upgrade --link` 流程

```bash
# 1. install pg17 binary（不啟動）
# 2. stop pg14
sudo systemctl stop postgresql@14

# 3. 跑 pg_upgrade（hard link、不複製資料）
sudo -u postgres /usr/lib/postgresql/17/bin/pg_upgrade \
  --old-bindir=/usr/lib/postgresql/14/bin \
  --new-bindir=/usr/lib/postgresql/17/bin \
  --old-datadir=/var/lib/postgresql/14/main \
  --new-datadir=/var/lib/postgresql/17/main \
  --link \
  --jobs=8

# 4. 啟動 pg17
sudo systemctl start postgresql@17

# 5. 重建 statistics（pg_upgrade 結束時印出的建議；pg14 起不再產生 analyze_new_cluster.sh）
sudo -u postgres /usr/lib/postgresql/17/bin/vacuumdb --all --analyze-in-stages
```

`--link` 用 hard link、不複製 data dir、適合大 DB；缺點是 *回退到 pg14 不可能*（data dir 已被新 pg 修改）— 必須有完整 backup + tested restore。

## 故障演練

### Extension 相容性沒先 audit、upgrade 後啟動失敗

**徵兆**：pg_upgrade 跑完、`pg_ctl start` 失敗、log 顯示 `could not load library "timescaledb-2.13.so"`。

**根因**：TimescaleDB 對應 pg14、pg17 需要 TimescaleDB 2.16+；pg_upgrade 階段沒 check、library path 找不到。

**修法**：

1. **Pre-upgrade audit**：每個 extension 列出 target version 對應、預先升 extension（在 pg14 上跑、用 `ALTER EXTENSION ... UPDATE`）
2. **回退**：data dir 用 `--link` 已不可逆、必須從 backup restore + 重試
3. **預防**：staging 環境完整 dry-run、production upgrade 前已知 path 都驗證過

### Application 用 deprecated SQL、跑壞

**徵兆**：upgrade 後某些 application query 直接 error `ERROR: type "regtype" does not have a cast`。

**根因**：pg16 移除了某些隱性 cast、application code 用了 implicit cast、現在 explicit cast 才能跑。

**修法**：

1. **Pre-upgrade**：跑 application test suite 對 pg17 staging、catch 不相容 query
2. **緊急**：staging 找到的 query 在 production 改 application code、deploy 後再 upgrade DB
3. **長期**：application code 用 ORM / query builder、避免 raw SQL 對 PG version-specific behavior 依賴

### `ANALYZE` 沒跑、production query 性能崩

**徵兆**：upgrade 後 5 分鐘、application latency p99 從 50ms 衝到 5000ms；query plan 從 index scan 退化到 seq scan。

**根因**：`pg_upgrade` 重置 `pg_statistic`、planner 用空 stats 跑 plan、無法估 selectivity、保守選 seq scan。

**修法**：

```bash
# upgrade 完立刻跑；vacuumdb 對每個 database 依序跑三輪 ANALYZE，statistics target 由小到大
vacuumdb --all --analyze-in-stages --jobs=4
# 每一輪開始時 vacuumdb 印出的訊息：
#   Generating minimal optimizer statistics (1 target)     快、~5 分鐘
#   Generating medium optimizer statistics (10 targets)    ~30 分鐘
#   Generating default (full) optimizer statistics         1-3 小時
```

minimal 那一輪跑完，planner 就有大致正確的 selectivity 可用；default (full) 那一輪可以在 maintenance window 結束後繼續跑。

### Logical replication slot 漏 drop、Debezium 卡死

**徵兆**：upgrade 完開機後、Debezium connector log 顯示 `slot not found`、消費停滯；Kafka downstream 訊息斷流。

**根因**：logical replication slot 不跨 major version、`pg_upgrade` 不自動處理 logical slot；upgrade 前沒 drop、新 cluster 上 slot 不存在。

**修法**：

1. **Pre-upgrade**：列所有 logical replication slot、Debezium 暫停 consumer + drop slot
2. **Upgrade 後重建**：用新 LSN starting position 建 slot、Debezium snapshot.mode=schema_only_recovery 取代 initial（避免重 init load）
3. **架構**：未來考慮用 *outbox pattern*、CDC 只追 outbox 表、降低 logical slot 重建成本

### Standby 沒同步升、replication 斷

**徵兆**：primary 升 pg17 後、standby 仍 pg14、replication 不通；`pg_stat_replication` 沒 standby connection。

**根因**：streaming replication 不跨 major version；standby 必須 *先升* 或 *upgrade 後重 base backup*。

**修法**：

兩種策略：

1. **In-place upgrade standby**：standby 也跑 `pg_upgrade`、但要先 stop streaming、升完重接（standby 端 archive_command + restore_command 對齊）
2. **Rebuild standby**：upgrade primary 完、standby 跑 `pg_basebackup` 重建（適合 standby 容量小、network 快）

Patroni HA 環境同樣受「streaming replication 不跨 major version」限制：standby 不能先升級再 failover 過去，要等 primary 升完、再用上面兩種策略處理 standby。複雜度高、需要 staging 演練。

## Capacity / downtime trade-off

| 方法                      | Downtime 估算（500GB DB）          | 硬體成本                  | 風險                |
| ------------------------- | ---------------------------------- | ------------------------- | ------------------- |
| `pg_upgrade --link`       | 15-30 分鐘（含 ANALYZE 1st stage） | 同當前                    | 高（不可逆）        |
| `pg_upgrade`（預設 copy） | 1-3 小時                           | 暫時 2x storage           | 中                  |
| Logical replication       | < 1 分鐘 cutover                   | 暫時 2x compute + storage | 中（複雜）          |
| Blue-green                | 切換瞬間（< 30 秒）                | 持續 2x（cutover 後可拆） | 低（cloud managed） |

實務 default：

- 可接受 30 分鐘 downtime：`pg_upgrade --link`（hard link 不複製資料，停機時間不隨 DB 大小等比例增加）
- 要求 < 5 分鐘 downtime：logical replication（標準 PostgreSQL）
- 1TB+ 或 SLA 嚴格：blue-green via Aurora / RDS（cloud managed）

## 整合 / 下一步

### 跟 [Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/) 整合

HA cluster upgrade 流程：

1. 升新 standby（不在 cluster 中、用 logical replication 同步過去）
2. Promote 新 standby、舊 cluster failover 過去
3. 重建剩餘 standby

PostgreSQL 17+ 支援 [logical slot 跨 failover](/backend/01-database/vendors/postgresql/patroni-ha/) — major version upgrade 期間 logical consumer 影響降低。

### 跟 monitoring 整合

upgrade 期間特別關注的 metric：

```sql
-- Pre-upgrade baseline
SELECT pg_database_size('myapp'), version();

-- Post-upgrade verification
SELECT pg_database_size('myapp'), version();
SELECT count(*) FROM pg_stat_user_tables WHERE last_analyze IS NULL;
-- 應該 = 0、若有未 analyze 表、ANALYZE 沒跑完
```

Prometheus alert 三條：`pg_database_size` upgrade 後差異 < 1%、`pg_stat_replication` lag < 10s、`pg_query_p99_latency` 對 baseline < 1.5x。

### 下一步議題

- **Aurora major version upgrade**：blue-green deployment 是 default、流程跟 self-managed 完全不同、見 [PostgreSQL → Aurora migration](/backend/01-database/vendors/postgresql/migrate-to-aurora/) 對位段
- **Cross-major version skip upgrade**：pg13 → pg17 跨 4 major、breaking change 累積、建議 *逐 major 升* 而不是 *single hop*
- **Extension lifecycle 管理**：自動 audit extension 跟 PG version compatibility、每 quarter 跑 dry-run

## 相關連結

- 上游 vendor 頁：[PostgreSQL](/backend/01-database/vendors/postgresql/)
- PostgreSQL 的其他主題：[Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/) / [PITR + WAL Archiving](/backend/01-database/vendors/postgresql/pitr-wal-archiving/) / [Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/)
- 對位 migration：[PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/)
- Methodology：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/) / [Migration playbook methodology](/posts/migration-playbook-methodology/)（本文驗證 *漏類*）
