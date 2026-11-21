---
title: "goose 管理 PostgreSQL migration 的實測紀錄：只含 PostgreSQL 驅動的 CLI、歷史表、改過已套用的檔案、NO TRANSACTION、時間戳的順序與 goose fix、Provider 的 session 鎖"
date: 2026-11-21
description: "要用 goose 管理 PostgreSQL 的 schema，想先知道它在改過已套用的檔案、不能放進交易的語句、長交易擋住 ALTER、分支合併後時間戳順序顛倒，以及多個實例同時啟動時怎麼反應、要怎麼寫 migration 與 Go 程式時讀"
weight: 1
tags: ["go", "goose", "postgresql", "migration", "hands-on"]
slug: "goose-migration-lab"
---

實測日期是 2026-11-21，環境是 macOS 15 的筆電，Go 1.27.3、goose v3.30.1、pgx v5.13.0，PostgreSQL 17.12（Homebrew 的 `postgresql@17`，另外建一個只給這次用的資料庫 cluster；這次跟 [Alembic 那一篇](/programming/python/hands-on/alembic-autogenerate-lab/) 的實測共用同一個 cluster，各用自己的資料庫）；文中的時間戳是這次 `goose create` 產生的值，讀者那邊會不同；這次的操作是用 goose 的 CLI 從建表開始逐份寫 SQL migration、套用，刻意製造改過已套用的檔案、縮窄型別、不能放進交易的語句、時間戳順序顛倒的合併，最後把 migration 嵌進 Go 程式，用 Provider API 讓兩個程序同時套用。

這篇記錄用 goose 管理 PostgreSQL schema 的完整操作：建一個只給這次用的 PostgreSQL；只編入 PostgreSQL 驅動的 goose CLI 與它的環境變數；`goose create` 產生的檔案、`up` 與 `status`、歷史表 `goose_db_version` 記了什麼；修改已經套用過的 migration 時 goose 的反應；改名加縮窄型別的 migration 遇到過長資料時整份隨交易回滾（transaction rollback，資料庫撤銷交易裡做過的變更）；`CREATE INDEX CONCURRENTLY` 與 `-- +goose NO TRANSACTION`；不包交易的 migration 中途失敗之後留下的狀態與重跑的寫法；一筆沒結束的長交易讓排隊的 `ALTER` 擋住一般查詢，以及設了 `lock_timeout` 之後的等待時間；兩個分支的 migration 時間戳先後顛倒時的 `found missing migrations` 與 `-allow-missing`，以及之後 `down` 撤回的是哪一份；`goose fix` 用在已經套用的檔案上的結果；用 `embed` 把 migration 編進執行檔、用 Provider 在程式裡套用，兩個程序同時啟動時不開鎖與開 session 鎖的結果；最後是清理。四種 schema 變更做法的比較、表鎖與 `lock_timeout` 的機制、啟動時套用與獨立部署步驟的取捨，寫在 [1.20 Schema 變更由誰寫出、何時套用](/backend/01-database/schema-change-management/)；GORM 的 `AutoMigrate` 在同一個改名與縮窄情境的行為，見 [10.5 GORM 的〈AutoMigrate 在正式環境的限制〉](/programming/go/basic/10-database-access/gorm/)；從 model 產生 migration 的工具在同樣情境的樣子，見 [Alembic autogenerate 的實測紀錄](/programming/python/hands-on/alembic-autogenerate-lab/)。Go 寫的 migration（`.go` 檔）、MySQL 與 goose 的 table-based locker 不在這次的實測裡。

## 只給這次用的 PostgreSQL

這次在工作目錄底下用 `initdb` 建一個新的 cluster，用完整個目錄刪掉，不動系統上已有的 PostgreSQL。下面的指令跟 Alembic 那一篇的相同（只換了目錄名與資料庫名）；這次的實測沒有另外跑一次 `initdb`，而是在 Alembic 那一篇建好的 cluster 上 `createdb goosedemo`。讀者做過 Alembic 那一篇、那個 cluster 還在 55432 執行時，跳過 `initdb` 與 `pg_ctl`，只跑 `createdb`；兩個 cluster 用同一個 port 時，第二個 `pg_ctl start` 會因為 port 已被佔用而啟動失敗。Homebrew 的 `postgresql@17` 是 keg-only，指令不在 `PATH` 上，下面用完整路徑：

