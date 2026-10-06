---
title: "10.6 GORM 的 gorm.Model、軟刪除與 Save：慣例欄位加上的查詢條件與整列寫回"
date: 2026-10-06
description: "gorm.Model 帶進來的 ID、CreatedAt、UpdatedAt、DeletedAt 與 UpdatedAt 的更新時機、DeletedAt 讓刪除變成 UPDATE 並替每個查詢加上條件、不經過那個條件的路徑（Raw、其他服務）、軟刪除與關聯載入、外鍵、唯一約束的衝突與部分索引、無條件刪除的保護，以及 Save 寫回全部欄位、找不到主鍵時改成 upsert 而把已刪除的列寫回或恢復"
weight: 6
tags: ["go", "database", "gorm", "orm"]
---

這篇接著 [10.5 GORM：model、關聯載入與 ORM 送出的 SQL](/go/10-database-access/gorm/)，整理 GORM v1.31.2 的 `gorm.Model`、軟刪除（soft delete）與 `Save` 的實際行為。三者的共同點是 GORM 在組 SQL 時替程式加上條件或欄位：`gorm.Model` 與軟刪除的行為由欄位的**名稱或型別**觸發，GORM 看到 `UpdatedAt`、`DeletedAt` 就替寫入補欄位、替每個查詢加條件；`Save` 的行為來自它的寫回規則，把 struct 的每個欄位都寫回去，找不到那一列時再改成另一種寫入。這些條件與欄位都不會出現在程式碼上，只出現在 GORM 送出的 SQL 裡，所以本篇每一節都附上 GORM 的 SQL 記錄；審查用 `gorm.Model` 與 `Save` 的程式時，對照的也是開著記錄跑出來的語句（GORM 的 SQL 記錄與 PostgreSQL 語句記錄各記到什麼，見 [Query Log 知識卡](/backend/knowledge-cards/query-log/)）。

