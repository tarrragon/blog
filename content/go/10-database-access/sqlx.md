---
title: "10.3 sqlx：手寫 SQL 加上 struct 對映"
date: 2026-10-06
description: "sqlx 在 database/sql 之上補的 struct 對映：Get 與 Select 依 db tag 把查詢結果放進 struct、查詢結果的欄位多於 struct 時的錯誤（missing destination name）與 SELECT * 的風險、具名參數與 IN 的展開，以及 SQL 仍是字串所留下的檢查缺口"
weight: 3
tags: ["go", "database", "sqlx"]
---

這篇整理 [sqlx](https://github.com/jmoiron/sqlx) v1.4.0 的用法。範例沿用 [10.1 database/sql：連線池、查詢結果的讀取與交易](/go/10-database-access/database-sql/#範例資料表) 定義的 `customers` 與 `orders` 兩張表。在 [1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/) 的分類裡，sqlx 屬於結果對映：SQL 仍然由程式手寫，它接手的是把查詢結果的每一列放進 struct。取得套件的指令是 `go get github.com/jmoiron/sqlx@v1.4.0`。

## sqlx.DB 與 database/sql 的關係

`*sqlx.DB` 內嵌了 `*sql.DB`，所以 [10.1 database/sql：連線池、查詢結果的讀取與交易](/go/10-database-access/database-sql/) 的內容都照樣成立：同一個連線池、同樣的 `SetMaxOpenConns`、同樣要關閉的讀取物件、同樣的交易規則。sqlx 只在上面加方法，驅動也沿用 `database/sql` 的那一個：

```go
import (
	_ "github.com/jackc/pgx/v5/stdlib"
	"github.com/jmoiron/sqlx"
)

db, err := sqlx.ConnectContext(ctx, "pgx", dsn) // Open 加上 Ping
```

`sqlx.ConnectContext` 等於 `sql.Open` 再 `PingContext`，設定錯誤在這一行就回報。手上已經有一個 `*sql.DB` 時，用 `sqlx.NewDb(db, "pgx")` 包起來，兩者共用同一個連線池。

## Get 與 Select：依 db tag 對映

sqlx 依 struct 欄位上的 `db` tag 對應查詢結果的欄位名稱：

```go
type Order struct {
	ID         int64     `db:"id"`
	CustomerID int64     `db:"customer_id"`
	Amount     int       `db:"amount"`
	Note       *string   `db:"note"` // NULL 時是 nil
	OrderedAt  time.Time `db:"ordered_at"`
}

var orders []Order
err := db.SelectContext(ctx, &orders,
	"SELECT id, customer_id, amount, note, ordered_at FROM orders WHERE customer_id = $1 ORDER BY id", 1)

var o Order
err = db.GetContext(ctx, &o, "SELECT * FROM orders WHERE id = $1", 999)
```

```text
select: 2 <nil>
get none: sql: no rows in result set
```

`SelectContext` 讀出多列放進 slice，內部做完 `database/sql` 讀多列的那一整套「`Next`、`Scan`、`Close`、`Err`」；`GetContext` 讀一列，查不到時回傳的仍然是 `sql.ErrNoRows`，判斷「找不到」的寫法和 `database/sql` 相同。沒有 `db` tag 的欄位，sqlx 預設用欄位名稱的小寫去比對（`CustomerID` 比對 `customerid`），和資料庫慣用的 `customer_id` 對不上，所以每個欄位都寫 tag。

## 查詢結果的欄位多於 struct 時

對映發生在執行時。查詢結果有一個 struct 裡沒有的欄位，那一次呼叫就回傳錯誤：

```go
type Small struct {
	ID int64 `db:"id"`
}
var s []Small
err := db.SelectContext(ctx, &s, "SELECT id, amount FROM orders")
```

```text
extra column: missing destination name amount in *[]main.Small
```

這個行為在查詢寫 `SELECT *` 時會變成部署事故：資料表新增一個欄位之後，所有用 `SELECT *` 讀進同一個 struct 的查詢，從 migration 套用的那一刻起同時開始失敗，而 Go 程式一行都沒改。反方向（struct 有、查詢結果沒有的欄位）不會報錯，那個欄位保持零值，同樣不會被發現。所以用 sqlx 時查詢明確列出欄位，struct 與欄位清單一起改。

sqlx 提供 `db.Unsafe()`，回傳一個會略過多出來欄位的 `*sqlx.DB`。它讓上面那種事故不發生，代價是 struct 和查詢對不上時一律安靜通過。

## 具名參數與 IN

sqlx 補了兩個 `database/sql` 沒有的參數寫法。具名參數用 `:名稱`，值從 map 或 struct（依 `db` tag）取：

```go
res, err := db.NamedExecContext(ctx,
	"UPDATE orders SET note = :note WHERE id = :id",
	map[string]any{"id": 103, "note": "改地址"})
```

`IN` 後面要放一組值時，佔位符的數量要跟著值的數量變。`sqlx.In` 把一個 slice 展開成對應數量的 `?`，`Rebind` 再把 `?` 換成驅動用的佔位符寫法：

```go
q, args, err := sqlx.In("SELECT id FROM orders WHERE id IN (?)", []int64{101, 103})
q = db.Rebind(q)
var ids []int64
err = db.SelectContext(ctx, &ids, q, args...)
```

```text
in: SELECT id FROM orders WHERE id IN (?, ?) [101 103] <nil>
rebind: SELECT id FROM orders WHERE id IN ($1, $2)
ids: [101 103] <nil>
```

只連 PostgreSQL 時另一種寫法是 `WHERE id = ANY($1)`，把整個 slice 當成一個陣列參數傳，佔位符的數量固定，查詢文字也不隨值的數量改變。

## sqlx 留給程式的同步工作：struct 與查詢的欄位清單

sqlx 接手了逐欄 `Scan` 與讀取物件的收尾，而 struct 的欄位與每一段查詢列出的欄位是兩份清單，要在兩處同步改：查詢多一欄是執行時的錯誤，struct 多一欄是安靜的零值，兩者都要測試實際跑過才看得到。把這類檢查提前到產生程式碼時（`sqlc generate`）的是 [10.4 sqlc：從 SQL 產生型別安全的 Go 程式碼](/go/10-database-access/sqlc/)；只連 PostgreSQL、不需要 `*sql.DB` 相容性的話，[10.2 pgx：PostgreSQL 驅動的原生介面、連線池與 COPY 大量寫入](/go/10-database-access/pgx/) 的 `RowToStructByName` 提供同樣依欄名的對映，不必再加一個函式庫；它在 struct 有、查詢結果沒有的欄位上會報錯，sqlx 則讓那個欄位保持零值。