```bash
brew install postgresql@17
P=/opt/homebrew/opt/postgresql@17/bin
mkdir goose-lab && cd goose-lab
$P/initdb -D "$PWD/pgdata" -U postgres --auth=trust -E UTF8 --locale=C
$P/pg_ctl -D "$PWD/pgdata" -o "-p 55432 -k '' -c listen_addresses=127.0.0.1" -l "$PWD/pg.log" start
$P/createdb -h 127.0.0.1 -p 55432 -U postgres goosedemo
```

`goose-lab` 的目錄名是這次取的，沒有比較其他值。`-U postgres` 指定超級使用者的名稱（預設是執行 `initdb` 的作業系統使用者），這次固定成 `postgres`，後面的連線字串才通用；`-E UTF8 --locale=C` 指定編碼與排序規則，不給時取環境變數 `LC_*`，這次用 `C` 讓排序不受這台機器的語系影響，沒有比較其他值。`--auth=trust` 讓本機連線不用密碼；`--auth` 不給時預設也是 trust，PostgreSQL 的 `initdb` 文件說這個預設是為了安裝方便，並提醒除非信任這台機器上的所有使用者，否則不要用。這次明寫出來，讓指令自己交代驗證方式；建正式的 cluster 時改成 `--auth=scram-sha-256` 並用 `--pwprompt` 設密碼。`pg_ctl` 的 `-l` 是 server log 的路徑。`-p 55432` 避開預設的 5432；`-k ''` 不建 Unix socket、只聽 `127.0.0.1` 的 TCP，原因是這台機器的工作目錄路徑太長，放在那裡的 socket 路徑超過 103 個位元組的上限，路徑短的讀者可以拿掉 `-k ''`。`goosedemo` 是這次的資料庫名稱。查資料表時用 `LANG=C $P/psql -h 127.0.0.1 -p 55432 -U postgres goosedemo -c '<SQL>'`，`LANG=C` 讓 `psql` 印英文訊息。

## 只編入 PostgreSQL 驅動的 goose CLI

```bash
go mod init example.com/gooselab
go get github.com/pressly/goose/v3@v3.30.1 github.com/jackc/pgx/v5@v5.13.0
GOBIN=$PWD/bin go install \
  -tags='no_clickhouse no_libsql no_mssql no_mysql no_sqlite3 no_vertica no_ydb' \
  github.com/pressly/goose/v3/cmd/goose@v3.30.1
./bin/goose --version
```

模組路徑 `example.com/gooselab` 是這次取的，沒有比較其他值。這次實際跑的是 `go get ...@latest`，當天解析到 goose v3.30.1 與 pgx v5.13.0；上面寫死成這兩個版本，讓讀者重做時拿到同一版。`go get` 與 `go install` 都寫死 v3.30.1，後半段 Go 程式用的 goose 與 CLI 才一致；換成較新的版本時兩處一起改，並照新版 `cmd/goose/driver_*.go` 的檔頭重列 `-tags`。`GOBIN=$PWD/bin` 把執行檔放在這個目錄的 `bin/`，不放進 `~/go/bin`，下面一律用 `./bin/goose` 執行。

`-tags` 那一串是這次加的。goose 的 CLI 預設把它支援的每一種資料庫驅動都編進去（ClickHouse、MSSQL、MySQL、SQLite、Vertica、YDB、libSQL 等），第一次不帶 `-tags` 時，這台機器在編 ClickHouse 驅動的途中以 `no space left on device` 失敗（當時磁碟只剩不到 1 GB，編譯的中間檔放在 Go 的 build cache）。`cmd/goose/` 底下每個 `driver_*.go` 檔頭有 `//go:build !no_<名稱>`，帶上對應的 tag 就不編那個驅動；上面那串是 v3.30.1 原始碼裡 PostgreSQL 以外各驅動的 tag（Azure SQL 另有 `no_azuresql`，它的檔頭同時要求 `!no_mssql`，所以 `no_mssql` 已經一併排除）。編出來的執行檔 18 MB。`goose -h` 的 Drivers 清單照樣列出全部名稱，那是寫死的說明文字，沒有編進去的驅動在連線時才會報錯。

goose 從三個環境變數讀連線設定，設好之後指令不必每次帶參數：

```bash
export GOOSE_DRIVER=postgres
export GOOSE_DBSTRING='postgres://postgres@127.0.0.1:55432/goosedemo?sslmode=disable'
export GOOSE_MIGRATION_DIR=./migrations
mkdir migrations
```

