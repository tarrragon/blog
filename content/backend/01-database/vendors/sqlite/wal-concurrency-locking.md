---
title: "SQLite WAL Concurrency and Locking"
date: 2026-05-21
description: "SQLite WAL mode 如何降低 reader / writer 衝突、保留 single writer boundary，先讀後寫的交易為什麼設了 busy timeout 仍在 0 ms 回傳 database is locked（SQLITE_BUSY、SQLITE_BUSY_SNAPSHOT），並用 SQLITE_BUSY、WAL growth、checkpoint 訊號判斷 production 上限"
tags: ["backend", "database", "sqlite", "wal", "locking", "deep-article"]
---

SQLite WAL concurrency 的核心責任是讓 reader / writer 衝突下降，同時保留單檔案資料庫的寫入邊界。[WAL mode](/backend/knowledge-cards/write-ahead-log/) 把寫入 append 到 `-wal` sidecar file，reader 可以從 main database file 加 WAL snapshot 讀取一致視圖；這讓 read-heavy workload 能比 rollback journal mode 更順。但 SQLite 仍遵循 [single writer model](/backend/knowledge-cards/single-writer-model/)、只有一條 writer path，長交易、背景 migration、慢 disk 或多 process 寫入都會在這條 path 上排隊。

本文的範圍是 WAL mode 下的 locking model、`SQLITE_BUSY` 與 busy timeout、在應用程式端排隊寫入的單一寫入連線池、busy timeout 不會等待的先讀後寫交易、checkpoint strategy 與 checkpoint starvation，以及 filesystem 與部署方式對 WAL 的限制。服務看到 `SQLITE_BUSY`、WAL file 持續變大、checkpoint duration 變長或偶發 commit latency spike 時，各節依序對到的成因是 transaction duration、先讀後寫的交易用 `BEGIN`（DEFERRED）開始、checkpoint cadence、filesystem lock 與 process ownership。

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

`SQLITE_BUSY` 的核心意義是某個 connection 當下拿不到需要的 lock。SQLite 提供 `busy_timeout` 讓 connection 等待一段時間；這能吸收短暫 writer queue，但它只是等待策略，single writer boundary 仍然存在。交易已經讀過資料時，申請寫入鎖拿不到就立刻回傳 `SQLITE_BUSY`，不經過 busy timeout 的等待（下方〈先讀後寫的交易〉）。

