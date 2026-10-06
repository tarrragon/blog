---
title: "10.6 Go 專案的資料庫存取工具選型：GORM、sqlc 與 pgx 的組合"
date: 2026-10-06
description: "把語言無關的資料存取選型軸套到 Go 的工具上：驅動入口選 pgx 原生介面還是 database/sql、主力選 GORM 還是 sqlc、為什麼用 GORM 與用 sqlc 的專案都把 schema 交給 migration 工具、常見的混用組合，以及混用時交易能不能共用"
weight: 6
tags: ["go", "database", "gorm", "sqlc", "pgx"]
---

這篇把 [1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/) 的選型軸套到 Go 的工具上。那一篇給的是跨語言的軸（schema 的權威、查詢的形狀、框架的整合程度、審查要看到什麼）；Go 的選型多出兩件事要決定：驅動入口用哪一種，以及沒有主導框架時主力工具由誰來定；主力工具的選擇另外加上團隊背景這一軸。本模組前面各篇示範的行為是這篇的材料：[10.1 database/sql：連線池、查詢結果的讀取與交易](/go/10-database-access/database-sql/)、[10.2 pgx：PostgreSQL 驅動的原生介面、連線池與 COPY 大量寫入](/go/10-database-access/pgx/)、[10.3 sqlx：手寫 SQL 加上 struct 對映](/go/10-database-access/sqlx/)、[10.4 sqlc：從 SQL 產生型別安全的 Go 程式碼](/go/10-database-access/sqlc/)、[10.5 GORM：model、關聯載入與 ORM 送出的 SQL](/go/10-database-access/gorm/)。

## Go 資料庫存取工具的生態現況

Go 沒有一個像 Laravel 或 Django 那樣把 ORM、驗證、後台整合在一起的主導框架，資料庫存取是各專案自己挑的。從 GitHub 的星數（2026 年 10 月查詢）看各工具受到的關注：GORM 約四萬，sqlc、sqlx、ent 各約一萬七千到一萬八千多，pgx 約一萬四千。星數量的是關注度，不是採用率；ent 是另一種 ORM，schema 寫成 Go 程式碼、再產生型別安全的查詢 API，同時帶有 ORM 與產生程式碼的性質，本模組不示範。pgx 也是 GORM 的 PostgreSQL 方言套件底下用的驅動，所以用 GORM 的專案同時也在用 pgx。

本模組示範兩種常見的做法：用 GORM 這個關注度最高的 ORM，或用 sqlc 加 pgx 這組「SQL 手寫、工具產生程式碼」的組合。團隊選哪一種，比較的是驅動入口、查詢的形狀、審查要看到什麼、團隊背景與錯誤被發現的時間點。

## 驅動入口：pgx 原生介面還是 database/sql

這個決定先做，因為它決定後面哪些函式庫用得上：

| 條件                                                | 選擇                                     | 理由                                                                                                                                                                                           |
| --------------------------------------------------- | ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 會用到 GORM、sqlx，而且要和主程式在同一個交易裡寫入 | `database/sql`（驅動用 pgx 的 `stdlib`） | 這些函式庫的交易是 `*sql.Tx`，和 `pgx.Tx` 不相容                                                                                                                                               |
| 只連 PostgreSQL，主力是 sqlc 或直接寫 pgx           | pgx 原生介面（`pgxpool`）                | 少一層轉換，`COPY`、陣列、`jsonb` 這些 PostgreSQL 功能直接可用（例如每晚用 `CopyFrom` 匯入數十萬筆對帳資料、把標籤存成 `text[]` 用 `= ANY($1)` 查詢）                                          |
| 程式可能換資料庫，或要同時支援 MySQL 與 PostgreSQL  | `database/sql`                           | 換驅動時 Go 的呼叫方式（`QueryContext`、`Scan`、`*sql.Tx`）不變；SQL 字串裡的佔位符（`$1` 對 `?`）與方言（`RETURNING`、`ANY`）仍要逐段改。例如賣給客戶自行部署的軟體，要接客戶手上現有的資料庫 |

