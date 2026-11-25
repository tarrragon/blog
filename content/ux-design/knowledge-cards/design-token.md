---
title: "Design Token（具名設計值）"
date: 2026-11-25
description: "想把元件裡寫死的色碼、px 字級與間距改成具名的值、判斷哪些值值得取名，或讀到 primitive token、semantic token、設計令牌而要分清兩層各管什麼時"
weight: 17
tags: ["ux-design", "knowledge-card", "css", "design-token", "design-system"]
---

Design Token（具名設計值）是替一個設計決定取的名字，元件引用名字，不寫值：顏色、字級、行高、間距、線寬、圓角、動畫時長都可以是 token。CSS 裡最常見的載體是自訂屬性（custom property），例如 `--brand-bg: #000` 定義在元件的根元素上，元件規則寫 `background: var(--brand-bg)`；同一份 token 也可以寫成 JSON，再由建置工具產生 CSS、iOS 或 Android 的常數。其他中文資料常寫作「設計令牌」。token 定義在哪個元素上、被誰覆寫，照 CSS 的層疊規則決定，其中選擇器之間的勝負看 [Specificity（特定性）](/ux-design/knowledge-cards/specificity/)。這張卡的 token 跟語言模型切分文字的單位不是同一件事，那個意思在 [Token](/llm/knowledge-cards/token/) 卡。

## 跟其他概念的關係

token 常分成兩層，兩層調整的範圍不同：

- **primitive token**（也稱尺寸階、色階這類「階」）只放數值，名字描述值本身：`--size-md: 16px`、`--teal-500: #00bde3`。元件規則不直接引用這一層。
- **semantic token**（也稱功能 token、role token）用用途命名，值引用 primitive token：`--t-body: var(--size-md)`、`--link-fg: var(--teal-500)`。元件規則只引用這一層。

要整體調整某一階（16px 全部改 17px）時改 primitive token，用到它的用途一起變；要單獨調整某一種用途（只有說明文字要大一點）時，改那個 semantic token 對到哪一階，其他用途不受影響。只有一層時，名字是數值的變數改值之後名不副實，名字是用途的變數又沒有一個值能讓同一級的幾種用途一起變。

token 也可以用在觸控命中區這類尺寸上：[Touch Target（觸控目標）](/ux-design/knowledge-cards/touch-target/) 的 44px 底線寫成一個 token 之後，每一個可點元件引用同一個值，調整底線時不必逐一找出寫死的 44px。

## 可觀察訊號與例子

需要 token 的訊號是同一個設計決定散在很多處寫死：改一個品牌色要在幾份 CSS 裡搜尋色碼；兩個看起來同一級的文字，一個寫 17px、一個寫 18px；手機版的字級散在好幾個 media query 裡，每個元件各寫一份。反方向的訊號是同一個值在兩處代表不同的設計決定：同樣是 16px，一處是內文字級、一處是間距，兩者寫成同一個 token 之後，調整其中一個會連帶改到另一個。

2026 年本站 SQL 練習頁把字級改成兩層：尺寸階 `--sqlp-size-xs` 到 `--sqlp-size-2xl` 只放 14、16、18、22、26、30px，功能字級 `--sqlp-t-<用途>`（題目需求、按鈕、說明文字……）各自對到一階；手機版只在一個 media query 裡改功能字級對到哪一階，元件規則沒有任何一條自己的手機字級（[CSS 改用 token 取值的重構與驗證：逐元素比對計算後的樣式、字級分成尺寸階與功能字級（primitive 與 semantic token）、!important 與提高特定性的 id 選擇器的替代寫法](/work-log/css-token-refactor-verified-by-computed-style-diff/)）。

## 判斷條件與後果

判斷一個值要不要寫成 token，數的是設計決定，不是值出現的次數。同一個設計決定出現在兩處以上時，寫成 token 換到的是改一處、全部跟著變；只出現一次的版面尺寸寫成 token，要改時仍然只改一個地方，換到的只有多一層名字。顏色與字級即使只用一次也常一律寫成 token，理由是自動檢查只能依屬性判斷（凡是 `color` 寫了色碼就報），數不出一個值代表幾個設計決定。

兩層分開的條件是有整階一起調整的需求、而且用途夠多：用途只有少數幾種、沒有整階調整的需求時，一層用途命名的 token 加一張記錄哪幾種用途同級的表就夠，少一層間接。

寫在取不到自訂屬性的位置時，token 用不上：`var()` 只能寫在屬性值裡，media query 的條件（`@media (max-width: 599px)`）不能引用它，所以斷點通常留著字面值；token 定義在元件根元素上時，根元素外面的元素（例如頁面的 `body`）也取不到它。
