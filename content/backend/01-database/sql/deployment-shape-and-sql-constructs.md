---
title: "SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異"
date: 2026-11-12
description: "SQLite 的嵌入式單一寫入者與 PostgreSQL 的多連線伺服器各自需要哪些 SQL 構造：工作佇列認領與班表不重疊在兩家上的並行實測，列鎖、FOR UPDATE SKIP LOCKED、排除約束與 SERIALIZABLE，建議鎖與 LISTEN/NOTIFY，角色與資料列政策，以及更換引擎時交易與並行設計的調整方式"
weight: 21
tags: ["sql", "sqlite", "postgresql", "concurrency", "portability"]
---

SQLite 與 PostgreSQL 支援的 SQL 構造不同，其中許多差異直接源自兩家的**部署形態**：SQLite 是嵌在應用程式行程裡的函式庫，同一時間只允許一個交易寫入；PostgreSQL 是讓多條連線與多個使用者同時讀寫的伺服器。本篇整理從部署形態推導出的差異：

- 嵌入式單一寫入者與多連線伺服器各自的定義，以及它們衍生出的需求。
- 多個交易同時先讀後寫時，工作佇列認領與班表不重疊在兩家上的實測，以及 PostgreSQL 用來協調寫入者的列鎖、`FOR UPDATE SKIP LOCKED`、排除約束與 `SERIALIZABLE`。
- 跨連線協調用的建議鎖與 `LISTEN`／`NOTIFY`。
- 身分與權限：角色、`GRANT` 與資料列層級的政策。
- 更換引擎時，這幾類差異各自要改動交易與並行設計的哪些地方。

量測執行於 SQLite 3.53.0（Python 3 內建版本）與 PostgreSQL 16.2，涵蓋 SQLite 近幾版加入的構造；本篇的 SQLite 指官方發行版，且 PostgreSQL 討論限定於單一主節點上的多連線並行（讀寫分離與唯讀複本的複製延遲屬跨節點架構議題）。SQLite 的 `BEGIN CONCURRENT` 分支與支援它的衍生引擎允許寫入交易並行，衝突改在提交時以 `SQLITE_BUSY_SNAPSHOT` 回報並由整個交易重試（依分支文件，本篇未實跑）。與部署形態無關的型別與語法差異列在 [SQLite SQL Dialect and Index Limits](/backend/01-database/vendors/sqlite/sql-dialect-index-limits/)，各家對寬鬆寫法的接受程度與分級則詳述於 [SQL.19 引擎寬鬆度與可攜性：各家對同一組寫法的差異、分級與處理時機](/backend/01-database/sql/engine-leniency-and-portability/)。

## 嵌入式單一寫入者與多連線伺服器：部署形態各自推出的需求

對照 SQLite 與 PostgreSQL 時，「部署形態」同時拉開了兩條正交軸：**寫入並行模型**（單一寫入鎖對上多版本列鎖）與**行程／網路邊界**（同機嵌入式函式庫對上獨立網路伺服器）。兩條軸在預設官方發行版上綁在一起，但衍生分支（如 `BEGIN CONCURRENT`）或網路封裝服務（如 Cloudflare D1）會單獨調整其中一條軸。

**SQLite 是嵌入式函式庫**：應用程式把它連結進自身行程，資料庫是磁碟上的一個檔案，讀寫由該行程呼叫函式庫直接操作檔案（見 [Embedded Database](/backend/knowledge-cards/embedded-database/)）。多條連線可以同時讀取；寫入必須先取得整個資料庫檔案的寫入鎖，因此同一時間只有一個交易能寫入，其餘寫入者等待或收到 `SQLITE_BUSY`（見 [Single Writer Model](/backend/knowledge-cards/single-writer-model/)）。同一台機器本地磁碟上的多個行程可開啟同一個檔案，這把寫入鎖在行程之間同樣生效。讀寫不經過獨立伺服器行程轉手，也沒有登入流程：作業系統允許哪個行程讀寫該檔案，該行程就能讀寫全部資料。

