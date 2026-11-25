# 本專案（blog repo）的資產地址

`references/addresses.md` 列出的方法論、元件庫規格範本、agent 派發範本、執法工具與本規格票，在本 repo 的實際位置寫在這個資料夾裡。這個資料夾不隨 skill-sync 同步，內容只對本 repo 成立。

| 簡稱 | 在本 repo 的位置 | 備註 |
| --- | --- | --- |
| 方法論 | `content/record/component-library-bidirectional-constraint-methodology.md`（網站上的 `/record/component-library-bidirectional-constraint-methodology/`） | 本 repo 的段名把 skill 正文寫的「判準」寫成「判斷標準」：skill 的〈元件契約判準〉〈命名與通用元件判準〉〈Web/HTML 端 L2 特別判準〉，在這一篇是〈元件契約判斷標準〉〈命名與通用元件判斷標準〉〈Web/HTML 端 L2 特別判斷標準〉；〈容器亦為元件〉〈形態因素先決〉兩邊同名。用 skill 的段名搜這一篇時，把「判準」換成「判斷標準」再搜 |
| 元件庫規格範本 | 本 repo 沒有 `doc` skill 的範本 | 照 `SKILL.md`〈起手〉新建規格檔；先例是 `scripts/sql-practice/ui/components.md`（SQL 練習頁的元件庫規格：起點判定、形態因素矩陣、token、候選表、逐元件契約、畫面狀態表、齊全檢查、實作註記） |
| 規格檔與 spec 目錄 | 沒有統一的 spec 目錄 | 規格檔放在功能自己的目錄（SQL 練習頁是 `scripts/sql-practice/ui/components.md`） |
| agent 派發範本 | 本 repo 沒有框架層的派發範本 | 派 agent 時照 `docs/rules/claude-code.md`〈Agent tool 的派發〉 |
| 執法工具 | SQL 練習頁有一支逐行比對的檢查腳本 `scripts/sql-practice/ui/check_css_tokens.mjs`，pre-commit 在 `assets/sql-practice/` 底下的 token 檔、練習頁、總覽頁與文章入口的 CSS 有 staged 時檢查 staged 的內容；其他 CSS 沒有檢查 | token 檔是 `assets/sql-practice/tokens.css`（手寫的 CSS 自訂屬性，沒有 DTCG 檔：只有網頁一個讀取端）。腳本的限制與正對照照 `design-system-token-layer.md`〈檢查：擋什麼、在哪裡擋、用什麼工具、例外怎麼寫、怎麼確認它在讀〉。這支腳本跟那一節「擋的寫法」的落差，都屬於「沒有量過」的範圍：它只讀每行最後一個 `{` 之後的內容；不擋色名（`white`）、`oklch()` 這類它沒列的色彩函式與帶 id 的選擇器；允許註解 `sqlp-lint: allow` 不強制寫原因；只檢查 CSS 檔，模板裡的 `style` 屬性（例如 `layouts/_default/single.html` 的行內顏色與字級）與 JavaScript 設定的樣式不在範圍內。要不要補進腳本另外決定，記在 SQL 練習頁的 Backlog。Web 端的元件規則與 token 只在 `assets/` 底下的 CSS；畫面不符契約時用瀏覽器量計算後的樣式（量法在 `content/work-log/css-silent-override-measurement.md`）。元件展示頁只載入元件自己的 CSS，改了全域規則或宿主樣式之後，拿「展示頁依正式頁面的順序加載 `themes/hugo-bearcub/assets/herman.css`、`assets/custom.css` 與 `layouts/partials/custom_head.html` 的內嵌樣式」的複本逐元素比較，比較的結果（不同的項數與那幾項的元素和屬性）寫進規格檔的實作註記與 commit message |
| 本規格票與專案待辦清單 | 本 repo 沒有 ticket 系統 | 照 `SKILL.md`〈專案沒有 ticket 系統時〉：中間產出物寫進規格檔開頭的章節；待辦條目記進最近一層承接這個功能規劃的目錄頁的 `## Backlog`，判斷依據是功能的規劃寫在哪一份目錄頁、從哪些文章連過去。SQL 練習頁的規劃與待辦在 `content/backend/01-database/sql/practice/_index.md`。找不到任何目錄頁承接的工具（只在 `scripts/` 或 `bin/` 底下、沒有文章連過去），待辦記在規格檔的實作註記，並照 `AGENTS.md`〈延到工作結束之後的動作〉寫進最後一則總結；commit message 寫出判定「沒有目錄頁承接」用的 `rg -n '<功能的路徑或網址>' content` 指令原文與結果 <!-- portability-allow: 只留在本 repo 的專案對照表 --> |
