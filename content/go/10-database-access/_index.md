---
title: "模組十：資料庫存取"
date: 2026-10-06
description: "在 Go 服務裡接 PostgreSQL、要在 database/sql、pgx、sqlx、sqlc 與 GORM 之間選擇，或排查連線池、讀取物件與交易的行為時"
weight: 11
tags: ["go", "database"]
---

本模組是 Go 存取關聯式資料庫的實作：標準庫 `database/sql`、PostgreSQL 驅動 pgx、sqlx、sqlc 與 GORM 各自怎麼用、替程式接手了哪一段工作、接手之後哪些行為在程式碼上看不出來。

語言無關的那一層在 [1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/)：存取資料庫的程式要做哪幾件事、驅動／結果對映／從 SQL 產生程式碼／Query Builder／ORM 各接手哪一段、選型時比較什麼，並對照 Go、PHP（Laravel）與 Python 的對應工具。本模組照那一篇的分層展開 Go 的部分；其他語言的教材對應同一篇，各自寫自己的實作。

## 讀者定位

讀者會寫基本的 SQL（`SELECT`、`JOIN`、`INSERT`、交易），讀過本系列的模組一到模組五（package、struct、interface、error、`context`、測試），要在 Go 服務裡接上 PostgreSQL。缺的是 Go 資料庫生態的使用經驗：標準庫與各個函式庫分別做了什麼、哪些行為在程式碼上看不出來、團隊選型時在比較什麼。

## 推導源頭

推導源頭是 backend 1.17 的分層：存取資料庫的程式要做三件事——寫出要送出的 SQL、取得連線並執行（連線池、交易）、把查詢結果的每一列對映成程式語言的值（含 NULL）。本模組各篇依序看 Go 的工具接手這三件事裡的哪幾件，每一篇回答同一組問題：這個工具接手了哪一段、程式因此看不到什麼、看不到的那一段在什麼情況下會出問題。

| 工具           | 在 1.17 分層裡的類別 | SQL 由誰寫                   | 連線與交易                                   | 查詢結果的對映                  |
| -------------- | -------------------- | ---------------------------- | -------------------------------------------- | ------------------------------- |
| `database/sql` | 驅動與標準介面       | 程式手寫                     | 標準庫的連線池                               | 逐欄 `Scan`                     |
| pgx 原生介面   | 驅動（附結果對映）   | 程式手寫                     | `pgxpool`                                    | 逐欄 `Scan`，或執行時依欄名對映 |
| sqlx           | 結果對映             | 程式手寫                     | 沿用 `database/sql` 的連線池                 | 執行時依 `db` tag 對映          |
| sqlc           | 從 SQL 產生程式碼    | 寫在 `.sql` 檔，產生 Go 函式 | 沿用選定驅動的連線池                         | 產生時決定，型別在編譯期檢查    |
| GORM           | ORM                  | 由方法呼叫組出               | 沿用 `database/sql` 的連線池，寫入預設包交易 | 依命名慣例對映                  |

和本系列其他模組的關係：[模組六的 repository port](/go/06-practical/repository-port/) 定的是 port 的切法，本模組的工具寫在 port 背後的 adapter 裡；交易語意與 migration 的原則在進階模組的 [資料庫 transaction 與 schema migration](/go-advanced/07-distributed-operations/database-transactions/)。

## 章節列表

| 章節                                                                                                       | 交付的內容                                                                                                                 |
| ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| [10.1 database/sql：連線池、查詢結果的讀取與交易](/go/10-database-access/database-sql/)                    | 標準庫的模型：`*sql.DB` 是連線池、驅動註冊、`Scan` 與 NULL、讀取物件不關閉時連線被佔住、交易的寫法；範例資料表也定在這一篇 |
| [10.2 pgx：PostgreSQL 驅動的原生介面、連線池與 COPY 大量寫入](/go/10-database-access/pgx/)                 | 驅動的兩種用法、`pgxpool`、依欄名對映、`*pgconn.PgError`、`CopyFrom`、語句快取與連線池代理                                 |
| [10.3 sqlx：手寫 SQL 加上 struct 對映](/go/10-database-access/sqlx/)                                       | `Get` 與 `Select`、欄位對不上時的錯誤、具名參數與 `IN`                                                                     |
| [10.4 sqlc：從 SQL 產生型別安全的 Go 程式碼](/go/10-database-access/sqlc/)                                 | 設定檔與查詢註記、產生的程式碼、產生時擋下的錯誤、NULL 與型別對應、選擇性條件                                              |
| [10.5 GORM：model、關聯載入與 ORM 送出的 SQL](/go/10-database-access/gorm/)                                | 命名慣例、`First` 與 `Take`、N+1 與 `Preload`、零值更新、預設交易、錯誤判讀、`AutoMigrate` 的限制                          |
| [10.6 Go 專案的資料庫存取工具選型：GORM、sqlc 與 pgx 的組合](/go/10-database-access/choosing-data-access/) | 把 1.17 的選型軸套到 Go 的工具上，以及 Go 專案常見的混用組合                                                               |

## 跨分類引用

- 語言無關的分層、選型軸與 PHP、Python 的對應工具：[1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/)
- 不分語言的 ORM 概念：[ORM 知識卡](/backend/knowledge-cards/orm/)
- Raw SQL、Query Builder、ORM 三類的取捨與 repository adapter 的責任：[Repository Adapter 實作](/backend/01-database/repository-adapter/)
- N+1 與其他查詢反模式：[查詢反模式](/backend/01-database/query-anti-patterns/)

## 驗證環境

各篇的輸出在 Go 1.25、PostgreSQL 17、pgx v5.11.0、sqlx v1.4.0、sqlc v1.31.1、GORM v1.31.2（PostgreSQL 方言套件 v1.6.3）上實際跑過。

## Backlog

| 項目                                                                          | 類型 | 前置條件                     | 規模 |
| ----------------------------------------------------------------------------- | ---- | ---------------------------- | ---- |
| Query Builder（squirrel、goqu）專篇                                           | 主章 | 讀者回饋顯示 10.6 的簡介不夠 | 小   |
| ent 專篇（schema 寫成 Go 程式碼的另一種 ORM）                                 | 主章 | 同上                         | 中   |
| 資料庫整合測試（testcontainers 與交易回滾）                                   | 主章 | 無                           | 中   |
| GORM 的 `gorm.Model` 與軟刪除（`DeletedAt`、`Unscoped`）、`Save` 寫回全部欄位 | 主章 | 先實測 GORM v1.31 的行為     | 小   |
