---
title: "SQLite WAL Concurrency and Locking"
date: 2026-05-21
description: "SQLite WAL mode 如何降低 reader / writer 衝突、保留 single writer boundary，並用 SQLITE_BUSY、WAL growth、checkpoint 訊號判斷 production 上限"
tags: ["backend", "database", "sqlite", "wal", "locking", "deep-article"]
---

> 本文是 [SQLite](/backend/01-database/vendors/sqlite/) overview 的 implementation-layer deep article。Overview 已說明 SQLite 的 single-file / embedded 定位；本文聚焦 *WAL concurrency、single writer boundary、`SQLITE_BUSY` 與 checkpoint strategy*。

SQLite WAL concurrency 的核心責任是讓 reader / writer 衝突下降，同時保留單檔案資料庫的寫入邊界。WAL mode 把寫入 append 到 `-wal` sidecar file，reader 可以從 main database file 加 WAL snapshot 讀取一致視圖；這讓 read-heavy workload 能比 rollback journal mode 更順。但 SQLite 仍只有一條 writer path，長交易、背景 migration、慢 disk 或多 process 寫入都會在這條 path 上排隊。

本文的判讀錨點是：WAL 提升的是 reader concurrency，治理的是 writer queue。當服務看到 `SQLITE_BUSY`、WAL file 持續變大、checkpoint duration 變長或偶發 commit latency spike，問題通常在 transaction duration、checkpoint cadence、filesystem lock 或 process ownership，而非單純「資料庫太小」。

## WAL mode 的服務責任

WAL mode 的服務責任是把「寫入直接改 main database file」改成「寫入先 append 到 WAL，再由 checkpoint 合併回 main database」。SQLite 官方文件把 WAL 模型拆成 reading、writing、checkpointing 三個 primitive；這個 framing 對 production runbook 很重要，因為 checkpoint 會變成獨立的操作訊號。

| 模式             | 寫入路徑                                 | Reader 影響                        | Production 判讀                            |
| ---------------- | ---------------------------------------- | ---------------------------------- | ------------------------------------------ |
| Rollback journal | 寫入前保存原始 page，再修改 main file    | write 期間更容易和 reader 互相等待 | 適合簡單、低並發、短交易路徑               |
| WAL              | 寫入 append 到 `-wal`，checkpoint 後合併 | reader 可看自己的 WAL snapshot     | 適合 read-heavy、互動式、短寫交易 workload |

這張表的讀法是先看服務是否主要受 read / write 衝突影響。Read-heavy CLI、desktop、mobile、edge-local API 或 small backend 往往能從 WAL mode 受益；write-heavy queue consumer、batch import、multi-process writer 或 high-concurrency OLTP 則會先撞到 single writer boundary。

## Locking model：多 reader 與單 writer 是同時成立的

SQLite locking model 的核心責任是保護單一 database file 的 ACID 邊界。Rollback journal mode 的官方 locking 文件描述了 SHARED、RESERVED、PENDING、EXCLUSIVE 等狀態；WAL mode 的細節另由 WAL 文件說明，但服務判讀上仍要記住同一件事：跨 connection / process 的寫入要被序列化。

| 角色       | WAL mode 下的責任                        | 常見失效訊號                                           |
| ---------- | ---------------------------------------- | ------------------------------------------------------ |
| Reader     | 讀取開始時固定自己的 snapshot end mark   | 長讀取讓 checkpoint 停在舊 snapshot，WAL file 持續變大 |
| Writer     | append 新 transaction 到同一個 WAL file  | 其他 writer 看到 `SQLITE_BUSY` 或 write latency spike  |
| Checkpoint | 把 WAL frame 合併回 main database file   | checkpoint duration 拉長、commit 偶發變慢              |
| Filesystem | 提供可靠 file lock 與 shared-memory 支援 | network filesystem、container mount 或權限造成異常     |

多 reader 與單 writer 的組合是 SQLite 的正常設計。讀者在查問題時，要避免把 `SQLITE_BUSY` 直接解讀成資料毀損；它多半代表某個 connection 正在持有 writer 所需的 lock，或 checkpoint / transaction 正在等待可前進的窗口。

## `SQLITE_BUSY` 的第一輪排查

