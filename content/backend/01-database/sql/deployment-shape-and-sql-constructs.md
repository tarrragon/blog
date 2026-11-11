---
title: "SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異"
date: 2026-11-12
description: "SQLite 的嵌入式單一寫入者與 PostgreSQL 的多連線伺服器各自需要哪些 SQL 構造：工作佇列認領與班表不重疊在兩家上的並行實測，列鎖、FOR UPDATE SKIP LOCKED、排除約束與 SERIALIZABLE，建議鎖與 LISTEN/NOTIFY，角色與資料列政策，以及換引擎時哪些交易與並行的設計要跟著改"
weight: 21
tags: ["sql", "sqlite", "postgresql", "concurrency", "portability"]
---

SQLite 與 PostgreSQL 支援的 SQL 構造不同，其中一部分差異可以從兩家的**部署形態**推出來：SQLite 是嵌在應用程式程序裡的函式庫，同一時間只讓一個交易寫入；PostgreSQL 是讓多條連線、多個使用者同時讀寫的伺服器。本篇整理從部署形態推得出來的差異：

- 嵌入式單一寫入者與多連線伺服器各自的定義，以及它們推出的需求。
- 多個交易同時先讀後寫時，工作佇列認領與班表不重疊在兩家上的實測，以及 PostgreSQL 用來協調寫入者的列鎖、`FOR UPDATE SKIP LOCKED`、排除約束與 `SERIALIZABLE`。
- 跨連線協調用的建議鎖與 `LISTEN`／`NOTIFY`。
- 身分與權限：角色、`GRANT` 與資料列層級的政策。
- 換引擎時，這幾類差異各自要改交易與並行設計的哪些地方。

量測跑在 SQLite 3.53.0（Python 3 自帶的那一份）與 PostgreSQL 16.2 上；本分類其他篇用的是 SQLite 3.51 與 PostgreSQL 18，本篇換版本是為了涵蓋 SQLite 近幾版加入的構造。本篇的 SQLite 指官方發行版；SQLite 的 `BEGIN CONCURRENT` 分支與支援它的衍生引擎讓多個寫入交易同時進行，衝突改在提交時以 `SQLITE_BUSY_SNAPSHOT` 回報、整個交易要重試（依分支文件，本篇沒有實跑）。兩家另有一批跟部署形態無關的差異，是各自的設計選擇與實作範圍，寫在 SQLite 的 vendor 頁 [SQLite SQL Dialect and Index Limits](/backend/01-database/vendors/sqlite/sql-dialect-index-limits/)：SQLite 各構造加入的版本與查實際執行版本的方法、彈性型別與 `STRICT` 表對照 PostgreSQL 的型別檢查、`INSERT OR REPLACE` 與 `ON CONFLICT DO UPDATE` 的語意差異、`LATERAL`／`DISTINCT ON`／`ROLLUP`／`MERGE` 在 SQLite 上的改寫，以及只是拼法不同的寫法。同一個寫法各家是否收下、收下之後替寫的人補上什麼決定，在 [SQL.19 引擎寬鬆度與可攜性：各家對同一組寫法的差異、分級與處理時機](/backend/01-database/sql/engine-leniency-and-portability/)。

## 嵌入式單一寫入者與多連線伺服器：部署形態各自推出的需求

**SQLite 是一個函式庫**：應用程式把它連結進自己的程序，資料庫是磁碟上的一個檔案，讀寫由那個程序呼叫函式庫直接對檔案做（[Embedded Database](/backend/knowledge-cards/embedded-database/)）。多條連線可以同時讀；寫入要先取得整個資料庫檔案的寫入鎖，所以同一時間只有一個交易在寫，其餘的寫入者等待或收到 `SQLITE_BUSY`（[Single Writer Model](/backend/knowledge-cards/single-writer-model/)）。同一台機器、本地磁碟上的幾個程序可以開同一個檔案，這把寫入鎖在程序之間同樣有效。對檔案的讀寫沒有經過另一個程序轉手，所以也沒有「登入」這個動作：作業系統允許哪個程序讀寫這個檔案，那個程序就讀寫得了全部資料。