**PostgreSQL 是多連線伺服器行程**：應用程式經由網路連線送出 SQL，每條連線由伺服器的後端行程服務。多個交易可以同時修改不同的列，伺服器透過 [MVCC（多版本並行控制）](/backend/knowledge-cards/mvcc/) 與 [Row Lock（列鎖）](/backend/knowledge-cards/row-lock/) 讓並行寫入互不干擾。MVCC 為每一列保留多個版本，每次讀取依快照（某一刻已提交的資料）選出可見版本；預設 `READ COMMITTED` 隔離等級下，快照在每句 SQL 開始時取得。列鎖在交易修改某一列時鎖定該列，其他欲修改同一列的交易須等待其結束（機制見 [PostgreSQL MVCC + Lock Model：為什麼 PG 比 MySQL 少 deadlock、但 vacuum 是別的代價](/backend/01-database/vendors/postgresql/mvcc-lock-model/)）。每條連線皆須以特定角色登入，伺服器依該角色決定存取權限。

部署形態的差異衍生出以下 PostgreSQL 具備而 SQLite 沒有對應情境的需求：

- **寫入者之間的協調**：多個交易同時寫入時，必須能在 SQL 層表達「這一列有人正在處理」或「這兩筆資料不能同時成立」。SQLite 的寫入交易依序執行，只要將讀取與寫入放在同一個寫入交易內（以 `BEGIN IMMEDIATE` 開始或首句即寫入），整庫寫入鎖即可保證不交錯；PostgreSQL 則提供列鎖、`FOR UPDATE SKIP LOCKED`、排除約束與 `SERIALIZABLE`。
- **連線之間的訊號**：分散在不同機器上的服務實例需要互斥或通知時，若未額外引入獨立的協調服務或訊息佇列，各實例現成共用的基礎設施便是資料庫伺服器，PostgreSQL 為此提供建議鎖與 `LISTEN`／`NOTIFY`。SQLite 的寫入者位於同一台機器：同一行程內的執行緒使用程式語言的鎖與佇列；同機多行程之間的互斥仰賴整庫寫入鎖，通知則另用作業系統的跨行程通訊（如 socket 或 pipe）。
- **身分與權限**：多連線伺服器須先辨識送出 SQL 的角色，才能執行授權檢查，PostgreSQL 因此提供角色、`GRANT` 與資料列層級政策。

## 多個交易同時先讀後寫：工作佇列的認領與班表不重疊

工作佇列認領與班表不重疊都屬於**先讀後寫**（[Check-then-act（先讀後寫）](/backend/knowledge-cards/check-then-act/)）：先查詢資料，再依讀到的結果決定寫入內容。兩個交易交錯執行時可能讀到對方寫入前的舊狀態：若各自寫入同一筆列且後寫覆蓋先寫，稱為 [Lost Update（遺失更新）](/backend/knowledge-cards/lost-update/)（如工作佇列同一筆工作被認領兩次）；若各自通過條件檢查後寫入不同列、單筆合法但合起來違反不變式，稱為 [Write Skew（寫入偏斜）](/backend/knowledge-cards/write-skew/)（如班表出現兩段重疊時段）。兩者在各隔離等級下的表現見 [Isolation Level](/backend/knowledge-cards/isolation-level/)。

以下兩組實測採用相同的交錯順序：第一條連線執行完寫入語句但尚未提交時，第二條連線送出相同 SQL（工作佇列為同一句 `UPDATE`，班表為同一句 `INSERT`）；第一條連線在 1 秒後提交。SQLite 端設定如下：

- **WAL 模式**（[Write-Ahead Log](/backend/knowledge-cards/write-ahead-log/)）：寫入先記進預寫日誌檔，寫入進行期間其他連線仍可讀取已提交資料。
- **`BEGIN IMMEDIATE`**：交易在 `BEGIN` 語句當下即取得寫入鎖，不等到首句寫入。
- **`busy_timeout` 5 秒**：取不到寫入鎖時最多等待 5 秒才回報 `SQLITE_BUSY`；第一條連線 1 秒後提交，落於等待上限內。