`GOOSE_DBSTRING` 換成讀者自己的連線字串。`sslmode` 控制連線要不要用 TLS，pgx 與 libpq 的預設是 `prefer`：伺服器支援 TLS 就用，不支援時改用明文，讓同一個連線字串在有沒有 TLS 的伺服器上都連得上。這次的本機 cluster 沒有開 TLS，帶 `disable` 是讓連線不先嘗試 TLS；連到有 TLS 的資料庫時拿掉它，或改成 `verify-full` 驗證伺服器憑證，照抄 `disable` 的話連線會走明文。`GOOSE_MIGRATION_DIR` 不設時預設是目前目錄。

## 第一份 migration 與歷史表 goose_db_version

```bash
./bin/goose create create_coupons sql
```

```text
2026/11/21 03:26:56 Created new file: migrations/20261120192656_create_coupons.sql
```

檔名的前綴是建立時的 UTC 時間（台北時間 03:26 是 UTC 前一天 19:26），goose 把它當成版本號。`create` 的最後一個參數 `sql` 產生 SQL migration，換成 `go` 產生 Go migration。產生的檔案只有範本，內容改成：

```sql
-- +goose Up
CREATE TABLE coupons (
    id   bigserial PRIMARY KEY,
    code varchar(50) NOT NULL,
    rate integer NOT NULL,
    CONSTRAINT coupons_code_key UNIQUE (code)
);

-- +goose Down
DROP TABLE coupons;
```

`-- +goose Up` 與 `-- +goose Down` 是 goose 讀的註記，分出套用與撤回兩段；約束這次自己取名，之後的 migration 才能用名稱指到它。

```bash
./bin/goose status
./bin/goose up
./bin/goose status
```

`up` 之前 `status` 把它列成 `Pending`；`up` 印出 `OK   20261120192656_create_coupons.sql (1.73ms)` 與 `successfully migrated database to version: 20261120192656`；之後的 `status` 在那一列印出套用的時間。歷史表用 `LANG=C $P/psql -h 127.0.0.1 -p 55432 -U postgres goosedemo -c 'TABLE goose_db_version'` 查：

```text
 id |   version_id   | is_applied |           tstamp
----+----------------+------------+----------------------------
  1 |              0 | t          | 2026-11-21 03:27:02.502544
  2 | 20261120192656 | t          | 2026-11-21 03:27:02.514546
```

`version_id` 為 0 的那一列是 goose 第一次建這張表時寫的起點；之後每套用一份加一列。goose 記的只有版本號與時間，沒有檔案內容的雜湊。

接著放兩列資料，第二列的 `code` 有 27 個字元，後面縮窄型別時會用到：

```sql
INSERT INTO coupons (code, rate) VALUES ('SPRING10', 10), ('WELCOME-NEW-MEMBER-2026-NOV', 15);
```

## 修改已經套用的 migration：goose 的 up 與 validate 比對什麼

把剛才那份已經套用的檔案裡的 `varchar(50)` 改成 `varchar(80)`，再跑：

```bash
./bin/goose up; echo "exit=$?"
./bin/goose validate; echo "validate exit=$?"
```

```text
2026/11/21 03:27:07 goose: no migrations to run. current version: 20261120192656
exit=0
validate exit=0
```

資料庫的 `code` 仍是 50，goose 沒有任何訊息。它判斷要不要套用只看版本號在不在歷史表裡；`validate` 檢查的是檔案能不能解析（註記與語句的格式），不比對內容有沒有變。用同一批檔案建一個新環境時，新環境的 `code` 會是 80，跟這個資料庫不同。Flyway 在歷史表存每份檔案的 checksum、內容變了 `validate` 就失敗，goose 沒有這一層，所以已經合併、已經套用的 migration 不再修改，要改就新增一份。實測完把 `varchar(80)` 改回 50。

## 改名加縮窄型別的 migration 與交易回滾

```bash
./bin/goose create rename_rate_shorten_code sql
```

```sql
-- +goose Up
ALTER TABLE coupons RENAME COLUMN rate TO discount;
ALTER TABLE coupons ALTER COLUMN code TYPE varchar(20);

-- +goose Down
ALTER TABLE coupons ALTER COLUMN code TYPE varchar(50);
ALTER TABLE coupons RENAME COLUMN discount TO rate;
```