只要共用連線池、不必共用交易時，主程式可以用 `pgxpool`，再用 `stdlib.OpenDBFromPool(pool)` 做出一個共用同一個池的 `*sql.DB`，交給 GORM（`postgres.New(postgres.Config{Conn: sqlDB})`）或 sqlx；實測兩者共用之後池裡只開一條連線。migration 工具多半在部署步驟或啟動時另開一個 `*sql.DB`、跑完就關，不影響主程式選哪個入口。應用程式和 PostgreSQL 之間有一層交易模式的 PgBouncer 時，兩個入口都要另外處理：pgx 不論走哪個入口，預設都會在連線上快取預先解析的查詢，實測會出現 `prepared statement "stmtcache_…" already exists (SQLSTATE 42P05)`，處理方式見 [10.2 pgx：PostgreSQL 驅動的原生介面、連線池與 COPY 大量寫入](/go/10-database-access/pgx/)〈pgx 的語句快取與 PgBouncer 交易模式〉。兩個入口可以在同一個程式裡並存；分別用 `sql.Open` 與 `pgxpool.New` 建立時各有一個連線池（連線數要合起來算），而不論池是否共用，交易都不能互通：`pgx.Tx` 與 `*sql.Tx` 是兩個不相容的型別，一段要在同一個交易裡完成的寫入，必須全部走同一個入口。

## 主力工具：GORM 還是 sqlc

[1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/) 的選型軸套到這兩個工具上：

| 讀者要決定的事       | 條件                                                          | 傾向                                  |
| -------------------- | ------------------------------------------------------------- | ------------------------------------- |
| 查詢的形狀           | 多數是單表或一層關聯的增刪查改，後台管理頁面多                | GORM                                  |
|                      | 報表、多表聚合、視窗函數佔了查詢的一大部分                    | sqlc                                  |
|                      | 列表頁的篩選條件多、依使用者輸入動態組合                      | GORM 的條件串接，或另加 Query Builder |
| 審查要看到什麼       | 審查者要在 diff 裡直接看到每一段 SQL                          | sqlc                                  |
|                      | 審查看方法呼叫，SQL 靠開發時 GORM 的 SQL 記錄確認             | GORM                                  |
| 團隊的背景           | 成員從 Laravel、Rails、Django 轉過來，習慣 ORM 的寫法         | GORM                                  |
|                      | 成員熟 SQL，查詢常要調執行計畫                                | sqlc                                  |
| 錯誤在什麼時候被發現 | 希望欄位改名、查詢寫錯在產生程式碼時（`sqlc generate`）就失敗 | sqlc                                  |
|                      | 接受由整合測試在執行時抓出來                                  | GORM                                  |

團隊背景這一軸的理由在於改 SQL 的位置：用 sqlc 時，送出的 SQL 就是 `.sql` 檔裡那一段，調執行計畫就是改那一段；用 GORM 時要先把那個查詢改寫成 `Raw`。熟 SQL 的團隊在前一種位置上工作，習慣 ORM 的團隊在後一種。

表裡沒有 sqlx，因為它和 sqlc 處在同一側（SQL 手寫、審查看得到），差別在檢查的時間點與步驟：sqlx 不需要產生步驟，欄位錯誤到執行時才出現；只連 PostgreSQL 時，pgx 原生介面的 `RowToStructByName` 提供同樣的對映而不必多一個函式庫。所以 sqlx 的落點是：要走 `database/sql`（例如和 GORM 共用連線池，或要支援 PostgreSQL 以外的資料庫）、想手寫 SQL、又不想加產生步驟。

不同的軸給出相反的傾向時（例如團隊的背景傾向 GORM、查詢的形狀傾向 sqlc），不必二選一，看下面的混用組合。判錯的代價各軸不同：後台列表有十幾個篩選條件卻全交給 sqlc，每加一個條件就多一組 `sqlc.narg ... IS NULL OR`，查詢越來越長、執行計畫也可能變差；以報表為主的服務選了 GORM，多數查詢最後寫進 `Raw`，SQL 回到字串，產生時的檢查與 ORM 的對映兩邊都沒拿到；習慣 ORM 的團隊被要求全用 sqlc，初期每一段增刪查改都要寫 SQL 加註記，交付速度明顯變慢。

## Go 專案裡 schema 的權威：migration 檔、GORM model 與 Atlas

