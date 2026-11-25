---
title: "Computed Style（計算後的樣式）"
date: 2026-11-25
description: "CSS 規則看起來寫對了、畫面卻不對，要確認元素實際套用的值與勝出的規則；或重構 CSS 時要證明畫面沒變，想知道 getComputedStyle 讀到的是哪一個階段的值、哪些情形讀不到時"
weight: 19
tags: ["ux-design", "knowledge-card", "css", "computed-style", "measurement"]
---

Computed Style（計算後的樣式）是瀏覽器替一個元素把層疊（cascade）、繼承、初始值與單位換算處理完之後，每一個 CSS 屬性的值；本卡指的是 JavaScript 用 `getComputedStyle(元素)` 讀到的那一組值，DevTools 的 Computed 面板顯示的也是它。計算後的樣式是層疊比較出勝者之後的結果，哪一條規則勝出看 [Specificity（特定性）](/ux-design/knowledge-cards/specificity/) 與 [Cascade Layer（層疊分層）](/ux-design/knowledge-cards/cascade-layer/)。CSS 規範把一個屬性的值分成幾個階段：

- **指定值（specified value）**：作者寫的宣告經層疊選出勝者之後的值。
- **計算值（computed value）**：把相對單位換成絕對值之後的值。
- **使用值（used value）**：排版之後才定得下來的值，例如百分比寬度換成像素。

`getComputedStyle` 回傳的是規範所謂的解析值（resolved value）：多數屬性就是計算值，`width`、`height`、`margin` 這類排版相關的屬性在元素有排版時回傳使用值。

## 跟其他概念的關係

CSS 寫對了、畫面卻不對時，讀原始碼的人只看得到「寫了什麼」，讀計算後的樣式才看得到「最後套用了什麼」，兩者之間隔著整頁所有規則的層疊。原始碼裡一條 `font-size: var(--t-body)` 在計算後的樣式裡是 `16px`；[Design Token（具名設計值）](/ux-design/knowledge-cards/design-token/) 的自訂屬性本身也有計算值，`getPropertyValue('--t-body')` 讀回的是代換 `var()` 之後的字串，不是換算成像素的長度。

它也是重構 CSS 時「畫面沒變」的驗收對象：逐元素記錄一組屬性的計算後值寫成快照，改寫法前後各量一次比對，分得出是哪個元素的哪個屬性變了；截圖比對抓得到屬性清單以外的變化，分不出原因。兩種比對各量得到什麼，見 [螢幕截圖比對](/testing/04-ui-automation/visual-regression/)。

## 可觀察訊號與例子

要讀計算後樣式的訊號是「規則有寫、畫面不像」：DevTools 的 Styles 面板裡自己的宣告被劃掉（輸給了另一條規則），或沒出現（選擇器沒選到）。2026 年本站 SQL 練習頁的元件規格寫 SQL 的字級 16px，畫面上的字看起來偏小；作者讀 `<code>` 的計算後 `font-size` 是 13.76px，往回查勝出的規則，找到一條只作用在練習區裡的全域重設 `#sql-practice code { font-size: 0.86em }` 以 id 的特定性蓋過了元件的 class 規則（16 × 0.86 = 13.76）。量法與成因在 [CSS 規則沒生效時的量測與成因：範圍重設的特定性與宿主樣式、container-type 與 subgrid、捲動陰影的覆蓋漸層](/work-log/css-silent-override-measurement/)；同一頁之後整份 CSS 改成引用 token 時，用逐元素的計算後樣式快照證明畫面沒變，見 [CSS 改用 token 取值的重構與驗證：逐元素比對計算後的樣式、字級分成尺寸階與功能字級（primitive 與 semantic token）、!important 與提高特定性的 id 選擇器的替代寫法](/work-log/css-token-refactor-verified-by-computed-style-diff/)。

## 判斷條件與後果

讀計算後的樣式得到的是「某個元素、某個狀態、某個寬度、某個瀏覽器」下的值，沒放進量測的那幾項結論是沒有量過：hover、焦點、`prefers-reduced-motion` 這類狀態要先讓元素進入那個狀態再讀；斷點與容器查詢的每一個區段各量一個寬度；字型還沒載入完成時讀到的行高與寬度會跟載入後不同，要等 `document.fonts.ready` 之後再讀。

有幾種值讀不到或要另外讀。偽元素要用 `getComputedStyle(元素, '::before')` 讀；`:visited` 的樣式，瀏覽器為了隱私一律回傳未造訪時的值，要改成讀出套用到 `:visited` 的規則、依特定性判斷；shadow root 裡的元素不在 `children` 裡，走訪 DOM 的腳本要另外進去。`display: none` 的元素仍然讀得到計算值，但排版相關的屬性沒有使用值，讀到的是計算值或 `auto`。

讀計算後的樣式拿到的是瀏覽器在元素上套用了什麼值，讀不出這個值來自哪一條規則：要知道勝出的是哪一條，看 DevTools 的 Styles 面板，或拿掉候選的規則再讀一次、看值有沒有變。