手寫的 migration 直接寫 `RENAME COLUMN`，資料留在原本的欄位；GORM 的 `AutoMigrate` 在同一個 model 變更下新增一個空的 `discount`、舊的 `rate` 留著，從 model 產生 migration 的工具則產生新增加刪除。`Down` 的順序跟 `Up` 相反。

```bash
./bin/goose up; echo "exit=$?"
./bin/goose version
```

```text
goose run: ERROR 20261120192715_rename_rate_shorten_code.sql: failed to run SQL migration: failed to execute SQL query "ALTER TABLE coupons ALTER COLUMN code TYPE varchar(20);": ERROR: value too long for type character varying(20) (SQLSTATE 22001)
exit=1
goose: version 20261120192656
```

goose 預設把每一份 migration 包在一個交易裡，第二句失敗時第一句的改名一起隨交易回滾，欄位仍是 `id, code, rate`，版本也沒有前進。這裡沒有 `USING`，PostgreSQL 用會檢查長度的轉型而拒絕；GORM 送出的 `USING code::varchar(20)` 是寫在語句裡、指定要轉成哪個型別的轉換（explicit cast），PostgreSQL 用 explicit cast 轉成較短的 `varchar` 時把超出的字元截掉，所以成功。

過長的那一列要變成什麼是業務的決定，這次改成較短的代碼再套用：

```bash
LANG=C $P/psql -h 127.0.0.1 -p 55432 -U postgres goosedemo -c "UPDATE coupons SET code = 'WELCOME-NOV26' WHERE id = 2"
./bin/goose up
```

這次印出 `OK   20261120192715_rename_rate_shorten_code.sql`。正式環境上，資料的修正也寫成一份 migration，放在型別變更之前，讓每個環境照同一個順序做。

這份 migration 的寫法，前提是同一時間只有一版程式在讀寫這張表（單一實例、或部署時先停掉舊版）。滾動部署時舊版實例還在用 `rate`，改名那一刻起它的查詢就失敗；這時候要照 expand-contract 拆成幾份 migration、隔著程式部署分次套用，拆法見 [1.20 的〈比對 model 與資料庫推不出的三件事〉](/backend/01-database/schema-change-management/) 的變更順序那一段與 [1.6 的〈Expand-Contract 模式〉](/backend/01-database/database-migration-playbook/)。

## CREATE INDEX CONCURRENTLY 與 NO TRANSACTION

`CREATE INDEX CONCURRENTLY` 建 index 時不擋這張表的寫入，代價是 PostgreSQL 不讓它在交易裡執行。先用 `./bin/goose create add_discount_index sql` 建檔，照一般的寫法：

```sql
-- +goose Up
CREATE INDEX CONCURRENTLY coupons_discount_idx ON coupons (discount);

-- +goose Down
DROP INDEX CONCURRENTLY coupons_discount_idx;
```

```text
goose run: ERROR 20261120192721_add_discount_index.sql: failed to run SQL migration: failed to execute SQL query "CREATE INDEX CONCURRENTLY coupons_discount_idx ON coupons (discount);": ERROR: CREATE INDEX CONCURRENTLY cannot run inside a transaction block (SQLSTATE 25001)
```

在檔案第一行加上 `-- +goose NO TRANSACTION`，goose 就不替這一份開交易，`up` 印出 `OK   20261120192721_add_discount_index.sql`。

不包交易的代價出現在中途失敗的時候。再用 `./bin/goose create add_two_indexes sql` 建一份，建兩個 index，第二句刻意寫錯欄位名：

```sql
-- +goose NO TRANSACTION
-- +goose Up
CREATE INDEX CONCURRENTLY coupons_code_lower_idx ON coupons (lower(code));
CREATE INDEX CONCURRENTLY coupons_missing_idx ON coupons (no_such_column);

-- +goose Down
DROP INDEX CONCURRENTLY IF EXISTS coupons_missing_idx;
DROP INDEX CONCURRENTLY IF EXISTS coupons_code_lower_idx;
```

`up` 在第二句失敗，`goose version` 仍是上一份，而 `pg_indexes` 裡已經有 `coupons_code_lower_idx`：第一句做完了，goose 沒有記錄這份 migration。把第二句的 `(no_such_column)` 改成 `(discount, code)`（兩欄的複合 index，跟前一份的 `coupons_discount_idx` 不重複）之後重跑，第一句反而失敗：

