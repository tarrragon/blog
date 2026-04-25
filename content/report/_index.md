---
title: "Report — 開發過程的事後檢討"
date: 2026-04-25
description: "blog 開發過程中，把實際遇到的版型 / 整合 / 框架共處等情境，整理成「應該怎麼做、沒這樣做會有什麼麻煩」的事後檢討。每篇皆為正向指引，幫助下一輪同類任務跳過反覆試錯。"
tags: ["report", "事後檢討", "工程方法論"]
---

## 這個資料夾是什麼

`content/report/` 收錄 blog 開發過程中累積的事後檢討文件。每篇對應一個具體情境，不寫「做錯了什麼」，而寫「這需求應該怎麼做、沒這樣做會有什麼麻煩」。

每篇結構統一：

| 區塊           | 內容                                   |
| -------------- | -------------------------------------- |
| 情境           | 任務背景與當時的限制                   |
| 理想做法       | 系統層的解法（為什麼這個方向是對的）   |
| 沒這樣做的麻煩 | 略過此做法會在後續遇到的具體問題       |
| 判讀徵兆       | 下次遇到同類情境時、可以提早識別的訊號 |

---

## 第一輪規劃：搜尋頁開發過程的檢討（待補完）

以下六篇大綱來自「在 blog 加上 Pagefind 站內搜尋」這次任務的反覆試錯。先列大綱、後續補完內文。

### 1. 在外部組件上加客製功能的方法選擇

**涵蓋情境**

- Pagefind 預設抓站名 `<h1>Tarragon</h1>` 當搜尋結果 title。解法：`--root-selector main` 限定索引邊界，讓組件只看 main 內容。
- 把 `.pagefind-ui__filter-panel`（fieldset）從 `.pagefind-ui` 搬到外部 aside 後，UA 預設邊框跑出來。原因是失去 `.pagefind-ui--reset` 的覆寫脈絡 — 在落腳處重新關掉 UA 樣式即可。
- Pagefind 的 svelte hash class 以 `.x.svelte-yyy.svelte-yyy` 雙寫提升 specificity 到 30，一般選擇器 specificity 20 蓋不過。我們也雙寫（`.x.x`）或在關鍵屬性用 `!important`。

**理想做法骨架**：找組件最外層的「索引邊界」與「重置邊界」，在這兩條邊界上做客製，不深入組件內部。

### 2. 跨 viewport 雙模式 UI 的物理空間預算

**涵蓋情境**

- Filter sidebar 在中等寬度視窗看不見：當初取 `768px` 當 breakpoint 沒做空間計算。
- 真正的最小寬度推算：`main 70ch ≈ 720px` + `filter 400px` + `gap 32px` + `body padding 128px` ≈ **1280px**。安全門檻取 `1400px`。
- 用 `matchMedia + appendChild` 在「左側 aside」與「pagefind 原生 drawer」兩個 slot 之間搬同一個 DOM 節點，避免複製造成 state 分裂（checkbox 勾選狀態只活在一份節點上）。

**理想做法骨架**：先列出每個元素的固有尺寸與 gap、加總得最小可行寬度、breakpoint 從這個數字往上取一個安全餘裕。

### 3. 視覺對齊用單一真實來源

**涵蓋情境**

- H1、search input、filter slot padding-top、scope 高度 — 四處要共用同一組視覺 token。寫死數值會在每次調整時忘記同步。
- 三個 CSS 變數定義在 `body.page-search`：`--search-title-h`、`--search-form-h`、`--search-gap`，多處 `calc()` 引用。
- 利用 Pagefind 的 `--pagefind-ui-scale: 1.0`，讓 input 自然渲染為 64px、剛好對齊我們設定的 `--search-form-h`；把組件內部的尺寸 token 拉到我們的設計系統。
- Scope UI 的高度受字型 / 換行影響、不可預測 — 用 `ResizeObserver` 量測寫回 `--search-scope-h`，drawer 的 `margin-top` 與 filter slot 的 `padding-top` 都吃這個變數。

**理想做法骨架**：可預測的尺寸用 CSS 變數、不可預測的（runtime 動態）用 `ResizeObserver` 寫回變數。**值的定義位置只能有一處。**

### 4. 拓樸理解先行於 CSS 規則

**涵蓋情境**

- 假設 `.pagefind-ui__drawer` 是 `.pagefind-ui` 的直接子節點 → 實際它在 `<form>` 裡面。CSS Grid 的 `grid-row` 設了卻不生效，因為 form 與 drawer 共用一個 box。
- 用 `playwright browser_evaluate` 直接讀 live DOM 的 parent chain 與 computed style，比靜態 CSS 推理快得多。
- `display: contents` 串接有邊界 — 不能跨越 form 的盒子把 drawer 提升到外層 grid。

