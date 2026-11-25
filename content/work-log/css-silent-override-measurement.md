---
title: "CSS 規則沒生效時的量測與成因：範圍重設的特定性與宿主樣式、container-type 與 subgrid、捲動陰影的覆蓋漸層"
date: 2026-11-24
description: "CSS 寫了卻沒有效果、瀏覽器也不報錯，例如字級改大之後看起來還是一樣小、內距設了卻貼著邊、元件嵌進 blog 主題之後多出外距或連結變色、subgrid 的列高被平分，或清單放得下、沒有溢出時捲動陰影漏出一塊灰色時"
tags: ["work-log", "css", "specificity", "subgrid", "playwright", "量測"]
slug: "css-silent-override-measurement"
---

2026-11-24 在 macOS 15.3、Chrome 上調整本站 SQL 練習頁的元件（vanilla JavaScript 產生 DOM，兩份手寫的 CSS：`practice.css` 與 `callout.css`，放在 Hugo 產生、套用 blog 主題的頁面裡）。每一輪由本站作者看元件展示頁（把每個元件的各種狀態排在同一頁、供檢視用的頁面）提出回饋，再改 CSS。量測用 Playwright 1.59.1 驅動的 Chromium 147.0.7727.15，沒有在 Firefox 與 Safari 上量。

這篇整理那一輪調整裡要量測才判得準的事：CSS 規則寫了卻沒有生效、瀏覽器也不報錯時，怎麼量出實際套用的值、分出規則是沒套上還是輸了；這一輪找出的成因，分別是帶 id 的範圍重設蓋掉元件的 class 規則、整條重設改成零特定性之後又輸給 blog 的主題與自訂樣式（而元件展示頁沒有載入它們，量不到這一類衝突）、`container-type` 讓 subgrid 失效、捲動陰影的覆蓋漸層不透明範圍比陰影窄。元件該長什麼樣、Microsoft 的 Metro 設計語言這個視覺方向怎麼選，不在這篇的範圍；同一輪的狀態配色對比在 [狀態色塊配色的對比量測：文字對色塊、色塊對背景、細標記對底色，以及紅綠色覺差異](/work-log/state-color-contrast-and-color-vision/)；元件契約的寫法在 [元件庫雙向約束方法論 - 設計端與工程端的雙向契約](/record/component-library-bidirectional-constraint-methodology/)。

## 判斷哪一條 CSS 規則生效：讀計算後的樣式與 Styles 面板

CSS 的層疊（cascade）在兩條宣告衝突時，依序比來源與重要性（`!important`）、cascade layer、特定性（specificity）與先後順序，選一條套用；元素的 `style` 屬性排在同一來源的選擇器規則之前。落選的那一條不產生錯誤、不產生警告，所以「改了沒效果」在畫面上看起來跟改之前差不多。從截圖只看得出「好像還是太小」「好像貼著邊」，看不出實際套用的值是多少、是哪一條宣告決定的。

瀏覽器算出來的值是判斷的依據，截圖只用來發現「好像不對」。這一輪的量測用了兩種讀法：

```js
// 在 Playwright 的 page.evaluate 裡執行；".sqlp-sql" 換成要查的元素的選擇器
const el = document.querySelector(".sqlp-sql");
const cs = getComputedStyle(el);
return {
  fontSize: cs.fontSize,                  // 屬性名用 camelCase：font-size 寫成 fontSize
  marginLeft: cs.marginLeft,
  gridTemplateRows: cs.gridTemplateRows,
  rect: el.getBoundingClientRect().toJSON(),  // toJSON 讓結果可以直接 JSON.stringify 存檔
};
```

`getComputedStyle` 回傳層疊決定之後的值（跟版面有關的屬性回傳的是排版之後的使用值），也就是計算後的樣式（computed style）；`getBoundingClientRect` 回傳版面排完之後的位置。算出來的值跟規則寫的不同，代表寫的那一條沒有決定這個值，成因要在 DevTools 的 Styles 面板上分：