PostgreSQL 採用預設的 `READ COMMITTED`。每個情境實測一次，其他日誌模式與交錯順序未實跑。

### 工作佇列：兩個 worker 認領同一張待辦表

`job` 表存放待處理工作，`worker` 欄為 `NULL` 代表尚未被認領。第一個 worker（`'w1'`）送出以下 `UPDATE` 認領一筆工作，第二個 worker（`'w2'`）將字面值換成 `'w2'` 後送出同一語句：

```sql
UPDATE job SET worker = 'w1'
WHERE id = (SELECT id FROM job WHERE worker IS NULL ORDER BY id LIMIT 1)
RETURNING id;
```

對照的兩種 PostgreSQL 改寫只在條件或子查詢各加一段子句：

```sql
-- 改寫一：外層 WHERE 補上條件，重檢最新版本時擋下覆蓋
UPDATE job SET worker = 'w1'
WHERE id = (SELECT id FROM job WHERE worker IS NULL ORDER BY id LIMIT 1)
  AND worker IS NULL
RETURNING id;

-- 改寫二：子查詢加列鎖並跳過已被鎖住的列
UPDATE job SET worker = 'w1'
WHERE id = (SELECT id FROM job WHERE worker IS NULL ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED)
RETURNING id;
```

| 寫法與引擎                                    | 第二個 worker 是否等待 | 兩個 worker 領到的 `id` | 結束後的表                  |
| --------------------------------------------- | ---------------------- | ----------------------- | --------------------------- |
| SQLite，原 `UPDATE` 語句                      | 等到第一個提交         | 1、2                    | 1 歸 w1、2 歸 w2            |
| PostgreSQL，原 `UPDATE` 語句                  | 等到第一個提交         | 1、1                    | 1 歸 w2，w1 的認領被覆蓋    |
| PostgreSQL，外層再加 `AND worker IS NULL`     | 等到第一個提交         | 1、無                   | 1 歸 w1，第二個 worker 空手 |
| PostgreSQL，子查詢加 `FOR UPDATE SKIP LOCKED` | 沒有等                 | 1、2                    | 1 歸 w1、2 歸 w2            |

在 SQLite 上，第二個 worker 在 `BEGIN IMMEDIATE` 就因寫入鎖而等待；待第一個提交並釋放鎖後，第二個的 `UPDATE` 才執行，子查詢直接看到 `id = 1` 已被認領，因而領到 `2`。

在 PostgreSQL 上，第二個 worker 的 `UPDATE` 直接執行，子查詢選出 `id = 1`，試圖更新該列時遇上第一個 worker 的列鎖而等待。第一個提交後，在 `READ COMMITTED` 下 PostgreSQL 會取該列最新版本重新檢查外層 `WHERE`（PostgreSQL 文件〈Transaction Isolation〉的 Read Committed 一節），但子查詢不會重跑：因為外層只寫 `id = 1`，最新版本仍符合條件，第二個 worker 於是覆蓋並重複認領了 `1`。外層加上 `AND worker IS NULL` 後，重新檢查發現該列已有值便不更新，避免重複認領，但代價是第二個 worker 等待一輪後更新 0 列，須重新查詢。

加上 `FOR UPDATE SKIP LOCKED` 後，子查詢選列同時鎖定該列，遇上已被其他交易鎖住的列則直接跳過（PostgreSQL 文件〈The Locking Clause〉）。實測第二個 worker 不必等待即領到 `2`。此構造只在多交易同時持有列鎖時生效，SQLite 沒有列鎖且寫入本來就排隊，因此不支援此語法（回報 `near "FOR": syntax error`）。該寫法在售票搶購情境的應用見 [9.0.1 售票搶購的負載路徑：熱點列與連線池、CDN 合併回源、排隊放行的速率、資料庫認領與加入 Redis 閘門的條件、付款期限的條件更新](/backend/09-performance-capacity/ticketing-load-path/)。

### 班表不重疊：同一位員工的兩段班不能有時間重疊