**PostgreSQL 是一個伺服器程序**：應用程式經由網路連線送出 SQL，每一條連線由伺服器的一個後端程序服務。多個交易可以同時寫不同的列，伺服器用多版本並行控制（MVCC）與**列鎖**（row lock）讓它們互不干擾。MVCC 讓每一列保留多個版本，每個讀取依一份快照（某一刻已提交的資料）挑出它看得到的版本；預設的 `READ COMMITTED` 隔離等級下，快照在每一句開始時取。列鎖是交易修改某一列時替那一列上的鎖，其他要修改同一列的交易等它結束。機制在 [PostgreSQL MVCC + Lock Model：為什麼 PG 比 MySQL 少 deadlock、但 vacuum 是別的代價](/backend/01-database/vendors/postgresql/mvcc-lock-model/)。連線要先以某個角色登入，伺服器依角色決定這條連線能做什麼。

部署形態的差別推出 PostgreSQL 有、SQLite 沒有對應情形的需求，各自的構造在後面幾節：

- **寫入者之間的協調**：多個交易同時寫，交易之間要有辦法表達「這一列有人在處理」「這兩筆不能同時成立」。SQLite 的寫入交易一個接一個執行；讀取也放在同一個寫入交易裡時（交易以 `BEGIN IMMEDIATE` 開始，或第一句就寫入），這類協調由那把寫入鎖一次做完。PostgreSQL 的構造是列鎖、`FOR UPDATE SKIP LOCKED`、排除約束與 `SERIALIZABLE`。
- **連線之間的訊號**：分散在不同機器上的服務實例要互斥或互相通知時，它們共用的只有資料庫伺服器，伺服器上的鎖與通知是最近的協調點。SQLite 的寫入者都在同一台機器上：同一個程序裡的執行緒之間，訊號用程式語言的鎖與佇列傳；同一台機器上的幾個程序之間，互斥只剩那把寫入鎖，通知要另外用作業系統的程序間通訊（例如 socket 或 pipe）。PostgreSQL 的構造是建議鎖與 `LISTEN`／`NOTIFY`。
- **身分**：伺服器要先分辨送出 SQL 的是哪個角色，權限才有檢查的依據。PostgreSQL 的構造是角色、`GRANT` 與資料列層級的政策。

## 多個交易同時先讀後寫：工作佇列的認領與班表不重疊

工作佇列與班表不重疊這兩個需求，交易都**先讀後寫**（check-then-act）：先讀資料，依讀到的內容決定要寫什麼。兩個交易交錯執行時，各自讀到的可能都是對方寫入之前的狀態；兩個交易依同一份舊狀態各自寫入同一筆資料、後寫的蓋掉先寫的，叫遺失更新（lost update），工作佇列的同一筆工作被認領兩次屬於這一種；兩個交易各自讀過條件、寫入不同的列，每一筆單獨看都合法，合起來違反條件，叫 write skew，班表的兩段班重疊屬於這一種。兩者在各隔離等級下會不會發生，在 [Isolation Level](/backend/knowledge-cards/isolation-level/)。

下面兩組實測的交錯順序相同：第一條連線執行完它的寫入語句、還沒提交時，第二條連線送出同樣的 SQL（工作佇列是同一句 `UPDATE`，班表是同一句 `INSERT`）；第一條連線在 1 秒之後提交。SQLite 這一側的設定：

- **WAL 模式**（[write-ahead log](/backend/knowledge-cards/write-ahead-log/)）：寫入先記進另一個日誌檔，寫入進行中，其他連線仍然讀得到已提交的資料。
- **`BEGIN IMMEDIATE`**：交易在 `BEGIN` 這一句就取得寫入鎖，不等到第一句寫入。
- **`busy_timeout` 5 秒**：拿不到寫入鎖時最多等 5 秒，才回 `SQLITE_BUSY`；第一條連線 1 秒後就提交，在這個等待時間之內。

PostgreSQL 用預設的 `READ COMMITTED`。每個情境跑一次，其他日誌模式與交錯順序沒有實跑。

### 工作佇列：兩個 worker 認領同一張待辦表

