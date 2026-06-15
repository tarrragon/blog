---
title: "驗證導向的 CLI 工具文章生產流程：用 Docker fixture 實機跑過再寫"
date: 2026-06-15
description: "寫 CLI 工具教學時，靠官方 docs fact-check 會放過版本差異與實作落差。本文整理一套驗證導向的生產流程：工具分類決定驗證分工（非互動自驗 vs TUI 人工互動）、用 Docker image 造可拋棄的測試 fixture、驗過 / caveat / 移除三層標註、把實跑抓到的 gotcha 寫回文章。以 content/cli/ 五類工具的實作為證。"
tags: ["methodology", "writing-workflow", "cli", "verification", "docker", "claude-code"]
---

## 這篇要說什麼

驗證導向的工具文章生產，是在寫下每一條 install 與操作指令前，先在本機實際跑過、確認正確才寫進去的流程。它承擔的責任是讓工具教學的指令可信：靠官方文件 fact-check 會放過版本差異與實作落差，這些只有實跑才現形。

`content/cli/` 的五類終端機工具文章（監控 / 圖表 / 多工器 / 檔案管理 / SQL 客戶端）都用這套流程生產。本文把流程抽成 playbook，之後擴展任何類別都照走。

## 為什麼官方文件查核不夠

工具文章最容易出錯的是指令本身：旗標名、設定鍵、子指令在不同版本會變，而文件常落後於 binary。下面是同一批文章在實機驗證時抓到、純靠 docs 查核會放過的落差：

- `zellij web` 文件寫有 `--bind`，實際 0.43.1 是分開的 `--ip` 與 `--port`。
- `lazygit` 的 pager 設定文件寫 `git.paging.pager`，新版 0.62.2 改成 `git.pagers`（list），舊鍵啟動時會被自動 migrate、改寫設定檔。
- `dblab` 的查詢編輯器要 schema 限定（`SELECT * FROM public.products`），裸 `products` 會報 relation 不存在，因為它的編輯器連線 search_path 不含 public — 文件沒提。
- `nvtop` 在 Apple Silicon mac 裝得起來、但 snapshot 模式直接 segfault，GPU 後端不穩。
- 同一個 Postgres，`lazysql`（Go pq driver）連無 SSL 的 DB 要 `?sslmode=disable`，`pgcli` / `harlequin`（Python psycopg）不用。

這些落差有個共通點：讀者照文件走會撞牆、卻在文件裡找不到答案。實機跑一次就現形，而且現形的正是文章最該寫的內容。

## 工具分類決定驗證分工

驗證前先把工具分兩類，分工不同。

非互動工具能在一次呼叫裡印出結果就結束：版本、`--help` 旗標、以及非互動模式（`dive --ci`、`usql -c`、`litecli -e`、`pgcli` 讀 stdin、`nvtop -s`、`ncdu -o`、`gnuplot set terminal dumb`）。這類由作者或自動化直接跑，看輸出對不對、旗標存不存在。

全螢幕 TUI 工具會接管終端機（`lazygit`、`btop`、`harlequin`、`lazysql`、`dblab`、`rainfrog`、`broot` 等），代跑會卡住自動化流程。這類交給人互動操作、截圖回報，再對照文章宣稱逐項判讀。

分工的判準是先 grep `--help` 找有沒有非互動模式：有就自動驗（最可靠、零人力），沒有才走人工互動。很多 TUI 工具附帶 snapshot / ci / execute 旗標（`dive --ci`、`nvtop -s`、`zellij web --status`），優先用這些把「需要人」的範圍縮到最小。

## 測試 fixture：用 Docker image 造可拋棄的環境

驗證資料庫與容器類工具需要真實後端。用 Docker（OrbStack 等）起可拋棄的測試環境，是這套流程的關鍵基礎建設。

對資料庫客戶端（`pgcli` / `harlequin` / `lazysql` / `dblab` / `rainfrog` / `usql`），起一個 `postgres:alpine` 容器、seed 幾筆資料、用非標準 port（例如 55432）避免撞到既有服務，連線字串帶 `?sslmode=disable`：

```bash
docker run -d --name sqltest-pg \
  -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=testdb \
  -p 55432:5432 postgres:alpine
# 等 ready 再 seed
docker exec sqltest-pg psql -U test -d testdb \
  -c "CREATE TABLE products(id serial primary key, name text, price numeric);
      INSERT INTO products(name,price) VALUES('widget',9.99),('gadget',19.50);"
```

對容器監控工具，起一個常駐容器給 `ctop` 看即時資源、pull 一個多層 image 給 `dive --ci` 逐層分析。對檔案與 SQLite 工具，用 `sqlite3` 造一個小 db 當 fixture。

fixture 的紀律有三條：用獨立命名加非標準 port，只動自己造的、不碰使用者既有資源；測完 `docker stop` / `rm` 自己的容器、刪自己的暫存檔；image 可以留著重用，避免下次重複 pull。這條紀律讓驗證在使用者的真實開發機上跑也安全 — 本系列驗證全程，使用者既有的專案容器一個都沒被動到。

## 三層標註：驗過、caveat、移除

實機驗證會把工具分到三種狀態，文章對它們的處理不同。

驗過的寫進去、當正式內容，並把實機觀察（範式、手感、gotcha）一起記。

本機驗不了但工具有效的（需真實網域的 `certbot`、需 k8s cluster 的 k9s 叢集操作、特定 OS 的防火牆指令），保留但加 blockquote caveat 標「依官方文件、本機未實機驗證」；同一段已驗證的部分也標明，讓讀者分得出哪些經實測、哪些是文件依據。

裝得起來但操作完全無法驗證、又無保留價值的（`nvtop` 在無 GPU 的 mac），移除、不寫進去。裝不起來的（`gobang` 不在 crates.io 與 Homebrew），列出供參考、標未驗證。

這三層的共同精神是：文章只斷言驗證過的內容，其餘明確標示其證據等級，而非含糊帶過。

## 把 gotcha 寫回文章

實跑抓到的「文件沒寫的真實行為」是文章最有價值的部分，因為它正是讀者照文件走會撞到、卻找不到答案的點。每個 gotcha 寫進對應工具的段落、標「實測」，例如 lazysql 的 `?sslmode=disable`、dblab 編輯器的 schema 限定、broot 的 `:cd` 要透過 `br` 啟動、rainfrog 不支援滑鼠。這些一句話的提醒，省下讀者各自撞一次的時間。

## 擴展本系列時照這個跑

把流程收斂成一條可重複的步驟鏈：

1. 列候選工具，分非互動與全螢幕 TUI 兩類。
2. 安裝：`brew` 優先，不在 core 的用 `cargo install` 或 `go install` 備案（`go install` 還能繞過從源碼 build 撞到的 Xcode 版本問題）。
3. 造 fixture：DB 工具起 Docker 容器、檔案工具造 sqlite db，seed 樣本資料。
4. 驗證：非互動工具自己跑（版本 / `--help` 旗標 / 非互動模式），TUI 交人互動操作加截圖。
5. 標註：驗過寫進去、驗不了加 caveat、無價值又驗不了移除。
6. gotcha 寫回對應段落、標實測。
7. 收尾：`mdtools lint` / `cards` 過、清理自己造的 fixture、commit。

工具層面的選型內容怎麼組織，見 [終端機圖形化工具總覽](/cli/cli-graphical-tools-overview/)；本文是它背後的生產與驗證流程。