| Styles 面板上那一條宣告    | 代表                                                                         |
| -------------------------- | ---------------------------------------------------------------------------- |
| 畫刪除線、旁邊沒有警告圖示 | 套上了，在層疊裡輸給另一條                                                   |
| 畫刪除線、旁邊有警告圖示   | 值無效，瀏覽器丟掉了                                                         |
| 沒有出現在這個元素的清單裡 | 選擇器沒對上，或那份 CSS 沒載入                                              |
| 灰字、旁邊有資訊圖示       | 套上了、值也對，但這個元素上沒有版面效果（例如 `margin-top` 寫在行內元素上） |

這兩個 API 在 DevTools 的 Console 也能直接跑，Playwright 的用處是同一段量測可以用 `page.setViewportSize` 換成 1440px、390px、2560px 幾種寬度各跑一次，結果寫進終端機，不必每次手動拉視窗。

## 範圍重設的特定性：低於元件的 class 規則、又要贏過宿主樣式（SQL 從 16px 變成 13.76px）

練習頁的 CSS 開頭有一段全域重設，範圍限定在練習區 `#sql-practice` 裡，用來清掉瀏覽器預設的段落與清單外距、統一行內 `code` 的字級：

```css
#sql-practice p, #sql-practice dl { margin: 0; }
#sql-practice code { font-size: 0.86em; }
```

元件規則都用 class 寫，例如解析區（每個選項底下說明它為什麼推薦或不推薦的文字）`.sqlp-analysis { margin: 12px 12px 0; }`、SQL 區塊 `.sqlp-sql code { font-size: inherit; }`。本站作者回報 SQL 放大到 16px 之後看起來還是偏小，「不推薦」那塊選項磚（每個選項的方塊，分標頭、SQL、解析三層）的灰色解析區蓋住了磚的邊線。量出來的值：

| 元素                               | 規則寫的             | 實際套用的                      |
| ---------------------------------- | -------------------- | ------------------------------- |
| SQL 區塊裡的 `<code>`              | 跟著 `<pre>` 的 16px | 13.76px（16 × 0.86）            |
| 解析區 `<dl>` 的左右外距           | 12px                 | 0，左右邊緣跟磚的邊緣同一個位置 |
| 只有文字的選項裡的 `<p>`，左右外距 | 12px                 | 0                               |

成因是選擇器的特定性。`#sql-practice code` 是一個 id 加一個元素，特定性 (1, 0, 1)；`.sqlp-sql code` 是一個 class 加一個元素，(0, 1, 1)。比較從 id 那一位開始，id 多的那一條直接贏，跟規則寫在檔案的哪個位置、class 有幾個都無關。這段重設的特定性因此高過所有用 class 寫的元件規則：凡是元件用 class 設的外距與字級，只要元素的標籤名對得上（`code`、`p`、`dl`），都被它蓋掉。瀏覽器因此從磚的邊緣開始畫灰色的解析區，把 1.5px 的邊線蓋在底下。同一份 CSS 裡用 id 開頭的 `#sql-practice :focus-visible` 特定性是 (1, 1, 0)，同樣蓋掉了元件自己的焦點宣告（輸入框的 `outline: none` 沒有生效），所以以 id 開頭的全域規則，不論後面接的是元素、偽類還是 `*`，都屬於同一個問題。

重設的特定性要低於元件的 class 規則 (0, 1, 0)，又要贏過它要清掉的那些宿主樣式。只清瀏覽器預設時，整條包進 `:where()`：`:where()` 裡的選擇器不計入特定性，`:where(#sql-practice) :where(p, dl)` 是 (0, 0, 0)；瀏覽器預設屬於使用者代理（user agent）來源，作者寫的一般宣告都贏過它，特定性 0 就清得掉。在元件展示頁上量，這樣寫之後 SQL 是 16px，解析區兩側各內縮 12px，邊線露出來了。

元件展示頁只載入練習頁自己的兩份 CSS。正式頁面的 head 另有三份宿主樣式，都屬於作者來源，跟練習頁的 CSS 同一層，要比重要性、特定性與先後：

