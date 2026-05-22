---
title: "SQLite PRAGMA Tuning and Performance"
date: 2026-05-21
description: "SQLite journal_mode、synchronous、busy_timeout、wal_autocheckpoint、cache_size、mmap_size、auto_vacuum 與 performance evidence 的操作判準"
tags: ["backend", "database", "sqlite", "performance", "pragma", "deep-article"]
---

> 本文是 [SQLite](/backend/01-database/vendors/sqlite/) overview 的 implementation-layer deep article。Overview 已說明 SQLite 的容量規劃要點；本文聚焦 *PRAGMA 設定如何變成 durability、latency、檔案大小與 restore risk 的取捨*。

SQLite PRAGMA tuning 的核心責任是把單檔資料庫的行為固定成可重複、可觀測、可回退的操作契約。SQLite 的許多重要行為由 connection-level 或 database-level PRAGMA 控制；這些設定看起來像小開關，實際上會影響 crash recovery、commit latency、reader / writer 衝突、檔案大小與測試一致性。

本文的判讀錨點是：PRAGMA 是 durability / latency / maintenance 的顯性取捨，而非效能魔法。Production runbook 要記錄設定值、設定時機、驗證 query 與回退條件，避免不同 process、test runner 或 migration tool 用不同 SQLite 行為。

## Baseline PRAGMA