`SQLITE_BUSY` 的核心意義是某個 connection 當下拿不到需要的 lock。SQLite 提供 `busy_timeout` 讓 connection 等待一段時間；這能吸收短暫 writer queue，但它只是等待策略，single writer boundary 仍然存在。

| 觀察訊號                | 可能原因                             | 第一輪處理                                                      |
| ----------------------- | ------------------------------------ | --------------------------------------------------------------- |
| 短暫 `SQLITE_BUSY`      | 多個短寫入撞在一起                   | 設定 bounded busy timeout，縮短 transaction duration            |
| 持續 `SQLITE_BUSY`      | 長交易、migration、batch import      | 找出持鎖 connection，拆小 transaction 或移到 maintenance window |
| commit latency 偶發變慢 | auto-checkpoint 在 commit path 上    | 調整 auto-checkpoint，改由 background checkpoint                |
| read query 讓 WAL 變大  | long reader 卡住 checkpoint          | 限制長查詢、拆 reporting query、設定 reader timeout             |
| 部署後 busy rate 上升   | instance 數增加、multi-process write | 重新檢查 writer ownership，必要時升級 server SQL                |

這張表的重點是先找「誰持有 writer path」。如果問題來自單一長 transaction，修 transaction boundary；如果問題來自多個 process 同時寫同檔，修 process ownership；如果問題來自真實高寫入吞吐，SQLite 已經接近服務邊界。

## Busy timeout 是緩衝器，容量邊界仍在 writer path

Busy timeout 的服務責任是吸收短時間 lock collision。它適合 desktop app autosave、mobile local store、短 API write、測試 fixture 或偶發 background job；它不適合作為高寫入吞吐的主要容量策略。

```sql
PRAGMA busy_timeout = 5000;
```

這個設定代表 connection 最多等待 5000 ms。Production runbook 要同時記錄三個訊號：busy 次數、等待時間分布、等待後成功率。若等待後成功率高且 p99 可接受，代表 writer queue 仍在服務邊界內；若等待常超時，代表 transaction duration 或 writer 並發已經超出單檔模型。

## Checkpoint strategy：WAL growth 是操作訊號

Checkpoint 的核心責任是把 WAL 中的 committed frames 合併回 main database file。SQLite 預設會在 WAL file 達到約 1000 pages 後自動 checkpoint；這個預設適合多數小型場景，但 production 服務要把 checkpoint 視為獨立操作。

```sql
PRAGMA wal_checkpoint(PASSIVE);
PRAGMA wal_checkpoint(FULL);
PRAGMA wal_checkpoint(RESTART);
PRAGMA wal_checkpoint(TRUNCATE);
```

| Checkpoint 型態 | 操作語意                               | 適合場景                                |
| --------------- | -------------------------------------- | --------------------------------------- |
| PASSIVE         | 盡量前進，避免主動阻塞 reader / writer | 日常觀測、低風險背景 checkpoint         |
| FULL            | 等待 writer，嘗試完成更多 checkpoint   | maintenance window、WAL growth 需要收斂 |
| RESTART         | 完成後讓後續 writer 可重新使用 WAL     | 想降低 WAL 持續膨脹，能接受等待         |
| TRUNCATE        | 完成後截斷 WAL file                    | 低流量窗口、需要回收檔案空間            |

Checkpoint 策略的判讀要看 workload cadence。互動式服務通常保留 auto-checkpoint，再加上低流量時段的 background checkpoint；長查詢或 reporting workload 需要避免讓 long reader 長期佔住 snapshot；batch import 則要把 transaction 切小，避免 WAL file 在單一交易期間快速膨脹。

## Checkpoint starvation：長 reader 會讓 WAL 持續長大

Checkpoint starvation 的核心概念是：只要總有 reader 還在使用舊 snapshot，checkpoint 就可能停在 reset 之前。SQLite 官方 WAL 文件明確指出，checkpoint 可以和 reader 並行，但遇到仍被 reader 使用的 WAL 位置時要停下來；如果長時間沒有 reader gap，WAL file 會持續成長。

