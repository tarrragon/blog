---
title: "1.17 應用程式存取資料庫的工具分層：驅動、結果對映、從 SQL 產生程式碼、Query Builder 與 ORM"
date: 2026-10-06
description: "應用程式存取關聯式資料庫的工作（寫 SQL、取得連線與交易、把結果對映成程式的值），驅動、結果對映、從 SQL 產生程式碼、Query Builder 與 ORM 各接手哪幾件、接手之後哪些行為看不見，ORM 的 N+1 與交易邊界、Go、gunicorn 與 PHP-FPM 各自對資料庫的連線總數與 max_connections、唯一約束違反時各語言讀取約束名稱的位置，以及 Go、PHP（Laravel）與 Python 的對應工具與選型軸"
weight: 17
tags: ["backend", "database", "orm", "data-access"]
---

這篇整理應用程式存取關聯式資料庫的工具分層，與語言無關：每一類工具替程式接手了哪一段工作、接手之後哪些行為從程式碼上消失、選型時比較什麼。各語言的工具名稱與 API 不同，分層相同，所以文中每一類都對照 Go、PHP（Laravel）與 Python 的代表工具。Go 的實際寫法在 [Go 的資料庫存取模組](/go/10-database-access/)；PHP 與 Python 目前只有執行模型與 ORM 回傳值的相關篇章，列在文末。工具分層與資料庫的種類也無關；文中錯誤代碼、預先解析查詢與連線上限的例子用 PostgreSQL，其他資料庫的差異在各節註明。

[1.4 Repository Adapter 實作](/backend/01-database/repository-adapter/) 把工具分成 Raw SQL、查詢建構器（Query Builder）、ORM 三類；這篇沿用那三類，再把 Raw SQL 細分成驅動、結果對映與從 SQL 產生程式碼，因為這三種工具都由程式寫 SQL，差別在取得連線並執行、把查詢結果對映成程式的值這兩項工作由誰做。

## 存取資料庫的工作：寫 SQL、取得連線與交易、對映結果

不論用哪一種語言、哪一個函式庫，程式從資料庫取資料都要完成三件事：

- **寫出要送出的 SQL**：查詢的文字與參數。
- **取得連線並執行**：從連線池取一條連線、送出查詢、需要時開始與結束交易、用完把連線放回去。
- **把查詢結果對映成程式的值**：每一列的每一欄放進程式語言的變數或物件，包括 NULL 要放成什麼。

每一類工具接手這三件事裡的幾件。接手的那幾件程式就不必寫，代價是那幾件工作的實際行為——送出了哪些 SQL、什麼時候佔用與歸還連線、NULL 被放成什麼——從程式碼上讀不出來了。這三件事說明了工具接手之後看不見什麼；選型時另外還要看 schema 的權威、查詢的形狀、錯誤被發現的時間點與部署環境，見〈選型：從要交出的資料存取層往回看〉。

## 各類工具與各語言的代表工具

| 類別              | 接手的事                                                                               | 仍由程式負責             | Go                               | PHP（Laravel）               | Python                                                           |
| ----------------- | -------------------------------------------------------------------------------------- | ------------------------ | -------------------------------- | ---------------------------- | ---------------------------------------------------------------- |
| 驅動與標準介面    | 連線、通訊協定、型別轉換，多數附帶連線池                                               | 寫 SQL、逐欄讀取結果     | `database/sql`、pgx              | PDO、Laravel 的 `DB::select` | DB-API 2.0 驅動（psycopg）                                       |
| 結果對映          | 把整列依欄名放進 struct 或物件                                                         | 寫 SQL                   | sqlx、pgx 的 `RowToStructByName` | PDO 的 `FETCH_CLASS`         | psycopg 的 `class_row`                                           |
| 從 SQL 產生程式碼 | 從手寫的 SQL 產生呼叫函式與結果型別，產生時檢查欄位                                    | 寫 SQL（放在 `.sql` 檔） | sqlc                             | 少見                         | sqlc 搭配產生 Python 程式碼的擴充套件（plugin，sqlc-gen-python） |
| Query Builder     | 用方法呼叫組出 SQL，結構仍對應 SQL 的子句                                              | 決定查詢的形狀           | squirrel、goqu                   | Laravel 的 `DB::table()`     | SQLAlchemy Core                                                  |
| ORM               | 從 model 與方法呼叫組出 SQL、對映、決定 `UPDATE` 寫哪些欄位；部分 ORM 另把寫入包進交易 | 理解它實際送出了什麼     | GORM、ent                        | Eloquent                     | SQLAlchemy ORM、Django ORM                                       |