**理想做法骨架**：寫 CSS 之前先看真實 DOM tree（不靠 class name 推測層級）、確定哪些元素是 grid item、哪些是子盒子內部的元素。

### 5. 與 framework-managed DOM 共處的隔離原則

**涵蓋情境**

- 把 scope UI 注入 `.pagefind-ui` 的 form 與 drawer 之間 — Svelte 在使用者輸入後重繪、清掉外加 children。
- 把客製 UI 留在 framework 邊界外，用 CSS（absolute + 對 framework 元素加 `margin-top` 讓位）控制視覺位置，避免與框架的渲染週期競爭。
- 必要的 DOM 移動（filter-panel 在兩 slot 切換）只搬「節點本身」、不動「節點內部」 — 框架對節點內部還能照常 patch。

**理想做法骨架**：客製 UI 與 framework UI 各自有自己的 DOM 邊界。要共存就用 CSS 控制位置與 spacer，不要在框架的 children 列表裡塞東西。

### 6. 資訊架構決策：排序與語意定位

**涵蓋情境**

- Filter 順序：`type`（選項少）放前、`tag`（選項多）放後 — 短清單優先讓使用者快速 scan。預設按字母順序的取值有違使用情境。
- Search scope（標題 / 內文 / 全部）是**搜尋模式（mode）**，不是 facet。語意上跟 type/tag filter 屬於不同層級，UI 位置也分開（scope 在 input 旁邊，filter 在 sidebar）。
- 覆寫成本評估：當客製需要對抗 UA 預設 + 跨瀏覽器相容性 + framework 內部 CSS 三層時，停下來重新評估「真的需要嗎」。本案決定接受 Pagefind 原本的 disclosure 三角圖示，避免無止盡的覆寫戰。

**理想做法骨架**：UI 順序由使用者掃描成本決定、語意層級不同的元素放在不同 UI 區域；對外部組件的覆寫深度有上限，達到後接受原設計。

---

## 第二輪補充：開發方法論與工具選擇（待補完）

第一輪六篇聚焦在「具體版型與整合問題」。以下九篇是另一個視角：**開發過程本身的方法論與決策**。

### 7. 量測值缺一不可：依賴未測量值會錯位

**涵蓋情境**

- Filter 的 padding 一直對不準 — 因為右邊元件（H1、search input、scope）的高度沒有被精確測量、就嘗試在左邊用估計值對齊。
- 對齊本質上是「同一條基準線在多個元素上重現」 — 任何一個元素的高度沒有確定值，整條線都靠不住。
- 解法：每個參與對齊的元件都要有「來源明確的高度數字」 — 寫死的 token 或 `ResizeObserver` 量測寫回變數，二選一。

**理想做法骨架**：把對齊問題當作「線性方程組」來看，每個元件貢獻一個未知數；任何未知數沒解出來，整組就無解。

### 8. 置中元件與絕對定位元件並存：用疊層而非排擠

**涵蓋情境**

- 中央欄（main 70ch 置中）跟側邊 filter（指定位置）需要並存。
- 若把 filter 放進 main 的 layout 流（grid / flex），就會擠壓中央欄、讓置中失準。
- 解法：filter 用 `position: absolute` 跳出 layout 流；中央欄完全不知道 filter 存在、繼續維持自己的置中。
- offset parent 的選擇：filter 的 `position: absolute` 以 main（或 search-shell）為定位基準，但**不參與其 layout 計算**。

**理想做法骨架**：layout 流負責「以內容驅動的尺寸」；絕對定位負責「在 layout 流之上額外貼上的元件」。兩者用疊層而非排擠的方式共存。

### 9. 同一個元件在三種互動狀態下顯示位置不同的 root cause

**涵蓋情境**

- 新增 scope UI 後：初始載入位置 A、點輸入框後位置 A、輸入字後位置 B（變到頁尾）。
- 三種狀態 = 三組 layout 結果，根因不在 scope UI 本身，而在**周圍環境的尺寸隨狀態改變**：drawer 在 form 內、輸入字後 form 撐大、scope 被推到下方。
- 診斷方法：把「元件位置」拆成「定位基準」與「基準的位置」兩層。位置變化先確認哪一層在動。

**理想做法骨架**：當元件「跟著狀態飄」，不是元件本身的問題，是它**所依賴的錨點本身在動**。先定位錨點。

