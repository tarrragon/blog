---
title: "CSS 改用 token 取值的重構與驗證：逐元素比對計算後的樣式、字級分成尺寸階與功能字級（primitive 與 semantic token）、!important 與提高特定性的 id 選擇器的替代寫法"
date: 2026-11-25
description: "一份手寫 CSS 混著 !important、寫死的 px 字級與色碼，想改成全部透過 CSS 自訂屬性（token）取值，又要確認改完畫面沒變；或字級種類多到每個元件各寫一套、手機版的字級散在好幾個媒體查詢（media query）裡時"
tags: ["work-log", "css", "design-token", "specificity", "playwright", "重構", "量測"]
slug: "css-token-refactor-verified-by-computed-style-diff"
---

2026-11-25 在 macOS 15.3.1 上重構本站 SQL 練習頁的樣式。練習頁的 DOM 由 vanilla JavaScript 產生，樣式是幾份手寫的 CSS：練習頁本身的 `practice.css`、練習總覽頁清單的 `hub.css`、文章結尾練習入口的 `callout.css`。這幾個元件嵌在 Hugo 0.151 產生的 blog 頁面裡，下文把這些頁面連同它們載入的 blog 主題樣式與自訂樣式 `custom.css` 稱為宿主。量測用 Playwright 1.59.1 驅動的 Chromium 147.0.7727.15，沒有在 Firefox 與 Safari 上量。

這篇的 token 指用 CSS 自訂屬性（custom property）命名的設計值，例如 `--sqlp-bg: #000`，元件規則以 `var(--sqlp-bg)` 引用它（概念見 [Design Token（具名設計值）](/ux-design/knowledge-cards/design-token/) 卡）。這篇整理那一次重構裡要量測才判得準的事：重構前後怎麼逐元素比對計算後的樣式（computed style），確認畫面沒變、或只在預期的屬性上變了；`!important` 的成因（減少動態效果的規則要蓋過後寫的 hover 規則、選擇器的特定性算錯）與不提高優先度的替代寫法；字級改成尺寸階與功能字級兩層，以及收斂字級時怎麼分出預期內的差異；顏色、線寬與命中區（可點元件的最小高度，概念見 [Touch Target（觸控目標）](/ux-design/knowledge-cards/touch-target/) 卡）改成 token 時，計算後的字串不同而畫面相同的差異、以及 CSS 改變不了的狀態造成的差異怎麼判；擋住新的寫死值的檢查腳本與它的正對照；怎麼量出帶 id 的選擇器實際要贏過哪一條規則；逐元素比對量不到、要靠截圖尺寸發現的 grid 子項溢出；以及練習頁、總覽頁與文章入口三個元件改從同一份 token 檔取值、JavaScript 讀 token 取代寫死的位移。量計算後的樣式的基本讀法、DevTools 的 Styles 面板怎麼分出規則沒套上還是輸了，在 [CSS 規則沒生效時的量測與成因：範圍重設的特定性與宿主樣式、container-type 與 subgrid、捲動陰影的覆蓋漸層](/work-log/css-silent-override-measurement/)，這篇不重寫；配色本身的對比量測在 [狀態色塊配色的對比量測：文字對色塊、色塊對背景、細標記對底色，以及紅綠色覺差異](/work-log/state-color-contrast-and-color-vision/)。

文中提到的練習頁元件：

- **回合磚**：首頁上每個練習階段一塊的入口，左上角是細體的關鍵字。
- **選項磚**：題目畫面上每個 SQL 選項一塊，分成三層：標頭（選項字母 a、b、c、d 與作答後的狀態）、程式碼區（SQL）、解析區（作答後出現的逐列說明）。
- **階段導覽列**：練習頁頂端列出各階段、切換階段用的那一列（程式裡的 class 是 `sqlp-pivot`）。
- **精簡頂列**：捲動到階段導覽列離開畫面之後，固定在視窗頂端的一列，顯示目前位置（例如「第 3／6 題」）與「回到頂部」「離開練習」兩顆按鈕。
- **資料表結構面板**：題目畫面上可以展開的面板，列出題目用到的每張資料表的欄位、型別與約束。
- **困惑筆記區**：作答後讓使用者選困惑類型、寫下哪裡不懂，並產生一列 Markdown 表格的區塊；那一列顯示在一個唯讀的輸出框裡。

## 重構前後的比對：逐元素記錄計算後的樣式、固定亂數種子、比對的範圍

重構是只換寫法、不換結果的改動，所以驗收的對象是瀏覽器算出來的值，不是 CSS 原始碼。原本寫 `font-size: 16px` 的規則改成 `font-size: var(--sqlp-t-body)` 之後，只要 `--sqlp-t-body` 算出來是 16px，元素的計算後字級就跟改之前一樣。看截圖的人分得出版面大致相同，分不出某個按鈕的行高從 24px 變成 26px。逐像素比對截圖的工具（做法見 [螢幕截圖比對](/testing/04-ui-automation/visual-regression/)）抓得到 2px 的位移，也不受下文記錄的屬性清單限制；它的缺點在刻意改值的批次上，像素差異沒有屬性與元素可以分組，這次的字級收斂讀不出哪些差異是預期的。

這次的比對腳本用 Playwright 開練習頁的四個畫面（首頁、題目、作答後、結果），在 1440px 與 390px 兩種寬度下各量一次：1440px 落在手機斷點 599px 以上、是桌機常見的寬度，390px 落在斷點以下、是手機常見的寬度。腳本從練習區的根元素往下走過每一個元素，記錄一組屬性的計算後值，寫成 JSON；下文把這份 JSON 稱為計算後樣式的快照，跟截圖分開。