| 觀察訊號                                                                                                           | 可能原因                                                                                                                                            | 第一輪處理                                                                                                                                                              |
| ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PRAGMA journal_mode` 回傳 `delete`，`SQLITE_BUSY` 在 busy timeout 到期後才出現，找不到長時間的寫入交易            | 資料庫還在 rollback journal mode，開著的讀取會擋住寫入的提交                                                                                        | 改成 WAL mode（[SQLite PRAGMA Tuning and Performance](/backend/01-database/vendors/sqlite/pragma-tuning-performance/) 的 `journal_mode`），之後再照下面各列判讀         |
| 短暫 `SQLITE_BUSY`                                                                                                 | 多個短寫入撞在一起                                                                                                                                  | 設定 bounded busy timeout，縮短 transaction duration                                                                                                                    |
| 同一個 process 的多條連線互相搶寫入鎖，busy wait 常態出現                                                          | 同一個 process 裡的寫入各自開連線競爭                                                                                                               | 寫入連線池上限一條（下方〈寫入連線池上限一條〉）                                                                                                                        |
| 等待時間接近 0 的 `SQLITE_BUSY`，失敗那條連線的 `PRAGMA busy_timeout` 回傳 0（可能只有部分連線，也可能每一條都是） | 連線池新開的連線沒有執行 `PRAGMA busy_timeout`，或 driver 開連線時本身不設（例如 modernc.org/sqlite 沒有在 DSN 指定時），拿到 SQLite 本身的預設值 0 | 每條連線建立時都執行 baseline PRAGMA（[SQLite PRAGMA Tuning and Performance](/backend/01-database/vendors/sqlite/pragma-tuning-performance/) 的作用範圍與連線池初始化） |
| 等待時間接近 0 的 `SQLITE_BUSY`，失敗那條連線的 `PRAGMA busy_timeout` 回傳設定值，失敗的都是先讀後寫的交易         | 另一條連線正持有寫入鎖，或在這個交易讀取之後提交了寫入                                                                                              | 會寫入的交易改用 `BEGIN IMMEDIATE`，或回滾後退避重跑（下方〈先讀後寫的交易〉）                                                                                          |
| 持續 `SQLITE_BUSY`                                                                                                 | 長交易、migration、batch import                                                                                                                     | 找出持鎖 connection，拆小 transaction 或移到 maintenance window                                                                                                         |
| commit latency 偶發變慢                                                                                            | auto-checkpoint 在 commit path 上                                                                                                                   | 調整 auto-checkpoint，改由 background checkpoint                                                                                                                        |
| read query 讓 WAL 變大                                                                                             | long reader 卡住 checkpoint                                                                                                                         | 限制長查詢、拆 reporting query、設定 reader timeout                                                                                                                     |
| 部署後 busy rate 上升                                                                                              | instance 數增加、multi-process write                                                                                                                | 重新檢查 writer ownership，必要時升級 server SQL                                                                                                                        |

`journal_mode` 回傳 `delete` 那一列是其餘各列的前提：rollback journal mode 下，開著的讀取也會擋住寫入，這時找不到長時間的寫入交易（SQLite 3.53.0 實測：另一條連線逐列慢慢讀取的期間，寫入在 busy timeout 5000 ms 到期、約 5.2 秒後回傳 `SQLITE_BUSY`；改成 WAL mode 之後同樣的操作立刻寫入成功）。WAL mode 下，這張表的重點是先找「誰持有 writer path」。如果問題來自單一長 transaction，修 transaction boundary；如果問題來自多個 process 同時寫同檔，修 process ownership；如果問題來自真實高寫入吞吐，SQLite 已經接近服務邊界。等待時間接近 0 的 `SQLITE_BUSY` 換掉持有寫入鎖的是哪一條連線也不會消失，成因在失敗那條連線的 PRAGMA 設定，或失敗那個交易的開始方式。兩者的判讀有依賴：那條連線的 `busy_timeout` 是 0 時，改用 `BEGIN IMMEDIATE` 一樣在 0 ms 失敗，所以連線的初始化排在交易寫法之前判讀。

## Busy timeout 是緩衝器，容量邊界仍在 writer path

Busy timeout 的服務責任是吸收短時間 lock collision。它適合 desktop app autosave、mobile local store、短 API write、測試 fixture 或偶發 background job；它不適合作為高寫入吞吐的主要容量策略。

```sql
PRAGMA busy_timeout = 5000;
```

這個設定代表 connection 最多等待 5000 ms。Production runbook 要同時記錄三個訊號：busy 次數、等待時間分布、等待後成功率。若等待後成功率高且 p99 可接受，代表 writer queue 仍在服務邊界內；若等待常超時，代表 transaction duration 或 writer 並發已經超出單檔模型。

### 寫入連線池上限一條：同一個 process 的寫入在應用程式這一端排隊

同一個 process 裡的寫入競爭，可以改在應用程式這一端排隊。寫入用一個上限一條連線的連線池（[connection pool](/backend/knowledge-cards/connection-pool/)），讀取用另一個可以開多條連線的連線池。讀取池的連線開成唯讀，程式誤用讀取池寫入時直接回傳錯誤：以 URI 檔名開檔並帶 `mode=ro`（`file:app.db?mode=ro`，driver 要開啟 URI 檔名，例如 Python 的 `sqlite3.connect(..., uri=True)`），或每條讀取連線建立時執行 `PRAGMA query_only = ON`（它是連線範圍的設定，執行位置見 [SQLite PRAGMA Tuning and Performance](/backend/01-database/vendors/sqlite/pragma-tuning-performance/) 的連線池初始化）。

寫入要依據的讀取，跟寫入一起放在寫入連線的同一個交易裡。打卡前查「今天打過卡沒有」的查詢走讀取池的話，查詢與寫入分在兩條連線，中間沒有隔離，兩個請求交錯時都查到還沒打卡，資料表留下兩列。讀取池只放不影響寫入決定的查詢。

這個 process 的寫入（包括啟動時的 migration 與背景工作）全部經過寫入池時，寫入請求在連線池等待那一條寫入連線空出來，不在 SQLite 的寫入鎖上互搶。等待的上限由連線池取得連線的逾時（acquire timeout）控制，等待時間可以當成連線池的 metric 記錄。這個 process 自己的寫入之間不再出現 `SQLITE_BUSY`，寫入連線上的先讀後寫交易也不會因為同一個 process 的其他寫入先提交而失敗（失敗的機制在下方〈先讀後寫的交易〉）。

代價是這個 process 的所有寫入共用一條連線。一筆長交易（批次匯入、migration）佔住那條連線時，互動式的寫入都排在它後面，等到 acquire timeout 到期，回傳的是連線池的逾時錯誤，不是 `SQLITE_BUSY`。程式碼在交易進行中又向同一個寫入池要一條連線時（Go 裡持有 `tx` 時呼叫了用 `db` 的函式），池子上限是一條，這個要求等不到連線，直到 context 逾時。

另一個 process 在同一台機器、同一個 local disk 上也寫同一個檔時（migration CLI、背景 job），寫入鎖的競爭回到 SQLite 這一層，兩邊的連線都要設 busy timeout，會寫入的交易用 `BEGIN IMMEDIATE` 開始。process 分在不同機器、或檔案放在 network filesystem 上時，照下方〈Filesystem 與 deployment boundary〉判讀。這一節的做法是從 single writer model 推出來的設計，這次沒有實跑量測。

## 先讀後寫的交易：busy timeout 不會等待的 `SQLITE_BUSY`

先讀後寫的交易是用 `BEGIN` 開始、先讀取、之後才寫入的交易，例如打卡前先查這個人今天打過卡沒有。`BEGIN` 在 SQLite 的預設模式是 DEFERRED（[SQLite 的 BEGIN TRANSACTION 文件](https://www.sqlite.org/lang_transaction.html)）：`BEGIN` 本身不取得任何鎖，第一個讀取的陳述式讓交易在 WAL 上固定一個讀取 snapshot，第一個寫入的陳述式才去申請寫入鎖（write lock）。寫入鎖同一時間只有一條連線持有，所有寫入都在它前面排隊（[single writer model](/backend/knowledge-cards/single-writer-model/)）。申請寫入鎖時，SQLite 還要求這個交易的 snapshot 是資料庫目前最新的版本：這次寫入要建立在交易已經讀到的內容上，讀取之後若有別的連線提交過寫入，交易讀到的內容就已經過時。

```sql
-- 先讀後寫：申請寫入鎖時才碰到衝突
BEGIN;
SELECT count(*) FROM attendance WHERE user_id = 42 AND day = '2026-11-12';
INSERT INTO attendance (user_id, day, punched_at) VALUES (42, '2026-11-12', '09:01');
COMMIT;