一張 `job` 表放待處理的工作，`worker` 欄為 `NULL` 的是還沒有人認領的。worker（從佇列取工作來執行的程序）用一段 `UPDATE` 認領一筆，`'w1'` 是這個 worker 的名字，第二個 worker 送同一段，把它換成 `'w2'`：

```sql
UPDATE job SET worker = 'w1'
WHERE id = (SELECT id FROM job WHERE worker IS NULL ORDER BY id LIMIT 1)
RETURNING id;
```

| 寫法與引擎                                    | 第二個 worker 等了沒有 | 兩個 worker 領到的 `id` | 結束後的表                  |
| --------------------------------------------- | ---------------------- | ----------------------- | --------------------------- |
| SQLite，上面那段                              | 等到第一個提交         | 1、2                    | 1 歸 w1、2 歸 w2            |
| PostgreSQL，上面那段                          | 等到第一個提交         | 1、1                    | 1 歸 w2，w1 的認領被覆蓋    |
| PostgreSQL，外層再加 `AND worker IS NULL`     | 等到第一個提交         | 1、無                   | 1 歸 w1，第二個 worker 空手 |
| PostgreSQL，子查詢加 `FOR UPDATE SKIP LOCKED` | 沒有等                 | 1、2                    | 1 歸 w1、2 歸 w2            |

在 SQLite 上，第二個 worker 卡在 `BEGIN IMMEDIATE` 這一句：第一個提交之前它拿不到寫入鎖。拿到之後它的 `UPDATE` 才開始執行，子查詢看到的是 1 已經有主人的表，所以領到 2。

在 PostgreSQL 上，第二個 worker 的 `UPDATE` 直接開始執行，子查詢拿到 1，接著要更新 `id = 1` 那一列時遇到第一個 worker 的列鎖而等待。第一個提交之後，`READ COMMITTED` 拿那一列的最新版本重新檢查外層的 `WHERE`（PostgreSQL 文件〈Transaction Isolation〉的 Read Committed 一節），子查詢不重跑：外層只寫了 `id = 1`，最新版本仍然符合，於是第二個 worker 把 1 再認領一次，兩個 worker 都拿到 1。外層加上 `worker IS NULL` 之後，重新檢查發現這一列已經有主人而不更新，不會重複認領，代價是第二個 worker 等了一輪之後更新 0 列，要再送一次。

`FOR UPDATE SKIP LOCKED` 讓子查詢在挑列的同時替它上列鎖，遇到別的交易已經鎖住的列就跳過、挑下一列；PostgreSQL 文件〈The Locking Clause〉把它的用途寫成多個消費者存取類似佇列的表時避免鎖爭用。實測第二個 worker 不等待，直接領到 2。它的作用只在「有其他交易同時持有列鎖」時出現，而 SQLite 沒有列鎖、寫入交易本來就排隊，所以 SQLite 沒有這個構造，語法也不收（`near "FOR": syntax error`）。同一個寫法在售票搶購的認領上怎麼用，在 [9.0.1 售票搶購的負載路徑](/backend/09-performance-capacity/ticketing-load-path/) 的〈扣庫存：資料庫逐張認領與加入 Redis 閘門的條件〉。

### 班表不重疊：同一位員工的兩段班不能有時間重疊

排班系統要求同一位員工的兩段班在時間上不能重疊。唯一鍵只表達得了「兩列的某幾欄不能相等」，而重疊是「兩段區間有交集」，所以常見的第一個寫法是觸發器：插入之前查有沒有重疊的班，有就拒絕。SQLite 這一側的表與觸發器（PostgreSQL 用同一個條件寫成 PL/pgSQL 的觸發器函式）：

```sql
CREATE TABLE shift (emp_id INT, start_at TEXT, end_at TEXT);
-- 起訖統一換成 UTC、存成同一種格式的 ISO 8601 文字，字串順序才等於時間順序；
-- 時區偏移或日期與時間之間的分隔字元不一致時，字串比較會放行實際重疊的班
CREATE TRIGGER no_overlap BEFORE INSERT ON shift
WHEN EXISTS (SELECT 1 FROM shift
             WHERE emp_id = NEW.emp_id AND start_at < NEW.end_at AND NEW.start_at < end_at)
BEGIN SELECT RAISE(ABORT, 'overlap'); END;
-- 這個觸發器只檢查新增；改時段的 UPDATE 要另一個 BEFORE UPDATE 觸發器，條件裡排除自己那一列
```