```js
// 在 page.evaluate 裡執行。
// PROPS：要記錄的屬性名清單，依這次的改動會動到哪些屬性挑（字級、行高、顏色、內外距、寬高、transform……，這次 29 個）
// "sql-practice"：要比對的範圍的根元素 id，換成自己頁面上那一塊的根元素
const out = {};
const walk = (el, path) => {
  const cs = getComputedStyle(el);
  const rec = {};
  for (const p of PROPS) rec[p] = cs.getPropertyValue(p);
  out[path + " " + el.tagName.toLowerCase() + "." + [...el.classList].join(".")] = rec;
  [...el.children].forEach((c, i) => walk(c, path + "/" + i));
};
walk(document.getElementById("sql-practice"), "0");
```

每個元素的鍵是它在樹裡的路徑加上標籤與 class，所以兩份快照可以逐鍵、逐屬性比對；兩份的元素數不同時，比對腳本先印出結構不同的畫面，代表 DOM 本身變了，那個畫面的逐值比對不能當作樣式的比對。這次兩種寬度、四個畫面共約 1690 個元素，腳本替每個元素記錄 29 個屬性，一次比對約 49000 個值。

這種比對只有在同一份 CSS 量兩次得到 0 差異時才有意義。這次用同一份 CSS 量第二次就有 84 處差異，而且兩份的元素數不同：練習頁出題時用 `Math.random` 挑選題目的變體、排定題目與選項的順序，兩次快照裡作答後與結果畫面上的題目不同。Playwright 的 `addInitScript` 注入的腳本在頁面的程式執行之前把 `Math.random` 換成固定種子的線性同餘產生器（linear congruential generator），兩次快照時練習頁就挑出同樣的題、排出同樣的順序：

```js
await page.addInitScript(() => {
  let x = 42; // 種子；任何固定值都可以，兩次快照用同一個值即可
  Math.random = () => ((x = (x * 16807) % 2147483647) / 2147483647);
});
```

換上之後，同一份 CSS 量兩次是 0 差異，之後每一批改動的比對才拿這兩份當基準。量兩次 0 差異只代表那兩次量測之間沒有出現不穩定的差異，不保證以後每一次都穩定：下文〈顏色、線寬與命中區的 token〉的展開區，就是通過這一步之後才在比對裡出現的時序差異。固定種子比較兩個版本的做法，在終端機動畫程式的量測裡也用過：[量終端機動畫程式的 CPU：用 pty 執行、認出 tsx 實際執行程式的程序、停掉之後檢查殘留、錄 profile 與數輸出量、用固定種子比較兩個版本，以及降頻之後 CPU 百分比的讀法](/work-log/terminal-animation-cpu-measurement/) 的〈用固定的種子比較兩個版本〉寫的是包一層程式、在模組載入前換掉亂數來源的寫法。

記錄的屬性清單就是比對的範圍：清單外的屬性改了，比對結果照樣是 0。走訪也只讀元素本身，`::before`、`::placeholder` 這類偽元素要用 `getComputedStyle(el, "::placeholder")` 另外記錄；這次的改動沒有改到偽元素的規則。這次只記錄靜止狀態下的值；hover、按下與減少動態效果偏好這幾種狀態另外寫一支腳本，讓滑鼠停在首頁第一塊回合磚與題目畫面第一塊選項磚上、按住不放，在 `reducedMotion: "reduce"` 與 `"no-preference"` 兩種設定下各讀一次 `transform`。改到 hover 或動畫相關的規則時，只跑靜止狀態的比對，結果是 0 差異，那個 0 代表沒有量到，不代表沒有改變。

量測的寬度也決定比對的範圍：每一個斷點與容器查詢的區段，要各有一個量測寬度落在裡面。390px 時 `max-width: 599px` 與 `max-width: 899px` 兩個 media query 都成立，答案解析在 420px 以下切成單欄的容器查詢也成立；1440px 時三者都不成立。這次沒量到 600 到 899px 之間只有 899px 那個 media query 成立的組合，也沒量到右欄寬於 1480px 才成立的 `@container sqlp-main (min-width: 1480px)`（1440px 的視窗裡右欄比視窗窄，條件不成立）。1480px 那一段的規則這次沒有改到；要改那一段時，量測的視窗要寬到右欄超過 1480px。快照腳本在讀值之前固定等 400ms，沒有等 `document.fonts.ready`；同一份 CSS 量兩次是 0 差異，代表這次兩次快照時字型的載入狀態相同。字型從網路載入較慢的環境要改成等 `document.fonts.ready` 再讀值，不然字型換上之前與之後的寬高會混進比對結果。

## !important 的成因與不提高優先度的替代寫法：減少動態效果的規則、算錯的特定性

兩條宣告衝突時，瀏覽器的層疊（cascade）在同一個來源、沒有用 cascade layer 的情形下，依序比重要性、特定性（specificity，選擇器裡 id、class 與元素各有幾個；見 [Specificity（特定性）](/ux-design/knowledge-cards/specificity/) 卡）與先後順序來選一條；包含來源與 layer 的完整順序在 [CSS 規則沒生效時的量測與成因：範圍重設的特定性與宿主樣式、container-type 與 subgrid、捲動陰影的覆蓋漸層](/work-log/css-silent-override-measurement/) 的〈判斷哪一條 CSS 規則生效〉。宣告帶 `!important` 時，層疊在比特定性之前就先選它，下一次有規則要蓋過它時，只能再寫一條 `!important`。這次練習頁的 CSS 有兩行用了 `!important`（減少動態效果那一行一個宣告，輸出框那一行兩個宣告），成因不同。

**減少動態效果的規則要蓋過寫在它後面的 hover 規則。** 練習頁的選項磚與回合磚在 hover 時傾斜一點，使用者在系統設定裡要求減少動態效果時（`prefers-reduced-motion: reduce`），傾斜要取消。原本的寫法是在減少動態的 media query 裡寫 `transform: none !important`：回合磚的 `.sqlp-round:hover` 規則寫在那個 media query 之後，兩者特定性相同，不加 `!important` 時後寫的 hover 規則勝出。替代寫法是反過來，只在使用者沒有要求減少動態效果時加上傾斜：

