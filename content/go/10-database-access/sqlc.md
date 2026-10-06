---
title: "10.4 sqlc：從 SQL 產生型別安全的 Go 程式碼"
date: 2026-10-06
description: "sqlc 的工作流程：設定檔指向 schema 與查詢檔、查詢上方的註記決定產生的函式、產生出來的參數與結果型別、欄位寫錯在產生時就被擋下、NULL 與時間欄位的型別對應（預設的 pgtype 型別與改成指標的設定）、選擇性篩選條件的寫法，以及產生步驟帶進建置流程的代價"
weight: 4
tags: ["go", "database", "sqlc", "code-generation"]
---

這篇整理 [sqlc](https://sqlc.dev/) v1.31.1 的用法。範例沿用 [10.1 database/sql：連線池、查詢結果的讀取與交易](/go/10-database-access/database-sql/#範例資料表) 定義的 `customers` 與 `orders` 兩張表，驅動用 [10.2 pgx：PostgreSQL 驅動的原生介面、連線池與 COPY 大量寫入](/go/10-database-access/pgx/) 的 pgx v5。在 [1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/) 的分類裡，sqlc 屬於從 SQL 產生程式碼：SQL 由人手寫在 `.sql` 檔裡，sqlc 讀 schema 與這些 SQL，產生呼叫它們的 Go 函式，以及參數與結果的 struct。

sqlc 是開發時執行的命令列工具，不是程式在執行時匯入的函式庫；執行時的程式碼只依賴它產生出來的檔案與 pgx。產生出來的 `store` 套件放在專案的 Go 模組裡，呼叫端以 `import "<go.mod 的 module 名稱>/sqlcdemo/store"` 引用。

## 設定檔與目錄

```text
migrations/                 # 專案的 migration 目錄，與 sqlcdemo/ 同一層
├── 001_init.up.sql
└── 001_init.down.sql
sqlcdemo/
├── sqlc.yaml
├── query/
│   └── orders.sql      # 手寫的查詢
└── store/              # sqlc 產生，不手動修改
    ├── db.go
    ├── models.go
    └── orders.sql.go
```

```yaml
version: "2"
sql:
  - engine: "postgresql"
    schema: "../migrations"   # 建表的 SQL；指向 migration 目錄
    queries: "query"          # 手寫查詢所在的目錄
    gen:
      go:
        package: "store"
        out: "store"            # 產生的程式碼放哪裡
        sql_package: "pgx/v5"   # 產生的程式碼呼叫 pgx 的原生介面
```

不寫 `sql_package` 時，產生的是呼叫 `database/sql` 的程式碼。要和 GORM 在同一個交易裡執行就選它，見 [10.6 Go 專案的資料庫存取工具選型：GORM、sqlc 與 pgx 的組合](/go/10-database-access/choosing-data-access/)〈混用時共用同一個交易〉。

`schema` 指向專案的 migration 目錄（資料表結構的版本化變更檔，見 [Schema Migration](/backend/knowledge-cards/schema-migration/)），sqlc 依序讀裡面的檔案、算出最終的資料表結構。它認得幾種 migration 工具的檔名慣例，例如 golang-migrate 的 `001_init.up.sql` 與 `001_init.down.sql` 放在同一個目錄時，只讀 `up` 那一份；把 `down` 也讀進去的話，`DROP TABLE` 會讓後面的查詢全部找不到表。schema 的權威因此留在 migration，sqlc 只是讀它。

## 查詢檔與註記

每一段查詢上方的註記（query annotation）決定產生的函式名稱與回傳形狀：

```sql
-- name: ListOrdersByCustomer :many
SELECT id, customer_id, amount, note, ordered_at
FROM orders
WHERE customer_id = $1
ORDER BY id;

-- name: GetCustomer :one
SELECT id, name, email FROM customers WHERE id = $1;

-- name: CreateCustomer :one
INSERT INTO customers (name, email) VALUES ($1, $2)
RETURNING id, created_at;

-- name: TotalByCustomer :many
SELECT c.name, sum(o.amount) AS total
FROM customers c JOIN orders o ON o.customer_id = c.id
GROUP BY c.name
ORDER BY c.name;
```

| 註記        | 產生的函式回傳                                                                                                           |
| ----------- | ------------------------------------------------------------------------------------------------------------------------ |
| `:one`      | 一個 struct；查不到時回傳 `pgx.ErrNoRows`                                                                                |
| `:many`     | struct 的 slice                                                                                                          |
| `:exec`     | 只回傳錯誤                                                                                                               |
| `:execrows` | 影響的列數與錯誤                                                                                                         |
| `:copyfrom` | 用 [10.2 pgx：PostgreSQL 驅動的原生介面、連線池與 COPY 大量寫入](/go/10-database-access/pgx/) 介紹的 `COPY` 協定批次寫入 |

產生指令在設定檔所在的目錄執行：

```bash
# 不安裝，直接執行指定版本；第一次要下載並編譯，需要一兩分鐘
go run github.com/sqlc-dev/sqlc/cmd/sqlc@v1.31.1 generate

# 安裝成執行檔之後，每次產生只要不到一秒；執行檔放在 $(go env GOPATH)/bin，那個目錄要在 PATH 裡
go install github.com/sqlc-dev/sqlc/cmd/sqlc@v1.31.1
sqlc generate
```

sqlc v1.31.1 要求 Go 1.26 以上來編譯它自己；手上的 Go 版本較舊時，Go 會依 `GOTOOLCHAIN` 的預設設定自動下載符合的工具鏈，這不影響專案本身用的 Go 版本。版本號寫在指令裡，團隊每個人產生的程式碼才會一致；產生出來的檔案開頭也會記下產生它的 sqlc 版本。

## 產生出來的程式碼

`ListOrdersByCustomer` 產生的函式就是 [10.1 database/sql：連線池、查詢結果的讀取與交易](/go/10-database-access/database-sql/) 讀多列的標準寫法，只是由工具寫出來：

```go
func (q *Queries) ListOrdersByCustomer(ctx context.Context, customerID int64) ([]Order, error) {
	rows, err := q.db.Query(ctx, listOrdersByCustomer, customerID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var items []Order
	for rows.Next() {
		var i Order
		if err := rows.Scan(&i.ID, &i.CustomerID, &i.Amount, &i.Note, &i.OrderedAt); err != nil {
			return nil, err
		}
		items = append(items, i)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return items, nil
}
```

參數與回傳型別依查詢決定：查詢選的欄位剛好是一整張表時，回傳那張表對應的 struct（`Order`，定義在 `models.go`）；選了部分欄位或含運算結果時，另外產生一個 `XxxRow` struct（`TotalByCustomer` 回傳 `[]TotalByCustomerRow`，`sum(o.amount)` 推成 `int64`）；參數超過一個時產生一個 `XxxParams` struct（`CreateCustomerParams{Name, Email}`）。呼叫端的寫法如下：

```go
pool, err := pgxpool.New(ctx, dsn)
q := store.New(pool)

orders, err := q.ListOrdersByCustomer(ctx, 1)
totals, err := q.TotalByCustomer(ctx)
```

```text
[{Name:佳穎 Total:800} {Name:宗翰 Total:250}] <nil>
```

`store.New` 接受的是 `DBTX` 這個介面（`Exec`、`Query`、`QueryRow` 三個方法），`*pgxpool.Pool` 與 `pgx.Tx` 都符合。交易裡執行時用 `q.WithTx(tx)` 取得一個綁在那個交易上的 `*Queries`，交易的開始與收尾仍然照 pgx 那一篇的寫法由程式負責。

## 產生時擋下的錯誤

sqlc 在產生時解析每一段查詢、對照 schema，欄位或表名寫錯就不產生程式碼。把 `GetCustomer` 那一行的 `name` 打成 `nmae` 再產生一次：

```text
# package store
query/orders.sql:8:12: column "nmae" does not exist
```

同樣的錯字在 sqlx 或 pgx 裡是一個要等到執行那一行才會出現的錯誤。換成 sqlc 之後，schema 改了欄位名稱，重新產生時所有用到舊名稱的查詢一起報錯，連帶呼叫端用到的 struct 欄位也跟著改名，Go 編譯器接著指出每一個要改的呼叫位置。

## NULL 與型別對應

pgx v5 的預設對應裡，可以是 NULL 的欄位與 `timestamptz` 都產生成 pgx 的 `pgtype` 型別：

```go
type Order struct {
	ID         int64
	CustomerID int64
	Amount     int32
	Note       pgtype.Text        // 可以是 NULL 的 text
	OrderedAt  pgtype.Timestamptz
}
```

`pgtype` 型別讓產生的 struct 依賴 pgx 的套件，放進 domain 型別或 JSON 回應前都要轉換一次。兩個設定改掉這個預設，加在前面 `sqlc.yaml` 的 `gen.go` 底下、和 `sql_package` 同一層：

```yaml
gen:
  go:
    emit_pointers_for_null_types: true   # 可以是 NULL 的欄位改成指標，例如 *string
    overrides:
      - db_type: "timestamptz"
        go_type: "time.Time"             # NOT NULL 的 timestamptz 對應成 time.Time
```

```go
type Order struct {
	ID         int64
	CustomerID int64
	Amount     int32
	Note       *string
	OrderedAt  time.Time
}
```

依 `db_type` 寫的 override 預設只套用在 NOT NULL 的欄位；可以是 NULL 的 `timestamptz` 欄位要另寫一條加上 `nullable: true` 的 override（例如 `go_type: {type: "time.Time", pointer: true}`），否則仍然是 `pgtype.Timestamptz`。

`integer` 欄位產生的是 `int32`，因為 PostgreSQL 的 `integer` 就是 32 位元；要 `int64` 的話建表時用 `bigint`，或同樣用 `overrides` 指定。

## 選擇性的篩選條件

sqlc 產生的函式裡，SQL 文字在產生時就固定了，「有給最低金額才加這個條件」這類依輸入增減的條件，寫法是把條件寫成「參數是 NULL 時永遠成立」。把下面這段加進 `query/orders.sql` 再重新產生：

```sql
-- name: SearchOrders :many
SELECT id, amount FROM orders
WHERE customer_id = $1
  AND (sqlc.narg(min_amount)::int IS NULL OR amount >= sqlc.narg(min_amount))
ORDER BY id;
```

`sqlc.narg` 宣告一個可以是 NULL 的具名參數。在開了 `emit_pointers_for_null_types` 的設定下，產生的參數 struct 裡它是指標（預設是 `pgtype.Int4`）：

```go
type SearchOrdersParams struct {
	CustomerID int64
	MinAmount  *int32 // nil 代表不篩選
}
```

```text
MinAmount = nil  → [{101 300} {102 500}]
MinAmount = 400  → [{102 500}]
```

這個寫法在條件只有兩三個時清楚好讀。條件多到十幾個、排序欄位也由使用者決定時，`OR` 堆疊的查詢讀起來吃力，資料庫為它選的執行計畫也可能不是最好的；那類查詢交給查詢建構器（Query Builder）或 ORM 的條件串接，和 sqlc 並存（混用的方式見 [10.6 Go 專案的資料庫存取工具選型：GORM、sqlc 與 pgx 的組合](/go/10-database-access/choosing-data-access/)）。

## sqlc 帶進來的工作

sqlc 把 SQL 的錯誤提前到產生時，代價是多了一個產生步驟：

- schema 或查詢改了要重新產生，產生的檔案通常提交進版本控制，審查時看得到產生結果的差異。
- CI 裡跑一次產生，再確認工作目錄沒有差異，可以擋下「改了 SQL 卻忘了重新產生」的提交。
- 產生的程式碼不手動修改；要改行為就改 SQL、設定檔，或在產生的函式外面再包一層。

不想要這個步驟、而查詢以單表增刪查改為主的專案，看的是 [10.5 GORM：model、關聯載入與 ORM 送出的 SQL](/go/10-database-access/gorm/)。