| 宿主樣式               | 會碰到練習區的規則                                                                                                                    | 特定性與重要性                                       |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| blog 主題 `herman.css` | `li` 的上外距、標題的下外距與行高、標題後面任何元素（`:is(h1, h2, h3, h4) + *`）的上外距、`code` 的內距與底色、`table, th, td` 的框線 | (0, 0, 1)；`nav a` 的右外距、`pre code` 是 (0, 0, 2) |
| 內嵌的 `custom.css`    | `a` 的顏色與底線、`h4` 與 `h5` 的字級、外距、框線                                                                                     | (0, 0, 1)，帶 `!important`                           |
| 內嵌在 head 的其他樣式 | `details`、`summary` 的內距、框線、負外距，`summary::before` 的「▶」                                                                  | (0, 0, 1) 到 (0, 1, 2)                               |

判斷的方法是把展示頁複製一份，在練習頁的 CSS 前面依正式頁面的順序加載這三份，跟沒有加載的展示頁逐一比較每個元素的外距、內距、字級、行高、顏色、底色、框線與 `display`。三份都加載時有 574 個值不同：連結變成 `#9dc4e8`、資料表結構的 `details` 多了外距與框線、摘要列被負外距往外推。

處置依宿主規則的形態分三種。主題的元素規則沒有 `!important`，練習頁的 CSS 又排在主題之後，所以重設的範圍包進 `:where()`、元素留在外面，讓每一條的特定性跟主題對應的那一條相同，同特定性時排在後面的贏：

```css
:where(#sql-practice) :is(h1, h2, h3, h4) { margin: 0; font-size: revert; line-height: inherit; }  /* (0,0,1) */
:where(#sql-practice) :is(h1, h2, h3, h4) + * { margin-block-start: 0; }                        /* (0,0,1) */
:where(#sql-practice) :is(p, dl, ul, ol, li) { margin: 0; }                                     /* (0,0,1) */
:where(#sql-practice) :is(ul, ol) { padding-inline-start: revert; }                             /* (0,0,1) */
:where(#sql-practice) code { font-size: 0.9em; padding: 0; background-color: transparent; }    /* (0,0,1) */
:where(#sql-practice) pre code { display: inline; padding: 0; overflow-x: visible; }           /* (0,0,2) */
:where(#sql-practice) nav a { margin-right: 0; }                                               /* (0,0,2) */
:where(#sql-practice) :is(table, th, td) { border: revert; border-collapse: revert; padding: revert; }  /* (0,0,1) */
:where(#sql-practice) table { width: revert; }                                                 /* (0,0,1) */
```

`revert` 寫上去時，作者寫的宣告全部不算，這個屬性改由使用者樣式或瀏覽器預設決定；那一層也沒有宣告時，會繼承的屬性取父元素的值，不會繼承的取初始值。這裡用在練習頁自己沒有另外設定、只要撤掉主題那一條的屬性。標題的 `line-height` 寫 `inherit` 或 `revert` 結果相同（瀏覽器預設沒有替標題設行高，`revert` 之後同樣繼承練習區的 28px），寫 `inherit` 是讓意圖一眼看得出來。

`custom.css` 的那幾條帶 `!important`，作者來源裡 `!important` 的宣告不論特定性與先後，都贏過一般宣告，重設寫得再精確也輸。宿主樣式也是這個 repo 的檔案，所以處置放在宿主那一邊：`custom.css` 的 `a`、`h4`、`h5` 與 head 內嵌的 `details`、`summary` 各條，選擇器後面加 `:where(:not(#sql-practice *))`，排除練習區裡的元素；`:where()` 不計入特定性，這幾條對其他頁面的元素特定性不變。宿主樣式不由元件庫控制時（嵌進第三方 CMS、元件庫有很多個宿主），這兩種處置都做不到，要改用 Shadow DOM 或 iframe 把元件跟宿主的層疊隔開，這一輪沒有實測。有了這條排除，練習頁元件規則上原本用來贏過宿主的 id 加權就用不到了，隔天的重構量出這一點之後拿掉 id 加權，同一天另外把這條排除擴大到練習總覽頁的清單與文章結尾的練習入口；怎麼量出 id 加權已經不必要，在 [CSS 改用 token 取值的重構與驗證：逐元素比對計算後的樣式、字級分成尺寸階與功能字級（primitive 與 semantic token）、!important 與提高特定性的 id 選擇器的替代寫法](/work-log/css-token-refactor-verified-by-computed-style-diff/) 的〈提高特定性的 id 選擇器〉。

