# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

主要讀者是專業工程師：懂研究方法與開發原則、有開發經驗，但在某個主題上缺經驗。他們多半從搜尋或站內連結進來，手上帶著一個具體疑問，要的是推導與判斷標準，不是語法表或 API 清單。

次要使用者是作者本人：把 blog 當工作筆記查，並用 SQL 練習頁的作答困惑回頭改教材（練習頁的「記下不懂的地方」產生的 Markdown 表格列，貼回練習規格的〈練習回饋紀錄表〉）。

SQL 練習頁（`/backend/01-database/sql/practice/play/`，計畫中）的使用者是同一群讀者，進來的時機有兩種：讀完一篇 SQL 或資料庫文章、想確認自己懂了沒；或者還寫不出 `SELECT`、`JOIN`，從階段一補起。

## Product Purpose

blog 是教學與工程紀錄：教學模組（Backend、DevOps、程式語言、軟體設計）、知識卡、work-log、report 卡與方法論。每一篇從需求推到判斷標準與取捨，讓讀者讀完能在自己的情境裡做判斷。

SQL 練習頁把 SQL 與資料庫模組的觀念接回實際的商業需求。成功的定義是：讀者作答之後**說得出為什麼錯**，也就是說得出每個選項在正常資料與邊界資料上的結果、成立的前提與失效的條件。作答本身要輕，作答後的解析才是主角。

## Positioning

- 每篇從需求推到判斷標準與取捨，結論寫在推導走完的位置。
- 知識卡加上全站自動連結，組成可以互相引用的概念網。
- 結論由實測佐證：容器實跑、基準快照、題庫斷言。
- 練習頁的每個選項都在 SQLite 上實跑過、或有 PostgreSQL 實測快照為證，解析逐項寫出成立前提與失效條件；題目跨三個商業領域（紙頁書店、雲課堂、捷配物流）與多條表路徑輪替，避免靠記住題目長相答對。

## Operating Context

- 讀者在桌機或手機的瀏覽器上閱讀長文，常在文章與知識卡之間來回跳。
- 練習頁的讀者在一輪題目中途會點進觀念文章，讀完按瀏覽器的上一頁回到同一題；也可能從文章結尾的「用 N 題 SQL 練習檢查這篇的觀念」直接進到只含那幾題的一輪。
- 題庫與驗證腳本在 `scripts/sql-practice/`，規格在 `content/backend/01-database/sql/practice/_index.md`（draft，讀者看不到）。

## Capabilities and Constraints

- Hugo 靜態網站，部署在 GitHub Pages，沒有後端伺服器。練習紀錄只能存在讀者的瀏覽器（localStorage），不送到任何伺服器。
- 介面與內容是繁體中文、台灣用語；CJK 排版與中英混排要顧到。
- 不用 emoji 與裝飾符號（✓ ✗ 這類）；狀態與優缺點用文字表達。
- 主題是 hugo-bearcub 的 herman 樣式，目前只有深色；左側分類色帶的色相由頂層分類名稱雜湊而來。
- 未決定：練習頁第二期要不要接 SQLite WASM 讓讀者在頁面內實跑選項（規格的 Backlog 有這一項）。

## Evidence on Hand

- SQL 練習題庫：`scripts/sql-practice/questions/`，101 題、404 個選項，每題有 `relatedDocs` 指向觀念文章（共 43 篇）。
- 基準快照：`scripts/sql-practice/benchmarks/`（SQLite 實跑、PostgreSQL 18 實測、還沒實測的參考快照分三份）。
- 三個領域的 schema 與邊界資料：`scripts/sql-practice/domains/`。
- 沒有讀者推薦、使用數據或作答統計，未來的設計不得編造。

## Product Principles

1. 推導先於結論：介面先給讀者判斷用的材料，再揭曉答案。
2. 解析是主角：作答是進入解析的入口，畫面重心放在每個選項為什麼成立或失效。
3. 讀者隨時回得去：每個畫面都有回到文章或分類的路，換題不吃掉瀏覽器的上一頁。
4. 只寫有證據的話：數字與結論都來自實跑或快照，介面不加沒有來源的宣稱。

## Accessibility & Inclusion

- 至少 WCAG 2.2 AA：全程鍵盤可操作、文字對比合格、焦點在換題與揭曉答案時移到合理的位置。
- 狀態（推薦、答對、答錯）不只靠顏色，另有文字標籤。
