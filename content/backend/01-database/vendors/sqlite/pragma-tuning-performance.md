---
title: "SQLite PRAGMA Tuning and Performance"
date: 2026-05-21
description: "SQLite journal_mode、synchronous、busy_timeout、wal_autocheckpoint、cache_size、mmap_size、auto_vacuum 與 performance evidence 的操作判斷標準，以及各 PRAGMA 的作用範圍（資料庫檔或單一連線）與連線池新開連線的初始化"
tags: ["backend", "database", "sqlite", "performance", "pragma", "deep-article"]
---

SQLite PRAGMA tuning 的核心責任是把單檔資料庫的行為固定成可重複、可觀測、可回退的操作契約。SQLite 的許多重要行為由 connection-level 或 database-level PRAGMA 控制；這些設定看起來像小開關，實際上會影響 crash recovery、commit latency、reader / writer 衝突、檔案大小與測試一致性。

本文的範圍是 `journal_mode`、`synchronous`、`busy_timeout`、`wal_autocheckpoint`、`cache_size`、`mmap_size` 與 `auto_vacuum` 這幾個 PRAGMA 各自在 durability、latency 與 maintenance 之間的取捨，各自的作用範圍（寫進資料庫檔或只對單一連線生效）與連線池新開連線時的初始化，以及 production runbook 要為每一個記錄的設定值、設定時機、驗證 query 與回退條件——這份記錄讓不同 process、test runner 與 migration tool 用同一組 SQLite 行為。

## Baseline PRAGMA