這一頁沒有用 cascade layer（`@layer`），理由是兩種包法都不合用：把主題包進 layer 要改全站主題的載入方式，影響每一頁；只把練習頁的 CSS 包進 layer，沒分層的主題會一律贏過它（layer 只在一般宣告之間比，帶 `!important` 時順序反過來，分層的 `!important` 贏過沒分層的）。宿主自己願意包進 layer 時，layer 是比對齊特定性更穩的做法，取捨在 [CSS Layers 取代 specificity 戰](/report/css-layers-over-specificity/)；宿主用帶 class 的選擇器（例如 `.post-content li`，(0, 1, 1)）時，重設贏得過它就會一起贏過元件的 class 規則，只靠特定性安排不了，也要改用 layer 或從宿主那一邊排除。

改完在兩種頁面上重新量測：沒有宿主樣式的展示頁，新舊 CSS 下每個元素的值相同；三份宿主樣式都加載的那一份，除了寬度與高度（主題的 CSS 限制了 `body` 的寬度，連帶改變換行的位置）與一個 `margin-left: auto` 算出的值，其餘屬性跟沒有宿主樣式時相同。用 id 限定範圍（只作用在練習區裡）跟用 id 提高特定性是兩件事，寫成 `:where(#id)` 時範圍限定在那個元素裡，特定性不增加。

## container-type 與 subgrid 在同一個元素上：兩欄磚的列高被平分

寬螢幕上，四個選項排成 2×2，每塊磚分三層（標頭、SQL、解析），想讓同一排兩塊的三層各自對齊，做法是 subgrid：外層格線 `.sqlp-tiles` 定義列，每個 `<li>` 與裡面的磚都用 `grid-template-rows: subgrid` 沿用外層的列。截圖上 SQL 區被壓成一行高，內容被裁掉。量外層與兩層子元素的列：

```text
.sqlp-tiles          grid-template-rows: 150.656px 150.656px 150.656px 156.328px 156.328px 156.328px
li（第一個）          grid-template-rows: 72px 24px 344px
.sqlp-tile（li 裡面） grid-template-rows: subgrid
```

外層的前三列一樣高，代表外層格線計算列高時沒有用到磚裡三層各自的高度：每個 `<li>` 是一個跨外層三列的單一格線項目，它的高度平均分到三列。`<li>` 自己算出了 72px、24px、344px 三列，代表它是一個獨立的格線，沒有變成 subgrid。中間那一列的 24px 是 SQL 程式碼區上下內距的合計：程式碼區可以水平捲動（`overflow-x: auto`），捲動容器在格線裡的自動最小高度是 0，所以它分到的只有內距。

`<li>` 上有另一條規則：`container-type: inline-size`，用來切換解析區的窄版（容器查詢（container query）依磚的寬度，在 420px 以下把兩欄的表改成單欄）。`container-type` 除了宣告容器，還讓元素建立獨立的格式化脈絡（formatting context），裡面的版面跟外層分開計算。CSS Grid Layout Module Level 2 定義 subgrid 時寫明：元素被迫建立獨立的格式化脈絡時，`subgrid` 的使用值退回 `none`，也就是退回成自己的獨立格線。把 `<li>` 的 `container-type` 改成 `normal`（初始值：元素不當尺寸查詢的容器）之後列高立刻恢復，跟這條定義一致。

