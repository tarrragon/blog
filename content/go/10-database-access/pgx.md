---
title: "10.2 pgx：PostgreSQL 驅動的原生介面、連線池與 COPY 大量寫入"
date: 2026-10-06
description: "pgx 當 database/sql 驅動與用原生介面的差別、pgxpool 連線池、依欄名把查詢結果對映進 struct、從 *pgconn.PgError 讀出約束名稱、交易輔助函式、CopyFrom 大量寫入，以及語句快取與連線池代理的關係"
weight: 2
tags: ["go", "database", "pgx", "postgresql"]
---

這篇整理 [pgx](https://github.com/jackc/pgx) v5.11.0 的原生介面。在 [1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/) 的分類裡，pgx 是驅動，它的 `RowToStructByName` 另外接手了結果對映。範例沿用 [10.1 database/sql：連線池、查詢結果的讀取與交易](/go/10-database-access/database-sql/#範例資料表) 定義的 `customers` 與 `orders` 兩張表。database/sql 那一篇已經把 pgx 當成 `database/sql` 的驅動用過，這篇看的是另一種用法：不經過 `database/sql`，直接呼叫 pgx 自己的 API。

## 兩種用法：database/sql 驅動與原生介面

pgx 同一個模組提供兩種入口：

| 入口                | 匯入                                                            | 拿到的物件      |
| ------------------- | --------------------------------------------------------------- | --------------- |
| `database/sql` 驅動 | `_ "github.com/jackc/pgx/v5/stdlib"`，用 `sql.Open("pgx", dsn)` | `*sql.DB`       |
| 原生介面            | `github.com/jackc/pgx/v5` 與 `github.com/jackc/pgx/v5/pgxpool`  | `*pgxpool.Pool` |

兩者連的是同一個 PostgreSQL、用的是同一套通訊協定實作，差別在程式碼看到的 API：

- **原生介面多出來的能力**：PostgreSQL 專有型別的直接對應（陣列、`jsonb`、`inet` 對應到 `netip.Prefix`）、`COPY` 協定的大量寫入、一次送出多個查詢的批次（`Batch`）、`LISTEN`／`NOTIFY`。`database/sql` 的介面是為所有資料庫設計的，這些功能放不進去。
- **`database/sql` 驅動保留的相容性**：只接受 `*sql.DB` 的函式庫——sqlx、GORM、多數 migration 工具——都要透過這一個入口。

所以程式只連 PostgreSQL、而且沒有依賴只吃 `*sql.DB` 的函式庫時，原生介面是比較直接的選擇；要和那些函式庫在同一個交易裡寫入時，用驅動那一個；只要共用連線池的話，pgx 的 `stdlib.OpenDBFromPool(pool)` 可以從 `pgxpool` 做出一個共用同一個池的 `*sql.DB`，交給那些函式庫。兩者可以在同一個程式裡並存；分別建立時各有一個連線池（連線數要合起來算），而且不論池是否共用， `pgx.Tx` 與 `*sql.Tx` 互不相容，一段要一起成功的寫入必須全部走同一個入口。

## pgxpool：連線池

原生介面的連線池是 `pgxpool`。`pgx.Connect` 只建立一條連線、不能被多個 goroutine 同時使用，服務程式用 `pgxpool.New`：

```go
// 連線字串的帳號、密碼、port 與資料庫名稱換成手上那一台的值；pool_max_conns 是池的上限
pool, err := pgxpool.New(ctx, "postgres://postgres:pw@localhost:55432/bookstore?sslmode=disable&pool_max_conns=10")
if err != nil {
	return err
}
defer pool.Close()
```

池的設定可以寫在連線字串裡（`pool_max_conns`、`pool_max_conn_lifetime`、`pool_max_conn_idle_time` 等），也可以先用 `pgxpool.ParseConfig` 解析成設定物件再改欄位。`pool_max_conns` 不寫時，上限是 4 與執行機器 CPU 核心數兩者中較大的那一個；這個預設值和 `database/sql` 的「不設上限」相反，流量大的服務常常是排隊等連線，而不是把資料庫連線開滿。

`pool.Stat()` 回傳池的狀態，可以直接輸出成監控指標：

| 方法                  | 意思                                               |
| --------------------- | -------------------------------------------------- |
| `MaxConns()`          | 池的上限                                           |
| `TotalConns()`        | 目前開著的連線數                                   |
| `AcquiredConns()`     | 使用中的連線數                                     |
| `IdleConns()`         | 閒置的連線數                                       |
| `EmptyAcquireCount()` | 取連線時池裡沒有閒置連線、必須等待或新開的累計次數 |
| `AcquireDuration()`   | 取連線花掉的累計時間                               |

`EmptyAcquireCount` 持續增加、`AcquireDuration` 跟著變長，代表請求在等連線；這和 `database/sql` 連線池的 `WaitCount` 是同一種訊號，持續發生而查詢本身不慢時，先查有沒有借了連線不還（[Connection Leak](/backend/knowledge-cards/connection-leak/)）。

## 讀取結果：CollectRows 與 RowToStructByName

原生介面也可以逐欄 `Scan`，寫法和 `database/sql` 幾乎一樣。多出來的是一組把整列對映進 struct 的輔助函式：

```go
type Order struct {
	ID         int64
	CustomerID int64
	Amount     int
	Note       *string // NULL 時是 nil
	OrderedAt  time.Time
}

rows, _ := pool.Query(ctx,
	"SELECT id, customer_id, amount, note, ordered_at FROM orders WHERE customer_id = $1 ORDER BY id", 1)
orders, err := pgx.CollectRows(rows, pgx.RowToStructByName[Order])
```

`pool.Query` 的錯誤可以先忽略，因為 `CollectRows` 會把查詢的錯誤一併回傳，並在結束時關閉讀取物件，`database/sql` 那種忘了 `Close` 而佔住連線的問題在這個寫法裡不會發生。

`RowToStructByName` 依欄位名稱對映：查詢結果的 `customer_id` 對到 struct 的 `CustomerID`，比對時忽略大小寫與底線；名稱不同時用 `db:"欄位名"` 這個 struct tag 指定。對映發生在執行時，查詢結果有一個 struct 裡找不到的欄位，就在那一次呼叫回傳錯誤：

```go
type Bad struct {
	ID    int64
	Total int // 查詢結果的欄位叫 amount
}
rows, _ = pool.Query(ctx, "SELECT id, amount FROM orders")
_, err = pgx.CollectRows(rows, pgx.RowToStructByName[Bad])
```

```text
mismatch: struct doesn't have corresponding row field amount
```

反方向的情形是 struct 有、查詢結果沒有的欄位：`RowToStructByName` 報錯，`RowToStructByNameLax` 讓那些欄位保持零值。查詢結果多出來的欄位，兩者都報錯，要改的是查詢列出的欄位。

查不到資料時，`QueryRow(...).Scan` 回傳的是 `pgx.ErrNoRows`，不是 `sql.ErrNoRows`；從 `database/sql` 換到原生介面時，判斷「找不到」的那幾行要一起改。

## 錯誤：*pgconn.PgError

資料庫回報的錯誤會被包成 `*pgconn.PgError`，裡面有 PostgreSQL 的錯誤代碼（SQLSTATE）與被違反的約束名稱：

```go
_, err := pool.Exec(ctx, "INSERT INTO customers (name, email) VALUES ($1, $2)", "重複", "jiaying@example.com")

var pgErr *pgconn.PgError
if errors.As(err, &pgErr) && pgErr.Code == "23505" {
	// 23505 是唯一約束違反；pgErr.ConstraintName 說是哪一個
}
```

```text
pgerr: 23505 customers_email_key
```

一張表通常有好幾個唯一約束（email、帳號名稱），錯誤代碼只說「有唯一約束被違反」，要回報「email 已被使用」還是「帳號已被使用」得看 `ConstraintName`。所以建表時替約束取明確的名字（`CONSTRAINT customers_email_key UNIQUE (email)`），程式就能依名字判斷，不必解析錯誤訊息的文字。

## 交易：BeginFunc

原生介面的交易同樣是 `Begin` 加 `defer tx.Rollback(ctx)` 加 `Commit`。pgx 另外提供 `pgx.BeginFunc`，把這三步包成一個函式：傳入的函式回傳 `nil` 就提交，回傳錯誤就撤銷：

```go
err := pgx.BeginFunc(ctx, pool, func(tx pgx.Tx) error {
	if _, err := tx.Exec(ctx, "UPDATE orders SET amount = amount - 10 WHERE id = $1", 101); err != nil {
		return err
	}
	return errors.New("中途失敗") // 回傳錯誤，前面的 UPDATE 一起撤銷
})
```

```text
beginfunc err: 中途失敗 amount still: 300
```

## 大量寫入：CopyFrom

一次寫入大量資料列時，逐列 `INSERT` 每一列都是一次來回（round trip）；多列寫成一句 `INSERT ... VALUES (...), (...)` 可以減少來回，但參數數量有上限（PostgreSQL 的單一查詢最多 65535 個參數）。`CopyFrom` 走 PostgreSQL 的 `COPY` 協定，把資料列串流送給資料庫，沒有參數數量的限制，而且通常是三種寫法裡最快的：

```go
n, err := pool.CopyFrom(ctx,
	pgx.Identifier{"orders"},              // 寫入哪張表
	[]string{"customer_id", "amount"},      // 寫入哪些欄位
	pgx.CopyFromRows([][]any{{3, 120}, {3, 80}}),
)
```

```text
copy: 2 <nil>
```

`COPY` 是整批成功或整批失敗，其中一列違反約束，整批都不會寫入；它也不支援 `ON CONFLICT`，所以要「已存在就略過」的寫入不適合用它。資料來源很大時，用 `pgx.CopyFromFunc` 逐列產生資料，不必先把全部資料放進記憶體。

## pgx 的語句快取與 PgBouncer 交易模式

pgx 預設會把執行過的查詢在每條連線上建成預先解析的查詢（[prepared statement](/backend/knowledge-cards/prepared-statement/)）並快取起來，同一段 SQL 第二次執行時，資料庫不必再解析；執行計畫是否重用，由 PostgreSQL 的計畫快取決定（見 [Prepared Statement](/backend/knowledge-cards/prepared-statement/) 的通用計畫那一點）。在 PostgreSQL 開啟語句記錄就看得到這件事（`ALTER DATABASE bookstore SET log_statement = 'all';` 之後新開的連線生效；PostgreSQL 跑在容器裡時用 `docker logs <容器名稱>` 讀記錄）：用 `pool.QueryRow` 對兩個顧客各執行一次 `SELECT count(*) FROM orders WHERE customer_id = $1`，兩次都以同一個 `stmtcache_` 開頭的名字執行。

```text
LOG:  execute stmtcache_209ed55a1131ce455f4cfc90494ae99f1af9c243b09d5ff6: SELECT count(*) FROM orders WHERE customer_id = $1
DETAIL:  Parameters: $1 = '1'
LOG:  execute stmtcache_209ed55a1131ce455f4cfc90494ae99f1af9c243b09d5ff6: SELECT count(*) FROM orders WHERE customer_id = $1
DETAIL:  Parameters: $1 = '2'
```

預先解析的查詢存在資料庫端的那一條連線上。應用程式和 PostgreSQL 之間有一層 PgBouncer 這類連線池代理（[connection pooler](/backend/knowledge-cards/connection-pooler/)），而它用交易模式（transaction pooling，`pool_mode = transaction`）時，應用程式連到 PgBouncer 的那條連線不變，而 PgBouncer 每個交易都可能從它自己對 PostgreSQL 的連線裡挑另一條，名字就對不上。pgx 的 `stmtcache_` 名字由查詢內容雜湊而成，同一段 SQL 在每條應用程式連線上都叫同一個名字，所以另一條應用程式連線先在那條資料庫連線上建了同名的查詢，這一條再建一次就撞名。PgBouncer 1.25.2 設成交易模式、`max_prepared_statements = 0`，六條 pgx 連線同時執行同一段查詢 300 次，失敗的 200 次全是同一個錯誤：

```text
ERROR: prepared statement "stmtcache_209ed55a1131ce455f4cfc90494ae99f1af9c243b09d5ff6" already exists (SQLSTATE 42P05)
```

同樣的程式改用下面任一種處理方式之後，300 次全部成功。處理方式有兩種：PgBouncer 1.21 起可以在交易模式下追蹤預先解析的查詢，要把 `max_prepared_statements` 設成非 0，1.24 起預設就是 200（PgBouncer 本身的設定見 [PostgreSQL pgBouncer 配置 + 連線池治理](/backend/01-database/vendors/postgresql/pgbouncer-config/)）；或者在 pgx 的連線字串加上 `default_query_exec_mode=exec`，改成每次執行都不留下具名的預先解析查詢。交易模式對其他連線層級設定（session state）的限制見 [Transaction Pooling](/backend/knowledge-cards/transaction-pooling/)。

## pgx 原生介面的適用範圍：只連 PostgreSQL 的程式

pgx 的原生介面接手了 PostgreSQL 型別的轉換、讀取物件的關閉與依欄名的對映，代價是程式只能連 PostgreSQL，而且只吃 `*sql.DB` 的函式庫用不上它的連線池。SQL 仍然是程式裡的字串，欄位名稱拼錯要到執行那一行才知道。[10.4 sqlc：從 SQL 產生型別安全的 Go 程式碼](/go/10-database-access/sqlc/) 從同樣的 SQL 產生呼叫 pgx 的程式碼，把這類錯誤提前到產生程式碼時（`sqlc generate`）；只想在 `database/sql` 上補齊依欄名對映的，是 [10.3 sqlx：手寫 SQL 加上 struct 對映](/go/10-database-access/sqlx/)。