-- 開始時就申請寫入鎖：拿不到時照 busy_timeout 等待
BEGIN IMMEDIATE;
SELECT count(*) FROM attendance WHERE user_id = 42 AND day = '2026-11-12';
INSERT INTO attendance (user_id, day, punched_at) VALUES (42, '2026-11-12', '09:01');
COMMIT;
```

`attendance` 表、`42` 與日期是示範值，兩段的差別只在 `BEGIN` 那一行。application 依 `SELECT` 回傳的 `count(*)` 是 0 才送出 `INSERT`，示範省略了這個判斷。

先讀後寫要解決的規則寫得成資料表的約束時，讀取可以整個拿掉。「同一個人同一天只打一次卡」寫成 `UNIQUE(user_id, day)`，寫入改成一句 `INSERT … ON CONFLICT(user_id, day) DO NOTHING`（SQLite 3.24 起支援這個寫法）：交易的第一句就是寫入，照下表「第一句就是 `INSERT`」那一列，busy timeout 照常等待；重複的那一筆由資料庫擋下，不論交易模式、driver 的預設值，也不論寫入來自哪一個 process。SQLite 3.53.0 實測，兩條連線各送一次同一個人、同一天的這句 `INSERT`，第一筆寫入一列，第二筆影響 0 列，資料表留下一列；不加 `ON CONFLICT` 時第二筆回傳 `UNIQUE constraint failed`。規則要依好幾列的彙總判斷時（剩餘名額、帳戶餘額），寫不成單一約束，才需要讀取之後再寫，這時交易的開始方式就是下面要處理的事。

先讀後寫的交易申請寫入鎖時，另一條連線在這個交易讀取之後已經提交了寫入的話，snapshot 已經過期，SQLite 回傳 `SQLITE_BUSY_SNAPSHOT`，這是 `SQLITE_BUSY` 的擴充錯誤碼（extended result code，見 [SQLite result codes](https://www.sqlite.org/rescode.html#busy_snapshot)）。另一條連線正持有寫入鎖、還沒結束交易的話，SQLite 回傳 `SQLITE_BUSY`。這兩個錯誤都不經過 busy timeout 的等待。

busy handler 是 SQLite 拿不到鎖時呼叫的回呼函式，它決定要不要等一下再試；`busy_timeout` 是 SQLite 內建的一個 busy handler。申請寫入鎖拿不到時，SQLite 只在交易還沒開始讀取時呼叫 busy handler，已經持有讀取 snapshot 的交易直接拿到錯誤（SQLite 原始碼 `btree.c` 的 `sqlite3BtreeBeginTrans`）。[busy handler 的文件](https://www.sqlite.org/c3ref/busy_handler.html)把這條規則的理由寫成通則：等待可能讓兩條連線互相等下去（死結，deadlock）時，SQLite 不呼叫 busy handler，直接回傳 `SQLITE_BUSY`，讓持有讀取的一方結束交易。文件的說明以 rollback journal 的鎖為背景，那裡的讀取會擋住寫入；WAL mode 下讀取不擋寫入，SQLite 仍然用同一條規則，這一點是依原始碼與下表實測的判讀，文件沒有逐字寫出。在 WAL mode 下，對方提交時，等到它提交之後這個 snapshot 也已經過期，等待換不到寫入；對方回滾、沒有留下任何寫入時，等待原本可以成功，SQLite 同樣不等待。

SQLite 回傳的錯誤訊息都是 `database is locked`（Python 的 `sqlite3` 模組原樣拋出），跟寫入鎖被長時間佔住、busy timeout 到期時的訊息相同。分辨兩者看擴充錯誤碼（Python 3.11 起，例外物件的 `sqlite_errorname` 屬性）與等待時間：不經過等待的那一種，等待時間接近 0。

SQLite 3.53.0 實測，經由 Python 3.14 的 `sqlite3` 模組，同一個 process 裡開兩條獨立的連線，以 `isolation_level=None` 開連線並由程式自己送出 `BEGIN`（Python 預設的交易控制結果不同，見本節最後一段），兩條連線都是 WAL mode、`busy_timeout = 5000`；每一列各跑一次：

| 受測連線的交易                                              | 另一條連線的狀態                                 | 結果                   | 等待時間  |
| ----------------------------------------------------------- | ------------------------------------------------ | ---------------------- | --------- |
| `BEGIN`，先 `SELECT`，再 `INSERT`                           | 在 `SELECT` 之後提交一筆寫入                     | `SQLITE_BUSY_SNAPSHOT` | 0 ms      |
| `BEGIN`，先 `SELECT`，再 `INSERT`                           | 持有寫入鎖，1 秒後提交                           | `SQLITE_BUSY`          | 0 ms      |
| `BEGIN`，先 `SELECT`，再 `INSERT`                           | 持有寫入鎖，1 秒後回滾                           | `SQLITE_BUSY`          | 0 ms      |
| 上一列失敗後 `ROLLBACK`，重新 `BEGIN`、`SELECT`、`INSERT`   | 在第一次 `SELECT` 之後提交一筆寫入，之後沒有再寫 | 重跑時寫入成功         | 0 ms      |
| `BEGIN`，第一句就是 `INSERT`                                | 持有寫入鎖，1 秒後提交                           | 寫入成功               | 約 1.1 秒 |
| `BEGIN IMMEDIATE`，再 `SELECT` 與 `INSERT`                  | 持有寫入鎖，1 秒後提交                           | 寫入成功               | 約 1.1 秒 |
| `BEGIN IMMEDIATE`（之後的 `SELECT` 與 `INSERT` 沒有執行到） | 持有寫入鎖 7 秒                                  | `SQLITE_BUSY`          | 約 5.2 秒 |

`BEGIN` 之後第一句就是 `INSERT` 的交易同樣是 DEFERRED，它申請寫入鎖時還沒有 snapshot，busy timeout 照常等待，約 1.1 秒後寫入成功。所以立刻失敗的成因是寫入之前的讀取，DEFERRED 模式本身照常等待。

`BEGIN IMMEDIATE` 讓交易在開始時就申請寫入鎖：拿不到時照 busy timeout 等待，拿到之後別的寫入交易進不來，snapshot 不會在交易中途過期。代價是寫入鎖從 `BEGIN IMMEDIATE` 開始就被佔住，交易裡讀取花的時間也算進寫入鎖的持有時間，其他寫入在這段時間排隊；所以 IMMEDIATE 交易裡只放這次寫入要依據的讀取，報表查詢放在交易之外。寫入同時依據一次外部 API 呼叫的結果時，呼叫放在交易裡，寫入鎖的持有時間就加上 API 的延遲，同一段時間其他寫入都在排隊；呼叫放在交易之前，就在 IMMEDIATE 交易裡重讀一次寫入要依據的資料，讀到的值跟呼叫之前不同時放棄這次寫入。只讀的交易照用 `BEGIN`，WAL mode 下的讀取不需要寫入鎖。寫入這個檔的只有一條連線時（只開一條連線的 process，或上文〈寫入連線池上限一條〉的寫入池，而且沒有別的 process 寫入），不會有別的寫入讓 snapshot 過期，DEFERRED 的先讀後寫交易碰不到 `SQLITE_BUSY_SNAPSHOT`，也碰不到持鎖造成的立刻失敗。

交易模式改不了時（ORM 沒有提供設定），另一個做法是捕捉立刻回傳的 `SQLITE_BUSY` 與 `SQLITE_BUSY_SNAPSHOT`，回滾整個交易，等一段退避時間再重跑；這跟其他資料庫的 [serialization failure](/backend/knowledge-cards/serialization-failure/) 是同一種處理：交易拿到的 snapshot 過期就放棄，回滾後重跑。重跑時的讀取拿到新的 snapshot，上表回滾後重跑的那一列寫入成功；另一條連線還持有寫入鎖時，不等待就重跑會在 0 ms 再失敗一次。[退避](/backend/knowledge-cards/exponential-backoff/)的間隔要長於另一條連線的寫入交易持有寫入鎖的時間，重跑才不會在寫入鎖還沒釋放時又立刻失敗；那段持鎖時間可以從應用程式記錄的 busy wait 時間分布估出來，這次沒有量測間隔的值。[重跑的次數](/backend/knowledge-cards/retry-policy/)要設上限並記錄：另一條連線長時間持有寫入鎖時，沒有上限的重跑讓同一個請求不斷失敗、一直不回應。被重跑的範圍裡呼叫了回滾不掉的外部操作（扣款、寄信）時，每重跑一次那個操作就再執行一次，所以這類呼叫移到重跑範圍之外，或帶上 [idempotency key](/backend/knowledge-cards/idempotency-key/) 讓外部服務辨識重複的請求。

交易由 driver 或 ORM 開始時，它的交易控制決定送出哪一種 `BEGIN`，以及讀取是否在交易裡。Python 標準庫的 `sqlite3` 模組（[交易控制的文件](https://docs.python.org/3/library/sqlite3.html#transaction-control)）在預設的 legacy 交易控制下，只在 `INSERT`、`UPDATE`、`DELETE`、`REPLACE` 之前隱含送出 `BEGIN`，前面的 `SELECT` 不在交易裡。同樣的先查詢、另一條連線提交、再寫入，寫入成功，不會碰到 `SQLITE_BUSY_SNAPSHOT`；代價是查詢與寫入之間沒有隔離，兩個請求交錯時都查到「還沒打卡」，各寫一筆，資料表留下兩列。`isolation_level` 設成 `"IMMEDIATE"` 時，隱含送出的換成 `BEGIN IMMEDIATE`，送出的時機不變，仍在第一個寫入陳述式之前，前面的 `SELECT` 仍不在交易裡，所以這個設定不等於上文的 `BEGIN IMMEDIATE` 交易：兩個請求交錯時一樣留下兩列。`autocommit=False`（Python 3.12 起）在開連線與每次 commit 之後立刻送出 `BEGIN`，讀取在 DEFERRED 交易裡，同樣的順序回傳 `SQLITE_BUSY_SNAPSHOT`。要讓查詢與寫入在同一個交易裡、而且開始時就取得寫入鎖，以 `isolation_level=None` 開連線，由程式自己送出 `BEGIN IMMEDIATE`。這一段的每一種設定送出 `BEGIN` 的時機與先讀後寫的結果，包括兩個請求交錯時寫出兩列的情形，都在 Python 3.14 與 SQLite 3.53.0 實測過。

Go 的 `database/sql` 由 driver 決定 `BeginTx` 送出哪一種 `BEGIN`。mattn/go-sqlite3 與 modernc.org/sqlite 都接受 DSN 參數 `_txlock=immediate`，帶上之後這個連線池開的每一個交易都以 `BEGIN IMMEDIATE` 開始，只讀的交易也一樣，所以這個參數只放在上文〈寫入連線池上限一條〉的寫入池 DSN，讀取池不帶。在多條連線的池上直接 `db.Exec("BEGIN IMMEDIATE")`，之後的陳述式可能拿到別的連線、不在那個交易裡。Go 1.27.3 搭 mattn/go-sqlite3 v1.14.53 與 modernc.org/sqlite v1.62.0 實測（每種各跑一次）：帶 `_txlock=immediate` 時，第二個交易的 `BeginTx` 等到第一個提交（約 1.05 到 1.09 秒）才開始，讀到第一個寫入的那一列，資料表留下一列。錯誤訊息也依 driver 而不同：mattn 只印 `database is locked`，modernc 印成 `database is locked (517)`，517 就是 `SQLITE_BUSY_SNAPSHOT` 的數值。其他 driver 送出哪一種 `BEGIN`，打開 driver 或 ORM 的 SQL log 看交易開始那一行與它前後的查詢，或在它的文件找交易模式的設定。

同一段先讀後寫搬到 PostgreSQL 的預設隔離等級 `READ COMMITTED` 之後，寫入不再排隊，兩個交易都讀到對方寫入之前的狀態；兩家的並行實測與 PostgreSQL 上改寫成約束、列鎖或 `SERIALIZABLE` 的條件，在 [SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異](/backend/01-database/sql/deployment-shape-and-sql-constructs/) 的〈多個交易同時先讀後寫：工作佇列的認領與班表不重疊〉。

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

| 情境                                             | 真實服務長相                            | 修正方向                                       |
| ------------------------------------------------ | --------------------------------------- | ---------------------------------------------- |
| Desktop app 開著長報表                           | 使用者查詢大列表，背景寫入持續發生      | 報表分頁、限制 read transaction duration       |
| API handler 把查詢結果的讀取物件（cursor）留太久 | streaming response 邊讀邊回，交易未結束 | 先 materialize 結果、縮短 DB read transaction  |
| Background sync 長讀取                           | sync worker 掃全表，UI 仍在寫資料       | 分批讀取、讀寫排程、低流量 checkpoint          |
| Test suite 平行讀寫 fixture                      | 測試共用同一 `.db`，多 worker 交錯      | per-test DB、read-only fixture、獨立 temp file |

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

### 多個 worker 同時寫同一個 SQLite 檔，writer ownership 消失

多 worker 寫入同一個 SQLite 檔的核心風險是 writer ownership 消失。常見情境是小型服務從單 instance 擴到多 instance，但仍把 database file 放在 shared volume；早期看起來可運作，流量上升後開始出現 busy timeout、WAL growth 與偶發資料修復壓力。

修正方向是重新定義 writer。若服務仍是 small backend，可以收斂到單 writer process + queue；若 multi-instance 是長期需求，應遷移到 [PostgreSQL](/backend/01-database/vendors/postgresql/) 或 [MySQL](/backend/01-database/vendors/mysql/)。

### Checkpoint starvation 讓 WAL 吃滿磁碟，而 main database file 沒有增長

長讀取卡 checkpoint 的核心風險是 WAL file 成為隱性容量消耗。讀者可能只看到 disk usage 增長，誤以為是資料量變大；實際上 main database file 沒有明顯增長，`-wal` sidecar 持續膨脹。

修正方向是先找到長 reader，再調整 query lifecycle。Reporting query、background sync、streaming response、互動式 UI 大列表都要有 pagination、timeout 或低流量窗口；checkpoint 只負責收斂 WAL，application 仍要主動結束長讀取。

### 把 busy timeout 當成擴容策略，延遲被藏進使用者路徑

Busy timeout 被當成擴容策略的核心風險是延遲被隱藏到使用者路徑。短暫 lock collision 可以等待；長期 write queue 則會把 API p99、UI freeze 或 worker backlog 拉高。

修正方向是把 busy wait 當 metric。設定 timeout 後要記錄等待時間與超時率；當 busy wait 成為常態，下一步是拆交易、調整 writer process、移走 batch job，或升級到 server database。

### Checkpoint 放在高流量 commit path，少數 commit 變得很慢

Checkpoint 放在高流量 commit path 的核心風險是少數 commit 變得很慢。SQLite 預設 auto-checkpoint 對多數場景合理，但互動式服務可能看到偶發 latency spike；這時可以把 checkpoint 移到背景 thread / process 或低流量窗口。

修正方向是把 checkpoint duration 變成 evidence。觀察 WAL size、checkpoint return、commit latency 與 disk sync；若尖峰可接受，維持預設；若尖峰影響 UX，調整 checkpoint cadence。

### SQLite runtime version 沒有被當成 dependency 維護

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
9. 會寫入的交易用 `BEGIN` 還是 `BEGIN IMMEDIATE` 開始，driver 或 ORM 實際送出的是哪一種，以及寫入要依據的讀取是否在同一個交易裡。

這份清單要接到 [Observability / runbook](/backend/01-database/vendors/sqlite/observability-runbook/) 與 [SQLite Hands-on](/backend/01-database/vendors/sqlite/hands-on/)；正文教判讀，hands-on 負責讓讀者重現 `SQLITE_BUSY`、WAL growth 與 checkpoint 行為。

## 何時維持 SQLite，何時升級

SQLite WAL mode 適合單機、短交易、read-heavy、writer ownership 清楚的服務。只要 busy wait 可控、checkpoint 能完成、backup / restore drill 成立，SQLite 可以承擔正式狀態。

升級訊號來自 writer boundary 外溢。多 instance write、多 region write、high-write OLTP、集中權限治理、read replica、PITR、DB account / role 與 audit requirement 都會把服務推向 server SQL、edge SQLite product 或 distributed SQL。

| 壓力                          | SQLite 內修正                                                                                                                      | 升級路由                                                                            |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| 偶發 `SQLITE_BUSY`            | busy timeout、縮短 transaction；先讀後寫的交易用 `BEGIN IMMEDIATE` 或改寫成唯一約束加單句寫入；同一個 process 的寫入改走寫入連線池 | 維持 SQLite                                                                         |
| WAL growth                    | 找長 reader、manual checkpoint                                                                                                     | 維持 SQLite，補 observability                                                       |
| 同一台機器的多 process 寫入   | busy timeout 加 `BEGIN IMMEDIATE`（〈寫入連線池上限一條〉最後一段）                                                                | busy wait 的 p99 或超時率超出服務目標時，PostgreSQL / MySQL                         |
| 多 instance 或跨機器的 writer | 收斂單 writer、queue 化                                                                                                            | PostgreSQL / MySQL                                                                  |
| Edge locality                 | D1 / Turso compatibility audit                                                                                                     | [D1 / Turso route](/backend/01-database/vendors/sqlite/d1-turso-libsql-comparison/) |
| HA / PITR / audit governance  | file backup 已經難以治理                                                                                                           | [SQLite to PostgreSQL](/backend/01-database/vendors/sqlite/migrate-to-postgresql/)  |

## 下一步路由

- 上游：[SQLite overview](/backend/01-database/vendors/sqlite/)
- 前置：[File lifecycle / backup boundary](/backend/01-database/vendors/sqlite/file-lifecycle-backup-boundary/)
- 操作：[SQLite Hands-on](/backend/01-database/vendors/sqlite/hands-on/) 與 [WAL busy reproduction](/backend/01-database/vendors/sqlite/hands-on/wal-busy-reproduction/)
- 平行：[PRAGMA tuning / performance](/backend/01-database/vendors/sqlite/pragma-tuning-performance/)、[Observability / runbook](/backend/01-database/vendors/sqlite/observability-runbook/)
- 遷移：[SQLite to PostgreSQL](/backend/01-database/vendors/sqlite/migrate-to-postgresql/)
- 官方：[SQLite Write-Ahead Logging](https://www.sqlite.org/wal.html)、[SQLite File Locking](https://www.sqlite.org/lockingv3.html)、[SQLite Isolation](https://www.sqlite.org/isolation.html)、[SQLite PRAGMA](https://www.sqlite.org/pragma.html)