SQLite baseline PRAGMA 的責任是讓 application 每次啟動都進入同一個資料庫模式。對 production-like local store、small backend 或 test fixture，建議把 journal、sync、foreign key、busy timeout 與 checkpoint 明確設定，而非依賴語言 binding 預設值。

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
PRAGMA wal_autocheckpoint = 1000;
```

| 設定                 | 服務責任                            | 作用範圍                               | 驗證方式                                  |
| -------------------- | ----------------------------------- | -------------------------------------- | ----------------------------------------- |
| `journal_mode=WAL`   | 降低 reader / writer 衝突           | 資料庫檔：寫進檔案，之後的連線都是 WAL | 回傳值為 `wal`，觀察 `-wal` file          |
| `synchronous=NORMAL` | 平衡 fsync cost 與 crash durability | 執行它的那一條連線                     | 查 `PRAGMA synchronous`，跑 restore drill |
| `foreign_keys=ON`    | 啟用 FK enforcement                 | 執行它的那一條連線                     | `PRAGMA foreign_key_check`                |
| `busy_timeout`       | 吸收短暫 writer queue               | 執行它的那一條連線                     | 記錄 busy wait 與 timeout rate            |
| `wal_autocheckpoint` | 控制 WAL growth cadence             | 執行它的那一條連線                     | 觀察 WAL size 與 checkpoint duration      |

這張表的重點是把設定與 evidence 綁在一起。若某個 PRAGMA 缺少成功訊號與失敗訊號，就先維持保守預設；盲目追求「最快」通常會把風險推到 power loss、restore 或長尾 latency。

PRAGMA 的作用範圍分成資料庫檔與單一連線。`journal_mode=WAL` 寫進資料庫檔，任何一條連線設過一次，之後打開這個檔的連線都在 WAL mode；表裡其餘的 PRAGMA 只對執行它的那一條連線生效，新開的連線拿到預設值。預設值有兩個來源：SQLite 本身的預設值，以及 driver 開連線時自己執行的設定。以 busy timeout 為例，SQLite 本身是 0；Python 的 `sqlite3` 模組由 `connect()` 的 `timeout` 參數設定（單位是秒，預設 5.0，所以開出來的連線是 5000 ms），Go 的 mattn/go-sqlite3 開連線時也設成 5000 ms；modernc.org/sqlite 在連線字串（DSN）沒有指定時不設。mattn 與 modernc 的值是在 mattn/go-sqlite3 v1.14.53、modernc.org/sqlite v1.62.0（Go 1.27.3）上查到的，Python 的值在 Python 3.14 上查到。driver 的預設值會隨版本改變，手上這個 driver 實際設了什麼，在新開的連線上查一次 `PRAGMA busy_timeout` 就知道，下面的實測用的就是這個查法。

SQLite 3.53.0 實測，經由 Python 3.14 的 `sqlite3` 模組、以 `timeout=0` 開連線（讓 driver 不設 busy timeout）。一條連線執行 `PRAGMA busy_timeout = 5000`、`foreign_keys = ON`、`synchronous = NORMAL`、`wal_autocheckpoint = 500`（取 500 是為了跟預設值 1000 分得開）之後，對同一個檔新開另一條連線，逐一查詢：

```sql
-- 在新開的那條連線上查詢；註解是回傳值，括號裡是設定過的那條連線的回傳值
PRAGMA journal_mode;        -- wal（wal）
PRAGMA busy_timeout;        -- 0（5000）
PRAGMA foreign_keys;        -- 0，外鍵檢查關閉（1）
PRAGMA synchronous;         -- 2，FULL（1，NORMAL）
PRAGMA wal_autocheckpoint;  -- 1000（500）
```

`synchronous` 新連線的預設值由 SQLite 編譯時的選項決定，`2` 是這次那個 SQLite build 的值，系統內建或發行版套件的 SQLite 可能查到別的值；busy timeout 的 0 不受編譯選項影響。所以連線範圍的 PRAGMA 要寫在每一條連線建立時都會走過的程式路徑上。

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

### PRAGMA 只在某個 connection 設定，不同程式路徑跑出不同行為

Connection-level PRAGMA 的核心風險是不同程式路徑行為不一致。Application 啟動時設了 `foreign_keys=ON`，migration tool 或 test runner 沒設，同一個資料庫在 production、migration 與 test 三條路徑上就有不同的 foreign key 行為：application 的 connection 會拒絕違反 FK 的寫入，另外兩條路徑照收。

修正方向是把 baseline PRAGMA 放進 shared DB open path，並在 startup health check 印出設定值。Migration CLI、background worker、test fixture 都要共用同一份 connection initialization。程式透過連線池開連線時，這份初始化要放在連線池建立每一條連線都會走的位置，只在開檔之後執行一次不夠，〈連線池新開的連線沒有執行 baseline PRAGMA〉寫的就是這個情形。

### 連線池新開的連線沒有執行 baseline PRAGMA，外鍵檢查與 busy timeout 只在部分連線生效

連線池漏掉 PRAGMA 初始化的核心風險是同一段程式的結果取決於請求拿到哪一條連線，同一條程式路徑有時正常、有時出錯。〈PRAGMA 只在某個 connection 設定〉寫的是不同程式路徑各用各的初始化；這裡是同一條路徑上，連線池裡的連線各自帶著不同的 PRAGMA。SQLite 是嵌在應用程式 process 裡的函式庫，連線池（[connection pool](/backend/knowledge-cards/connection-pool/)）由應用程式那一端的程式庫維護，例如 Go 的 `database/sql`，它依負載開新連線、關掉閒置的連線。

應用程式只在啟動時對拿到的第一條連線執行 `PRAGMA foreign_keys = ON` 的話，連線池之後新開的連線外鍵檢查是關閉的，違反外鍵的寫入在那些連線上照常提交，不回傳 `FOREIGN KEY constraint failed`。`busy_timeout` 也一樣，新開的連線拿到的是 driver 的預設值；driver 不設時是 SQLite 本身的 0，那條連線碰到寫入鎖被佔住就立刻回傳 `SQLITE_BUSY`。

修正方向是讓 PRAGMA 跟著連線建立執行。driver 支援時寫進連線字串（DSN）的參數，例如 mattn/go-sqlite3 的 `file:app.db?_foreign_keys=1&_busy_timeout=5000`，modernc.org/sqlite 的 `file:app.db?_pragma=foreign_keys(1)&_pragma=busy_timeout(5000)`；`app.db` 換成實際的檔案路徑。driver 不支援時，用連線建立時會呼叫的初始化函式：Go 的 `database/sql` 本身沒有這個 hook，要在 driver 那一層掛（mattn/go-sqlite3 註冊自訂 driver 時的 `ConnectHook`）；SQLAlchemy 用 `connect` 事件。驗證時，連線池會把剛歸還的閒置連線再交出來，一次取一條、查完歸還，量到的一直是同一條；要看到每一條，就同時從連線池取出多條、全部持有不歸還，再逐條查 `PRAGMA busy_timeout` 與 `PRAGMA foreign_keys`。Go 1.27.3 搭 mattn/go-sqlite3 v1.14.53 與 modernc.org/sqlite v1.62.0 實測：同時持有三條連線逐條查，帶上面 mattn 與 modernc 的 DSN 參數時三條都回傳設定值；DSN 不帶參數、只在啟動時執行一次 `PRAGMA foreign_keys = ON` 時，只有第一條是 1，另外兩條是 0。`ConnectHook` 與 SQLAlchemy 的 `connect` 事件依各自的文件，這次沒有實跑。

### `synchronous=OFF` 從測試環境流到正式資料，損失只在 OS crash 或斷電後出現

快速測試設定外流的核心風險是資料損失只在 OS crash 或斷電後出現。`synchronous=OFF` 讓 SQLite 把資料交給作業系統之後不等它寫進磁碟，所以平常 query 都正常，application process 自己 crash 也不會掉資料；直到 power loss 或 host crash，還留在 OS 快取、沒寫進磁碟的交易會遺失，資料庫檔案也可能損毀。

修正方向是設定分層。Test / benchmark 可以用 faster profile；formal state profile 要用 `NORMAL` 或 `FULL`，並要求 restore drill。

### WAL growth 被誤判成資料成長，擴 disk 蓋住了 checkpoint 問題

WAL growth 的核心風險是 checkpoint 問題被當成容量問題。Disk alert 看到 `db-wal` 變大，若只擴 disk，長 reader 或 checkpoint starvation 仍會持續。

修正方向是把 WAL size、checkpoint return 與 long reader 一起看。先找 reader lifecycle，再調 checkpoint cadence。

### Vacuum 在高峰期執行，把 maintenance I/O 放到使用者路徑

Vacuum 的核心風險是把 maintenance I/O 放到使用者路徑。檔案縮小是好事，但 full vacuum 會消耗 I/O 與時間，對 mobile / desktop / small backend 都可能造成卡頓。

修正方向是把 vacuum 當 maintenance job。大檔案用 `incremental_vacuum` 或低流量窗口；備份前的 compact copy 可考慮 `VACUUM INTO`。

## 操作檢查清單

SQLite PRAGMA runbook 至少要記錄：

1. 所有 connection 初始化時執行的 baseline PRAGMA，以及連線池新開連線時執行它的位置（DSN 參數或初始化 hook）。
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