兩條連線照上面的交錯順序插入兩段重疊的班（09:00–18:00 與 13:00–22:00）：

| 做法與引擎                                     | 第二筆等了沒有 | 結果                                                                      |
| ---------------------------------------------- | -------------- | ------------------------------------------------------------------------- |
| SQLite，觸發器先讀後寫，兩邊 `BEGIN IMMEDIATE` | 等到第一筆提交 | 第二筆被觸發器拒絕（`overlap`），表裡 1 列                                |
| PostgreSQL，同樣的觸發器，`READ COMMITTED`     | 沒有等         | 兩筆都提交，表裡 2 段重疊的班                                             |
| PostgreSQL，同樣的觸發器，`SERIALIZABLE`       | 沒有等         | 先提交的成功，另一筆提交時回 serialization failure                        |
| PostgreSQL，排除約束                           | 等到第一筆提交 | 第二筆回 `conflicting key value violates exclusion constraint`，表裡 1 列 |

PostgreSQL 在 `READ COMMITTED` 下讓兩筆插入同時進行：第二筆的觸發器查詢時第一筆還沒提交，那一句的快照裡看不到它，兩邊都判定沒有重疊。觸發器的條件寫得正確；寫觸發器的人另外假設了查詢與寫入之間沒有其他交易提交新的列，而這個假設在 SQLite 上要靠寫入鎖、在 PostgreSQL 上要靠 `SERIALIZABLE` 或約束才成立。SQLite 的第二筆拿到寫入鎖時第一筆已經提交，觸發器看得到它。

SQLite 這一列的結果有前提：交易的第一句就是寫入（觸發器在 `INSERT` 裡讀），或交易以 `BEGIN IMMEDIATE` 開始。另外兩種情形結果不同：交易用預設的 `BEGIN` 開始、先送一句 `SELECT` 再寫入時，這個交易的讀取停在 `SELECT` 那一刻的快照上，等別人提交之後再寫入就是寫在過期的快照上，所以 SQLite 不等待而直接回 `SQLITE_BUSY`；應用程式的驅動程式把 `SELECT` 放在交易之外時（Python 標準庫 `sqlite3` 的預設行為就是），兩個請求都查到沒有重疊、各寫一筆，SQLite 上也留下兩列。這幾種情形的實測與處理在 [SQLite WAL Concurrency and Locking](/backend/01-database/vendors/sqlite/wal-concurrency-locking/) 的〈先讀後寫的交易：busy timeout 不會等待的 `SQLITE_BUSY`〉。

在 PostgreSQL 上，讓資料庫自己保證「同一位員工的班不重疊」的做法有 `SERIALIZABLE` 與排除約束：

- **`SERIALIZABLE`**：伺服器追蹤交易之間的讀寫相依，偵測到兩個交易各自讀了對方要寫的範圍時，讓其中一個失敗，SQLSTATE 是 `40001`（[Serialization Failure](/backend/knowledge-cards/serialization-failure/)；機制在 [PostgreSQL MVCC + Lock Model：為什麼 PG 比 MySQL 少 deadlock、但 vacuum 是別的代價](/backend/01-database/vendors/postgresql/mvcc-lock-model/) 的〈Predicate lock — SERIALIZABLE isolation 才用〉）。觸發器不必改。失敗可能發生在交易裡的任何一句，也可能在提交時；本篇兩種提交順序各跑一次，都是先提交的成功、後提交的在 `COMMIT` 失敗。所以應用程式要把整個交易包在重試裡，只包 `COMMIT` 會漏接語句階段的失敗。
- **排除約束**（exclusion constraint）：把「兩列不能同時成立」寫成約束。約束由幾組「欄位與比較運算子」組成（班表是 `emp_id` 配 `=`、`during` 配 `&&`），新的一列跟既有的某一列在每一組上的比較都成立時，拒絕新的那一列。唯一鍵是它的特例：每一組的運算子都是 `=`。約束由 GiST 索引執行（GiST 是支援「重疊」這類比較的索引），整數欄位要放進 GiST 索引，需要 `btree_gist` 擴充。下面是有 `btree_gist` 時的寫法，本篇沒有在有這個擴充的建置上實跑：