```text
goose run: ERROR 20261120192800_add_two_indexes.sql: failed to run SQL migration: failed to execute SQL query "CREATE INDEX CONCURRENTLY coupons_code_lower_idx ON coupons (lower(code));": ERROR: relation "coupons_code_lower_idx" already exists (SQLSTATE 42P07)
```

兩句都改成 `CREATE INDEX CONCURRENTLY IF NOT EXISTS` 之後，重跑時已經存在的那一個被略過，`up` 成功。不包交易的 migration 一份只放一句，或把每一句寫成重跑也成立的形式，失敗之後才能直接重跑。`CREATE INDEX CONCURRENTLY` 本身中途失敗時，PostgreSQL 會留下一個標成 invalid 的 index，`IF NOT EXISTS` 會把它當成已經存在而略過；這種情形要先 `DROP INDEX` 再重跑（照 PostgreSQL 的 `CREATE INDEX` 文件，這次沒有實跑）。

## 長交易、排隊的 ALTER 與 lock_timeout

migration 裡的 `ALTER TABLE` 要拿 `ACCESS EXCLUSIVE` 鎖，這一節量它在表上有一筆沒結束的交易時，怎麼擋住後面的一般查詢。這一節直接用 `psql` 開三條連線，不經過 goose：goose 套用 migration 時送出的就是同樣的 `ALTER`，鎖的行為由 PostgreSQL 決定。三條連線在同一個 shell 裡以背景執行，`q` 是這次為了少打字定義的 shell 函式：

```bash
q() { LANG=C $P/psql -h 127.0.0.1 -p 55432 -U postgres goosedemo "$@"; }
q -c "BEGIN; SELECT count(*) FROM coupons; SELECT pg_sleep(6); COMMIT;" > a.log 2>&1 &
sleep 1
q -c '\timing on' -c 'ALTER TABLE coupons ADD COLUMN memo3 text' > b.log 2>&1 &
sleep 1
q -c '\timing on' -c 'SELECT count(*) FROM coupons' > c.log 2>&1 &
sleep 1
q -c "SELECT pid, left(query, 40) AS query, wait_event_type, wait_event FROM pg_stat_activity WHERE datname = 'goosedemo' AND pid <> pg_backend_pid() ORDER BY backend_start"
wait
rg Time b.log c.log
```

持有長交易的連線讀過 `coupons` 之後停 6 秒才提交，代表一筆還沒結束的長交易，它持有 `ACCESS SHARE`；送 `ALTER` 的連線送一個只改 catalog、本身瞬間完成的加欄位；送 `SELECT` 的連線送普通的查詢。`sleep 1` 讓三條依序送出。`pg_stat_activity` 在送 `SELECT` 的連線送出之後查：

```text
  pid  |                  query                   | wait_event_type | wait_event
-------+------------------------------------------+-----------------+------------
 40687 | BEGIN; SELECT count(*) FROM coupons; SEL | Timeout         | PgSleep
 40846 | ALTER TABLE coupons ADD COLUMN memo3 tex | Lock            | relation
 40852 | SELECT count(*) FROM coupons             | Lock            | relation
```

```text
c.log:Time: 3958.468 ms (00:03.958)
b.log:Time: 4973.748 ms (00:04.974)
```

`wait_event_type` 是 `Lock`、`wait_event` 是 `relation` 的連線在等表鎖。`ALTER` 在等持有長交易的連線結束，`SELECT` 在等排在它前面的 `ALTER`：`SELECT` 要的 `ACCESS SHARE` 跟長交易持有的鎖並不衝突，而它排在一個等待中的 `ACCESS EXCLUSIVE` 後面，所以一起等。表只有兩列，等待的時間來自長交易，與資料量無關。

同樣的三條連線，送 `ALTER` 的連線在 `ALTER` 之前先設 `lock_timeout`：

```bash
q -c "BEGIN; SELECT count(*) FROM coupons; SELECT pg_sleep(6); COMMIT;" > a.log 2>&1 &
sleep 1
q -c '\timing on' -c "SET lock_timeout = '1s'" -c 'ALTER TABLE coupons ADD COLUMN memo4 text' > b.log 2>&1 &
sleep 0.3
q -c '\timing on' -c 'SELECT count(*) FROM coupons' > c.log 2>&1 &
wait
rg 'ERROR|Time' b.log c.log
```

```text
c.log:Time: 677.609 ms
b.log:Time: 0.136 ms
b.log:ERROR:  canceling statement due to lock timeout
b.log:Time: 1002.652 ms (00:01.003)
```