表上的「多數附帶連線池」在不同語言的意思不同，見〈各語言執行模型下的連線模型〉。

「產生程式碼」本身是另一條軸，不只出現在第三類。從 schema 產生有型別 API 的工具分兩種：讀資料庫現有 schema 的（Go 的 SQLBoiler、go-jet，Java 的 jOOQ，Rust 的 Diesel），以及從自己的 schema 定義檔產生程式碼、並由它產生 migration 的（Go 的 ent 寫在 Go 程式碼裡，TypeScript 的 Prisma 寫在 `schema.prisma`），ent 與 Prisma 的 schema 權威在那份定義檔上。兩種的查詢都由方法呼叫組出，所以歸在 Query Builder 或 ORM，而欄位改名同樣在編譯時失敗。表上第三類特指從手寫的 SQL 產生程式碼的工具。

## 每一類接手之後看不見的行為

### 驅動與標準介面

用驅動直接寫 SQL 時三件事大多看得見，看不見的是驅動自己的預設行為：

- **連線什麼時候還回池裡**：各語言歸還連線的時機不同。Go 的 `database/sql` 每次查詢向池借一條連線，查詢結果的讀取物件（cursor，本站譯為查詢結果的讀取物件，見 [Cursor](/backend/knowledge-cards/cursor/)）關閉時才放回去；讀到最後一列時會自動關閉，讀到一半就離開、又沒有呼叫 `Close` 時，那條連線就一直被佔著。Python 的 SQLAlchemy 與 `psycopg_pool` 由程式明確借出連線，`with` 區塊結束時歸還，洩漏發生在借出連線的那一段沒有收尾（psycopg 預設的 cursor 在執行時就把結果全部讀進來）。PHP-FPM 在請求結束時一併釋放。
- **NULL 的對應**：每種語言要有一個能表示「沒有值」（[NULL](/backend/01-database/sql/knowledge-cards/null/)）的型別。Go 的 `string` 零值是空字串，沒有一個值代表 NULL，所以要用指標或 `sql.NullString`；PHP 與 Python 的動態型別直接用 `null`／`None`。
- **預先解析的查詢**：有些驅動會把執行過的查詢在連線上建成預先解析的查詢（[prepared statement](/backend/knowledge-cards/prepared-statement/)），下次執行同一段 SQL 只送名字與參數。那個名字只存在於建立它的那一條資料庫連線上，而 PgBouncer 這類連線池代理在交易模式（transaction pooling）下，同一條應用程式連線的下一個交易可能被分到另一條資料庫連線，名字因此對不上。各驅動的預設不同：Go 的 pgx 每條連線都快取；PHP 的 PDO pgsql 驅動預設在伺服器端建立具名的 `pdo_stmt_…`，Laravel 沒有改掉這個預設；Python 的 psycopg 3 在同一段查詢執行過 5 次之後、第 6 次執行時才建立（`prepare_threshold`，預設 5）；Django 預設用用戶端綁定，不建立。接上交易模式的代理時，處理方式是讓代理追蹤這些名字（PgBouncer 1.21 起的 `max_prepared_statements`，1.24 起預設開啟），或關掉驅動的這個行為。
- **參數一律用佔位符傳**：值拼進 SQL 字串就是 [SQL 注入（SQL injection）](/backend/knowledge-cards/sql-injection/)的入口，這件事在每一層工具都成立。

### 結果對映

依欄名對映讓程式不必逐欄讀取，而對映發生在**執行時**：查詢結果多了一個物件裡沒有的欄位、或欄位改了名字，錯誤在執行那一行時才出現。最常見的情形是查詢寫 `SELECT *`，資料表後來新增一個欄位：在 sqlx、psycopg 的 `class_row` 這類嚴格對映裡，所有對映到同一個型別的查詢從 migration 套用的那一刻起同時開始失敗，而程式碼一行都沒改；PDO 的 `FETCH_CLASS` 則把多出來的欄位塞成物件的動態屬性，只發出 Deprecated 警告。

### 從 SQL 產生程式碼