```css
.sqlp-round:hover { background: var(--sqlp-tile-hover); }
@media (prefers-reduced-motion: no-preference) {
  .sqlp-round:hover { transform: rotateX(2deg) rotateY(-2deg); }
}
```

這樣在減少動態的設定下，`transform` 維持初始值 `none`，蓋掉它的規則也就用不到，hover 規則寫在哪個位置也不影響結果。比對時用量 hover 與按下狀態的那支腳本，兩種動態偏好下選項磚與回合磚在 hover、按下時的 `transform` 跟改之前逐字相同。

**選擇器的特定性算錯，用 `!important` 補。** 困惑筆記區的輸出框是一個 `<textarea class="sqlp-note-out">`，它要用等寬字與 14px，而同一區有一條 `.sqlp-note textarea` 替所有文字欄設定字型與 16px。`.sqlp-note-out` 的特定性是 (0,1,0)，`.sqlp-note textarea` 是 (0,1,1)，`.sqlp-note textarea` 勝出，所以原本在字型與字級兩個宣告上都加了 `!important`。選擇器改寫成 `.sqlp-note .sqlp-note-out`，特定性 (0,2,0)，高過 (0,1,1)，不需要 `!important`。

兩處改完之後靜止狀態的比對是 0 差異。兩處的 `!important` 都是為了贏過另一條特定的規則，而那條規則屬於同一個元件自己的 CSS：讀出那條規則，改寫成不跟它衝突（減少動態效果那一處），或依特定性勝出（輸出框那一處），就不必動用重要性去越過特定性與先後順序。

## 字級：尺寸階與功能字級兩層、手機版的對應、收斂時怎麼分組讀差異

重構前練習頁的 CSS 有 56 個寫 px 的 `font-size` 與 36 個寫 px 的 `line-height`，原始碼裡用到 14 種字級：14、15、16、17、18、20、22、24、26、30、40、44、60、96。每個元件的規則各自寫數字，手機版的字級散在七個 `@media (max-width: 599px)` 裡，每個 media query 改一兩個元件。收到「題目需求的字要大一點」這種回饋時，改的人要找到題目需求那一條規則與它的手機版規則各改一次；同一種用途的文字（例如按鈕與離開連結）的規則各自寫了 17 與 18，看起來是同一級、實際差 1px。

這次的字級改成兩層 CSS 自訂屬性：

- **尺寸階**（scale；設計 token 的分層裡常稱 primitive token），`--sqlp-size-xs` 到 `--sqlp-size-2xl`，加上 Display 字體用的 `--sqlp-size-d1` 到 `d3`，只放數字：14、16、18、22、26、30，以及 40、60、96。這組值取自原本已經在用的字級：內文留 14、16、18 三級，每級差 2px（14 是中文的下限），往上的標題級每級差 4px（22、26、30）；15、17 夾在內文的級距中間，20、24 夾在標題的級距中間，所以併進相鄰的一級。Display 字體的大字裡，選項字母的 44 與回合磚關鍵字的 40 只差 4px，併成一級。元件規則不引用這一層。
- **功能字級**（role token，也稱 semantic token），`--sqlp-t-<用途>` 與成對的行高 `--sqlp-lh-<用途>`，用文字在畫面上的用途命名，例如 `--sqlp-t-lead` 是題目需求、`--sqlp-t-control` 是按鈕與連結、`--sqlp-t-caption` 是灰色說明。每一個功能字級對到一個尺寸階，元件規則只引用這一層。

兩層分開的理由是兩種調整的範圍不同。使用者回饋「某一種用途的字太小」時，改那個功能字級對到哪一階，其他用同一階的用途不受影響；要整體調大某一階（例如 16px 全部改 17px）時，改尺寸階，用到它的用途一起變。只有一層時，這兩種調整混在同一組變數裡：名字是數字的變數改值之後名不副實，名字是用途的變數又沒有一個值能讓「同一級」的幾種用途一起變。功能字級只有少數幾種、沒有整階一起調整的需求時，一層用途命名的變數加一張記錄哪幾種用途同級的表就夠，少一層間接。

手機版的字級集中在一個 media query 裡，在同一個根元素上依寬度改功能字級的對應：

```css
@media (max-width: 599px) {
  #sql-practice {
    --sqlp-t-poster: var(--sqlp-size-d2);  --sqlp-lh-poster: 72px;
    --sqlp-t-title: var(--sqlp-size-xl);   --sqlp-lh-title: 34px;
    /* 階段導覽列、目前所在的階段、精簡頂列也各降一階；題目需求不降 */
  }
}
```

自訂屬性會被子元素繼承，token 檔在手機寬度上替練習區的根元素重新定義 `--sqlp-t-title`，練習區裡寫 `font-size: var(--sqlp-t-title)` 的元素就取得手機的值，各元件不再需要自己的手機規則。token 的定義仍然只寫在 token 檔與這一個 media query 裡，元件規則沒有任何一條重新宣告它們。