| 情境                         | 真實服務長相                            | 修正方向                                       |
| ---------------------------- | --------------------------------------- | ---------------------------------------------- |
| Desktop app 開著長報表       | 使用者查詢大列表，背景寫入持續發生      | 報表分頁、限制 read transaction duration       |
| API handler 把 cursor 留太久 | streaming response 邊讀邊回，交易未結束 | 先 materialize 結果、縮短 DB read transaction  |
| Background sync 長讀取       | sync worker 掃全表，UI 仍在寫資料       | 分批讀取、讀寫排程、低流量 checkpoint          |
| Test suite 平行讀寫 fixture  | 測試共用同一 `.db`，多 worker 交錯      | per-test DB、read-only fixture、獨立 temp file |

這些情境的共同點是 reader lifecycle 沒有被 application 控制。SQLite 的 concurrency 問題常發生在 application boundary，而非 database engine 本身；修法也應回到 handler、worker、test runner 或 UI lifecycle。

## Filesystem 與 deployment boundary

SQLite WAL 的 deployment boundary 是 local filesystem 與可靠 shared-memory / file-locking primitive。官方 WAL 文件指出 wal-index 使用 shared memory，所有 reader 要位於同一台機器；這也是 WAL mode 不適合放在一般 network filesystem 上的主要原因。

| 部署方式                     | 判讀                                       | 建議路由                                            |
| ---------------------------- | ------------------------------------------ | --------------------------------------------------- |
| 單 process / 單機 local disk | SQLite 最自然的部署形狀                    | WAL + backup / restore runbook                      |
| 多 process / 同機 local disk | 可行，但要清楚 writer ownership 與 timeout | WAL + busy timeout + checkpoint evidence            |
| 多 instance / shared volume  | lock 與 writer ownership 風險上升          | 升級 PostgreSQL / MySQL，或改用明確 primary pattern |
| network filesystem           | WAL shared-memory 與 file lock 語意風險高  | 改 local disk + replication，或 server database     |
| container ephemeral disk     | durability 與 restore 路徑要重新設計       | persistent volume、backup drill、restore evidence   |

Deployment review 要問的第一個問題是「同一時間誰會寫這個檔案」。如果答案是多個 instance、跨機器 process 或不受控 job，SQLite 的服務邊界已經需要重新評估。

## Production 踩雷

### Case 1：多個 worker 同時寫同一個 SQLite 檔

多 worker 寫入同一個 SQLite 檔的核心風險是 writer ownership 消失。常見情境是小型服務從單 instance 擴到多 instance，但仍把 database file 放在 shared volume；早期看起來可運作，流量上升後開始出現 busy timeout、WAL growth 與偶發資料修復壓力。

修正方向是重新定義 writer。若服務仍是 small backend，可以收斂到單 writer process + queue；若 multi-instance 是長期需求，應遷移到 [PostgreSQL](/backend/01-database/vendors/postgresql/) 或 [MySQL](/backend/01-database/vendors/mysql/)。

### Case 2：長讀取卡住 checkpoint，磁碟被 WAL 吃滿

長讀取卡 checkpoint 的核心風險是 WAL file 成為隱性容量消耗。讀者可能只看到 disk usage 增長，誤以為是資料量變大；實際上 main database file 沒有明顯增長，`-wal` sidecar 持續膨脹。

修正方向是先找到長 reader，再調整 query lifecycle。Reporting query、background sync、streaming response、互動式 UI 大列表都要有 pagination、timeout 或低流量窗口；checkpoint 只負責收斂 WAL，application 仍要主動結束長讀取。

### Case 3：把 busy timeout 當成擴容策略

Busy timeout 被當成擴容策略的核心風險是延遲被隱藏到使用者路徑。短暫 lock collision 可以等待；長期 write queue 則會把 API p99、UI freeze 或 worker backlog 拉高。

修正方向是把 busy wait 當 metric。設定 timeout 後要記錄等待時間與超時率；當 busy wait 成為常態，下一步是拆交易、調整 writer process、移走 batch job，或升級到 server database。

### Case 4：checkpoint 放在高流量 commit path

Checkpoint 放在高流量 commit path 的核心風險是少數 commit 變得很慢。SQLite 預設 auto-checkpoint 對多數場景合理，但互動式服務可能看到偶發 latency spike；這時可以把 checkpoint 移到背景 thread / process 或低流量窗口。