從 SQL 產生程式碼的工具讀 schema 與手寫的 SQL，產生呼叫那段 SQL 的函式，以及參數與結果的型別。欄位拼錯、型別不符在產生程式碼時就被擋下，而 SQL 仍然是人寫的、審查時看得到。代價有兩項：產生步驟變成建置流程的一部分（schema 改了要重新產生；產生出來的程式碼二選一：提交進版本控制，或在建置時產生）；以及每一段 SQL 在產生時就固定了，「使用者勾了哪些篩選條件就加哪幾個 `WHERE`」這種動態組合的查詢寫起來吃力。

### Query Builder

Query Builder 用方法呼叫組出 SQL，每個方法大致對應一個子句（`where`、`join`、`orderBy`），所以讀程式碼仍然看得出送出的 SQL 長什麼樣，而且條件可以依執行時的輸入逐步加上去，正好補上從 SQL 產生程式碼的弱項。Query Builder 不負責 model 之間的關聯，也不追蹤物件的變更。

動態組合的條件有兩處容易出錯。排序欄位、排序方向這類**識別字**沒辦法用佔位符傳，由使用者決定時要用程式裡的白名單對映成欄位名（GORM 的 `Order(userInput)` 這類寫法會把輸入原樣放進 SQL）。另外，GORM 用 struct 當查詢條件時同樣略過零值欄位，「狀態 = 0」「啟用 = false」這種篩選會被靜默丟掉，條件要用 map 或明確的 `Where("col = ?", v)`。

### ORM

ORM 接手寫 SQL、取得連線與交易、對映結果這三件事，所以看不見的行為最多。四類最常在正式環境造成問題。

#### ORM 送出的查詢次數：延遲載入與 N+1

延遲載入（lazy loading）在程式每次存取關聯屬性時才發出一次查詢。這個存取寫在迴圈裡，迴圈跑 N 次就多出 N 次查詢，加上取主列表的那一次就是 N+1（見 [1.13 應用層查詢反模式與 Query 預算](/backend/01-database/query-anti-patterns/)）。各框架都有預先載入（eager loading）的寫法：Laravel 的 `with`、SQLAlchemy 的 `selectinload`、Django 的 `select_related` 與 `prefetch_related`、GORM 的 `Preload`。也有在開發時把延遲載入變成錯誤的開關：Laravel 的 `Model::preventLazyLoading()`、SQLAlchemy 關聯設定的 `lazy="raise"`。GORM 沒有延遲載入，它的 N+1 來自程式自己在迴圈裡發的查詢（見 [10.5 GORM：model、關聯載入與 ORM 送出的 SQL](/go/10-database-access/gorm/)）。

#### ORM 的交易邊界：GORM、Laravel、Django 與 SQLAlchemy

同一段「先寫 A 再寫 B」的程式碼，在各 ORM 裡的交易邊界不同（交易範圍怎麼劃見 [Transaction Boundary](/backend/knowledge-cards/transaction-boundary/)）：

- 每一次寫入自動包成一個交易（GORM 的預設行為）：A 與 B 是兩個各自提交的交易。
- 不自動包、要程式明確開始（Laravel 的 `DB::transaction`；Django 預設也是自動提交，要用 `transaction.atomic`，或設定 `ATOMIC_REQUESTS` 讓每個請求包成一個交易）：A 與 B 是兩個各自自動提交的語句。
- 第一次寫入時自動開始交易、到 `commit()` 才提交（SQLAlchemy 的 Session）：A 與 B 在同一個交易裡，忘了呼叫 `commit()` 則兩者都不會寫入。

前兩種情形下，B 失敗時 A 不會撤銷，除非程式自己把兩者包進一個交易。

#### ORM 寫回哪些欄位：變更追蹤、全部欄位與零值

ORM 要決定 `UPDATE` 要寫哪幾個欄位，常見的規則有三種：

- **變更追蹤（dirty tracking）**：Eloquent 與 SQLAlchemy 追蹤哪些屬性被改過，只寫改過的。
- **寫回全部欄位**：Django 的 `save()` 預設把 model 的每個欄位都寫回（傳 `update_fields` 才只寫指定的），兩個請求同時改同一列的不同欄位時，後寫的請求會用它讀出時的舊值，蓋掉先寫的請求改過的欄位。
- **跳過零值**：GORM 的 `Updates` 傳入 struct 時不追蹤變更（`Save` 則寫回全部欄位），而是跳過值為零值的欄位。Go 的 struct 欄位沒有「未設定」這個狀態，沒給值就是 0、空字串或 false（Go 稱為零值），所以 GORM 分不出「沒有設定」與「要改成 0」。