排班需求要求同一位員工的兩段班時間不得重疊。唯一鍵只能限制欄位值相等，無法表達區間交集，因此常見作法是以觸發器在插入前查詢是否有重疊時段。SQLite 端的建表與觸發器語句如下（PostgreSQL 以相同條件寫成 PL/pgSQL 觸發器函式）：

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

兩條連線依〈多個交易同時先讀後寫〉開頭的交錯順序（第一條寫入尚未提交時第二條送出，1 秒後第一條提交）插入重疊的兩段班（09:00–18:00 與 13:00–22:00）：

| 做法與引擎                                     | 第二筆是否等待 | 結果                                                                      |
| ---------------------------------------------- | -------------- | ------------------------------------------------------------------------- |
| SQLite，觸發器先讀後寫，兩邊 `BEGIN IMMEDIATE` | 等到第一筆提交 | 第二筆被觸發器拒絕（`overlap`），表裡 1 列                                |
| PostgreSQL，同樣的觸發器，`READ COMMITTED`     | 沒有等         | 兩筆都提交，表裡 2 段重疊的班                                             |
| PostgreSQL，同樣的觸發器，`SERIALIZABLE`       | 沒有等         | 先提交的成功，另一筆提交時回報序列化失敗（serialization failure）         |
| PostgreSQL，排除約束                           | 等到第一筆提交 | 第二筆回 `conflicting key value violates exclusion constraint`，表裡 1 列 |

在 PostgreSQL 的 `READ COMMITTED` 下，兩筆插入同時進行：第二筆觸發器查詢時第一筆尚未提交，其快照看不到第一筆，兩邊皆判定無重疊而雙雙提交。觸發器條件本身正確，但隱含假設「查詢與寫入之間沒有其他交易插入新列」；這項假設在 SQLite 靠寫入鎖成立，在 PostgreSQL 則必須靠 `SERIALIZABLE` 或排除約束成立。

SQLite 的結果依賴兩項前提：第一，交易首句即寫入（如觸發器在 `INSERT` 內執行讀取），或交易以 `BEGIN IMMEDIATE` 開始——若以預設 `BEGIN` 開始、先送 `SELECT` 再寫入，SQLite 會因過期快照不等待而直接回報 `SQLITE_BUSY`；若驅動程式把 `SELECT` 放在交易外（如 Python 標準庫 `sqlite3` 預設行為），兩個請求都會讀到無重疊並各自寫入，在 SQLite 同樣留下重疊資料（實測與處理見 [SQLite WAL Concurrency and Locking](/backend/01-database/vendors/sqlite/wal-concurrency-locking/)）。第二，因為 `BEGIN IMMEDIATE` 鎖定整個資料庫檔案（連帶阻塞所有不相關資料表的寫入），交易內不可夾帶外部網路呼叫或長時間同步 I/O，否則其他執行緒的寫入會撞上 `SQLITE_BUSY`。

在 PostgreSQL 上讓資料庫層保證班表不重疊有兩種方式：

- **`SERIALIZABLE`**：伺服器透過可序列化快照隔離（SSI）追蹤交易之間的讀寫相依，偵測到互相寫入對方讀取範圍時中止其中一個交易並回報序列化失敗（SQLSTATE `40001`，見 [Serialization Failure](/backend/knowledge-cards/serialization-failure/) 與 [PostgreSQL MVCC + Lock Model：為什麼 PG 比 MySQL 少 deadlock、但 vacuum 是別的代價](/backend/01-database/vendors/postgresql/mvcc-lock-model/)）。原觸發器無須改寫，但成立前提是**參與寫入同一不變式的所有併發交易皆須採用 `SERIALIZABLE`**——只要有一條後台或匯入路徑仍以預設 `READ COMMITTED` 寫入，SSI 不會偵測跨隔離等級的讀寫環，重疊班表仍會提交；此外，若查詢缺索引走全表掃描，SIREAD 謂詞鎖可能升級為表級鎖而對無關列產生假陽性 `40001`。由於失敗可能發生於交易內任一語句或 `COMMIT` 當下（實測兩種提交順序皆在 `COMMIT` 失敗），應用程式須將整個交易包進重試迴圈。
- **[Exclusion Constraint（排除約束）](/backend/01-database/sql/knowledge-cards/exclusion-constraint/)**：將「兩列不可同時滿足指定比較運算」寫進表結構（本例為 `emp_id` 配 `=`、`during` 配 `&&`），新列與既有列在所有條件皆成立時即遭拒絕，且在表層強制執法、不受連線隔離等級影響（表內若同時保留已取消或軟刪除的歷史列，可在約束尾端加 `WHERE` 部分條件排除）。唯一鍵是所有運算子皆為 `=` 的特例。排除約束由 GiST 索引（PostgreSQL 支援區間重疊等非等值查詢的索引型別）執行，將整數放進 GiST 索引須安裝 `btree_gist` 擴充（以下寫法需具該擴充，本篇未於含 `btree_gist` 的環境實跑）：