```sql
CREATE EXTENSION btree_gist;
CREATE TABLE shift (
  emp_id int NOT NULL,
  during tstzrange NOT NULL,  -- 一段班的起訖；[起, 訖) 含起點、不含訖點，18:00 結束與 18:00 開始的兩段班不算重疊
  EXCLUDE USING gist (emp_id WITH =, during WITH &&)  -- && 是區間的重疊比較
);
```

第二筆插入時要在索引裡登記自己，發現第一筆未提交的重疊列就等它結束，第一筆提交之後拒絕第二筆。實測的建置沒有 `btree_gist`，所以把 `emp_id WITH =` 寫成 `int4range(emp_id, emp_id, '[]') WITH =`（把員工編號包成只含一個值的區間，用區間的相等比較）；`emp_id` 不為 `NULL` 時兩種寫法的結果相同。區間型別與排除約束的其他用法在 [PostgreSQL SQL Features：PG 早就有的、MySQL 8.0 才補的、PG 仍領先的](/backend/01-database/vendors/postgresql/sql-features-baseline/) 的〈Range Types + Exclusion Constraints〉。

在工作佇列與班表這兩個需求上，SQLite 用一把資料庫層級的寫入鎖，讓讀取與寫入都在鎖內的交易不會被別的寫入者插進來，代價是同一時間只能有一個寫入者，寫入量的上限由這把鎖決定（容量的判讀在 [SQLite WAL Concurrency and Locking](/backend/01-database/vendors/sqlite/wal-concurrency-locking/)）。PostgreSQL 的預設隔離等級 `READ COMMITTED` 讓寫入者並行，寫的人要把條件明白寫成列鎖、約束或 `SERIALIZABLE`；沒寫出來的，並行的時序決定結果。

## 連線之間的協調：建議鎖與 LISTEN／NOTIFY

**建議鎖**（advisory lock，[Advisory Lock（建議鎖）](/backend/knowledge-cards/advisory-lock/)）是一個只有數字、不綁任何表或列的鎖，數字代表什麼由應用程式自己約定。兩條連線各送 `SELECT pg_try_advisory_lock(42)`，實測先送的回 `true`、後送的回 `false`。它讓分散在不同機器上的服務實例協調「這件事同一時間只有一個在做」，例如排程只讓一個實例執行。`pg_try_advisory_lock` 是 session 層級的鎖，持有者是那一條連線；經由連線池取得連線時，加鎖與解鎖可能拿到不同的連線，所以排程互斥多半改用交易層級的 `pg_try_advisory_xact_lock`，交易結束時自動釋放，原因與案例在 Advisory Lock 卡與 [1.18 高頻計數的寫入與彙總](/backend/01-database/high-frequency-counting/) 的〈同一時間只讓一個實例彙總：建議鎖與連線池〉。

**`LISTEN`／`NOTIFY`** 讓一條連線向某個頻道送出通知，其他對同一頻道送過 `LISTEN` 的連線收得到：

```sql
-- 連線 B
LISTEN punch_added;
-- 連線 A
BEGIN;
NOTIFY punch_added, 'emp 1';
-- 這時連線 B 收不到通知
COMMIT;
-- 提交之後連線 B 收到內容為 'emp 1' 的通知
```

通知在送出它的交易提交時才送達，交易回滾時不送。所以「寫入新的打卡紀錄並通知其他服務」放在同一個交易裡，兩件事一起成立或一起取消。`LISTEN` 要一條在整段監聽期間都不換手的連線：PgBouncer 的 transaction pooling 不支援 `LISTEN`（PgBouncer 文件的功能表），監聽的那一條要直連伺服器或走 session pooling。