SQLite baseline PRAGMA 的責任是讓 application 每次啟動都進入同一個資料庫模式。對 production-like local store、small backend 或 test fixture，建議把 journal、sync、foreign key、busy timeout 與 checkpoint 明確設定，而非依賴語言 binding 預設值。

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
PRAGMA wal_autocheckpoint = 1000;
```

| 設定                 | 服務責任                            | 驗證方式                                  |
| -------------------- | ----------------------------------- | ----------------------------------------- |
| `journal_mode=WAL`   | 降低 reader / writer 衝突           | 回傳值為 `wal`，觀察 `-wal` file          |
| `synchronous=NORMAL` | 平衡 fsync cost 與 crash durability | 查 `PRAGMA synchronous`，跑 restore drill |
| `foreign_keys=ON`    | 啟用 FK enforcement                 | `PRAGMA foreign_key_check`                |
| `busy_timeout`       | 吸收短暫 writer queue               | 記錄 busy wait 與 timeout rate            |
| `wal_autocheckpoint` | 控制 WAL growth cadence             | 觀察 WAL size 與 checkpoint duration      |

這張表的重點是把設定與 evidence 綁在一起。若某個 PRAGMA 缺少成功訊號與失敗訊號，就先維持保守預設；盲目追求「最快」通常會把風險推到 power loss、restore 或長尾 latency。

## `journal_mode` 與 WAL boundary

`journal_mode` 的核心責任是決定 transaction 如何保護原始資料。SQLite 預設 rollback journal 對簡單場景合理；WAL mode 則讓 reader 可以在 writer append WAL 時保有 snapshot，適合多 reader、短寫入、互動式 workload。

| 模式     | 適合情境                        | 注意事項                            |
| -------- | ------------------------------- | ----------------------------------- |
| `DELETE` | 最簡單、低併發、短生命週期檔案  | write / read 衝突較明顯             |
| `WAL`    | read-heavy、local app、小型 API | 需要治理 `-wal`、`-shm`、checkpoint |
| `MEMORY` | 暫存測試、可丟資料              | crash 後 recovery 風險高            |
| `OFF`    | 可重建資料、一次性 bulk load    | production formal state 應避開      |

WAL mode 是多數 production-like SQLite 的 baseline，但它也引入 sidecar file 與 checkpoint 責任。完整判讀見 [WAL concurrency / locking](/backend/01-database/vendors/sqlite/wal-concurrency-locking/)。

## `synchronous`：commit latency 與資料損失窗口

`synchronous` 的核心責任是控制 SQLite 在關鍵時刻要求 storage flush 的強度。官方 PRAGMA 文件說明 WAL mode 下 `NORMAL` 會把 sync 主要放在 checkpoint 路徑；這通常讓 commit 更快，但 crash durability 的語意要由 service owner 接受。

| 設定     | 服務語意                          | 適合情境                                      |
| -------- | --------------------------------- | --------------------------------------------- |
| `FULL`   | 更保守的 durability               | 金錢、ledger、不可重建 local state            |
| `NORMAL` | 多數 WAL production-like baseline | local app、小型服務、可接受極小 crash window  |
| `OFF`    | 追求速度，放棄重要 durability     | scratch DB、可重建 cache、bulk import staging |

`synchronous=OFF` 要被視為明確風險接受。若資料是 [source of truth](/backend/knowledge-cards/source-of-truth/)，設定檔、runbook 與 review 都應避免把 staging 的快速設定帶進 production。

## Cache、mmap 與 memory pressure

SQLite memory tuning 的核心責任是降低 read path I/O，同時避免把 device / container memory 壓到不可控。`cache_size` 控制 SQLite page cache；`mmap_size` 讓讀取可透過 memory-mapped I/O 加速，但仍受平台、檔案大小與 memory budget 影響。

```sql
PRAGMA cache_size = -64000;
PRAGMA mmap_size = 268435456;
```

| 設定         | 改善目標               | 觀測訊號                                   |
| ------------ | ---------------------- | ------------------------------------------ |
| `cache_size` | 減少重複 page read     | query latency、disk read、memory usage     |
| `mmap_size`  | 降低 read syscall cost | p95 / p99 read latency、address space      |
| `temp_store` | 控制 temp table 位置   | sort / join query latency、memory pressure |

Memory 設定要和 workload size 一起看。Desktop app、mobile app、edge worker、container service 的 memory ceiling 不同；把 server 上的設定複製到 mobile 或 edge runtime 會讓風險轉移到 OOM 或 OS reclaim。

## Vacuum 與檔案大小治理

Vacuum 設定的核心責任是控制 delete 後的空間回收。SQLite delete row 後，database file 不會自然縮小；`auto_vacuum` 要在 database 建立早期決定，後續切換通常需要 `VACUUM` 重整整個 database。

| 設定 / 操作               | 適合情境                       | 風險 / 成本                            |
| ------------------------- | ------------------------------ | -------------------------------------- |
| `auto_vacuum=NONE`        | 資料量穩定、delete 少          | 檔案可能長期保持高水位                 |
| `auto_vacuum=INCREMENTAL` | 需要逐步回收空間               | 需要排程 `incremental_vacuum`          |
| `VACUUM`                  | maintenance window、重整資料庫 | 需要額外空間與 I/O，可能影響服務       |
| `VACUUM INTO`             | compact copy / backup          | 產出新檔，適合 restore drill 或 export |

檔案大小治理要接到 backup 成本。Database file 長期膨脹會放大備份時間、restore 時間與 edge deploy artifact size；若服務有大量 delete / churn，vacuum policy 要被寫進 runbook。

## Production 踩雷

### Case 1：PRAGMA 只在某個 connection 設定

Connection-level PRAGMA 的核心風險是不同程式路徑行為不一致。Application 啟動時設了 `foreign_keys=ON`，migration tool 或 test runner 沒設，就會出現 production / migration / test 三種語意。

修正方向是把 baseline PRAGMA 放進 shared DB open path，並在 startup health check 印出設定值。Migration CLI、background worker、test fixture 都要共用同一份 connection initialization。

### Case 2：`synchronous=OFF` 從測試環境流到正式資料

快速測試設定外流的核心風險是資料損失只在 crash 後出現。平常 query 都正常，直到 power loss、container kill 或 host crash 後，資料庫出現落差。

修正方向是設定分層。Test / benchmark 可以用 faster profile；formal state profile 要用 `NORMAL` 或 `FULL`，並要求 restore drill。

### Case 3：WAL growth 被誤判成資料成長

WAL growth 的核心風險是 checkpoint 問題被當成容量問題。Disk alert 看到 `db-wal` 變大，若只擴 disk，長 reader 或 checkpoint starvation 仍會持續。

修正方向是把 WAL size、checkpoint return 與 long reader 一起看。先找 reader lifecycle，再調 checkpoint cadence。

### Case 4：Vacuum 在高峰期執行

Vacuum 的核心風險是把 maintenance I/O 放到使用者路徑。檔案縮小是好事，但 full vacuum 會消耗 I/O 與時間，對 mobile / desktop / small backend 都可能造成卡頓。

修正方向是把 vacuum 當 maintenance job。大檔案用 `incremental_vacuum` 或低流量窗口；備份前的 compact copy 可考慮 `VACUUM INTO`。

## 操作檢查清單

SQLite PRAGMA runbook 至少要記錄：

1. 所有 connection 初始化時執行的 baseline PRAGMA。
2. `journal_mode` 實際回傳值與 sidecar file 位置。
3. `synchronous` profile 與資料風險接受者。
4. `busy_timeout` 值、busy wait metric、timeout threshold。
5. `wal_autocheckpoint`、manual checkpoint cadence 與 WAL size alert。
6. `cache_size` / `mmap_size` 對 memory budget 的影響。
7. `auto_vacuum` / `VACUUM` / `VACUUM INTO` 的 maintenance window。

## 下一步路由

- 上游：[SQLite overview](/backend/01-database/vendors/sqlite/)
- 前置：[WAL concurrency / locking](/backend/01-database/vendors/sqlite/wal-concurrency-locking/)
- 操作：[SQLite Hands-on](/backend/01-database/vendors/sqlite/hands-on/)
- 平行：[Observability / runbook](/backend/01-database/vendors/sqlite/observability-runbook/)
- 官方：[SQLite PRAGMA](https://www.sqlite.org/pragma.html)、[SQLite VACUUM](https://www.sqlite.org/lang_vacuum.html)、[SQLite WAL](https://www.sqlite.org/wal.html)