修正方向是把 checkpoint duration 變成 evidence。觀察 WAL size、checkpoint return、commit latency 與 disk sync；若尖峰可接受，維持預設；若尖峰影響 UX，調整 checkpoint cadence。

### Case 5：WAL mode 版本與部署條件未納入維護

WAL mode 的維護責任包含 SQLite runtime version、filesystem、sidecar file 與 release notes。SQLite 官方 WAL 文件記錄 2026-03 修正過罕見 WAL-reset bug；雖然觸發條件很窄，production runbook 仍應記錄 SQLite version、runtime package 與更新策略。

修正方向是把 SQLite runtime 當成 dependency。Mobile、desktop、embedded、language binding、OS bundled SQLite 可能各自帶不同版本；需要在 support matrix 中標明版本來源、WAL mode 行為與升級路徑。

## 操作檢查清單

SQLite WAL / locking runbook 至少要能回答下列問題：

1. Database file、`-wal`、`-shm` 是否位於 local durable filesystem。
2. 同一時間哪些 process / thread 會寫入 database file。
3. `PRAGMA journal_mode`、`busy_timeout`、`wal_autocheckpoint` 如何設定。
4. `SQLITE_BUSY` 次數、等待時間、超時率是否被記錄。
5. WAL file size、checkpoint duration、disk usage 是否被觀測。
6. 長 read transaction 的來源與 timeout 如何治理。
7. Batch import、migration、background sync 是否避開互動式高峰。
8. SQLite runtime version 與 WAL 相關 release notes 如何追蹤。

這份清單要接到 [Observability / runbook](/backend/01-database/vendors/sqlite/observability-runbook/) 與 [SQLite Hands-on](/backend/01-database/vendors/sqlite/hands-on/)；正文教判讀，hands-on 負責讓讀者重現 `SQLITE_BUSY`、WAL growth 與 checkpoint 行為。

## 何時維持 SQLite，何時升級

SQLite WAL mode 適合單機、短交易、read-heavy、writer ownership 清楚的服務。只要 busy wait 可控、checkpoint 能完成、backup / restore drill 成立，SQLite 可以承擔正式狀態。

升級訊號來自 writer boundary 外溢。多 instance write、多 region write、high-write OLTP、集中權限治理、read replica、PITR、DB account / role 與 audit requirement 都會把服務推向 server SQL、edge SQLite product 或 distributed SQL。

| 壓力                         | SQLite 內修正                  | 升級路由                                                                            |
| ---------------------------- | ------------------------------ | ----------------------------------------------------------------------------------- |
| 偶發 `SQLITE_BUSY`           | busy timeout、縮短 transaction | 維持 SQLite                                                                         |
| WAL growth                   | 找長 reader、manual checkpoint | 維持 SQLite，補 observability                                                       |
| 多 worker 寫入               | 收斂單 writer、queue 化        | PostgreSQL / MySQL                                                                  |
| Edge locality                | D1 / Turso compatibility audit | [D1 / Turso route](/backend/01-database/vendors/sqlite/d1-turso-libsql-comparison/) |
| HA / PITR / audit governance | file backup 已經難以治理       | [SQLite to PostgreSQL](/backend/01-database/vendors/sqlite/migrate-to-postgresql/)  |

## 下一步路由

- 上游：[SQLite overview](/backend/01-database/vendors/sqlite/)
- 前置：[File lifecycle / backup boundary](/backend/01-database/vendors/sqlite/file-lifecycle-backup-boundary/)
- 操作：[SQLite Hands-on](/backend/01-database/vendors/sqlite/hands-on/) 與 [WAL busy reproduction](/backend/01-database/vendors/sqlite/hands-on/wal-busy-reproduction/)
- 平行：[PRAGMA tuning / performance](/backend/01-database/vendors/sqlite/pragma-tuning-performance/)、[Observability / runbook](/backend/01-database/vendors/sqlite/observability-runbook/)
- 遷移：[SQLite to PostgreSQL](/backend/01-database/vendors/sqlite/migrate-to-postgresql/)
- 官方：[SQLite Write-Ahead Logging](https://www.sqlite.org/wal.html)、[SQLite File Locking](https://www.sqlite.org/lockingv3.html)、[SQLite Isolation](https://www.sqlite.org/isolation.html)、[SQLite PRAGMA](https://www.sqlite.org/pragma.html)