### 10. 從色塊 placeholder 開始的漸進式 UI 除錯

**涵蓋情境**

- 想做出「左側 filter + 右側結果」的版型 — 先放一個紅色色塊代替 filter、寫死寬度 400px、底色明顯。
- 色塊先確認 grid / flex / absolute 是否如預期排在該在的位置；確定後再串實際內容。
- 對比一次組裝完整 UI：版型錯時 debug 困難（色彩、字、邊距全部一起出問題，不知道根因）。

**理想做法骨架**：UI 除錯的最小可驗證單位是「一個有顏色的盒子」。版型先用盒子確認，內容後填。

### 11. 在開發循環裡早一點用 playwright 看真實結果

**涵蓋情境**

- 多次「靜態 CSS 推理 → 試錯 → 截圖檢查 → 再試」的循環裡，最快定位到根因的那次是用 `playwright browser_evaluate` 直接讀 DOM tree、computed style、bounding rect。
- 例：發現 drawer 是 form 的 child（不是 sibling）— 純看 CSS 推不出來、看 live DOM 一眼就明白。
- 早一點用 = 試錯次數更少、心智負擔更輕；不用每改一次都靠視覺猜。

**理想做法骨架**：當 CSS 行為與預期不符 ≥ 2 次，就應該停止靜態推理、改用 playwright 讀 live DOM。工具的價值是「縮短診斷迴圈」、不是最後手段。

### 12. 排版精度的工具選擇：CSS-only vs JS-assisted

**涵蓋情境**

- 純 CSS 適合處理：**可預測的固定尺寸**（H1 height 寫死）、**靜態 layout**（grid template areas）、**rest-context 重置**（border 0、list-style none）。
- JS 適合處理：**runtime 才知道的尺寸**（scope 高度依字型換行而異 → ResizeObserver）、**狀態化 DOM 移動**（filter slot 兩處切換 → matchMedia + appendChild）、**post-filter**（scope mode 對結果做 regex 過濾）。
- 邊界誤判的代價：硬要 CSS 解決 runtime 問題會反覆試錯；硬要 JS 解決 layout 問題會跟 framework 渲染競爭。

**理想做法骨架**：問「這個值在 build time 能定下來嗎？」— 能 → CSS；不能 → JS 量測寫回 CSS 變數。問「這個 DOM 變動是 framework 管的嗎？」— 是 → 不要動；不是 → 才用 JS。

### 13. 元件邊界與 JS 操作的影響範圍

**涵蓋情境**

- JS 操作 DOM 時若元件邊界不清楚，容易誤動到框架管理的部分、引發超乎預期的副作用（例如 scope UI 被注入 form 內，被 Svelte 重繪清掉）。
- 反例：filter slot 切換只搬「filter-panel 整個節點」，不動節點內部；節點內部的 state（checkbox 勾選）由 framework 維護。
- 元件邊界 = 「我可以動什麼、不可以動什麼」的契約。JS 操作前要先界定。

**理想做法骨架**：JS 操作前列清楚「此次動的是哪個元件、它的邊界在哪、它的 state 由誰維護」。動的範圍越小越安全。

### 14. DOM 選擇與作用域的精準度

**涵蓋情境**

- Scope filter 的 selector 寫成「所有 result」時，邊界沒寫對的話會誤傷其他元素（例如把 radio 選單一起隱藏）。
- MutationObserver 範圍過大會頻繁觸發、可能在 layout 還沒穩時就跑邏輯，造成短暫的視覺錯位。
- 精準度 = selector 涵蓋的「最少必要範圍」 + observe 的「最少必要事件」。寬泛換來方便、但代價是難以預測的副作用。

**理想做法骨架**：selector 從最具體（`.pagefind-ui__result-title`）開始、有需要再放寬；observer 從最小範圍（特定 results 容器）開始、有遺漏再擴大。寧可調整一次、也不要起始就 catch-all。

### 15. 用前端測試把排版問題自動化

**涵蓋情境**

- 排版問題傳統靠人眼檢查、容易遺漏（特別是邊界寬度、interaction state）。
- Playwright 可以寫成測試：開特定 viewport、輸入字、斷言「scope 元件在 input 與 results 之間」。
- 測試替代了「手動檢查 + 手動截圖」的循環，讓版型回歸可被機器發現。
- 適用情境：對版型敏感的頁面（搜尋頁、文章 hero、首頁）、跨 viewport 的響應式檢查。