收斂字級會改變畫面，比對要確認的事因此從「0 差異」換成「差異只出現在預期的屬性上」；預期的屬性是這一批刻意要改變計算值的屬性（`font-size`、`line-height`），加上由它推導出的版面尺寸（元素的寬與高）。這次的收斂是：15 併進 16；17 依各處文字的用途併進 16 或 18；20 有兩處，精簡頂列的位置文字從 20 改成 18，手機上的題目需求從 20 改成 22；手機上的畫面標題從 24 改成 26；選項字母從 44 改成 40。比對結果有 3360 處差異。比對腳本依「屬性、舊值、新值、元素的 class」分組計數，作者逐組讀過分組結果：每一組的屬性是 `font-size` 或 `line-height`，或是隨字級改變的寬度與高度；沒有任何一組是顏色、內距或外距。寬與高任何原因都會改變（下文的展開區只改變高度），所以寬高的差異要出現在自己或子孫的 `font-size`、`line-height` 也有差異的元素上，才算隨字級改變；快照另外記錄 `<details>` 的 `open` 這類 DOM 狀態，比對時才分得開。差異的總數很大，判定的依據是分組之後每一組的屬性都在預期的範圍裡。用快照裡的計算後值數，四個畫面上出現的字級從 16 種降到 11 種：尺寸階的 9 個值，加上行內程式碼的 `0.9em`（16px 的 0.9 倍是 14.4px）與表單元件的瀏覽器預設值。輸出刻意改變時，另一種做法是把比對的參照換成同一個新行為的另一份實作，取捨寫在 [效能最佳化的正確性要拿一份產生同樣畫面的參照實作逐格比：輸出應該不變時參照是舊版，輸出刻意改變時參照換成同一個新行為的不最佳化版本](/report/optimization-equivalence-needs-a-reference-of-the-same-behavior/)；這次的新字級沒有另一份實作可以當參照，所以改用分組讀差異。

## 顏色、線寬與命中區的 token：字串不同而畫面相同的差異、CSS 改變不了的狀態、仍留字面值的斷點

顏色、線寬與 44px 命中區改成 token 時，每一條規則改的是值的寫法，算出來的值沒有改變，這一批比對的預期結果是 0 差異。焦點框的線寬寫在 `:focus-visible` 的規則裡，命中區另有一組 `pointer: coarse` 的值，靜止狀態、非觸控環境的快照兩者都量不到，這次沒有另外量；這兩處的改動只把同一個值換成 token 名稱。44px 是練習頁觸控命中區原本就用的值，也是 WCAG 2.5.5 Target Size 的 AAA 門檻（44 × 44 CSS px）；練習頁另有一組依 `pointer: coarse` 在觸控裝置上從 32px 切到 44px 的命中區 token，這次新增的是不隨指標裝置切換、一律 44px 的那一組。這次新增的 token 還包括細標記用的灰（為什麼不能跟答錯的色塊共用一個值，在 [狀態色塊配色的對比量測：文字對色塊、色塊對背景、細標記對底色，以及紅綠色覺差異](/work-log/state-color-contrast-and-color-vision/) 的〈細標記對它旁邊的底色〉）、選項磚程式碼區依狀態切換的底色、解析區的半透明底色與分隔線、兩組捲動提示陰影、兩組區塊陰影、語法上色的七個顏色，以及四種線寬（分隔線、外框、主要按鈕的粗框、焦點框）。練習頁的 CSS 替選項的 SQL 與資料表結構面板裡的約束各寫了一份語法上色規則，其中五個顏色兩份相同，合成一份 `:is(.sqlp-sql, .sqlp-sql-inline) .sqlp-k-kw`；`:is()` 的特定性取參數裡最高的那一個，合併之後是 (0,2,0)，跟原本兩份各自的特定性相同。

比對結果有 15 處差異：漸層的字串 8 處、首頁展開區的狀態 7 處，兩類的判法不同。

**計算後的字串不同、畫面相同。** 手機程式碼區的捲動陰影規則原本寫 `linear-gradient(to right, rgba(255, 255, 255, 0.28), rgba(255, 255, 255, 0))`，改成 token 時，尾端改寫成 `transparent`，計算後的字串從 `rgba(255, 255, 255, 0)` 變成 `rgba(0, 0, 0, 0)`。CSS Images 規範規定漸層在預乘透明度（premultiplied alpha）的色彩空間裡插值，透明度 0 的顏色預乘之後每個色彩分量都是 0，所以瀏覽器用白色透明與黑色透明畫出的漸層像素相同。判斷這一類差異時，要讀規範確認兩個值是否等價，只看字串是否相同會判錯。

**CSS 改變不了的狀態。** 首頁「怎麼使用這個練習」的展開區在改之前的那一次快照裡是收合的，改之後是展開的，連帶首頁的高度也不同。`<details>` 展開與否是 DOM 的狀態，由快照腳本在讀值之前設定，這一批改的顏色與線寬規則改變不了它；而那個展開區是練習首頁的程式在載入之後才插進頁面的，腳本設定展開的時候它不一定已經在 DOM 裡。改之後的 CSS 再量兩次快照，展開區兩次都是展開的；差異來自 CSS 改變不了的 DOM 狀態，所以把這一處歸給快照腳本的時序，不算樣式的改變。

這一批之後，元件規則裡還寫著字面值的是斷點（breakpoint：`max-width: 599px`、`max-width: 899px`，以及容器查詢（container query）的 420px 與 1480px）與只用一次的版面尺寸（左欄 300 到 400px、回合磚最小高 160px）。`var()` 只能用在屬性值裡，不能用在 media query 的條件裡，斷點寫成 token 也用不到 `@media` 上；只出現一次的版面尺寸寫成 token，要改它時仍然是改一個地方，換到的只有多一層名字。

## 用檢查腳本擋住新的寫死值：檢查的三種寫法、兩個 exit code、正對照

改完之後的 CSS 只透過 token 取值，這個狀態要靠一道檢查維持：沒有檢查時，下一次調整的人寫死一個 15px，不會收到任何訊號。這次寫了一支 Node 腳本 `check_css_tokens.mjs`，逐條讀 CSS 的宣告，回報三種寫法：任何宣告帶 `!important`；`font-size` 或 `line-height` 寫 px、rem 或 pt；任何宣告的值裡有色碼（`#…`）或 `rgb()`、`rgba()`、`hsl()`、`hsla()`。這三種寫法是依屬性判的，腳本不數一個值出現幾次，所以顏色與字級即使只用一次也要寫成 token。屬性名以 `--` 開頭的宣告是 token 的定義，本來就要寫字面值，不檢查。腳本略過同一行帶 `sqlp-lint: allow` 註解的宣告；`body` 不在練習區根元素的子孫裡，取不到定義在練習區上的 `--sqlp-bg`，這次就是在那一行加這個註解，並在緊鄰的註解裡寫出原因。