以「把金額從 300 改成 0」為例：變更追蹤看到金額被改過，寫入 0；GORM 看到金額是零值，當成沒有設定而略過金額這一欄，也不回報錯誤；model 沒有其他要寫的欄位時不送出任何 `UPDATE`，model 有 `UpdatedAt`（`gorm.Model` 就帶這個欄位）時仍會送出只更新 `updated_at` 的 `UPDATE`，影響列數是 1，看起來像更新成功。

#### schema 的權威在 model 還是 migration

有的 ORM 從 model 產生 schema（Django 的 `makemigrations`、GORM 的 `AutoMigrate`），有的 model 與 schema 分開定義（Laravel 的 migration 與 Eloquent model 是兩份檔案）。從 model 產生時，欄位改名最容易出錯：GORM 的 `AutoMigrate` 把它當成新增一欄、舊欄留著；Django 的 `makemigrations` 會詢問是不是改名，回答否就產生刪除舊欄加新增一欄的 migration，舊欄的資料跟著刪掉。產生出來的 migration 要逐份讀過。

這四類看不見的行為各有看得到它的地方：送出幾次查詢與寫回哪些欄位，看 ORM 的 SQL 記錄（應用程式端印出它送出的語句）；交易邊界看資料庫端的語句記錄（PostgreSQL 的 `log_statement`），因為有的 ORM（GORM）的 SQL 記錄不印 `begin` 與 `commit`；schema 的那一類看的是產生出來的 migration 檔。程式碼審查時看的是 ORM 的 SQL 記錄、資料庫的語句記錄與 migration 檔，而不只是方法呼叫。

## 各語言執行模型下的連線模型

「工具附帶連線池」這句話在三種語言裡的意思不同，因為池活在程序（process）裡，而三種語言的服務用不同的方式使用程序（池本身的概念見 [Connection Pool](/backend/knowledge-cards/connection-pool/)）：

| 執行模型                                                                              | 連線怎麼來                                                                                                                                                                                                                                                                                                    | 對資料庫的連線總數                                                                                    |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Go：一個程序，每個請求在各自的 goroutine（Go 執行期管理的輕量執行緒）裡處理，全部共用 | 程序裡的一個連線池，所有請求共用                                                                                                                                                                                                                                                                              | 實例數 × 池的上限                                                                                     |
| Python：多個 worker 程序（例如 gunicorn），每個程序各自持有連線                       | 每個程序各自的池（SQLAlchemy 的 engine 內建池；psycopg 用 `psycopg_pool`，沒設 `max_size` 時上限等於 `min_size`，而 `min_size` 預設 4）；Django 的連線依執行緒分開，預設 `CONN_MAX_AGE = 0`，每個請求開一條連線、請求結束時關閉，Django 5.1 起可在資料庫設定的 `OPTIONS` 開啟 `pool`（用的是 `psycopg_pool`） | 實例數 × worker 數 × 每個程序同時持有的連線數（有池時是池的上限；沒有池時是每個程序的執行緒或協程數） |
| PHP-FPM：每個請求從空白開始                                                           | 預設每個請求開一條連線、請求結束時關閉；開啟 PDO 的持久連線（persistent connection）時，每個 FPM worker 保留一條                                                                                                                                                                                              | 實例數 × FPM worker 數（一個 worker 同時只處理一個請求，所以兩者相同）                                |

所以「池的大小設多少」在 Go 是一個設定，在 Python 要乘上 worker 數，而 gunicorn 用多執行緒或 gevent worker 時，一個程序裡的每個執行緒或協程各自取用連線，所以每個程序同時持有的連線不只一條。PHP-FPM 沒有程序內的池，連線數跟著 FPM 的 worker 數走（FPM 的程序模型見 [PHP-FPM：常駐 PHP worker 的程序管理與主要的調校旋鈕](/php/01-server-runtime/php-fpm/)），每台機器的 `pm.max_children` 乘上機器數就是可能的連線數。PHP 改成常駐 worker（Laravel Octane、FrankenPHP 的 worker 模式）之後，應用程式跨請求留在記憶體裡，資料庫連線也跟著保留，行為往 Python 那一列靠（常駐 worker 模型本身見 [常駐 worker 模型：FrankenPHP worker 模式、Laravel Octane 與跨請求殘留的狀態](/php/01-server-runtime/long-running-workers/)）。

