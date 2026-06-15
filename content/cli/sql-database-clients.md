---
title: "終端機 SQL 客戶端：harlequin、lazysql 與 pgcli/litecli 的選型"
date: 2026-06-15
draft: false
description: "在純文字終端機連資料庫、跑查詢、看結果的客戶端：全螢幕 TUI（harlequin IDE 風、lazysql 瀏覽器風）與增強型 REPL（pgcli/litecli）兩種範式，以及遠端連線的 SSL driver gotcha。"
tags: ["cli", "tui", "sql", "database", "harlequin", "lazysql", "dblab", "rainfrog", "pgcli", "usql", "remote"]
---

終端機 SQL 客戶端把資料庫的 schema、表格與查詢結果做成可導航的文字介面，讓遠端只有終端機時也能瀏覽資料、跑查詢、看結果，取代把連線資訊餵給桌面 GUI（DBeaver、TablePlus）的需求。在純 SSH 情境下，它補上「連到遠端 DB 做事」這塊，而且全是文字、低頻寬友善。

本文承接 [終端機圖形化工具總覽](/cli/cli-graphical-tools-overview/) 的資料庫客戶端分類。工具分兩種範式：全螢幕 TUI 客戶端，與增強型 REPL。

## 兩種範式：全螢幕 TUI 與增強型 REPL

全螢幕 TUI（`harlequin` / `lazysql`）把 schema 樹、查詢編輯器、結果表格排進多個面板，像縮小版的 DBeaver。增強型 REPL（`pgcli` / `litecli`）仍是一行一行打 SQL，但加上語法高亮、智能補全與表格化輸出，是 `psql` / `mysql` 原生 client 的升級版。

選哪種看工作型態：要邊看 schema 邊探索資料，用全螢幕 TUI；要快速接上跑幾條查詢、或塞進腳本，用 REPL。

## 全螢幕 TUI：IDE 風與瀏覽器風

兩個全螢幕 TUI 的互動模型剛好相反，這是選型最該先分清的一點。

`harlequin` 是 SQL IDE 風：左側 Data Catalog 樹列出 db → schema → table → 欄位（帶型別標記，整數 `#`、字串 `s`、numeric `#.#`），中間是查詢編輯器，寫好 SQL 按 `Ctrl+Enter` 執行、結果在下方表格。點表只是把表的限定名稱插進編輯器、輔助組查詢，不會自動顯示資料。它用 Python（Textual）寫，adapter 涵蓋 postgres、mysql、sqlite、duckdb、odbc，預設 adapter 是 duckdb，連別的 DB 用 `-a` 指定，例如 `harlequin -a postgres "<連線字串>"` 或 `harlequin -a sqlite db.sqlite`。

`lazysql` 是瀏覽器風：左側選一個表，右邊直接顯示該表記錄、不必寫 SELECT。上方分頁切 Records / Columns / Constraints / Foreign Keys / Indexes（`[` 與 `]` 切換）。篩選按 `/` 開 WHERE 輸入，帶運算子補全（`=`、`≠`、`>`、`between`、`ilike`、`in`、`like`、`regexp` 等），只寫條件、不用整句。要跑自訂 SQL 按 `Ctrl+E` 開編輯器（vim modal、有 `-- INSERT --` 模式）寫完整語句、`Ctrl+R` 執行。它用 Go 寫、lazygit 風的鍵盤導航。

判讀：習慣先寫 query 再看結果的選 `harlequin`；習慣點開表瀏覽、偶爾才下複雜 SQL 的選 `lazysql`。

`dblab`（Go）與 `rainfrog`（Rust）是另外兩個實機驗證過的瀏覽風 TUI。`dblab` 走混合型：左側樹（`Ctrl+H` 聚焦、`j`/`k` 移動、`Enter` 看表的列）配上方查詢編輯器（`Ctrl+E` 執行），瀏覽與寫 query 兩條路都有。它有一個實測 gotcha：編輯器的查詢要 schema 限定（`SELECT * FROM public.products` 才行、裸 `products` 會報 relation 不存在），因為編輯器連線的 search_path 沒含 public，而樹瀏覽（`Enter`）不受這點影響。`rainfrog` 專注 Postgres：側欄選表看 rows / columns / constraints / indexes / rls policies，查詢編輯器是 vim modal（`i` 進 insert、`v` 進 visual），另有 history 與 favorites 分頁。實測它不支援滑鼠操作，面板與分頁一律用 `Tab` 切換、其餘靠鍵盤導航。

## 增強型 REPL：dbcli 家族

`pgcli`（Postgres）、`mycli`（MySQL）、`litecli`（SQLite）是同一個專案（dbcli）的三個 client，把原生 `psql` / `mysql` / `sqlite3` 補上智能補全（表名、欄位、關鍵字）、語法高亮與對齊的表格化輸出。手感仍是 REPL，但打 SQL 時會即時提示。

它們也能非互動執行、適合腳本：`litecli` 用 `-e`（`litecli db.sqlite -e "SELECT ..."`），`pgcli` 在 stdin 非 TTY 時讀管線（`echo "SELECT ..." | pgcli "<連線字串>"`），輸出是對齊的 ASCII 表格。要在腳本裡取一次查詢結果、又想要比 `psql -c` 更好的排版時，這條路最直接。

`usql` 走另一條路：universal CLI，一個工具用統一介面連 Postgres、MySQL、SQLite 等各種 DB，連線字串以 scheme 區分（`postgres://...`、`sqlite:...`），也支援 `-c` 非互動執行。它不是 TUI，行為像能連多種 DB 的加強版 `psql`。一台機器要連好幾種不同 DB 時，一個 usql 比每種 DB 各裝一個 client 省事。

## 遠端連線的一個 gotcha：SSL 模式因 driver 而異

同一個 Postgres、同一條連線字串，不同 client 的 SSL 預設不一樣。`lazysql` 走 Go 的 `pq` driver、預設要求 SSL，連沒開 SSL 的 DB 會報 `pq: SSL is not enabled on the server`，要在連線字串加 `?sslmode=disable`：`postgresql://user:pass@host:5432/db?sslmode=disable`。`pgcli` 與 `harlequin` 走 Python 的 psycopg、預設行為不同，同樣的 DB 不加也能連。遠端連不上、又確定帳密與 port 對的時候，先查的就是 sslmode。

## 同類其他選擇

同範式還有 `gobang`（Rust）。它未上 crates.io、Homebrew 也沒有對應 formula，本機未能安裝，列出供參考、未實機驗證。

## 下一步路由

- 把 DB client 擺進可持久化的多工器 pane：[tmux 基礎](/cli/tmux-persistence-and-basics/)。
- 編譯型工具（`lazysql` / `dblab` / `rainfrog`）搬到遠端的單一 binary 注意事項：[git 線圖工具選型](/cli/git-line-graph-tools-for-remote-cli/)。
- SQL 客戶端在遠端工具分類中的定位：[終端機圖形化工具總覽](/cli/cli-graphical-tools-overview/)。