```sql
CREATE EXTENSION btree_gist;
CREATE TABLE shift (
  emp_id int NOT NULL,
  during tstzrange NOT NULL,  -- 一段班的起訖；[起, 訖) 含起點、不含訖點，18:00 結束與 18:00 開始的兩段班不算重疊
  EXCLUDE USING gist (emp_id WITH =, during WITH &&)  -- && 是區間的重疊比較
);
```

第二筆插入於索引登記時偵測到未提交的重疊列而等待，待第一筆提交後即遭拒絕。本篇實測環境未裝 `btree_gist`，改以 `int4range(emp_id, emp_id, '[]') WITH =` 實測；當 `emp_id` 非 `NULL` 時兩種寫法等價（更多區間型別與排除約束用法見 [PostgreSQL SQL Features：PG 早就有的、MySQL 8.0 才補的、PG 仍領先的](/backend/01-database/vendors/postgresql/sql-features-baseline/) 的〈Range Types + Exclusion Constraints〉一節）。

綜上，SQLite 以單一寫入鎖排隊保證先讀後寫不被插隊，代價是寫入吞吐量受限於單一鎖（容量判讀見 [SQLite WAL Concurrency and Locking](/backend/01-database/vendors/sqlite/wal-concurrency-locking/)）；PostgreSQL 的預設 `READ COMMITTED` 允許寫入並行，開發者須將不變式顯式寫成列鎖、約束或 `SERIALIZABLE`，未寫明的部分將由並行時序決定結果。

## 跨連線協調的建議鎖與 LISTEN／NOTIFY

**[Advisory Lock（建議鎖）](/backend/knowledge-cards/advisory-lock/)** 是不綁定任何表或列的整數鎖，數字含義由應用程式約定。實測兩條連線各自執行 `SELECT pg_try_advisory_lock(42)` 時，先送達者回傳 `true`、後送達者回傳 `false`，可用於多台實例間的排程互斥。`pg_try_advisory_lock` 綁定於 session 層級；使用連線池時加鎖與解鎖可能分配到不同連線，因此排程互斥應改用交易結束即自動釋放的 `pg_try_advisory_xact_lock`（案例見 [1.18 高頻計數的寫入與彙總：熱點列的鎖、只新增的事件、可以重跑的彙總與重送的事件](/backend/01-database/high-frequency-counting/) 的〈同一時間只讓一個實例彙總：建議鎖與連線池〉一節）。

**`LISTEN`／`NOTIFY`** 讓連線向指定頻道發送通知，由訂閱同一頻道的連線接收：

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

通知僅在發送交易 `COMMIT` 時送達，交易回滾則不發送，讓「寫入資料」與「發送通知」具備原子性。`LISTEN` 需要不換手的持久連線，PgBouncer（連線池）的 transaction pooling 模式在每次交易結束即換手連線，因此不支援 `LISTEN`（見 PgBouncer 官方文件功能表），監聽連線須直連伺服器或採 session pooling（連線在整個工作階段期間固定給單一用戶端、不於交易間換手）。