範例沿用 [10.1 database/sql：連線池、查詢結果的讀取與交易](/go/10-database-access/database-sql/#範例資料表) 的 `customers` 與 `orders` 兩張表：顧客佳穎（id 1，有兩張訂單）、宗翰（id 2，有一張訂單）、雅文（id 3，沒有訂單）。每一節開始時，資料都重置成剛執行完 10.1 的建表 SQL、再套用〈gorm.Model 的欄位：ID、CreatedAt、UpdatedAt 與 DeletedAt〉那一節的 migration 之後的狀態；同一節裡的程式片段接續前一段的結果往下執行。程式裡的 `db` 是 10.5 用 `gorm.Open` 開好的 `*gorm.DB`，記錄器設成 `logger.Info`；`Customer` 是〈gorm.Model 的欄位：ID、CreatedAt、UpdatedAt 與 DeletedAt〉那一節嵌入 `gorm.Model` 的 struct。軟刪除本身是不分語言的做法，Laravel 等框架的對應寫法與共通的風險見 [Soft Delete 知識卡](/backend/knowledge-cards/soft-delete/)。

## gorm.Model 的欄位：ID、CreatedAt、UpdatedAt 與 DeletedAt

`gorm.Model` 是 GORM 提供的一個 struct，原始碼只有四個欄位：

```go
type Model struct {
	ID        uint `gorm:"primarykey"`
	CreatedAt time.Time
	UpdatedAt time.Time
	DeletedAt DeletedAt `gorm:"index"`
}
```

把它嵌入自己的 model，四個欄位與它們的行為就一起帶進來：

```go
type Customer struct {
	gorm.Model // id、created_at、updated_at、deleted_at
	Name   string
	Email  string
	Orders []Order
}
```

`ID` 是主鍵，`CreatedAt` 在建立時由 GORM 用應用程式的時鐘填入（見 [10.5 GORM：model、關聯載入與 ORM 送出的 SQL](/go/10-database-access/gorm/)〈model 與命名慣例〉），`UpdatedAt` 在每次更新時填入，`DeletedAt` 讓這個 model 改用軟刪除。範例資料表原本沒有 `updated_at` 與 `deleted_at`，用 migration 補上：

```sql
ALTER TABLE customers ADD COLUMN updated_at timestamptz, ADD COLUMN deleted_at timestamptz;
CREATE INDEX customers_deleted_at_idx ON customers (deleted_at);
```

`deleted_at` 上的索引對應 `gorm.Model` 裡的 `gorm:"index"`：每個查詢都會帶 `deleted_at IS NULL`，而 `AutoMigrate` 建表時也會建這個索引；schema 交給 migration 管理時（理由見 [10.5 GORM：model、關聯載入與 ORM 送出的 SQL](/go/10-database-access/gorm/)〈AutoMigrate 在正式環境的限制〉），migration 裡要自己建這個索引。

`ID` 的型別是 `uint`，對到資料表的 `bigint` 讀寫都正常；需要 `int64`（例如和其他程式共用的型別）時，不嵌入 `gorm.Model`，把需要的欄位自己寫進 struct，行為由欄位名稱與型別決定，一樣會生效。

## UpdatedAt 的更新時機

`Update`、`Updates` 與 `Save` 都會把 `updated_at` 設成現在時間並放進 `UPDATE`；`UpdateColumn` 與 `UpdateColumns` 只寫指定的欄位，不更新 `updated_at`，也不執行 model 上的 hook（`BeforeUpdate` 這類 GORM 在寫入前後自動呼叫的方法）：

```go
db.Model(&Customer{Model: gorm.Model{ID: 2}}).UpdateColumn("name", "宗翰 C")
db.Model(&Customer{Model: gorm.Model{ID: 2}}).Update("name", "宗翰 D")
```

```text
UPDATE "customers" SET "name"='宗翰 C' WHERE "customers"."deleted_at" IS NULL AND "id" = 2
UPDATE "customers" SET "name"='宗翰 D',"updated_at"='2026-10-06 14:27:15.524' WHERE "customers"."deleted_at" IS NULL AND "id" = 2
```

兩個 `UPDATE` 都帶著 `deleted_at IS NULL`，那是〈軟刪除：Delete 變成 UPDATE〉那一節的 `DeletedAt` 加上的。`updated_at` 常被拿來當增量同步的依據（「拿出上次同步之後改過的列」），用 `UpdateColumn` 改的資料不會被這種同步取出。GORM 的軟刪除也一樣：`Delete` 送出的是 `UPDATE "customers" SET "deleted_at"=... WHERE ...`，只寫 `deleted_at`、不寫 `updated_at`，所以依 `updated_at` 的同步收不到刪除，要另外用 `Unscoped` 取出 `deleted_at` 晚於上次同步的列（Laravel 的軟刪除會一併更新 `updated_at`，對照見 [Soft Delete 知識卡](/backend/knowledge-cards/soft-delete/)）。

## 軟刪除：Delete 變成 UPDATE

model 有 `gorm.DeletedAt` 型別的欄位時，`Delete` 送出的是 `UPDATE`：

```go
db.Delete(&Customer{}, 3)
```

```text
UPDATE "customers" SET "deleted_at"='2026-10-06 14:26:48.627' WHERE "customers"."id" = 3 AND "customers"."deleted_at" IS NULL
```

雅文那一列還在表裡，只是 `deleted_at` 有了值。之後這個 model 的每一個查詢都多一個條件，查不到雅文：

```go
var c Customer
err := db.First(&c, 3).Error // record not found

var n, nAll int64
db.Model(&Customer{}).Count(&n)
db.Unscoped().Model(&Customer{}).Count(&nAll) // n = 2, nAll = 3
```

```text
SELECT * FROM "customers" WHERE "customers"."id" = 3 AND "customers"."deleted_at" IS NULL ORDER BY "customers"."id" LIMIT 1
SELECT count(*) FROM "customers" WHERE "customers"."deleted_at" IS NULL
SELECT count(*) FROM "customers"
```

`Unscoped()` 取消這個條件，用在要看到已刪除資料的地方（後台的回收區、稽核）；`db.Unscoped().Delete(&Customer{}, 3)` 送出 `DELETE`，把那一列從表中移除。

對已刪除的列再刪一次、或更新它，條件裡的 `deleted_at IS NULL` 讓 `UPDATE` 影響零列，GORM 不回報錯誤：

```go
db.Delete(&Customer{}, 3)                                       // 雅文已經刪除，再刪一次
db.Model(&Customer{Model: gorm.Model{ID: 3}}).Update("name", "x") // 更新已刪除的列
```

```text
UPDATE "customers" SET "deleted_at"='2026-10-06 14:26:48.747' WHERE "customers"."id" = 3 AND "customers"."deleted_at" IS NULL
UPDATE "customers" SET "name"='x',"updated_at"='2026-10-06 14:26:48.749' WHERE "customers"."deleted_at" IS NULL AND "id" = 3
```

兩個呼叫的 `Error` 都是 `nil`、`RowsAffected` 都是 0。「改一筆不存在或已刪除的資料」要回報給呼叫端時，程式要自己檢查 `RowsAffected`。

## 不經過軟刪除條件的路徑

這個條件是 GORM 組 SQL 時加上的，所以 GORM 沒有參與組 SQL 的地方都看得到已刪除的列。`Raw` 送出的是程式寫的那一段 SQL，原樣執行：

```go
db.Delete(&Customer{}, 3) // 軟刪除雅文

var names []string
db.Raw("SELECT name FROM customers ORDER BY id").Scan(&names)
// [佳穎 宗翰 雅文]
```

已經軟刪除的雅文仍在結果裡。同樣的情形出現在用 sqlc 寫的報表查詢（混用方式見 [10.7 Go 專案的資料庫存取工具選型：GORM、sqlc 與 pgx 的組合](/go/10-database-access/choosing-data-access/)）、共用這個資料庫的其他服務，以及直接連進資料庫查問題的人。專案決定用軟刪除時，這些路徑的每一段 SQL 都要自己寫 `deleted_at IS NULL`，或由資料庫端提供只含未刪除列的 view 給報表與其他服務使用（做法見 [Soft Delete 知識卡](/backend/knowledge-cards/soft-delete/)）；頁面上的數字由 GORM 算、報表由手寫 SQL 算，兩邊差的就是已刪除的列。

## 軟刪除與關聯：關聯載入的結果與外鍵檢查

軟刪除佳穎（佳穎有兩張訂單）之後，從訂單載入顧客：

訂單的 model 多一個 `Customer` 欄位，GORM 依它與 `CustomerID` 知道每張訂單屬於哪位顧客：

```go
type Order struct {
	ID         int64
	CustomerID int64
	Customer   Customer // 所屬的顧客
	Amount     int
	Note       *string
	OrderedAt  time.Time
}

db.Delete(&Customer{}, 1)

var orders []Order
db.Joins("Customer").Order("orders.id").Find(&orders)
```

```text
SELECT "orders"."id", ... ,"Customer"."name" AS "Customer__name", ... FROM "orders" LEFT JOIN "customers" "Customer" ON "orders"."customer_id" = "Customer"."id" AND "Customer"."deleted_at" IS NULL ORDER BY orders.id
order 101 customer_id=1 Customer.ID=0 Name=""
order 102 customer_id=1 Customer.ID=0 Name=""
order 103 customer_id=2 Customer.ID=2 Name="宗翰"
```

GORM 把條件加在 `LEFT JOIN` 的 `ON` 上，所以訂單照樣查得到，關聯的顧客則是零值；`Preload("Customer")` 的結果相同：它另外送出一個查顧客的查詢（`WHERE id IN (1,2)`），在那個查詢上加同一個條件。畫面上會出現「訂單的顧客名稱是空白」，而 `customer_id` 仍然是 1。這筆資料的處理方式要由業務決定：訂單顯示「已刪除的顧客」、改用 `Unscoped` 載入顧客，或刪除顧客時一併處理訂單，三者可以擇一，也可以並用（例如畫面用 `Unscoped` 載入、再標示已刪除）。

`orders.customer_id` 上的外鍵檢查只在 `customers` 的列被 `DELETE` 或主鍵被改時動作，而軟刪除是 `UPDATE`，所以佳穎的軟刪除成功了，外鍵沒有替程式做這個決定；之後要永久刪除這位顧客，外鍵才擋下來：

```go
err := db.Unscoped().Delete(&Customer{}, 1).Error
```

```text
DELETE FROM "customers" WHERE "customers"."id" = 1
ERROR: update or delete on table "customers" violates foreign key constraint "orders_customer_id_fkey" on table "orders" (SQLSTATE 23503)
```

## 軟刪除與唯一約束：刪掉再建立同一個 email

雅文被軟刪除之後，用同一個 email 重新建立顧客：

```go
db.Delete(&Customer{}, 3)
err := db.Create(&Customer{Name: "雅文", Email: "yawen@example.com"}).Error
```

```text
ERROR: duplicate key value violates unique constraint "customers_email_key" (SQLSTATE 23505)
```

`customers_email_key` 這個唯一約束涵蓋表裡的每一列，包括已刪除的那一列。PostgreSQL 的做法是刪掉這個約束，另外建一個只涵蓋未刪除的列的唯一索引（部分索引，partial index；索引本身的取捨見 [PostgreSQL Index Selection：B-tree / GIN / GiST / BRIN / Hash 對應 workload 的決策樹](/backend/01-database/vendors/postgresql/index-selection/)〈Partial Index：條件式 index 救 storage〉）：

```sql
ALTER TABLE customers DROP CONSTRAINT customers_email_key;
CREATE UNIQUE INDEX customers_email_active_key ON customers (email) WHERE deleted_at IS NULL;
```

換上之後，刪掉再建立同一個 email 成功；兩個未刪除的顧客用同一個 email 時仍然報錯，`*pgconn.PgError` 的 `ConstraintName` 是索引的名字 `customers_email_active_key`，依約束名稱回報錯誤的程式要跟著改名（判讀方式見 [10.5 GORM：model、關聯載入與 ORM 送出的 SQL](/go/10-database-access/gorm/)〈錯誤判讀：唯一約束〉）。

部分索引會影響 upsert（`INSERT` 遇到唯一衝突時改成更新既有那一列的寫法，PostgreSQL 寫成 `INSERT ... ON CONFLICT`）。GORM 的 `clause.OnConflict` 只寫衝突欄位時，PostgreSQL 找不到與它相符的唯一約束：

```go
db.Clauses(clause.OnConflict{
	Columns:   []clause.Column{{Name: "email"}},
	DoUpdates: clause.AssignmentColumns([]string{"name"}),
}).Create(&Customer{Name: "佳穎2", Email: "jiaying@example.com"})
```

```text
INSERT INTO "customers" (...) VALUES (...) ON CONFLICT ("email") DO UPDATE SET "name"="excluded"."name" RETURNING "id"
ERROR: there is no unique or exclusion constraint matching the ON CONFLICT specification (SQLSTATE 42P10)
```

`ON CONFLICT` 的目標要寫出和部分索引相同的條件，PostgreSQL 才認得它；`clause.OnConflict` 的 `TargetWhere` 就是那個條件：

```go
db.Clauses(clause.OnConflict{
	Columns:     []clause.Column{{Name: "email"}},
	TargetWhere: clause.Where{Exprs: []clause.Expression{clause.Expr{SQL: "deleted_at IS NULL"}}},
	DoUpdates:   clause.AssignmentColumns([]string{"name"}),
}).Create(&Customer{Name: "佳穎2", Email: "jiaying@example.com"})
```

```text
INSERT INTO "customers" (...) VALUES (...) ON CONFLICT ("email")  WHERE deleted_at IS NULL DO UPDATE SET "name"="excluded"."name" RETURNING "id"
```

MySQL 沒有部分索引，「只對未刪除的列要求 email 唯一」要改用產生欄位（generated column）或複合唯一索引，兩種做法見 [Soft Delete 知識卡](/backend/knowledge-cards/soft-delete/)。

## 沒有條件的 Delete 與 Update

`Delete` 或 `Update` 沒有任何條件時，GORM 拒絕執行並回傳 `gorm.ErrMissingWhereClause`：

```go
err := db.Delete(&Customer{}).Error // WHERE conditions required
```

GORM 的記錄器（logger）印出了它組好的 `UPDATE "customers" SET "deleted_at"=... WHERE "customers"."deleted_at" IS NULL`，而 PostgreSQL 的語句記錄（`log_statement`，見 [Query Log 知識卡](/backend/knowledge-cards/query-log/)）裡沒有這一句：檢查發生在送出之前。

這個檢查看的是「有沒有條件」，不是「條件會挑出幾列」。條件寫成永遠成立的式子，檢查就通過：

```go
db.Where("1 = 1").Delete(&Customer{})
```

```text
UPDATE "customers" SET "deleted_at"='2026-10-06 14:42:48.947' WHERE 1 = 1 AND "customers"."deleted_at" IS NULL
```

影響三列，表裡的顧客全部被軟刪除。依使用者輸入組條件的程式常先放一個 `1 = 1` 再逐一串接 `AND`，篩選條件全部留空時組出的就是這一句，GORM 的檢查照樣放行；確實要對整張表操作時，GORM 的做法是 `Session(&gorm.Session{AllowGlobalUpdate: true})`，讓這個意圖寫在程式碼上。

## Save：寫回全部欄位

`Save` 把 struct 的每一個欄位都寫回去，包括沒有改的：

```go
var a Customer
db.First(&a, 2)
a.Name = "宗翰（改）"
db.Save(&a)
```

```text
UPDATE "customers" SET "created_at"='2026-10-06 14:27:11.427',"updated_at"='2026-10-06 14:27:15.442',"deleted_at"=NULL,"name"='宗翰（改）',"email"='zonghan@example.com' WHERE "customers"."deleted_at" IS NULL AND "id" = 2
```

`created_at`、`email` 都用讀出時的值再寫一次。兩個請求同時讀出同一位顧客、各改一個欄位、各自 `Save`，後寫的那一個會用它讀出時的舊值蓋掉前一個的修改。下面的 `p` 與 `q` 代表兩個請求各自讀出的宗翰，讀出時的名字是上一個示範寫進去的「宗翰（改）」：

```go
var p, q Customer
db.First(&p, 2)
db.First(&q, 2)
p.Name = "宗翰 A"
db.Save(&p)
q.Email = "zonghan.b@example.com"
db.Save(&q)
```

```text
UPDATE "customers" SET ...,"name"='宗翰 A',"email"='zonghan@example.com' WHERE "customers"."deleted_at" IS NULL AND "id" = 2
UPDATE "customers" SET ...,"name"='宗翰（改）',"email"='zonghan.b@example.com' WHERE "customers"."deleted_at" IS NULL AND "id" = 2
```

再讀一次這位顧客，名字是「宗翰（改）」：`p` 改的名字被 `q` 帶著的舊名字蓋掉了，兩個呼叫都沒有錯誤。這種情形叫遺失更新（lost update），Django 的 `save()` 預設也是寫回全部欄位（對照見 [1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/)〈ORM 寫回哪些欄位：變更追蹤、全部欄位與零值〉）。只改幾個欄位時，用 `Updates` 傳 map，或 `Select` 指定欄位，讓 `UPDATE` 只寫那幾個欄位；同一個欄位也可能被兩個請求同時改時，要另外加樂觀鎖（optimistic locking：`UPDATE` 的條件多帶一個讀出時的版本值，影響零列就代表被別人改過；它和悲觀鎖的取捨見 [1.3 Transaction 與一致性邊界](/backend/01-database/transaction-boundary/)〈Optimistic vs Pessimistic Locking〉）。另一個做法是把讀出與寫回放進 repeatable read 的交易：兩個交易時間重疊、改到同一列時，後寫入的那一個在它的 `UPDATE` 上失敗（`could not serialize access due to concurrent update`，SQLSTATE `40001`），程式重試，而不是默默蓋掉。

### 找不到主鍵時改成 upsert

`Save` 的 `UPDATE` 影響零列時，GORM 接著送出一個 `INSERT ... ON CONFLICT ("id") DO UPDATE`。GORM `Save` 原始碼裡改用 upsert 的條件是「更新沒有錯誤、影響零列、沒有用 `Select` 指定欄位」。拿一個不存在的主鍵 999 去 `Save`：

```go
g := Customer{Model: gorm.Model{ID: 999}, Name: "幽靈", Email: "ghost@example.com"}
db.Save(&g)
```

```text
UPDATE "customers" SET "created_at"='0000-00-00 00:00:00',...,"name"='幽靈',"email"='ghost@example.com' WHERE "customers"."deleted_at" IS NULL AND "id" = 999
INSERT INTO "customers" ("created_at","updated_at","deleted_at","name","email","id") VALUES (...,999) ON CONFLICT ("id") DO UPDATE SET "updated_at"=...,"deleted_at"="excluded"."deleted_at","name"="excluded"."name","email"="excluded"."email" RETURNING "id"
```

表裡多了一位 id 999 的顧客。主鍵來自請求內容的程式（例如 `PUT /customers/999` 直接把 body 解成 struct 再 `Save`），會因此建立一筆新資料。

同一個機制碰上軟刪除時，`UPDATE` 的 `deleted_at IS NULL` 讓已刪除的列影響零列，接下來的 upsert 用主鍵衝突寫進去，那個條件不在 upsert 裡。實測用 `Unscoped` 讀出已刪除的雅文、改名字、`Save`：

```go
db.Delete(&Customer{}, 3)
var d Customer
db.Unscoped().First(&d, 3)
d.Name = "雅文（改）"
db.Save(&d)
```

```text
UPDATE "customers" SET ...,"deleted_at"='2026-10-06 14:27:15.513',"name"='雅文（改）',... WHERE "customers"."deleted_at" IS NULL AND "id" = 3
INSERT INTO "customers" (...,"id") VALUES (...,3) ON CONFLICT ("id") DO UPDATE SET ...,"name"="excluded"."name",... RETURNING "id"
```

雅文那一列仍然是已刪除的狀態，名字卻被改掉了。upsert 寫入的 `deleted_at` 是 struct 上帶的值，這裡的 struct 是從資料庫讀出來的，所以帶著原本的刪除時間。struct 若是從請求內容組出來的，`DeletedAt` 是零值，upsert 就把 `deleted_at` 寫成 NULL，已刪除的列被恢復：

```go
// 雅文仍是上一段的已刪除狀態
in := Customer{Model: gorm.Model{ID: 3}, Name: "雅文", Email: "yawen@example.com"} // 從請求內容組出的 struct
db.Save(&in)
```

```text
INSERT INTO "customers" ("created_at","updated_at","deleted_at","name","email","id") VALUES (...,NULL,'雅文','yawen@example.com',3) ON CONFLICT ("id") DO UPDATE SET ...,"deleted_at"="excluded"."deleted_at",... RETURNING "id"
SELECT * FROM "customers" WHERE "customers"."id" = 3 AND "customers"."deleted_at" IS NULL ORDER BY "customers"."id" LIMIT 1
```

之後的 `First(&c, 3)` 查得到雅文，使用者刪掉的資料被一次編輯請求恢復成未刪除。

`Save` 適合的情形是 struct 本身就是那一列的完整內容、而且確定這一列存在且沒有被刪除（例如在交易裡用 `SELECT ... FOR UPDATE` 鎖住那一列再讀出、修改、寫回；只是放進交易而沒有鎖，PostgreSQL 預設的 read committed 照樣擋不住 `p` 與 `q` 互相蓋掉的遺失更新）；其他情形用 `Create` 建立、用 `Updates` 或 `Update` 修改，兩者都不會在找不到時建立資料。依主鍵同步外部資料的匯入工作，要的正是「有就更新、沒有就建立」，這時與其依賴 `Save` 的隱含行為，明寫 `clause.OnConflict` 讓意圖留在程式碼上。