這支腳本逐行讀原始檔，每一行只把最後一個 `{` 之後的內容當成宣告，所以適用的對象是每行一條規則或一個宣告的手寫 CSS。餵進壓縮成一行的 CSS 時，它只讀到最後一條規則的宣告；餵進 Sass 原始檔時，`color: $brand` 的值裡沒有色碼，`$brand: #123456` 又不是 CSS 宣告，兩行都不會被報出。用 Sass 或其他前處理器的專案，要檢查未壓縮的編譯產物，或改用以 CSS parser 為基礎的工具。腳本只比對上面三種寫法，色名（`white`）、`oklch()`、`hwb()`、`color()` 這幾種色彩函式，以及把字級寫在 `font` 簡寫裡的 `font: 16px/1.5 sans-serif`，都不會被報出。色名沒有擋，因為 `transparent`、`currentColor` 這類關鍵字要放行；其餘幾種寫法練習頁的 CSS 目前沒有用到，這次沒有加進檢查。Stylelint 是以 CSS parser 為基礎的檢查工具，`declaration-no-important` 擋 `!important`、`color-no-hex` 擋色碼、`function-disallowed-list` 列出 `rgb()` 這些色彩函式、`declaration-property-unit-allowed-list` 限制字級的單位、`color-named` 擋色名，合起來涵蓋這支腳本的三種寫法與色名（`color-no-hex` 本身不擋色彩函式，也會檢查 `--` 開頭的 token 定義，token 檔要另外排除），沒有讀到輸入檔時也會報錯；檢查的寫法要增加、或 CSS 不是每行一條規則時，改用它比擴充這支腳本省事。

腳本結尾印出「檢查了幾個宣告、幾處違規」，有違規時 exit 1，一個宣告都沒讀到時 exit 2。讀到 0 個宣告與讀到幾百個宣告而 0 違規，在只看違規清單時看起來一樣，所以分成兩個 exit code。這支腳本的正對照（positive control：餵進已知會違規的輸入，確認檢查確實讀到了要檢查的宣告；見 [Positive Control（正對照）](/testing/knowledge-cards/positive-control/) 卡）用重構前的 `practice.css`：它報出 123 處違規，包括兩行裡的三個 `!important` 宣告；重構完成後，`practice.css` 是 710 個宣告、0 處違規，連同下文的 `tokens.css`、`callout.css`、`hub.css` 四份合計 790 個宣告、0 處違規。pre-commit hook 在 `tokens.css`、`practice.css`、`callout.css` 或 `hub.css` 有 staged 時，用 `git show :<路徑>` 取出 staged 的內容交給腳本檢查，檢查的是這次要提交的版本，不是工作樹裡可能還在改的版本。

## 提高特定性的 id 選擇器：拿掉 id 量出它是否還要贏過某條規則、改寫腳本的過濾條件、七條規則的處置

練習頁有七條元件規則的選擇器寫成 `#sql-practice .sqlp-pivot-item:hover`、`#sql-practice a.sqlp-btn` 這種形式，用 id 把特定性提高到 (1,x,x)，下文稱為 id 加權。當初加 id 是為了贏過宿主的主題與自訂樣式裡的連結規則。這個理由是否還成立，可以直接量：拿掉 id 之後，哪些元素的哪些樣式會改變。

量法是在已經載入的頁面上，用 CSSOM 改寫那幾條規則的選擇器，比較改寫前後的計算後樣式：

```js
// 走過頁面上所有樣式表的規則，把開頭的 "#sql-practice " 拿掉；只定義自訂屬性的規則（token 的定義）不改
for (const sheet of document.styleSheets) {
  for (const rule of sheet.cssRules) {
    if (rule.selectorText && /(^|,\s*)#sql-practice [.a-z]/.test(rule.selectorText)
        && ![...rule.style].every((prop) => prop.startsWith("--"))) {
      rule.selectorText = rule.selectorText.replace(/#sql-practice /g, "");
    }
  }
}
```

（實際的腳本另外遞迴走進 `@media` 裡的規則。）比較的對象是階段導覽列的一般項目與目前所在的項目、主要與次要的連結按鈕，每一個在一般狀態與 hover 狀態各讀一次顏色、底色、字重與字級。頁面上沒有連結形式的按鈕，腳本另外插入兩個 `<a class="sqlp-btn">`：量測只看得到當時在頁面上的元素，元件有某個變體（這裡是 `<a>` 形式的按鈕）沒出現在頁面上時，受它影響的規則量不出改變。七條裡的 `#sql-practice .sqlp-docs li a:visited` 用這個量法量不到：瀏覽器為了不洩漏瀏覽紀錄，`getComputedStyle` 對已造訪的連結回傳未造訪時的樣式。這一條改用特定性推算，拿掉 id 之後是 (0,2,2)，仍然高過練習區連結重設 `:where(#sql-practice) a` 的 (0,0,1)。

這種改寫腳本的過濾條件寫錯時，讀比對結果的人分不出「規則改寫了而樣式沒有改變」與「規則沒被改寫」。過濾條件寫成「規則的 `cssText` 不含 `--sqlp`」時，用意是跳過 token 的定義，而元件規則的值裡也寫著 `var(--sqlp-muted)`，七條規則有六條被當成 token 定義跳過，只有一條被改寫，比對結果是「沒有改變」。腳本印出它改寫了哪幾條規則，拿清單的條數對照預期的七條，就看得出過濾條件錯了。過濾條件改成「每一個屬性名都以 `--` 開頭」之後，七條都被改寫。