SQLite 不支援建議鎖與 `LISTEN`／`NOTIFY`（分別回報 `no such function: pg_advisory_lock` 與 `near "LISTEN": syntax error`）。同行程內執行緒使用語言本身的鎖與佇列；C API 的 `sqlite3_update_hook` 可在單條連線上監聽 rowid 表（SQLite 預設每列自帶隱藏整數鍵 `rowid`、未宣告 `WITHOUT ROWID` 的資料表）的變更事件（依 SQLite 官方文件，本篇未實跑）。同機多行程共用本地檔案時，`BEGIN IMMEDIATE` 的寫入鎖可作跨行程互斥，但檔案位於網路檔案系統時該鎖不可靠（見 [SQLite WAL Concurrency and Locking](/backend/01-database/vendors/sqlite/wal-concurrency-locking/) 的〈Filesystem 與 deployment boundary〉一節）。

## 角色、GRANT 與資料列層級政策的身分控制

PostgreSQL 每條連線以特定角色登入，由 `GRANT` 控制物件權限（模型與最小權限見 [SQL.16 SQL 的權限模型：角色、GRANT 的授權單位與最小權限](/backend/01-database/sql/privilege-model/)），並可透過資料列層級政策（`CREATE POLICY`）進一步限制該角色可見的列（見 [Row-Level Security](/backend/knowledge-cards/row-level-security/)、[PostgreSQL Security / RLS / Audit Logging](/backend/01-database/vendors/postgresql/security-rls-audit-logging/)，以及多租戶 RLS 與 `SET LOCAL` 連線池邊界 [1.21 資安、權限與合規決定的資料表設計：軟刪除與唯一約束、多租戶子表與列級安全性、RBAC 與非同步任務複查、存取憑證撤銷與優先序、個資分離與不可變稽核、角色預設權限與逾時護欄](/backend/01-database/security-and-compliance-schema-decisions/)）。

SQLite 不接受 `CREATE ROLE`、`GRANT` 或 `CREATE POLICY`，因為缺乏驗證連線身分的伺服器行程，檔案存取直接受作業系統權限控制。函式庫層另提供授權回呼（C API 的 `sqlite3_set_authorizer`、Python 的 `Connection.set_authorizer`），讓應用程式在編譯每句 SQL 時決定是否允許讀寫特定表或欄，但使用者身分仍由應用程式自行維護。阻擋外部寫入仰賴檔案系統權限；避免程式自身誤寫則以唯讀 URI 開啟（`file:app.db?mode=ro`，Python 須加 `uri=True`，此模式不阻止其他行程以讀寫模式開啟同一檔案）。將 SQLite 封裝為網路服務的產品（如 Cloudflare D1，其產品定位與服務責任比較見 [SQLite D1 / Turso / libSQL Comparison](/backend/01-database/vendors/sqlite/d1-turso-libsql-comparison/)）在服務層驗證存取權杖，SQL 層同樣不具 `GRANT`。

## 換引擎時的判讀：交易邊界與並行構造的對應關係

並行寫入、連線協調與身分這幾類差異，在兩個遷移方向的錯誤發現時機相反。從 SQLite 遷移至 PostgreSQL 時，一般資料操作語句照常執行（僅 `BEGIN IMMEDIATE` 在 PostgreSQL 須改為 `BEGIN`），並行與權限錯誤直到併發流量出現才暴露；從 PostgreSQL 遷移至 SQLite 時，列鎖、建議鎖、`LISTEN` 與 `GRANT` 會在首次剖析直接報語法錯誤，改寫重點在於交易與並行設計。與部署形態無關的語法方言差異詳見 [SQLite SQL Dialect and Index Limits](/backend/01-database/vendors/sqlite/sql-dialect-index-limits/)，各家對寬鬆寫法的接受程度與四級分級則整理在 [SQL.19 引擎寬鬆度與可攜性：各家對同一組寫法的差異、分級與處理時機](/backend/01-database/sql/engine-leniency-and-portability/)。