**理想做法骨架**：當一個版型被 debug 兩次以上，就值得寫成 playwright 測試把規範固定下來。下一次有人改 CSS 時，測試會立刻指出哪個假設被破壞。

---

## 第三輪補充：指令理解與澄清時機（待補完）

從這次對話本身回看：哪些指令類型、我下次該先停下來確認再執行。每篇用「下次看到這類指令我應該怎麼處理」的角度寫，不歸咎指令本身。

### 16. 空間 / 尺寸類指令的澄清時機

**涵蓋情境**

- 「padding 對齊到搜尋欄下緣」沒給數字 — 我用估算寫死、多輪試錯才用 `ResizeObserver` 量回。
- breakpoint 取值（768 / 1199 / 1400）我自決、視窗落在過渡區才被指出。
- 對比：filter 寬度 400px 是少數有明確數值的情境，那次一次到位。

**理想做法骨架**：聽到「對齊 X」「擺在 Y 旁邊」但沒給數字時，**先列出計算過程或假設**讓使用者確認，不直接寫死。如：「我會用 H1 64px + form 68px = 132px 當基準，OK 嗎？」

### 17. 元件相對位置類指令的澄清時機

**涵蓋情境**

- scope UI 一開始放搜尋框上方、被你指正才知該放下方 — 我以為「在搜尋框附近」就好。
- 「filter 在主欄左側」其實是側邊絕對定位、不是 grid 一個 column — 我用 grid 試了三輪。

**理想做法骨架**：聽到「X 在 Y 旁/上/下」**先用文字畫個 layout 草圖**（「H1 / input / scope / results 由上到下；filter 在 main 左外側絕對定位」），讓使用者確認後再開工。

### 18. 隔離程度類指令的澄清時機

**涵蓋情境**

- 「不動 pagefind 行為」我多次把 scope 注入 pagefind DOM — 沒分清「行為」是指程式邏輯還是 DOM 結構。
- 「左右不要在同一層」我先理解成 DOM 層級、其實是指 layout flow 互不影響。

**理想做法骨架**：聽到「隔離」「不要動 X」**先確認邊界是 DOM 結構、layout flow、state、還是 framework 管轄區**。每種邊界的實作策略不同。

### 19. 覆寫深度的成本告知

**涵蓋情境**

- 移除 disclosure 三角寫了 6 條 CSS 跨 3 種瀏覽器的 pseudo-element — 最後使用者說「成本太高、還原回去」。

**理想做法骨架**：客製可能對抗 UA + 跨瀏覽器 + framework 三層時，**先報需要寫多少規則 / 哪幾條、是否可能有殘留風險**，讓使用者判斷值不值，再開工。

### 20. 同方向反覆失敗的轉折點

**涵蓋情境**

- display:contents 串接、specificity 雙寫、!important 加碼 — 同一個 grid 思路反覆三次後使用者才說「思路錯了」。

**理想做法骨架**：**第 2 次同方向失敗就停下來回報「假設可能錯了，要不要換思路」**，不要第 4 次失敗才被使用者打斷。失敗 2 次大多是底層假設有問題。

### 21. 「可決定」與「該先確認」的邊界

**涵蓋情境**

- breakpoint 1400px / filter 順序 type→tag / scope-h 預設 56px — 這些都是我自決後才被肯定或否定。
- 影響使用者體驗的 visible 數字、順序、文字屬於「該先確認」；純技術選擇（用 grid 或 flex）屬於「可決定」。

**理想做法骨架**：寫死任何**使用者會看到的數字 / 順序 / 文字**之前，**先給選項讓使用者點頭**。技術實作細節可以自決。

### 22. 「先還原」「先重來」類退出指令的處理

**涵蓋情境**

- 「先還原回去，先不做這個變更」我立刻刪 CSS，沒先 commit checkpoint，後續想比較沒得比。

**理想做法骨架**：聽到「還原 / 重來」**先問「還原到哪個 commit？要不要先 commit 一個 checkpoint 再動，方便日後比對？」**

### 23. 驗證方法的選擇時機

**涵蓋情境**

- 多輪「靜態 CSS 推理 + 截圖溝通」反覆試錯 — 啟 server 後我用 `playwright browser_evaluate` 一查就找到 drawer 在 form 內。

**理想做法骨架**：靜態推理 ≥ 2 次失敗就**主動提「啟個 server，我用 playwright 看 live DOM 比較快」**，不要繼續猜。Playwright 是縮短診斷迴圈的工具、不是最後手段。

---

## 第四輪補充：程式碼結構與重構機會（待補完）