三種情形都用同一條原則估算上限：全部實例加起來的連線數，要小於資料庫的 `max_connections` 扣掉維運保留的那幾條（有些託管的資料庫服務另外保留一部分給自己的管理程式）。例如 8 個 Go 實例、每個的池上限設 25，總共 200 條，超過 PostgreSQL 預設的 `max_connections = 100`；平時流量用不滿池，問題要到流量尖峰，或滾動部署時才出現——滾動部署期間新實例已經啟動、舊實例還沒關閉，實例數短時間變多，新開的連線收到 `FATAL: sorry, too many clients already`。PostgreSQL 每條連線是一個獨立的程序，上限不能無限調高（成本見 [PostgreSQL Connection Scaling：process-per-connection model 跟為什麼 pooler 是必裝](/backend/01-database/vendors/postgresql/connection-scaling/)）。

這張表描述的是各語言最常見的部署方式。同一種語言部署成 serverless 函式時，每個並行的執行個體各自有池，連線數跟著並行數走，行為接近 PHP-FPM 那一列；Python 用 async worker 時，一個程序內的協程共用同一個池。

超過時在應用程式與資料庫之間加一層連線池代理（[Connection Pooler](/backend/knowledge-cards/connection-pooler/)），讓多個實例共用較少的資料庫連線。加了代理之後，上面那條原則的右邊換成代理接受的應用程式連線上限（PgBouncer 的 `max_client_conn`），實際連到資料庫的連線數改由代理自己的池設定決定（`default_pool_size` 是每一組使用者與資料庫各自的上限，總數還要乘上組合數）；PgBouncer 的設定與故障演練見 [PostgreSQL pgBouncer 配置 + 連線池治理](/backend/01-database/vendors/postgresql/pgbouncer-config/)。

## 各語言讀取約束名稱的位置

資料庫回報唯一約束違反時，錯誤代碼（PostgreSQL 是 SQLSTATE `23505`）只說「有唯一約束被違反」，是哪一個約束要看約束名稱。這個轉換是把資料庫錯誤轉成業務錯誤（error translation）的一部分，約束本身見 [Constraint](/backend/01-database/sql/knowledge-cards/constraint/)。以下以 PostgreSQL 為例，它的錯誤回報帶有約束名稱欄位，三種語言的驅動都直接暴露；MySQL 的驅動只給錯誤代碼 1062（SQLSTATE `23000`）與訊息文字，索引名稱要從訊息解析；SQLite 只回報欄位名稱（`UNIQUE constraint failed: customers.email`）。

| 語言              | 取得約束名稱的位置                                                                                                                                                                         |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Go（pgx）         | `*pgconn.PgError` 的 `ConstraintName`                                                                                                                                                      |
| PHP（Laravel）    | 唯一約束違反拋出 `UniqueConstraintViolationException`（`QueryException` 的子類別），約束名稱在它帶的資料庫錯誤訊息裡；Laravel 13.2 起直接放在例外的 `index` 屬性（違反的欄位在 `columns`） |
| Python（psycopg） | `psycopg.errors.UniqueViolation` 的 `diag.constraint_name`；Django 把它包成 `django.db.IntegrityError`，原本的 psycopg 例外在 `__cause__`                                                  |

所以建表時替約束取明確的名字（SQL 寫 `CONSTRAINT customers_email_key UNIQUE (email)`；schema 由 Django model 管理時寫 `Meta.constraints` 的 `UniqueConstraint(fields=["email"], name="customers_email_key")`），程式就能依名字回報「email 已被使用」而不是籠統的「資料重複」；讓資料庫自動命名，名字會隨建表工具與版本而不同。

## 選型：從要交出的資料存取層往回看

選型要交出的是專案的資料存取層：各個 repository 用哪一類工具寫、哪些例外。比較的軸取自那一層要承擔的事，而不是工具本身的特性清單；其中「schema 的擁有者」與「應用程式與資料庫之間的基礎設施」兩列是部署與擁有權的環境，其餘是程式碼庫自己的性質：