七條都拿掉 id 之後，只有一處樣式改變：連結形式的主要按鈕在 hover 時，文字從白色變成黑色。拿掉 id 之前的值是白底白字，`#sql-practice a.sqlp-btn { color: var(--sqlp-fg) }` 的特定性 (1,1,1) 高過主要按鈕 hover 時把文字改成黑色的 `.sqlp-btn[data-v="primary"]:hover`（(0,3,0)）。練習頁目前的主要按鈕都是 `<button>`，所以畫面上還沒出現這個白底白字。其他元素沒有改變的原因是宿主的 `custom.css` 在帶 `!important` 的連結規則上已經寫著 `a:where(:not(#sql-practice *))`，練習區裡的連結本來就不受它影響；這條排除為什麼只能從宿主那一邊做，在 [CSS 規則沒生效時的量測與成因：範圍重設的特定性與宿主樣式、container-type 與 subgrid、捲動陰影的覆蓋漸層](/work-log/css-silent-override-measurement/) 的〈範圍重設的特定性〉。層疊裡已經沒有任何規則要靠 id 加權才贏得過。

七條規則的處置：`#sql-practice svg` 改成 `:where(#sql-practice) svg`，跟練習區其他的元素重設同一種寫法；`#sql-practice .sqlp-pivot-item` 跟沒有 id 的 `.sqlp-pivot-item` 設的是同樣的顏色與底線，整條刪掉；其餘五條改成只用 class。這五條裡，要贏過練習區自己的 `:where(#sql-practice) a:hover`（特定性 (0,1,1)，hover 時把連結變成藍綠色）的有兩種寫法：階段導覽列的 `.sqlp-pivot-item:hover` 與 `.sqlp-pivot-item[aria-current]` 是 (0,2,0)，高過它；連結按鈕的 `a.sqlp-btn` 是 (0,1,1)，跟它同級、寫在它後面而勝出，同時低於主要按鈕 hover 的 (0,3,0)，主要按鈕 hover 時的黑字規則才蓋得過來。兩種寫法的規則（階段導覽列的 hover 與連結按鈕）旁各有一段註解，寫出它要贏過的是哪一條：下一個人調整那一條規則的選擇器時，從註解看得出這條規則的特定性是照它算的，要一起檢查。

## 逐元素比對量不到的共有錯誤：grid 子項 min-width: auto 撐寬整頁

390px 寬的題目畫面整頁截圖寬度是 747px，將近視窗的兩倍。快照腳本在讀值之前展開了資料表結構面板，展開之後整頁可以橫向捲動 357px。資料表結構面板的設計是表格在手機上最小寬 640px、在自己的外框裡水平捲動，實際被撐寬的是整頁，連選項磚都跟著變成 731px 寬。

成因在外框的上一層。每一張表的 `<section class="sqlp-schema-table">` 是 `.sqlp-schema-body` 這個 grid 容器的子項，grid 子項的 `min-width` 預設是 `auto`，在這裡算成內容的最小寬度（這次量到這個區段寬 715px，比表格的 640px 寬，這次沒有逐項拆開多出來的寬度屬於哪幾個子元素）。子項的最小寬度算成 715px，縮不到比它窄，grid 容器跟著變寬，一路撐到頁面。表格外框的 `overflow-x: auto` 沒有作用，因為外框本身從來沒有比表格窄過。替 `.sqlp-schema-table` 加上 `min-width: 0` 之後，子項可以縮到容器的寬度，表格在外框裡捲動，量到的整頁溢出從 357px 變成 0，區段寬度變成 342px。

這個溢出在改 token 之前就存在，日常使用時，使用者要先展開資料表結構面板才會遇到；而改 token 那幾批的比對只比較改之前與改之後是否相同，兩個版本都有同一個溢出，比出來是 0 差異。這個溢出是讀截圖的寬度時發現的：逐元素比對驗的是兩個版本相同，不驗兩個版本都對。

## 跨元件共用 token：tokens.css 與 resources.Concat、字型載入的確認、custom.css 的排除範圍、JavaScript 讀 token

練習總覽頁的清單與文章結尾的練習入口長得像練習頁的小磚：左邊一塊藍綠色的關鍵字方塊裝著細體小寫的關鍵字，右邊是說明文字。這兩份 CSS 原本各自照抄了練習頁的顏色字面值，兩份給關鍵字方塊寫的字級一個是 34/36、一個是 30/32，內距用了 2、6、10、14、20 這些不在間距階（spacing scale：`--sqlp-s1` 到 `--sqlp-s8`，4、8、12、16、24、32、48、64px）上的值，三份 CSS 也各寫了一次 Display 字體的 `@font-face`。這次把 token 與 `@font-face` 從 `practice.css` 搬到一份 `tokens.css`，選擇器寫成三個元件的根元素：`#sql-practice, .practice-hub, .sql-practice-callout`。三個頁面的 Hugo 模板用 `resources.Concat` 把 `tokens.css` 接在各自的元件樣式前面，輸出成一份 CSS：

```go-html-template
{{- /* resources.Get 的路徑以 assets/ 為起點；Concat 的參數是合併後輸出的路徑 */ -}}
{{- $css := slice (resources.Get "sql-practice/tokens.css") (resources.Get "practice/hub.css")
    | resources.Concat "practice/hub-bundle.css" | minify | fingerprint -}}
```

`resources.Concat` 的輸出路徑跟原本的 CSS 放在同一層資料夾，`@font-face` 裡 `url("../fonts/…")` 這種相對路徑在合併之後仍然指到同一個字型檔。練習頁搬出 token 之後，靜止狀態的比對是 0 差異。