**從 SQLite 遷移至 PostgreSQL 時，原本仰賴整庫寫入鎖序列執行才成立的隱性前提會失效。** 一旦 PostgreSQL 端以多條連線同時寫入，原本在 SQLite 依賴寫入鎖排隊的先讀後寫交易會開始交錯（若寫入路徑仍被收斂在單一連線內序列執行，原邏輯會維持正確，代價是寫入吞吐量上限也鎖在該連線）。SQLite 原有的先讀後寫可依交易開啟方式分為三種狀態：

- **以 `BEGIN IMMEDIATE` 開啟或首句即寫入**：在 SQLite 由整庫寫入鎖保證不交錯，遷移至 PostgreSQL 的多連線環境後該保證消失。
- **以預設 `BEGIN` 開啟並先讀再寫**：在 SQLite 遇並行立即回報 `SQLITE_BUSY` 觸發重試，遷移至 PostgreSQL 後預設隔離等級不再報錯，轉為靜默的遺失更新。
- **讀寫分落不同交易或自動提交語句**（例如 Python `sqlite3` 預設行為，即使設 `isolation_level="IMMEDIATE"` 時 `SELECT` 仍在交易外）：在 SQLite 原就存在遺失更新或寫入偏斜，不依賴引擎切換就已失守。

在 PostgreSQL 重新建立對應保證時，衝突對象的形狀決定了應採用的 SQL 構造與代價：

- **多欄靜態條件不可共存**（如重複打卡、班表重疊）：唯一鍵或排除約束在寫入當下拒絕衝突，且不受連線隔離等級影響（含軟刪除或已取消列時加 `WHERE` 部分條件）；原已採唯一鍵搭配 `ON CONFLICT DO NOTHING`／`DO UPDATE`（寫入衝突時略過或改為更新）的段落可維持原寫法。
- **單列狀態扣減或更新**（如餘額扣款）：讀寫可併入單句條件式 `UPDATE`（如 `UPDATE account SET balance = balance - 10 WHERE id = ? AND balance >= 10`）時，在 `READ COMMITTED` 下 PostgreSQL 等到列鎖後會以最新版本重檢 `WHERE`，避免餘額扣負（代價是後到交易可能更新 0 列）。若改由應用層先 `SELECT` 餘額再寫入 `SET balance = <計算值>`，則保護失效——實測餘額 15 兩筆各扣 10 時，單句條件更新讓後到者更新 0 列、餘額留 5；先讀再算則兩筆各寫入 5，遺失一次扣減。跨請求編輯同一列則可於條件帶入版本號（樂觀鎖 `WHERE id = ? AND version = ?`）；單交易內多步邏輯無法併入單句時，可藉 `SELECT ... FOR UPDATE` 鎖列，或採 `REPEATABLE READ` 搭配 `40001` 重試。
- **多 worker 認領佇列列**：`FOR UPDATE` 鎖定既有列、`SKIP LOCKED` 讓其他 worker 跳過已鎖列（列鎖不保護尚未插入的列）。由於長交易停在開啟狀態不提交（`idle in transaction`）會持續占住列鎖與連線資源，涉及外部網路呼叫的流程通常改以單句 `UPDATE … WHERE id = (SELECT … FOR UPDATE SKIP LOCKED)` 寫下認領狀態並立即提交，待外部呼叫完成再以獨立交易回寫結果；因為認領提交後列鎖即釋放，必須同步記錄認領時間並配套逾時回收（[Visibility Timeout](/backend/knowledge-cards/visibility-timeout/)），以免 worker 崩潰讓任務永久滯留。
- **同一父資源下的跨列彙總不變式**（如單人月請假總天數上限）：可在 `READ COMMITTED` 下於交易開頭對父資源主列執行 `SELECT ... FOR UPDATE`，將同一資源的寫入序列化，不必將全域隔離等級升至 `SERIALIZABLE`。
- **無單一父列可鎖的跨多列不變式**（如班表每時段至少一人）：所有參與寫入該不變式的路徑須一致於交易內採 `BEGIN ISOLATION LEVEL SERIALIZABLE`（避免在連線池上改動 session 預設值）並由呼叫端重試 `40001`；代價是高衝突下重試成本上升，且須確認查詢走索引以降低 SIREAD 鎖升級的假陽性失敗。