會讓元素被迫建立獨立格式化脈絡的不只 `container-type`。在 Chromium 147 上逐一套在 `<li>` 上量：`contain: layout`、`contain: paint`、`contain: content`、`contain: strict`、長清單常用來省重繪的 `content-visibility: auto`、`position: absolute` 都讓 subgrid 退回；`contain: size`、`contain: inline-size`、`contain: style`、`overflow: hidden`、`overflow: clip` 單獨使用時不影響。

2×2 只在主區夠寬時出現，`sqlp-main` 是主區的容器名稱。門檻 1480px 依 SQL 的字級、字型與練習頁的 SQL 排版器（把題目的 SQL 依行寬上限換行的格式化程式，上限 72 字元）算出：主區寬 1480px 時每塊磚寬 (1480 − 12) / 2 = 734px（12px 是兩塊磚之間的間距），扣掉內縮與內距約 678px，16px 的等寬字（SF Mono、Menlo 一個字元約 0.6em）一行放得下約 70 字元，所以排版器排到 71、72 字元的那幾行仍會換行。換了字級、字型或行寬，這個門檻要重算。734px 遠大於解析區切換窄版的 420px，排成 2×2 時解析區不會切到窄版，所以修法是在 2×2 的條件裡把 `<li>` 的 `container-type` 設回 `normal`：

```css
/* 外層 .sqlp-tiles 另有 display: grid 與兩欄的 grid-template-columns；磚 .sqlp-tile 自己也是 grid-template-rows: subgrid */
@container sqlp-main (min-width: 1480px) {
  .sqlp-tiles > li { display: grid; grid-row: span 3; grid-template-rows: subgrid; container-type: normal; }  /* span 3 對應磚的三層 */
}
```

改完外層的列各自等於那一排兩塊裡較高的一層（第一排是 72px、336px、356px），兩塊的 SQL 區等高、解析區從同一條線開始。同一個元素同時要當 subgrid 又要當容器查詢的容器時，兩者衝突；容器查詢的容器要改放在磚裡面不接外層格線的元素上（例如解析區本身），或像這一頁一樣，只在用不到那個容器查詢的條件裡把 `container-type` 設回 `normal`。

## 捲動陰影的覆蓋漸層：不透明範圍比陰影窄時，清單放得下也漏出灰塊

導覽列放不下全部項目時要水平捲動；導覽列的邊緣有一道捲動陰影（scroll shadow）時，讀者看得出那一側還有內容。捲動陰影只用 CSS 背景的兩種附著方式就畫得出來，不需要 JavaScript。`background-attachment` 的預設值是 `scroll`：背景固定在元素上、不隨內容捲動，這一層漸層就是陰影。另一層刻意寫成 `local`，背景跟著內容捲動，顏色取容器的底色，下文稱覆蓋漸層：它疊在陰影上方，把陰影蓋住（它是背景層，不是 CSS 的 `mask` 屬性）。

```css
.sqlp-pivot-items {
  overflow-x: auto;
  background:
    linear-gradient(to right, var(--sqlp-bg) 28px, transparent) left / 40px 100% no-repeat local,   /* 覆蓋漸層：完全不透明 28px */
    linear-gradient(to left,  var(--sqlp-bg) 28px, transparent) right / 40px 100% no-repeat local,
    linear-gradient(to right, rgba(255, 255, 255, 0.32), transparent) left / 28px 100% no-repeat scroll,  /* 陰影：寬 28px */
    linear-gradient(to left,  rgba(255, 255, 255, 0.32), transparent) right / 28px 100% no-repeat scroll,
    var(--sqlp-bg);
}
```

內容捲到一側的盡頭時，那一側的覆蓋漸層跟著內容移到邊緣，把陰影蓋住；還沒捲到時，覆蓋漸層在內容的另一端，陰影露出來。