[1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/) 把「schema 的權威放哪裡」列為選型軸：schema 由 model 定義時傾向 ORM，由 migration 的 SQL 定義時傾向從 SQL 產生程式碼。GORM 本身的 `AutoMigrate` 不適合正式環境（改名變成新增欄位、沒有變更記錄與退回方法，見 [10.5 GORM：model、關聯載入與 ORM 送出的 SQL](/go/10-database-access/gorm/)），所以用 GORM 的專案有兩種做法。一種是同樣用版本化 migration 工具、由手寫的 migration 檔當 schema 的權威，這時這個軸分不開 GORM 與 sqlc。另一種是用 Atlas 的 GORM provider（`ariga/atlas-provider-gorm`）從 model 算出版本化的 migration 檔，model 仍然是 schema 的權威，產生出來的每一份檔案照樣要審查；這時軸又分得開：model 是權威選 GORM 加 Atlas，migration 的 SQL 是權威選 sqlc。golang-migrate 與 goose 都是依序執行手寫的 SQL 檔；Atlas 另外能比對資料庫現況與期望的 schema、產生差異的 migration，三者在這個用途上擇一即可。

以 migration 檔當權威時，用 GORM 與用 sqlc 的差別落在「model 怎麼跟上 schema」：

- **sqlc**：讀 migration 目錄產生 struct，schema 改了重新產生，對不上的地方在產生或編譯時報錯。
- **GORM**：model 是手寫的 struct，schema 改了要手動同步 model，對不上的地方在執行時才出現，而且不一定報錯：欄位從資料表移除之後，讀取送出的是 `SELECT *`，不會報錯，那個欄位保持零值，寫入時才報錯；資料表多出來的欄位則一律被忽略。

用 GORM 的專案通常靠整合測試補上「model 與 schema 不一致要到執行時才發現」這個缺口：在測試環境依序套用全部 migration，再讓每個 model 實際讀寫一次。

以上都假設 schema 由這個 Go 服務擁有。資料庫被多個服務共用、schema 由另一個服務（例如 Laravel 的 migration）管理時，Go 這一側不跑 migration、也不用 `AutoMigrate`：sqlc 的 `schema` 改指向 `pg_dump --schema-only` 匯出的檔案，GORM 的 model 則靠整合測試對著擁有方建出的 schema 驗證；約束名稱也要照擁有方的命名判讀（Laravel 預設把唯一約束命名成 `customers_email_unique`）。

## 常見的混用組合

多數 Go 專案不只用一個工具。三種組合最常見：

| 組合                         | 分工                                                                                   | 要留意的地方                                                                                                                                                                                               |
| ---------------------------- | -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GORM 加 `Raw`                | 增刪查改用 GORM，報表用 `db.Raw(sql).Scan(&rows)` 直接寫 SQL                           | `Raw` 裡的 SQL 是字串，錯誤到執行時才出現，和 sqlx 一樣                                                                                                                                                    |
| GORM 加 sqlc                 | 增刪查改用 GORM，固定而複雜的查詢用 sqlc                                               | sqlc 要產生 `database/sql` 版本的程式碼，才能和 GORM 共用交易（見〈混用時共用同一個交易〉）                                                                                                                |
| sqlc 加 pgx 加 Query Builder | 多數查詢用 sqlc，條件多變的搜尋用 squirrel 這類 Query Builder 組出 SQL 再交給 pgx 執行 | Query Builder 組出的 SQL 沒有產生時的檢查，要有測試涵蓋；它在審查時看不到最終的 SQL，要求每段 SQL 在審查時可見的服務不適合；squirrel 預設的佔位符是 `?`，接 PostgreSQL 要設 `PlaceholderFormat(sq.Dollar)` |

## 混用時共用同一個交易

GORM 與 sqlc 寫在同一個交易裡的前提，是兩者都走 `database/sql`。sqlc 的設定檔不寫 `sql_package`（或寫 `database/sql`）時，產生的 `DBTX` 介面用的是 `ExecContext`、`QueryContext` 這組 `database/sql` 的方法，`*sql.Tx` 符合它。GORM 的交易函式裡，`tx.Statement.ConnPool` 就是那個 `*sql.Tx`（`gorm.Config` 開了 `PrepareStmt` 時不是，下面的型別斷言會 panic）。sqlc 這一側的查詢檔裡有這一段：

```sql
-- name: AddNote :exec
UPDATE orders SET note = $2 WHERE id = $1;
```

兩者寫在同一個交易裡：

```go
err := db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
	if err := tx.Model(&Order{ID: 103}).Update("amount", 999).Error; err != nil {
		return err
	}

	sqlTx := tx.Statement.ConnPool.(*sql.Tx) // GORM 這個交易底下的 *sql.Tx
	q := store.New(sqlTx)                     // sqlc 產生的程式碼跑在同一個交易裡
	if err := q.AddNote(ctx, store.AddNoteParams{
		ID:   103,
		Note: sql.NullString{String: "同一個交易", Valid: true},
	}); err != nil {
		return err
	}
	return errors.New("撤銷") // 回傳錯誤：GORM 與 sqlc 的兩筆修改一起撤銷
})
```