從現在的 `layouts/_default/search.html` 看回去：哪些寫法可以更簡單、哪些結構性決策可以更乾淨。每篇從「現狀 → 更簡單的做法 → 不重構的麻煩」三層寫。

### 24. CSS Layers 取代 specificity 戰

**涵蓋情境**

- 多處 `!important`、`.x.x` 雙寫只為了蓋過 svelte hash class 的 specificity 30。
- 用 `@import url('pagefind-ui.css') layer(pagefind)` 把 pagefind 整包降到 layer 內，我們 unlayered CSS **自動贏過 layered CSS 不論 specificity**。

**理想做法骨架**：把外部組件的 CSS 用 `@layer` 包進降權層，自家 CSS 留在 unlayered（最高權）。一次設定、所有 `!important` / specificity hack 可以拿掉。

### 25. CSS / JS 拆出獨立檔案

**涵蓋情境**

- search.html 內含 ~80 行 CSS + ~110 行 JS inline，混雜 Hugo template。
- 拆到 `assets/search.css`、`assets/search.js`，用 Hugo `resources.Get | minify | fingerprint` 引入。

**理想做法骨架**：當 inline CSS / JS 超過 ~30 行就值得拆檔。template 變單純、editor syntax highlight、minify 自動化、cache-busting fingerprint 自動處理。

### 26. CSS 變數定義位置統一

**涵蓋情境**

- `--search-*` 變數散在 `body.page-search`、`:root`、`.search-shell` 三處。

**理想做法骨架**：一次定義在離 root 最近的合適位置（這裡是 `body.page-search`），其他地方只引用、不重複宣告。改 token 只動一處。

### 27. runtime 量測模式統一

**涵蓋情境**

- `--search-scope-h` 用 ResizeObserver 量；H1 和 form 寫死值（64 / 68）。寫死值跟實際渲染可能不一致（theme 對 h1 的 margin、字型差異）。

**理想做法骨架**：三個值都用 ResizeObserver 量、寫回變數；或三個值都寫死、強制 H1 height + form scale 各自等於 token。**選一邊不要混搭**。混搭時某些字型 / theme 變化會打破對齊，且難以重現。

### 28. 以 class toggle 取代 inline `display: none !important`

**涵蓋情境**

- scope filter 用 `el.style.setProperty('display', 'none', 'important')` 防 Svelte 重繪覆寫。

**理想做法骨架**：在 layered CSS 寫 `.pagefind-ui__result.is-scope-filtered { display: none }`（layered 後不需要 important）、JS 只 toggle class。檢查與 debug 都更直觀，devtools 看到的是語意化的 class 而非 inline style。

### 29. JS query 範圍限定在元件內

**涵蓋情境**

- `document.querySelector('.pagefind-ui__filter-panel')` 全文件搜。

**理想做法骨架**：所有 query 都從 `shell` / `ui` 等已知元件根節點往下找。避免未來同頁有第二個 pagefind 實例時失控、也避免無關的同名 class 元素被誤命中。

### 30. setTimeout 輪詢換 MutationObserver

**涵蓋情境**

- `waitAndInit` 用 `setTimeout(..., 100)` 等 pagefind mount。

**理想做法骨架**：用 `MutationObserver` 觀察 `#search`，看到目標元素出現就 `disconnect()`。沒延遲、CPU 不被輪詢吃。輪詢只在「沒有事件可監聽」的場景使用。

### 31. setupScopeFilter 拆三個職責

**涵蓋情境**

- 一個 init function 同時做：搬 scope、量高度、註冊 radio listener、註冊 result observer、reorder filter。

**理想做法骨架**：拆成 `measureScopeHeight()`、`wireScopeFilter()`、`reorderFilters()` 等獨立函式，各自有清楚的 input / output。Debug 時知道哪個壞了，也容易單獨重用。

### 32. baseof.html override 範圍最小化

**涵蓋情境**

- 整個 theme baseof.html 複製一份只為了加 `body class="page-search"` 與一行 partial 引用。

**理想做法骨架**：override theme 檔案時，**只動非改不可的部分**，並在註解裡明確標出「跟 theme 版本相比改了哪幾行」。這樣 theme 升級時容易 sync 變更、不會吃掉本地客製。或評估改用 partial / hook 點達成相同效果，避免完整複製。

---

## 待補

之後使用者會補充漏掉的情境。每篇大綱補完後再寫成完整內文。

---

**Last Updated**: 2026-04-25 — 初版：搜尋頁開發四輪共 32 篇大綱待寫成內文。