字型是否還載入得到，這次用兩個讀法判：監聽頁面的網路回應，看字型檔有沒有被要求、狀態碼是不是 200；以及走過 `document.fonts`，讀那個字族的 `FontFace` 物件的 `status` 是不是 `loaded`。三個頁面都讀到 200 與 `loaded`。瀏覽器只在頁面上有文字用到這個字族、而且字元落在 `@font-face` 的 `unicode-range` 裡時才下載字型，其餘情形 `status` 停在 `unloaded`、也沒有網路請求，所以 `unloaded` 要在頁面確實有這種文字時才代表載入失敗。量的人從 `document.fonts.check()` 的回傳值看不出載入失敗：CSS Font Loading 規範規定，頁面上沒有任何字型宣告符合那個字族時，它也回傳 `true`。Hugo 的 minify 會把 `font-family` 的名字改成小寫（`sqlp display`），字族名的比對不分大小寫，所以不影響套用。

總覽頁與入口原本要在連結內層的 `<span>` 再宣告一次白字，因為宿主 `custom.css` 的連結規則寫了 `color: #9dc4e8 !important`，連結本身設的顏色贏不過它。這次把 `custom.css` 這條連結規則的排除範圍擴大成 `a:where(:not(#sql-practice *, .practice-hub *, .sql-practice-callout))`，兩個元件的白字宣告直接寫在連結上。`:where()` 的特定性是 0，排除範圍變大不改變 `custom.css` 這條規則對其他連結的特定性；比對文章頁時，一般連結的顏色仍是 `#9dc4e8`，知識卡的自動連結是另一組樣式，顏色本來就不同，不屬於這次的改動。總覽頁與入口這一批刻意改了字級與內距，比對照〈字級〉的方式依屬性分組讀：1440px 與 390px 的靜止狀態下，差異只有關鍵字方塊與說明文字的字級、行高、內距、隨之改變的高度，以及連結本身的顏色（從宿主的藍色變成白色，畫面上的文字原本就由內層的白字顯示）；兩個元件的 hover 這次沒有量。

JavaScript 裡也有一個照抄 token 值的寫死值：捲到練習區頂端時，上方留一個間距階 `--sqlp-s4` 的空隙（16px），JavaScript 卻寫死數字 16，寫在兩個幾乎相同的函式裡。兩個函式合成一個，位移改成讀 CSS：

```js
// root：練習區的根元素，或任何在 token 定義範圍內的元素；token 定義在三個元件的根元素上，不在 :root，
// 傳 document.documentElement 會取到空字串
const gap = parseFloat(getComputedStyle(root).getPropertyValue("--sqlp-s4")) || 0;
```

`getPropertyValue` 對沒有註冊型別的自訂屬性回傳它的值的字串（這裡是 `"16px"`），`parseFloat` 取出開頭的數字；token 寫成 px 的字面值時，間距階改了，JavaScript 取得的值跟著改。token 改寫成 `1rem` 時 `parseFloat` 得到 1，寫成 `calc()` 時得到 `NaN`，兩種都不報錯；token 可能不是 px 時，改讀一個套用這個 token 的元素的計算後長度（例如它的 `padding-top`），或用 `@property` 把 token 註冊成 `<length>`，計算後的值就是 px。取不到 token 時 `parseFloat` 得到 `NaN`，`|| 0` 這個運算式的結果是 0，位移退回 0：頁面仍然捲得到頂端，只是上方少了空隙；需要在取不到時收到訊號的話，改成拋錯或印警告。手機版的斷點 `599px` 也寫在 JavaScript 的 `matchMedia` 裡：呼叫 `matchMedia` 時要自己帶條件字串，CSS 裡的斷點沒有對應的自訂屬性可以讀，所以改成一個常數，註解寫出要跟哪幾份 CSS 的 media query 一起改。

## 判斷標準：哪些值寫成 token、比對差異怎麼歸類、!important 與 id 加權的替代、檢查怎麼算數

一個值寫成 token 換到的，是改它的時候只改一個地方、而且用到它的位置一起變；付出的是多讀一層名字。判斷時數的是設計決定，不是值：同一個值在兩處代表不同的設計決定時（同樣是 16px，一處是內文字級、一處是間距），各自屬於不同的 token。依屬性分三種處置。顏色與字級即使只用一次也寫成 token，檢查腳本依寫法擋下色碼、`rgb()` 這類色彩函式，以及 `font-size`、`line-height` 的 px、rem、pt，理由是檢查只能依寫法判，數不了一個值代表幾個設計決定；腳本擋不到的寫法（色名、`font` 簡寫）要靠審查。間距、圓角、動畫時長這類屬性，同一個設計決定在兩處以上出現時寫成 token（這次的間距階）。版面尺寸與斷點只用一次、或用在取不到自訂屬性的位置（media query 的條件、宿主頁面上練習區以外的元素）時，留著字面值，取不到的位置在旁邊註明原因。字級另外分成尺寸階與功能字級兩層，因為「某一種用途要大一點」與「某一階要整體調大」是兩種範圍不同的調整；這個理由不限於字級，同一個藍綠色同時當按鈕底色與連結顏色、而兩種用途將來可能分開調整時，顏色也可以分成只放色值的一層與依用途命名、引用它的一層。這次的顏色 token 大多直接放色值、依用途命名，沒有分兩層。