第一版的覆蓋漸層寫成 `linear-gradient(to left, var(--sqlp-bg) 30%, transparent)`、寬 40px，陰影寬 28px。本站作者在 2004px 寬的螢幕上看到導覽列右端有一塊灰色，而那個寬度下全部項目放得下，沒有溢出。成因在覆蓋漸層的不透明範圍：40px 的 30% 是 12px，只有離右緣 12px 以內完全不透明，12px 到 28px 之間覆蓋漸層逐漸透明，那一段的陰影沒有被蓋住，畫面上看得到。沒有溢出時兩層的位置完全重疊，看得到的那一段就是那塊灰色。

修法是讓覆蓋漸層完全不透明的寬度至少等於陰影的寬度，寫成 `var(--sqlp-bg) 28px`，也就是上面那一段 CSS。手機版 SQL 程式碼區用同一個做法、同一個比例（寬 24px 的覆蓋漸層，完全不透明 7.2px，對 12px 的陰影），覆蓋漸層完全不透明的寬度一起改成 12px。這類「用一層蓋另一層」的做法，蓋的那一層的不透明範圍要涵蓋被蓋那一層的全部範圍。這個缺口只在沒有溢出的寬度看得到：有溢出、還沒捲到盡頭時，那一側的陰影本來就該露出來，沒蓋住的那一段跟陰影連在一起，看起來就是正常的陰影。

這組量測在整數的裝置縮放比（1、1.5、2）下成立。系統縮放 125% 再加上頁面縮放時，右緣最後一列裝置像素仍量到亮度約 20/255 的髮絲線，修法沒有驗證。Windows 對比主題這類強制色彩模式會把漸層換成 `none`，兩層都消失，不會漏灰，捲動提示也一起不見。

## 判斷標準：計算後的樣式、範圍重設、宿主樣式、subgrid 與容器查詢、捲動陰影

- **畫面看起來沒變**：`getComputedStyle` 讀到的值跟自己寫的規則不同時，寫的那一條沒有決定這個值；Styles 面板上畫刪除線而沒有警告圖示是輸了，有警告圖示是值無效，沒有出現是沒套上，灰字是套上了而沒有版面效果。從截圖分不出這幾種情形。
- **以 id 開頭的全域規則**：`#容器 元素`、`#容器 :偽類`、`#容器 *` 的特定性都有一個 id，高過所有用 class 寫的元件規則，跟它同一個屬性、同一類元素的元件宣告不生效，瀏覽器也不報錯。
- **重設的特定性與宿主樣式**：雙方都沒有用 `!important` 與 cascade layer 時，整條包進 `:where()` 的重設特定性是 0，只贏得過瀏覽器預設；寫成 `:where(#容器) 元素` 時特定性跟宿主的元素規則相同，排在後面的那一份 CSS 勝出。宿主的宣告帶 `!important` 時，重設的特定性與先後都比不過，要從宿主那一邊把範圍排除；宿主用帶 class 的選擇器、或有一方用了 `@layer` 時，勝負由 layer 或更高的特定性決定，對齊特定性沒有用。
- **展示頁與正式頁面載入的 CSS 不同**：宿主樣式只在正式頁面載入時，在展示頁上量不到它們造成的衝突；展示頁的複本依正式頁面的順序加載 head 裡的全部樣式來源（含內嵌的 `<style>`）之後，跟沒有加載的展示頁之間的計算後樣式差異，就是宿主造成的衝突。只加載其中一份時，其餘幾份的衝突照樣量不到。
- **subgrid 項目被迫建立獨立格式化脈絡**：`container-type`、`contain: layout`／`paint`／`content`／`strict`、`content-visibility: auto`、絕對定位落在 subgrid 項目上時，subgrid 退回成獨立格線，外層被它跨過的那幾列平分它的高度；`contain: size`、`contain: style`、`overflow: hidden` 單獨使用時不影響。
- **覆蓋漸層完全不透明的寬度小於陰影寬度**：在清單放得下、沒有溢出的寬度，陰影的一段沒有被蓋住；不透明的寬度等於或大於陰影寬度時，在整數裝置縮放比下，有溢出與沒有溢出的寬度都乾淨。