這類交錯錯誤在兩條連線各自快速提交的測試裡容易序列跑完而不浮現，驗證時須刻意讓第一條連線在寫入後暫停提交，再由第二條送出同段 SQL 才能重現。跨連線協調方面，原本仰賴 SQLite `BEGIN IMMEDIATE` 與 `busy_timeout` 的同機排程序列，在 PostgreSQL 對應為會等待的 `pg_advisory_xact_lock`（只需單一實例執行、其餘直接跳過時對應 `pg_try_advisory_xact_lock`）；跨行程事件通知則從 `sqlite3_update_hook` 對應至 `LISTEN`／`NOTIFY`。身分控制方面，若仍由應用層辨識終端使用者，PostgreSQL 可維持單一依最小權限 `GRANT` 的應用程式角色（詳見 [SQL.16 SQL 的權限模型：角色、GRANT 的授權單位與最小權限](/backend/01-database/sql/privilege-model/)）；需要資料庫層依使用者過濾列時，直連長連線可於連線層設定角色或 session 變數，但經連線池（如 PgBouncer transaction pooling）時必須於每筆交易內以 `SET LOCAL` 設定，否則租戶變數會殘留至下一個重用該連線的請求而造成跨租戶隔離穿透（實測與防線見 [1.21 資安、權限與合規決定的資料表設計：軟刪除與唯一約束、多租戶子表與列級安全性、RBAC 與非同步任務複查、存取憑證撤銷與優先序、個資分離與不可變稽核、角色預設權限與逾時護欄](/backend/01-database/security-and-compliance-schema-decisions/)）。

**從 PostgreSQL 遷移至 SQLite 時，資料庫層的並行與通知構造會收斂回整庫寫入鎖與應用層。** 排除約束、區間型別與 `FOR UPDATE SKIP LOCKED` 在 SQLite 皆無對應語法：`during tstzrange` 改拆為統一轉成 UTC 的起訖欄位，重疊檢查改由 `BEFORE INSERT` 與 `BEFORE UPDATE`（排除自身列）觸發器實作，並靠 `BEGIN IMMEDIATE` 或首句寫入維持交易不交錯（同時須避免在寫入交易內夾帶網路 I/O，以免整庫寫鎖阻塞其他表寫入）；認領作業移除 `SKIP LOCKED` 後改由整庫寫入鎖排隊，並藉 `busy_timeout` 控制等待逾時（完整機制與容量邊界在 [SQLite WAL Concurrency and Locking](/backend/01-database/vendors/sqlite/wal-concurrency-locking/)）。建議鎖、`LISTEN`／`NOTIFY`、角色與資料列政策則脫離 SQL 層，改由應用層或作業系統承擔。其中 `LISTEN`／`NOTIFY` 移出資料庫後會失去「提交時才送出」的原子保證，常見替代方式是在同交易寫入 outbox 表（在同一個資料庫交易內記錄待發事件的表）供接收端輪詢，或在提交後另送跨行程通訊（代價是提交與送訊之間若行程崩潰會遺失通知）。多機分散服務轉向 SQLite 時，須收斂至單機共用本地檔，或改用網路封裝版 SQLite（如 Cloudflare D1 提供自動提交與序列執行的 `batch()`，先讀後寫須放進同批或同句）；這類架構簡化的評估基準整理在 [PostgreSQL to SQLite Simplification](/backend/01-database/vendors/sqlite/migrate-from-postgresql-simplification/)。

總結兩個維度的檢查位置：更換引擎時，寬鬆度差異（語法接受與輸出異同）在查詢文字與資料裡排查；部署形態差異（並行寫入、跨連線協調與身分構造）則在交易邊界與並行架構中調整。上述差異源自引擎的執行環境與並行模型；若在同一引擎上查詢結果正確，但關鍵字向後續維護者傳達的資料預期與實際行為分岔，查證方式見 [SQL.21 關鍵字的宣告與引擎的行為：宣告落空的形態與查證](/backend/01-database/sql/declared-intent-vs-behaviour/)。