SQLite 兩者都沒有（`no such function: pg_advisory_lock`、`near "LISTEN": syntax error`）。同一個程序裡的執行緒，互斥與通知用程式語言的鎖與佇列；SQLite 的 C API 另有資料變更的回呼 `sqlite3_update_hook`，它註冊在一條連線上，回報這條連線對 rowid 表（沒有宣告 `WITHOUT ROWID` 的一般表）做的新增、修改與刪除，用來在程序內部觸發後續動作（依 SQLite 官方文件，本篇沒有實跑）。同一台機器、本地磁碟上的幾個程序共用同一個檔案時，`BEGIN IMMEDIATE` 拿到的寫入鎖就是一把跨程序的互斥鎖，鎖住的範圍是整個資料庫的寫入；檔案放在網路檔案系統上時，這把鎖的語意不可靠，見 [SQLite WAL Concurrency and Locking](/backend/01-database/vendors/sqlite/wal-concurrency-locking/) 的〈Filesystem 與 deployment boundary〉。

## 身分與權限：角色、GRANT 與資料列層級的政策

PostgreSQL 的每條連線以某個角色登入，`GRANT` 決定角色能對哪個物件做什麼，模型與最小權限的做法在 [SQL.16 SQL 的權限模型：角色、GRANT 的授權單位與最小權限](/backend/01-database/sql/privilege-model/)。資料列層級的政策（row-level security，語法是 `CREATE POLICY`）再決定同一張表裡哪些列對這個角色可見，概念在 [Row-Level Security](/backend/knowledge-cards/row-level-security/)，PostgreSQL 的設定在 [PostgreSQL Security / RLS / Audit Logging](/backend/01-database/vendors/postgresql/security-rls-audit-logging/) 的〈Row Level Security〉。

SQLite 的語法不收 `CREATE ROLE`、`GRANT`、`CREATE POLICY`。SQLite 沒有一個伺服器程序居中驗證連線的身分，所以 SQL 層沒有角色與 `GRANT`：作業系統允許某個程序讀寫這個檔案，那個程序就能讀寫全部的表。函式庫提供授權回呼（C API 的 `sqlite3_set_authorizer`，Python 的 `Connection.set_authorizer`），應用程式在每一句 SQL 編譯時決定允不允許讀寫某張表或某個欄位；判斷依據的使用者身分仍由應用程式提供，資料庫只看得到應用程式這一個使用者。要由作業系統擋下寫入，用檔案權限；程式只是要避免自己誤寫時，以 URI 檔名的唯讀模式開啟（`file:app.db?mode=ro`，Python 要加 `uri=True`），這不擋別的程序以讀寫模式開同一個檔案。把 SQLite 包成網路服務的產品（例如 Cloudflare D1，比較在 [SQLite D1 / Turso / libSQL Comparison](/backend/01-database/vendors/sqlite/d1-turso-libsql-comparison/)）在服務層另有帳號與存取權杖的檢查，SQL 層照樣沒有 `GRANT`。

## 換引擎時的判讀：交易與並行的設計要跟著改的地方

並行寫入、連線協調與身分這幾類差異，換引擎時兩個方向發現錯誤的時機不同。從 SQLite 搬到 PostgreSQL 時，資料操作的查詢文字照樣跑得動（交易開頭的 `BEGIN IMMEDIATE` 在 PostgreSQL 回語法錯誤，要改成 `BEGIN`），錯誤要到並行或權限的情境才出現；從 PostgreSQL 搬到 SQLite 時，列鎖、建議鎖、`LISTEN`、`GRANT` 這些構造在 SQLite 上直接回語法錯誤，改寫的對象是交易與並行的設計。跟部署形態無關的型別與查詢寫法差異，改寫的範圍與方法在 [SQLite SQL Dialect and Index Limits](/backend/01-database/vendors/sqlite/sql-dialect-index-limits/) 與 [SQL.19 引擎寬鬆度與可攜性：各家對同一組寫法的差異、分級與處理時機](/backend/01-database/sql/engine-leniency-and-portability/)。

**從 SQLite 搬到 PostgreSQL**：