`b.log` 的第一個 `Time` 是 `SET` 本身的計時。`lock_timeout` 是單一 session 等鎖的上限，預設 0（不限時），讓一般的查詢等到鎖為止、不因為短暫的鎖衝突而失敗（從預設值的行為推論，文件沒有寫這個預設值的意圖）；PostgreSQL 的文件不建議把它設在 `postgresql.conf`（會影響所有 session），所以只在套用 migration 的連線上設，取捨寫在 [1.20 Schema 變更由誰寫出、何時套用](/backend/01-database/schema-change-management/) 的〈同一個 ALTER 在大表上的代價〉。設成 1 秒之後，`ALTER` 等滿 1 秒就放棄，`SELECT` 等了 0.68 秒就拿到結果（沒有設時是 3.96 秒）；代價是這次的變更沒有做，要排在長交易結束之後重試。`SET` 只對這條連線有效，所以寫在 migration 檔的開頭（`-- +goose Up` 之下第一句），套用那份 migration 的連線才帶著它。第一輪加的 `memo3` 實測完用 `ALTER TABLE coupons DROP COLUMN memo3` 刪掉；第二輪的 `memo4` 沒有建成。

## 時間戳的先後與 -allow-missing

兩位開發者各自在分支上 `goose create`，先建的那一份如果較晚合併，它的時間戳會小於主幹上已經套用的最新一份。這次手動建一份時間戳介於兩份已套用 migration 之間的檔案來模擬。`goose create` 只會用目前的時間取檔名，所以檔名自己取：前綴填一個介於讀者自己 `add_discount_index` 與 `add_two_indexes` 兩份時間戳之間的值（這次是 `20261120192730`；本篇各處的時間戳都換成讀者那邊實際產生的值），存成 `migrations/20261120192730_add_expires_at.sql`：

```sql
-- +goose Up
ALTER TABLE coupons ADD COLUMN expires_at timestamptz;

-- +goose Down
ALTER TABLE coupons DROP COLUMN expires_at;
```

時間戳照抄 `20261120192730` 而它比讀者自己全部的 migration 都早時，這一份會排在建表之前，後面 Provider 那一節在空資料庫上套用時，它會在 `coupons` 還不存在時執行而失敗（從 goose 依版本號排序推論，沒有實跑）。

```bash
./bin/goose status
./bin/goose up; echo "exit=$?"
```

```text
    Sat Nov 21 03:27:21 2026 -- 20261120192721_add_discount_index.sql
    Pending                  -- 20261120192730_add_expires_at.sql
    Sat Nov 21 03:27:35 2026 -- 20261120192800_add_two_indexes.sql
goose run: error: found 1 missing migrations before current version 20261120192800:
	version 20261120192730: migrations/20261120192730_add_expires_at.sql
exit=1
```

goose 預設拒絕套用排在目前版本之前、還沒套用的 migration。確認這一份跟之後的那幾份沒有先後的依賴之後，加 `-allow-missing` 套用：

```bash
./bin/goose -allow-missing up
```

```text
OK   20261120192730_add_expires_at.sql (730.29µs)
goose: successfully migrated database to version: 20261120192730
```

歷史表最後一列是 `20261120192730`，排在 `20261120192800` 之後。goose 以最後套用的那一列當目前版本：

```bash
./bin/goose version
./bin/goose down
./bin/goose version
```

第一個 `version` 印出 `20261120192730`；`down` 撤回的也是 `20261120192730_add_expires_at.sql`，不是時間戳最大的那一份；之後的 `version` 變回 `20261120192800`，`20261120192730` 又回到 Pending，再跑不帶參數的 `goose up` 仍回 missing migrations。下面 `goose fix` 的實測就在這個狀態上做。

`-allow-missing` 以外的做法，是在合併之前把較晚合併的那一份改成新的時間戳（重新 `goose create` 再把內容搬過去），它就排在最後，不需要 `-allow-missing`，`down` 也照時間戳的順序撤回；前提是那一份還沒套用到任何環境。這個做法照 goose 的版本判斷推得出結果，這次沒有實跑。

`goose fix` 把時間戳檔名改成 `00001_`、`00002_` 這樣的連續序號（保留原本的先後），官方 README 建議在 CI pipeline 裡執行，讓合併之後的順序由主幹決定。它只改檔名，不碰資料庫。這次刻意把它用在已經套用過的檔案上（先把 `migrations/` 複製一份備份）：

