---
title: "10.5 GORM：model、關聯載入與 ORM 送出的 SQL"
date: 2026-10-06
description: "GORM 的 model 與命名慣例、開著 SQL 記錄寫程式的方式、First 與 Take 的差別與重用變數時多出的條件、找不到資料的判斷、N+1 與 Preload、零值更新被略過、寫入時的預設交易、唯一約束錯誤的判讀，以及 AutoMigrate 在正式環境的限制"
weight: 5
tags: ["go", "database", "gorm", "orm"]
---

這篇整理 [GORM](https://gorm.io/) v1.31.2 搭配 PostgreSQL 方言套件 v1.6.3 的用法（取得套件：`go get gorm.io/gorm@v1.31.2 gorm.io/driver/postgres@v1.6.3`）。範例沿用 [10.1 database/sql：連線池、查詢結果的讀取與交易](/go/10-database-access/database-sql/#範例資料表) 定義的 `customers` 與 `orders` 兩張表。在 [1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/) 的分類裡，GORM 是 ORM：SQL 由方法呼叫組出、查詢結果依命名慣例對映、寫入時預設包一層交易，三件事都由它接手。這篇多數節附上 GORM 實際送出的 SQL，因為用 ORM 的程式碼，要讀的是那些 SQL。

GORM 的 PostgreSQL 方言套件（`gorm.io/driver/postgres`，GORM 稱為 dialector）底層用的是 pgx 的 `database/sql` 驅動，所以 `database/sql` 那一篇的連線池設定照樣適用：`db.DB()` 取得底下的 `*sql.DB`，在它上面呼叫 `SetMaxOpenConns`。

## model 與命名慣例

GORM 用 struct 描述資料表，GORM 稱這種 struct 為 model，欄位與表名依命名慣例推出：

```go
type Customer struct {
	ID        int64     // 名為 ID 的欄位是主鍵
	Name      string
	Email     string
	CreatedAt time.Time // 名為 CreatedAt 的欄位，建立時由 GORM 填入現在時間
	Orders    []Order   // 一對多關聯：orders.customer_id 指向 customers.id
}

type Order struct {
	ID         int64
	CustomerID int64   // 欄位 customer_id
	Amount     int
	Note       *string // 可以是 NULL
	OrderedAt  time.Time
}
```

`Customer` 對到資料表 `customers`（struct 名稱轉成蛇形命名（snake_case）再加複數），`CustomerID` 對到欄位 `customer_id`。名稱不符合慣例時，用 `TableName()` 方法或 `gorm:"column:..."` tag 指定。

`CreatedAt` 這個名稱帶有行為：建立資料時 GORM 用應用程式的時鐘填入現在時間，再放進 `INSERT`，所以資料表上的 `DEFAULT now()` 不會被用到（下面〈寫入時的預設交易〉那一節的語句記錄裡看得到這個值被當成參數送出）。多個服務實例的時鐘不一致時，建立時間的順序就不一定等於寫入的順序；需要依時間排序的地方，改依主鍵排序，或讓資料庫給值。主鍵與資料庫給的時間反映的是配號與交易開始的順序，不是提交的順序，拿它們當「處理到哪裡」的位置會漏掉晚提交的資料（見 [1.18 高頻計數的寫入與彙總：熱點列的鎖、只新增的事件、可以重跑的彙總與重送的事件](/backend/01-database/high-frequency-counting/)〈已處理位置與交易的提交順序〉）。

## GORM 的 SQL 記錄

GORM 的記錄器（logger）設成 `Info` 層級，每一個查詢都會連同耗時與影響列數印出來：

```go
db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{
	Logger: logger.New(log.New(os.Stdout, "", 0), logger.Config{LogLevel: logger.Info}),
})
```

下面的範例為了簡短，直接在 `db` 上呼叫；服務程式裡每個查詢都從 `db.WithContext(ctx)` 開始，理由和 [10.1 database/sql：連線池、查詢結果的讀取與交易](/go/10-database-access/database-sql/) 要求一律用帶 `Context` 的方法相同：請求取消或逾時時，查詢跟著中止。

這個記錄是 GORM 的方法呼叫與實際送出的 SQL 之間的對照，下面多數的 SQL 取自它；實際每個查詢前面還有呼叫位置與耗時一行，文中的輸出只留 SQL。GORM 自動包的 `begin` 與 `commit` 不出現在它的記錄裡，要看交易的那幾節改用 PostgreSQL 的語句記錄（`log_statement = 'all'`）。兩種記錄各記到什麼、正式環境怎麼開，見 [Query Log](/backend/knowledge-cards/query-log/)。

## 查一筆：First、Take 與重用的變數

```go
var c Customer
db.First(&c, 1)
db.Take(&c, 1)
```

```text
SELECT * FROM "customers" WHERE "customers"."id" = 1 ORDER BY "customers"."id" LIMIT 1
SELECT * FROM "customers" WHERE "customers"."id" = 1 AND "customers"."id" = 1 LIMIT 1
```

`First` 在條件之外加上依主鍵排序，取排序後的第一筆；`Take` 不排序，取資料庫回傳的任何一筆。依唯一欄位查一筆時兩者結果相同，`Take` 省掉排序。

第二行多了一個重複的 `"customers"."id" = 1`，原因是 `Take` 傳入的 `c` 已經被 `First` 填過，主鍵是 1，**GORM 會把傳入物件上已有的主鍵加進條件**。重用同一個變數去查另一筆時，這個行為會讓查詢靜默地查不到：

```go
db.Where("email = ?", "jiaying@example.com").First(&c) // c.ID 還是 1
db.First(&c, 999)                                     // 想查 id 999
```

```text
SELECT * FROM "customers" WHERE email = 'jiaying@example.com' AND "customers"."id" = 1 ORDER BY "customers"."id" LIMIT 1
SELECT * FROM "customers" WHERE "customers"."id" = 999 AND "customers"."id" = 1 ORDER BY "customers"."id" LIMIT 1
```

第二個查詢的條件是 `id = 999 AND id = 1`，永遠不會有結果。每一次查詢用一個新宣告的變數，就不會帶到前一次留下的主鍵。

## 找不到資料的判斷

`First`、`Take`、`Last` 查不到時回傳 `gorm.ErrRecordNotFound`；`Find` 查不到時不回傳錯誤，只是 slice 是空的：

```go
err := db.First(&c, 999).Error
// record not found, errors.Is(err, gorm.ErrRecordNotFound) == true

var cs []Customer
err = db.Where("id = ?", 999).Find(&cs).Error
// err == nil, len(cs) == 0
```

用 `Find` 加上一個 struct（不是 slice）去查一筆，查不到時同樣不回錯誤，struct 保持零值；要「找不到就報錯」的地方用 `First` 或 `Take`。

## 關聯：迴圈裡的查詢與 Preload

逐一讀每個顧客的訂單時，在迴圈裡查就是 N+1：一次查顧客，再每個顧客一次查訂單。

```go
var all []Customer
db.Find(&all)
for i := range all {
	db.Where("customer_id = ?", all[i].ID).Find(&all[i].Orders)
}
```

```text
SELECT * FROM "customers"
SELECT * FROM "orders" WHERE customer_id = 1
SELECT * FROM "orders" WHERE customer_id = 2
SELECT * FROM "orders" WHERE customer_id = 3
```

顧客有一千個就是一千零一次查詢，每一次都是一次資料庫來回（round trip）（N+1 的成本與判讀見 [1.13 應用層查詢反模式與 Query 預算](/backend/01-database/query-anti-patterns/)）。`Preload` 改成兩次查詢，第二次用 `IN` 一次取回全部顧客的訂單，再由 GORM 依 `customer_id` 分配回各個顧客：

```go
var all []Customer
db.Preload("Orders").Find(&all)
```

```text
SELECT * FROM "orders" WHERE "orders"."customer_id" IN (1,2,3)
SELECT * FROM "customers"
```

（記錄的順序是 GORM 印出的順序，執行時先查顧客、再依取回的主鍵查訂單。）GORM 沒有存取屬性時自動查詢的延遲載入（lazy loading，Eloquent 與 SQLAlchemy 有，對照見 [1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/)〈ORM 送出的查詢次數：延遲載入與 N+1〉），沒有 `Preload` 的關聯欄位就是空的；所以在 GORM 裡，N+1 的來源是程式自己在迴圈裡查，而不是框架代查，GORM 的 SQL 記錄裡同一個形狀的查詢重複出現 N 次就是訊號。

## 更新：零值欄位與 Updates

用 struct 更新時，GORM 只寫入**非零值**的欄位，因為它分不出「欄位是 0」與「沒有設定這個欄位」：

```go
var o Order
db.Take(&o, 103)
db.Model(&o).Updates(Order{Amount: 0})                // 想把金額改成 0
db.Model(&o).Updates(map[string]any{"amount": 0})
```

GORM 的記錄裡，第一個 `Updates` 沒有任何 `UPDATE`；第二個才有：

```text
UPDATE "orders" SET "amount"=0 WHERE "id" = 103
```

PostgreSQL 的語句記錄（`log_statement`）顯示第一個 `Updates` 送出了一組空的交易（`begin` 之後直接 `commit`；GORM 的寫入預設包在交易裡，見〈寫入時的預設交易〉），沒有錯誤、影響零列，程式完全不會發現金額沒有改。範例的 `Order` 沒有 `UpdatedAt`；model 帶 `UpdatedAt`（嵌入 `gorm.Model` 就有，見 [10.6 GORM 的 gorm.Model、軟刪除與 Save：慣例欄位加上的查詢條件與整列寫回](/go/10-database-access/gorm-model-and-soft-delete/)）時，GORM 仍會送出只更新 `updated_at` 的 `UPDATE`，影響列數是 1，看起來像更新成功，而金額照樣沒改。和 Eloquent、SQLAlchemy 這類追蹤變更的 ORM 不同（對照見 [1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/)〈ORM 寫回哪些欄位：變更追蹤、全部欄位與零值〉）。要寫入零值（`0`、`""`、`false`）時，用 map、用 `Select("amount")` 指定欄位，或用 `Update("amount", 0)` 更新單一欄位。可以是 NULL 的欄位宣告成指標（`*int`），`nil` 是「不寫」、指向 0 的指標是「寫成 0」，兩者就分得開。

## 寫入時的預設交易

GORM 的每一個建立、更新、刪除，預設都包在一個交易裡。在 PostgreSQL 開啟語句記錄（`log_statement = 'all'`）就看得到：

```text
LOG:  statement: begin
LOG:  execute stmtcache_230b...: INSERT INTO "customers" ("name","email","created_at") VALUES ($1,$2,$3) RETURNING "id"
DETAIL:  Parameters: $1 = '新顧客', $2 = 'new@example.com', $3 = '2026-10-06 04:59:33.855131+00'
LOG:  statement: commit
```

`stmtcache_` 開頭的名字是 pgx 在連線上快取的預先解析查詢（見 [Prepared Statement](/backend/knowledge-cards/prepared-statement/)）。一個 `INSERT` 變成三次來回。GORM 這樣做，是因為一次 `Create` 可能連帶寫入關聯的資料（建立顧客時一併建立訂單），包在交易裡才會一起成功或一起失敗。寫入沒有關聯、或交易由程式自己用 `db.Transaction` 控制時，這一層是多出來的，`gorm.Config{SkipDefaultTransaction: true}` 關掉它之後，同樣的 `INSERT` 只剩一行，前後沒有 `begin` 與 `commit`。

這兩次多出來的來回在一般的增刪查改流量下不構成瓶頸，在寫入密集的路徑上才量得出差別；而關掉它的前提是那條路徑沒有依賴它的連帶寫入。所以這個預設值是否要關，取決於壓測或正式環境的延遲數字有沒有指向它。

`db.Transaction(func(tx *gorm.DB) error { ... })` 是程式自己控制的交易，回傳 `nil` 提交、回傳錯誤撤銷；函式裡每一個查詢都要用參數 `tx`，用外面的 `db` 會從池裡另取一條連線、跑在交易之外（交易物件怎麼傳進各個 repository、誤用時交易外的寫入卡在交易持有的鎖上，見 [Transaction Propagation](/backend/knowledge-cards/transaction-propagation/)），和 [10.1 database/sql：連線池、查詢結果的讀取與交易](/go/10-database-access/database-sql/)〈交易：BeginTx、defer Rollback 與 Commit〉是同一個規則。

## 錯誤判讀：唯一約束

`jiaying@example.com` 已經是範例資料裡佳穎的 email，而 `customers_email_key` 是 `customers.email` 上的唯一約束。建立的資料違反唯一約束時，GORM 回傳的錯誤裡包著 pgx 的 `*pgconn.PgError`，用 `errors.As` 取出之後讀約束名稱：

```go
err := db.Create(&Customer{Name: "重複", Email: "jiaying@example.com"}).Error

var pgErr *pgconn.PgError
if errors.As(err, &pgErr) && pgErr.ConstraintName == "customers_email_key" {
	// email 已被使用
}
```

`gorm.Config{TranslateError: true}` 讓 GORM 把資料庫錯誤轉成自己的錯誤值，唯一約束違反變成 `gorm.ErrDuplicatedKey`。實測轉換之後 `errors.As` 仍然取得到 `*pgconn.PgError`：

```text
TranslateError: duplicated key not allowed: ERROR: duplicate key value violates unique constraint "customers_email_key" (SQLSTATE 23505) true true
```

`ErrDuplicatedKey` 讓程式不必認得 PostgreSQL 的錯誤代碼，換資料庫時判斷式不用改；它只說「有唯一約束被違反」，一張表有好幾個唯一約束時，要回報是哪一個，仍然要讀約束名稱。

## AutoMigrate 在正式環境的限制

`db.AutoMigrate(&Customer{})` 依 model 建表、補上缺少的欄位與索引。它方便在開發初期快速建表，而它只往「讓資料表容得下這個 struct」的方向改。下面先用一版 model 建表，再把欄位 `Rate` 改名成 `Discount`、`Code` 加上長度限制：

```go
type Coupon struct {
	ID   int64
	Code string
	Rate int
}

type CouponV2 struct {
	ID       int64
	Code     string `gorm:"size:20"`
	Discount int
}

func (CouponV2) TableName() string { return "coupons" }

db.AutoMigrate(&Coupon{})
db.AutoMigrate(&CouponV2{})
```

以 `SELECT column_name, data_type, character_maximum_length FROM information_schema.columns WHERE table_name = 'coupons'` 讀出欄位，整理成一行：

```text
[id bigint code character varying(20) rate bigint discount bigint]
```

改名被當成新增一個欄位 `discount`，舊的 `rate` 和它的資料都留著；`code` 的型別直接被改成 `varchar(20)`。GORM 送出的是 `ALTER ... TYPE varchar(20) USING code::varchar(20)`，PostgreSQL 的明確轉型會把超過 20 個字元的值直接截斷，所以表裡已經有較長的資料時，這一步照樣成功、不報錯，被截掉的資料就此遺失。整個過程沒有一份檔案記錄它做了什麼，也沒有退回的方法。

所以正式環境的 schema 交給版本化的 migration 工具（golang-migrate、goose、Atlas）：每一次改動是一份可以審查的檔案，依序套用，可以在測試環境先跑過。GORM 只負責讀寫，model 跟著 migration 改。版本化 migration 的流程與相容性規則見 [資料庫 transaction 與 schema migration](/go-advanced/07-distributed-operations/database-transactions/)。

## GORM 的慣例：主鍵、零值、CreatedAt 與預設交易

主鍵條件、零值更新、`CreatedAt` 與預設交易這幾節的現象有同一個來源：程式碼寫的是方法呼叫，實際行為由 GORM 的慣例決定——傳入物件上的主鍵、零值的含義、`CreatedAt` 這個欄位名稱、寫入時的交易。慣例讓常見的增刪查改很短，而每一條慣例都要先知道它存在，才知道程式碼底下發生了什麼。其中三條在 GORM 的 SQL 記錄裡看得到：主鍵條件多出來、零值欄位沒有出現在 `UPDATE` 裡、`INSERT` 帶著應用程式填的建立時間；預設交易的 `begin` 與 `commit` 要開資料庫的語句記錄（`log_statement`）才看得到。

`gorm.Model` 帶進來的 `UpdatedAt` 與 `DeletedAt`、軟刪除替每個查詢加的條件，以及 `Save` 寫回全部欄位的行為，是同一類由欄位名稱與型別決定的慣例，見 [10.6 GORM 的 gorm.Model、軟刪除與 Save：慣例欄位加上的查詢條件與整列寫回](/go/10-database-access/gorm-model-and-soft-delete/)。

需要報表、多表聚合這類固定而複雜的查詢時，GORM 的 `Raw` 可以直接寫 SQL 並對映回 struct；這類查詢多的專案，也常把它們交給 [10.4 sqlc：從 SQL 產生型別安全的 Go 程式碼](/go/10-database-access/sqlc/)，兩者怎麼並存見 [10.7 Go 專案的資料庫存取工具選型：GORM、sqlc 與 pgx 的組合](/go/10-database-access/choosing-data-access/)。