- **並行寫入**：這一項的前提是 PostgreSQL 這一側有兩條以上的連線同時寫入（連線池大於 1，或有多個服務實例）。搬過去之後仍然只用一條連線依序寫入、或所有寫入都經過應用程式裡單一的寫入者（一個 goroutine、一個 actor）時，寫入照樣一個接一個執行，原本的先讀後寫照樣正確，寫入量的上限改由那一條連線決定。讓先讀後寫正確的是寫入者被排成一個接一個，SQLite 的寫入鎖是做到這件事的一種方式。SQLite 上的先讀後寫交易依開始的方式分成三種：
  - 以 `BEGIN IMMEDIATE` 開始、或第一句就寫入的：在 SQLite 上正確，搬到 PostgreSQL 之後要改寫。
  - 以預設的 `BEGIN` 開始、先讀再寫的：在 SQLite 上碰到並行時不等待，立刻回 `database is locked`（`SQLITE_BUSY`），資料不會錯，錯誤由應用程式重試；搬到 PostgreSQL 之後不再報錯，變成遺失更新，同樣要改寫。同一台機器上幾支程序共用一個檔、常看到 `database is locked` 的系統，要先查交易裡有沒有這一種。
  - 讀與寫分在兩個交易或兩個自動提交的語句時（Python `sqlite3` 的預設；設成 `isolation_level="IMMEDIATE"` 時 `SELECT` 也仍在交易之外）：SQLite 上已經有同樣的遺失更新或 write skew，搬過去之前就要改寫。

  改寫的方式依條件的形狀選：
  - 條件能寫成「某幾欄的組合不能同時成立」時（重複打卡、班表重疊），唯一鍵或排除約束把它交給資料庫：衝突在第二筆寫入時被拒絕，並行的時序不影響結果，應用程式要處理的是約束錯誤。已經用唯一鍵加 `ON CONFLICT DO NOTHING`／`DO UPDATE` 寫入的段落搬過去不必改：後到的交易等前一個提交之後寫入 0 列或改成更新，不回錯誤。
  - 讀與寫能合成同一句 `UPDATE` 時（扣點數寫成 `UPDATE account SET balance = balance - 10 WHERE id = ? AND balance >= 10`），`READ COMMITTED` 在等到列鎖之後拿最新版本重新檢查外層條件，不符合就不更新，所以不會扣成負數；代價是後到的交易可能更新 0 列，應用程式要判斷並重送（工作佇列表的外層條件那一列就是這個情形）。應用程式先 `SELECT` 餘額、算好新值再寫入 `SET balance = <算好的值>` 時，重新檢查保護不到。實測餘額 15、兩個交易各扣 10：單句帶條件的寫法，後到的交易更新 0 列，餘額 5；先讀再寫入算好的值，兩個交易都在對方提交之前讀到 15、各自寫入 5，餘額也是 5，其中一次扣減遺失了。判斷邏輯合不進單句時，在讀餘額的 `SELECT` 加 `FOR UPDATE`，後到的交易等前一個提交、讀到扣過的餘額再判斷；或把交易設成 `REPEATABLE READ`，後到的交易回 `40001`，由應用程式重試。
  - 交易要搶先拿到某一列、再依它的狀態做好幾步時（認領一筆工作之後再寫訂單），`FOR UPDATE` 讓讀到的列在交易結束前只屬於這個交易，`SKIP LOCKED` 讓其他寫入者改拿下一列；鎖只保護被讀到的那幾列，條件涉及還不存在的列（班表裡還沒有的那一段）時保護不到。後續步驟包含外部呼叫或耗時數秒時，交易一直開著會讓列鎖與連線在整段呼叫期間停在 `idle in transaction`；這時認領寫成單句 `UPDATE … WHERE id = (SELECT … FOR UPDATE SKIP LOCKED)` 以自動提交送出，在列上記下認領者與認領時間，呼叫完再用另一個交易寫回結果，worker 中途停止時靠認領時間判斷逾時並收回那筆工作。
  - 條件跨好幾列、寫不成約束時（同一人一個月的請假合計不能超過 3 天、值班表任何時段至少要有一人在班：每一筆單獨插入或刪除都合法，違反的是幾列的合計或存在與否），`SERIALIZABLE` 讓既有的觸發器與查詢不必改，代價是衝突到某一句或提交時才出現，整個交易要重試，衝突多時重試的成本隨並行度上升。

  後果依需求不同，只在兩個交易的讀與寫交錯時出現：認領工作與打卡可能寫出重複的列、班表寫出重疊、扣點數或扣庫存遺失其中一次扣減，而每一筆寫入單獨看都合法，所以不報錯。兩條連線各自送完就提交的測試多半跑成一前一後，看不到錯誤；要讓第一條連線寫完之後先不提交、第二條在這時送出同一段 SQL，才重現得出來。
