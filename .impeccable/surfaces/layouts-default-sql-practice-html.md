---
version: 1
slug: "layouts-default-sql-practice-html"
primary_target: "layouts/_default/sql-practice.html"
related_targets: ["assets/js/sql-practice.js","assets/sql-practice/practice.css"]
---

# SQL 練習頁（/backend/01-database/sql/practice/play/）

## Scope

- Visitor mode: Operate。讀者在一輪題目裡作答、讀解析、跳到觀念文章再回來。
- 畫面：練習首頁（模式與各階段進度）、題目（未作答、已作答）、一輪的結果、篩選後 0 題、載入中、載入失敗、localStorage 不能用的提示。
- 外框：整頁只有練習區，blog 的頁首、左側分類色帶與頁尾不輸出（2026-11-25 使用者決定，原本保留，文章版型與練習區並排時兩個世界互相衝突）；離開練習的路是樞紐列的離開按鈕與瀏覽器的上一頁。
- 操作形態（使用者簽核）：桌機指標加鍵盤、手機單手觸控；平板視為觸控的寬版。

## Audience and task

同 PRODUCT.md 的讀者。作答目標是說得出為什麼錯：作答輕，解析是主角。

## Constraints

- 繁體中文介面，不用 emoji 與裝飾符號，狀態要有文字標籤，不只靠顏色。
- WCAG 2.2 AA：色塊上的字一律白色，所以承載文字的色塊都用低明度色階（白字對比 5.7:1 以上）；亮 cyan 不放內文。
- 沒有後端；紀錄只在 localStorage 與 sessionStorage。
- 不載入外部字型；字型用系統字型堆疊。

## Direction contract

THESIS: 字就是介面。題目考的那個 SQL 關鍵字用超大細體小寫裁出畫面右緣，當成這一題的樞紐標題；四個選項是平面色磚，作答後整塊磚染上自己的狀態色，解析就寫在磚上。拒絕的類別預設是白色題卡、單選鈕、答對變綠的刷題卡。

OWN-WORLD: 純黑底（#000），白字；狀態色只有一種彩色：深藍綠 #0b6e8e 標推薦，深灰 #4f4f4f 標讀者選了而失效的選項（使用者 2026-11-24 比較過紅綠、藍橘、紫琥珀之後選定）。藍綠專指推薦，所以按鈕不用實心色：主要按鈕是 2px 白框加粗體，次要是灰框；亮 cyan #00bde3 只用在焦點框、細線與小箭頭；首頁的盲測磚與文章結尾入口沿用深藍綠底。色塊上的字一律白色。零陰影、零圓角；色塊不加邊框，按鈕與空心標記用外框表示可按或未作答。細體（200 到 300）Latin 小寫與中文大字當版面骨架，內文 16/24，SQL 用系統等寬字。點陣（cyan dot matrix）只用在未作答的磚與空狀態。

STORY: 讀者看到大字知道這題在考哪個子句，讀需求與資料前提，點一塊磚作答；四塊磚同時翻成狀態色，每塊寫出正常資料與邊界資料的結果、成立前提與失效條件；讀者點觀念文章，讀完按上一頁回到同一題的翻開狀態，按下一題往前。

FIRST VIEWPORT: 桌機 1440 寬：最上一列是樞紐列（階段名，目前所在白色，其餘灰色，另一端是離開練習的連結）；其下是超大小寫關鍵字（96px 細體，裁出右緣）；左欄 520 寬放中文題目標題（34px）、需求（18/28）與資料前提四列；右欄是 2×2 色磚，每塊至少 250 高，頂端大寫字母 a 到 d（56px 細體），下方 SQL；左下是本輪進度條（每題一段，狀態色加文字），右下是「下一題」主要按鈕（作答後出現）。手機：關鍵字 60px 仍裁出右緣，色磚改單欄，主要按鈕固定在拇指範圍的底部。

FORM: catalog challenger digital-design-canon-metro-typographic-tiles（不在我的候選清單上，使用者在決策頁選它）；seed:cc1cef3cd7785da1。Signature interaction：作答時四塊磚依閱讀順序在 200ms 內各自翻面（3D rotateX），露出狀態色與解析；prefers-reduced-motion 時改成直接換色。Motion grammar：進場由左緣滑入、字先於磚；狀態變化 150 到 250ms；沒有裝飾性動畫。

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Unresolved

- 題目標題在盲測模式作答前要隱藏（會洩漏考點），樞紐關鍵字同樣洩漏考點：盲測時改顯示題號。
- 文章結尾入口「用 N 題 SQL 練習檢查這篇」在 blog 的 herman 世界裡，不屬於這個表面；元件契約時決定它要不要借用 Metro 的語彙。