```bash
cp -R migrations ../migrations-before-fix
./bin/goose fix
./bin/goose status
```

```text
RENAMED 20261120192656_create_coupons.sql => 00001_create_coupons.sql
...
    Pending                  -- 00001_create_coupons.sql
    Pending                  -- 00002_rename_rate_shorten_code.sql
    Pending                  -- 00003_add_discount_index.sql
    Pending                  -- 00004_add_expires_at.sql
    Pending                  -- 00005_add_two_indexes.sql
```

資料庫記的版本是時間戳，檔案的版本變成 1 到 5，goose 對不上任何一份，全部列成 Pending，`goose up` 回 `found 5 missing migrations before current version 20261120192800`。`fix` 要在檔案套用到任何環境之前執行；已經套用過的檔名不再改。實測完把改名後的 `migrations/` 換回備份，下一節的 Provider 要用時間戳檔名的那五份：

```bash
rm -r /<goose-lab 的完整路徑>/migrations
cp -R ../migrations-before-fix migrations
```

`rm -r` 的目標寫成 `goose-lab/migrations` 的完整絕對路徑，執行前用 `ls` 確認那是改名後的檔案。

## 在 Go 程式裡套用：embed、Provider 與 session 鎖

應用程式啟動時自己套用 migration，或部署時跑一支專門套用 migration 的程式，都可以把 SQL 檔用 `embed` 編進執行檔，部署時不必另外帶 `migrations/` 目錄。goose v3.16.0 起的 Provider API 是程式裡套用的介面，下面是這次的 `main.go`：

```go
package main

import (
	"context"
	"database/sql"
	"embed"
	"io/fs"
	"log"
	"os"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"
	"github.com/pressly/goose/v3"
	"github.com/pressly/goose/v3/lock"
)

//go:embed migrations/*.sql
var embedded embed.FS

func main() {
	db, err := sql.Open("pgx", os.Getenv("DATABASE_URL"))
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	migrations, err := fs.Sub(embedded, "migrations")
	if err != nil {
		log.Fatal(err)
	}

	var opts []goose.ProviderOption
	if os.Getenv("MIGRATION_LOCK") == "on" {
		locker, err := lock.NewPostgresSessionLocker()
		if err != nil {
			log.Fatal(err)
		}
		opts = append(opts, goose.WithSessionLocker(locker))
	}

	provider, err := goose.NewProvider(goose.DialectPostgres, db, migrations, opts...)
	if err != nil {
		log.Fatal(err)
	}

	start := time.Now()
	results, err := provider.Up(context.Background())
	for _, r := range results {
		log.Printf("applied %s in %s", r.Source.Path, r.Duration)
	}
	if err != nil {
		log.Fatalf("migrate: %v", err)
	}
	log.Printf("migrations done after %s, %d applied", time.Since(start).Round(time.Millisecond), len(results))
}
```

`//go:embed migrations/*.sql` 把檔案編進 `embedded`，`fs.Sub` 去掉 `migrations/` 這一層，讓 Provider 看到的路徑就是檔名。`_ "github.com/jackc/pgx/v5/stdlib"` 註冊 `database/sql` 的 `pgx` 驅動。`MIGRATION_LOCK` 是這次為了比較兩種情形而加的開關；`DATABASE_URL` 由執行時的環境變數給。`go mod tidy` 之後 `go build -o bin/app .`。

`WithSessionLocker` 不呼叫時不上鎖（goose 原始碼的註解：「If WithSessionLocker is not called, locking is disabled」）；goose 的 README 與 Provider 的 godoc 沒有說明這個預設值服務的情境。`lock.NewPostgresSessionLocker()` 用 PostgreSQL 的 session 層級[建議鎖（advisory lock）](/backend/knowledge-cards/advisory-lock/)（`pg_try_advisory_lock`），拿不到時每 5 秒重試一次、最多 60 次（合計 5 分鐘），這兩個值用 `lock.WithLockTimeout(間隔秒數, 次數)` 傳進 `NewPostgresSessionLocker` 改；migration 可能跑超過 5 分鐘時，等鎖的程序會先放棄而以錯誤結束，所以上限要大於最長一份 migration 的時間。這次用預設值，沒有比較其他值。goose 的 CLI 沒有這把鎖。

比較時讓兩個程序同時跑。第一份 migration 的 `-- +goose Up` 下面暫時加一行 `SELECT pg_sleep(2);`、重新 build，讓兩個程序的套用時間重疊；每一輪先重建一個空的 `race` 資料庫：