- **連線協調**：原本靠寫入鎖讓同一台機器上同一時間只有一個程序做某件事的段落（兩個排程程序各自以 `BEGIN IMMEDIATE` 開交易，設了 busy timeout 時後到的那一個等前一個提交後接著執行），在 PostgreSQL 上兩個程序會同時執行。要保持依序執行，改寫成會等待的 `pg_advisory_xact_lock`；同一件工作只要一個實例做時，才用 `pg_try_advisory_xact_lock`，沒拿到鎖就跳過。程序內用 `sqlite3_update_hook` 觸發的後續動作，換成跨程序時改用 `LISTEN`／`NOTIFY`。
- **身分**：原本由應用程式分辨使用者、資料庫只看到一個使用者的設計，搬過去之後可以照舊用一個角色連線，這個角色照最小權限 `GRANT`（[SQL.16 SQL 的權限模型：角色、GRANT 的授權單位與最小權限](/backend/01-database/sql/privilege-model/)）；要讓資料庫依使用者限制看得到的列時，才新增資料列政策，這時每個請求要以對應的身分連線或設定 session 變數，屬於連線設計的改動。

**從 PostgreSQL 搬到 SQLite**：

- **並行寫入**：排除約束、區間型別與 `FOR UPDATE SKIP LOCKED` 在 SQLite 上沒有對應。班表的 `during tstzrange` 要拆成起訖兩個欄位，兩端先換成 UTC、存成同一種格式；「不重疊」改由兩個觸發器檢查，`BEFORE INSERT` 與 `BEFORE UPDATE`（UPDATE 的那一個在條件裡排除自己那一列），因為排除約束對新增與修改都生效，只寫新增的觸發器擋不到改時段；這兩個觸發器只有在交易以 `BEGIN IMMEDIATE` 開始、或第一句就寫入時才可靠。`SKIP LOCKED` 拿掉之後，認領由寫入鎖排隊，worker 不再並行認領。寫入量的上限變成這把鎖的吞吐量，寫入者等不到鎖時收到 `SQLITE_BUSY`：交易要以 `BEGIN IMMEDIATE` 開始並設定 busy timeout，做法在 [SQLite WAL Concurrency and Locking](/backend/01-database/vendors/sqlite/wal-concurrency-locking/)。
- **連線協調與身分**：用到建議鎖、`LISTEN`／`NOTIFY`、角色與資料列政策的地方，在 SQLite 上沒有對應的構造，那些工作要搬進應用程式。`LISTEN`／`NOTIFY` 搬進應用程式之後，「提交時才送出」不再由資料庫保證：把通知寫成同一個交易裡的一列（outbox 表）由接收端輪詢，或提交成功之後才送程序間通訊，並接受程序在兩步之間停止時那一則通知遺失。原本分散在幾台機器上的服務要搬到同一台機器、存取同一個本地檔案，或改用把 SQLite 包成網路服務的產品；這類產品的交易形態不一定是 `BEGIN IMMEDIATE` 的互動式交易，Cloudflare D1 的文件寫的是自動提交與 `batch()`（一批語句依序、不並行地執行，任一句失敗整批回滾），先讀後寫要放進同一批或同一句才受保護。同一台機器上的幾個程序仍然可以共用這個檔案，寫入由寫入鎖排隊。什麼條件下適合往這個方向走，在 [PostgreSQL to SQLite Simplification](/backend/01-database/vendors/sqlite/migrate-from-postgresql-simplification/)。

一段 SQL 搬到另一家時，寬鬆度的差異（同一個寫法各家是否收下、收下之後結果是否相同）要在查詢文字與資料裡找；部署形態的差異（某個構造只有一家有，因為另一家的部署形態沒有它要處理的情形）要在交易與並行的設計裡找。