重構的比對結果有三種：0 差異、差異都落在預期的屬性上、出現預期以外的差異。預期的屬性是這一批刻意要改變計算值的屬性，加上由它推導出的版面尺寸；只換寫法的批次（這次的顏色與線寬那一批）沒有預期的屬性，任何差異都歸到預期以外。比對腳本依「屬性、舊值、新值、class」分組，逐組確認屬性在這個範圍裡。比對的範圍是記錄下來的屬性、狀態（hover、按下、焦點、動態偏好、`pointer: coarse` 這類指標裝置）、量測寬度（每個斷點與容器查詢的區段各一個）、瀏覽器，以及快照腳本走得到的元素（`children` 走不進 shadow root）；範圍外的改動，比對得到的 0 差異是沒有量到。預期以外的差異依序分兩層判：差異來自 CSS 改變不了的狀態（腳本設定的 `<details>` 展開與否這類 DOM 狀態、讀值的時序），或同一個版本量兩次結果不同時，來自量測，不算改動造成的；差異落在 CSS 屬性上時，即使那個屬性不是這批改的，也先查它有沒有經由 `currentColor`、`var()` 或繼承連到這次的改動（`box-shadow` 沒寫顏色時用的是 `color` 的值）。其餘的差異是改動造成的，再讀規範判斷兩個值是否等價，等價的不算畫面改變（漸層裡的 `transparent` 與白色透明），不等價的是畫面確實改了，要回頭確認這個改變是不是想要的。比對驗的是兩個版本相同，兩個版本共有的錯誤（這次的整頁溢出）不會出現在比對結果裡，要靠截圖尺寸或另外的量測發現。

`!important` 與 id 加權都是用提高優先度贏過另一條規則。被它蓋過的規則屬於同一個元件自己的 CSS 時，替代的寫法是讀出那一條規則：改寫成不跟它衝突，或用剛好高過它、或同級而寫在它後面的選擇器勝出，並在規則旁寫出要贏過的是哪一條。被蓋過的是元件自己的 JavaScript 寫的行內樣式（`el.style.transform`）時，任何選擇器都贏不過它，改成讓 JavaScript 切換 class 或設定自訂屬性。要贏過的是所有規則時（`[hidden] { display: none !important }` 要蓋過每一條設定 `display` 的規則），讀不出單一的那一條，改寫成條件反轉（顯示用的規則加上 `:not([hidden])`），或留著 `!important`、在同一行加 allow 註解寫出原因。全站的減少動態效果重設（`*` 上的 `animation-duration`、`transition-duration` 帶 `!important`）也是這一種：它要蓋過現在與以後的每一條動態規則，新規則寫在 `no-preference` 的區塊外時，反轉寫法擋不住它，所以動態規則分散在很多份 CSS 或有第三方元件時留著 `!important`。這次能用反轉寫法，是因為練習頁的動態規則都在同一份 CSS 裡。

被蓋過的規則屬於宿主時，只替部分規則提高特定性，那幾條也會一起高過元件自己的其他 class 規則，元件內部的層疊就跟著亂掉（這次的 id 加權是七條規則加了 id、其餘沒有）；所以處置看宿主的 CSS 改不改得了、宿主的宣告帶不帶 `!important`、宿主有幾種：

- 宿主的 CSS 改得了、宣告是一般宣告：把宿主包進較低的 cascade layer，layer 的順序在特定性之前比，元件規則不必再跟宿主比特定性；代價是改宿主的載入方式會影響宿主的每一頁。
- 宿主的 CSS 改得了、宣告帶 `!important`：從宿主那一邊把元件的範圍排除（這次 `custom.css` 的做法），因為 `!important` 在比特定性之前就勝出，元件那一邊寫得再精確也輸。
- 宿主的 CSS 改不了、只有一種宿主、宣告是一般宣告而且特定性已知（例如 CMS 主題的 `.entry-content a`，(0,1,1)）：元件的每一條規則統一加上同一個根 class 當前綴，各規則之間的相對特定性不變，全部高過宿主那一條；代價是宿主改了選擇器時要重新比一次。
- 宿主的 CSS 改不了，而且宿主有很多種、特定性未知或宣告帶 `!important`：用 Shadow DOM 或 iframe 把元件跟宿主的層疊隔開。Shadow DOM 隔開的是宿主的選擇器，宿主設在祖先元素上的顏色、字級、行高仍然會被 shadow root 裡的元素繼承，要在 `:host` 重設會繼承的屬性。這次的重構沒有用到這一種。

layer 與特定性的取捨在 [CSS Layers 取代 specificity 戰](/report/css-layers-over-specificity/)。加權是否還必要可以直接量：拿掉加權、比較計算後的樣式，這個結論只對量測時在頁面上、而且量了那個狀態的元素成立，也只對量測的那一種宿主頁面成立，所以會受影響的選擇器，要把它的每一種變體都放進頁面（這次另外插入 `<a>` 形式的按鈕），也量 hover 這類狀態；元件嵌在幾種宿主頁面上時，每一種頁面各量一次。結論也只對量測時的宿主版本成立：宿主的主題是別人維護的第三方套件時，主題升級可能新增要靠加權才贏得過的連結規則，升級之後要重量一次。在場的元素都沒有改變時，層疊裡已經沒有規則要靠這個加權才贏得過；有元素改變時，逐一確認改變後的值是不是想要的結果。這次拿掉 id 之後改變的那一處，改變後的白底黑字才是想要的結果，id 加權原本讓主要按鈕 hover 時變成白底白字。

檢查腳本與量測腳本回報「沒有問題」時，算數的條件是它確實讀到了要檢查的對象：檢查腳本印出讀到的宣告數、對得上檔案大致的宣告數，並用已知會違規的舊檔跑一次正對照，正對照的輸入跟受檢的輸入是同一種形式（同樣是未壓縮的手寫 CSS，或同一條編譯流程的產物）；宣告數與違規來自同一次解析，被跳過的宣告不會計入，所以宣告數只抓得出一個宣告都沒讀到的情形，漏讀一部分要靠正對照涵蓋每一種語法形式；改寫選擇器的腳本印出它改寫了哪幾條規則，對得上預期的數量；字型的載入用網路回應與 `FontFace` 的狀態判，不用在沒有符合的字型時也回傳 `true` 的 `document.fonts.check()`。