```bash
for mode in off on; do
  $P/dropdb -h 127.0.0.1 -p 55432 -U postgres --if-exists race
  $P/createdb -h 127.0.0.1 -p 55432 -U postgres race
  export DATABASE_URL='postgres://postgres@127.0.0.1:55432/race?sslmode=disable' MIGRATION_LOCK=$mode
  ./bin/app > "g_${mode}_1.log" 2>&1 &
  ./bin/app > "g_${mode}_2.log" 2>&1
  wait
done
```

`dropdb` 刪的是這次自己建的 `race` 資料庫；指令裡寫的是資料庫名稱，換成別的名稱前先確認它是可以刪的。結果（去掉時間前綴）：

```text
== lock=off 失敗的那一個
migrate: partial migration error (type:sql,version:20261120192656): ERROR: relation "coupons" already exists (SQLSTATE 42P07)
== lock=off 另一個
applied 20261120192656_create_coupons.sql in 2.006973167s
...（其餘四份）
migrations done after 3.029s, 5 applied
== lock=on 先拿到鎖的那一個
applied 20261120192656_create_coupons.sql in 2.005738375s
...（其餘四份）
migrations done after 2.029s, 5 applied
== lock=on 等鎖的那一個
migrations done after 6.013s, 0 applied
```

兩個程序哪一個先開始建表、先拿到鎖，每次執行不一定，這次跑了兩次，兩次的先後相反，結果的形態相同。不開鎖時兩個程序都讀到空的歷史表、都去建 `coupons`，其中一個以 `relation "coupons" already exists` 結束；在應用程式啟動時套用的話，那就是一個實例啟動失敗。開鎖之後第二個程序等鎖，拿到時歷史表已經是最新版，`0 applied` 正常結束。它多等的 6 秒分兩段，都不是 migration 的時間：`Provider.Up` 在取鎖之前先呼叫 `HasPending` 檢查有沒有待套用的 migration，這一步會建 `goose_db_version`、而且不受 session 鎖保護（goose 的 CHANGELOG v3.20.0 寫明 HasPending 「does not respect the SessionLocker」），PostgreSQL 的 server log 記下第二個程序建表時撞上 `goose_db_version_id_seq`，goose 以固定 1 秒的間隔重試；之後去取鎖，第一次沒取到，5 秒後重試才取到。所以開了 session 鎖，歷史表第一次建立時多個實例仍會撞名，由 goose 自己重試。實測完把 `pg_sleep(2)` 那一行拿掉。

session 鎖綁在一條連線上，套用期間這條連線一直佔著；連線池設得很小的服務，要把這一條算進去。同一個理由，migration 的連線要直連資料庫，或走 session 模式的連線池代理：PgBouncer 這類代理在[交易模式（transaction pooling）](/backend/knowledge-cards/transaction-pooling/)下，每個交易可能分到不同的後端連線，session 層級的鎖沒有固定的持有者（從 Advisory Lock 卡的機制推論，這次沒有接 PgBouncer 實測）。把 migration 放在部署流程裡只跑一次的步驟（CI 的一個 job、Kubernetes 的 Job），是另一種避免並行的方式，兩者的取捨在 [1.20 Schema 變更由誰寫出、何時套用](/backend/01-database/schema-change-management/) 的〈套用的時機：應用程式啟動時與獨立的部署步驟〉。

## 清理

```bash
$P/pg_ctl -D "$PWD/pgdata" stop
```

停掉 server 之後，`goose-lab/` 目錄（含 `pgdata/`、`bin/`）與 `../migrations-before-fix` 都是這次建的，確認路徑之後用 `rm -r` 加完整路徑刪掉。Go 的 build cache 在這次多了編 goose 與它依賴的套件的中間檔，磁碟緊的話用 `go clean -cache` 清掉，下一次編譯會重建；goose、pgx 與它們依賴的套件原始碼另外放在模組快取（`go env GOMODCACHE` 印出的目錄），`go clean -modcache` 會清掉全部專案共用的模組快取，其他專案下次建置時要重新下載，所以只在確定要清時執行。這次在 shell 裡 export 過的環境變數，用 `unset GOOSE_DRIVER GOOSE_DBSTRING GOOSE_MIGRATION_DIR DATABASE_URL MIGRATION_LOCK` 清掉，或直接關掉那個終端機分頁。