```text
ConnPool is *sql.Tx: true
tx err: 撤銷 amount: 250 note nil: true
```

金額仍是原來的 250、備註仍是 NULL，兩邊的修改都被撤銷了。sqlc 改成產生 pgx 原生版本（`sql_package: "pgx/v5"`）的話，它要的是 `pgx.Tx`，和 GORM 的 `*sql.Tx` 接不起來；這時有兩個做法：GORM 與 sqlc 各自開交易，接受它們不在同一個交易裡；或把需要一起成功的寫入全部交給 GORM，或全部交給 sqlc。

## 選型結果裡要統一的項目：連線池、例外路徑、migration 工具、錯誤值、NULL、交易傳遞與記錄

選型的結果不只是一個工具名稱，因為同一個工具兩個開發者各自決定細節時，會在下面這幾處分岔：

- **連線池由哪一段程式建立、上限多少**：兩處各建一個池，連線數加倍、各自的上限也就失效（池的設定見 [10.1 database/sql：連線池、查詢結果的讀取與交易](/go/10-database-access/database-sql/)）。
- **主力工具與例外**：一人把報表寫成 GORM 的 `Raw`、另一人寫成 sqlc，同一類查詢有兩種檢查時間點，例外要寫成規則（例如「報表類查詢放 `query/` 用 sqlc」）。
- **schema 由哪個 migration 工具管理**：一人用 `AutoMigrate`、另一人寫 migration 檔，schema 會漂移，改名還會留下舊欄（見 [10.5 GORM：model、關聯載入與 ORM 送出的 SQL](/go/10-database-access/gorm/)〈AutoMigrate 在正式環境的限制〉）。
- **唯一約束的錯誤怎麼判讀**：一人讀錯誤代碼、另一人讀約束名稱，回報給使用者的訊息就不一致（見 [10.2 pgx：PostgreSQL 驅動的原生介面、連線池與 COPY 大量寫入](/go/10-database-access/pgx/)〈錯誤：*pgconn.PgError〉）。
- **前面有沒有交易模式的連線池代理，以及驅動的查詢執行模式**：一人在本機直連 PostgreSQL、另一人在正式環境經過 PgBouncer，預先解析查詢的錯誤只在經過 PgBouncer 的正式環境出現（見 [10.2 pgx：PostgreSQL 驅動的原生介面、連線池與 COPY 大量寫入](/go/10-database-access/pgx/)）。
- **主力是 GORM 時，開發與測試環境的兩種記錄**：GORM 的 SQL 記錄看得到送出的語句，零值更新被略過時那裡會少一行 `UPDATE`；預設交易的 `begin` 與 `commit` 只在資料庫的語句記錄（`log_statement`）裡看得到。
- **NULL 的表示**：`sql.NullString`、`*string` 與 sqlc 預設的 `pgtype.Text` 混在同一個專案裡，轉成 domain 型別的程式就要寫三套（見 [10.1 database/sql：連線池、查詢結果的讀取與交易](/go/10-database-access/database-sql/)〈Scan 與 NULL〉）。
- **「找不到」的錯誤值**：`sql.ErrNoRows`、`pgx.ErrNoRows`、`gorm.ErrRecordNotFound`，以及 GORM 的 `Find` 不回錯誤；混用的專案三種都會出現，repository 要在邊界把它們轉成同一個錯誤。
- **交易物件怎麼傳進各個 repository**：一人用參數傳 `*sql.Tx`、另一人放進 `context`，混用時就接不起來（傳遞方式見 [1.4 Repository Adapter 實作](/backend/01-database/repository-adapter/)〈Transaction 傳遞〉）。
- **`gorm.Config` 的旗標由同一處設定**：`PrepareStmt`、`SkipDefaultTransaction`、`TranslateError` 都會改變行為；開了 `PrepareStmt`，〈混用時共用同一個交易〉的 `ConnPool.(*sql.Tx)` 型別斷言會 panic。

這幾條決定了 repository 背後的 adapter 長什麼樣；adapter 對上層暴露的 port 怎麼切，見 [6.6 如何新增 repository port](/go/06-practical/repository-port/)。