| 讀者要決定的事                 | 條件                                                                                                                                                               | 適合的類別                                                                                                                                        |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| schema 的權威放哪裡            | schema 由 migration 的 SQL 定義，程式跟著 schema 走                                                                                                                | 從 SQL 產生程式碼、驅動加結果對映                                                                                                                 |
|                                | schema 由 model 定義（Django 的 `makemigrations` 從 model 產生 migration），或 migration 與 model 由同一個框架的慣例管理（Laravel 的 migration 與 Eloquent model） | ORM                                                                                                                                               |
| schema 的擁有者                | schema 由另一個服務擁有（多個服務共用一個資料庫、DBA 管理，或接手既有資料庫）                                                                                      | 本服務不跑 migration；從 SQL 產生程式碼的工具把 `schema` 指向 `pg_dump --schema-only` 的輸出，或用整合測試比對 schema；約束名稱照擁有方的命名判讀 |
| 應用程式與資料庫之間的基礎設施 | 前面有交易模式的連線池代理                                                                                                                                         | 不影響類別的選擇，但會快取預先解析查詢的驅動要調整（見〈驅動與標準介面〉）；連線池上限改對代理的 `max_client_conn` 估算                           |
| 查詢的形狀                     | 多數是單表或一層關聯的增刪查改                                                                                                                                     | ORM                                                                                                                                               |
|                                | 報表、多表聚合、視窗函數這類固定而複雜的查詢                                                                                                                       | 從 SQL 產生程式碼，或在 ORM 裡直接寫 SQL                                                                                                          |
|                                | 篩選條件依使用者輸入動態組合                                                                                                                                       | Query Builder，或 ORM 的條件串接                                                                                                                  |
| 框架的整合程度                 | 用的是 ORM 與驗證、序列化、後台管理整合在一起的框架（Laravel、Django）                                                                                             | 照框架的 ORM 寫，例外的查詢另外寫 SQL                                                                                                             |
|                                | 語言沒有主導的全端框架（Go）                                                                                                                                       | 依 schema 的權威與查詢的形狀決定，沒有預設答案                                                                                                    |
| 錯誤在什麼時候被發現           | 希望欄位改名、查詢寫錯在產生程式碼或編譯時就失敗                                                                                                                   | 從 SQL 產生程式碼，或從 schema 產生型別的 Query Builder 與 ORM（ent、jOOQ、Prisma）                                                               |
|                                | 接受由整合測試在執行時抓出來                                                                                                                                       | 沒有產生步驟的驅動、結果對映、Query Builder 與 ORM                                                                                                |
| 程式碼審查要看到什麼           | 審查者要直接看到每一段送出的 SQL                                                                                                                                   | 驅動、結果對映、從 SQL 產生程式碼                                                                                                                 |
|                                | 審查者看得出查詢的子句結構即可，參數展開與方言細節靠記錄確認                                                                                                       | Query Builder                                                                                                                                     |
|                                | 審查看方法呼叫，SQL 靠開發時 ORM 的 SQL 記錄確認（受稽核、要求每段 SQL 在審查時可見的服務不適用）                                                                  | ORM                                                                                                                                               |
| 資料庫的種類                   | 要支援多種資料庫                                                                                                                                                   | ORM、Query Builder（方言由工具處理）                                                                                                              |
|                                | 只連一種資料庫                                                                                                                                                     | 不受限；從 SQL 產生程式碼的工具要選有支援該資料庫的                                                                                               |

多數專案不只用一類。三種語言都常見同一個組合：一般的增刪查改用框架或專案選定的 ORM，報表與效能敏感的查詢直接寫 SQL（Laravel 的 `DB::select`、Django 的 `raw()`、GORM 的 `Raw`），或在 Go 裡改用從 SQL 產生程式碼的 sqlc。組合本身不是問題，要留意的是兩條路徑共用同一個連線池與交易：ORM 開的交易裡，直接寫的 SQL 也要走同一個交易物件，否則它會從池裡另取一條連線、跑在交易之外；交易物件怎麼一路傳進各個 repository，見 [1.4 Repository Adapter 實作](/backend/01-database/repository-adapter/)〈Transaction 傳遞〉。

## 各語言的實作

- Go：[Go 的資料庫存取模組](/go/10-database-access/) 依本篇的分層，逐一示範 `database/sql`、pgx、sqlx、sqlc 與 GORM，每一篇的輸出都在 PostgreSQL 上實際跑過。
- Python：ORM 與 DataFrame 在回傳值與查詢送出時機上的差別見 [8.3 ORM 與 DataFrame 的分辨：回傳值的形狀、連線物件與查詢送出的時機](/python/08-data-analysis/orm-and-dataframe/)。
- PHP：PHP-FPM 的程序模型見 [PHP-FPM：常駐 PHP worker 的程序管理與主要的調校旋鈕](/php/01-server-runtime/php-fpm/)，連線跨請求保留的常駐 worker 模型見 [常駐 worker 模型：FrankenPHP worker 模式、Laravel Octane 與跨請求殘留的狀態](/php/01-server-runtime/long-running-workers/)。
