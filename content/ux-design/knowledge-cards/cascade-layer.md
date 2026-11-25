---
title: "Cascade Layer（層疊分層）"
date: 2026-11-25
description: "自己的 CSS 一直輸給第三方或主題的樣式、想用 @layer 取代加長選擇器、加 id 或 !important，或要判斷把元件 CSS 放進 layer 會贏還是會輸時"
weight: 20
tags: ["ux-design", "knowledge-card", "css", "cascade-layer", "cascade"]
---

Cascade Layer（層疊分層）是 CSS 用 `@layer` 把規則分進具名的層、讓層的順序在比 [Specificity（特定性）](/ux-design/knowledge-cards/specificity/) 之前就決定勝負的機制。這裡的「層疊」指 CSS 的 cascade，也就是瀏覽器從所有規則裡選出每個屬性的勝出宣告的那套比較；其他中文資料常寫作「層疊層」或「級聯層」。它跟兩個也帶「層」字的概念不同：stacking context（z-index 的堆疊次序）管的是繪製的前後，不管哪條規則勝出；cascade 的來源（瀏覽器預設樣式、使用者樣式、作者樣式）是比 layer 更早的一關，layer 只在同一個來源之內排順序，網頁作者寫的 `@layer` 排的是作者樣式。

## 跟其他概念的關係

層疊依序比：宣告的來源與重要性（`!important`）、行內樣式、cascade layer 的順序、特定性，最後是樣式表裡的先後。一般宣告之間，排在後面的 layer 勝過排在前面的 layer，沒有放進任何 layer 的規則勝過所有 layer；帶 `!important` 的宣告順序反過來，排在前面的 layer 裡的 `!important` 最強，也勝過沒放進 layer 的 `!important`。所以 layer 的順序一旦分出勝負，[Specificity（特定性）](/ux-design/knowledge-cards/specificity/) 就不必比：較低 layer 裡特定性再高的選擇器，也輸給較高 layer 裡最簡單的 class 規則。

layer 的順序由第一次出現的位置決定，也可以在樣式表開頭用 `@layer reset, vendor, components;` 一次宣告。外部的樣式表用 `@import url("vendor.css") layer(vendor);` 放進某一層，這一行要寫在樣式表最前面（`@charset` 與 `@layer` 宣告之後）。layer 與提高特定性（加權）各自的取捨在 [CSS Layers 取代 specificity 戰](/report/css-layers-over-specificity/)；實際套用了哪個值，讀 [Computed Style（計算後的樣式）](/ux-design/knowledge-cards/computed-style/)。

## 可觀察訊號與例子

要考慮 layer 的訊號是「自己的規則一直要加權才贏得過別人的樣式」：為了贏過第三方元件或主題的選擇器，自己的選擇器愈寫愈長、多加一層 class、加 id，最後加 `!important`。把對方的 CSS 放進較低的 layer、自己的規則不放進 layer，自己的一般 class 規則就勝出，不必再比特定性。

反過來的訊號是「放進 layer 之後反而輸了」：元件被嵌進一個沒有分層的頁面，元件作者把自己的 CSS 包進 `@layer components`，頁面主題沒放進任何 layer 的元素規則（`a { color: … }`）就勝過元件的每一條規則，因為沒放進 layer 的規則勝過所有 layer。2026 年本站 SQL 練習頁嵌在 blog 主題裡，主題的 CSS 沒有分層，練習頁的作者因此沒有把練習頁的 CSS 包進 layer（包進去就會輸給主題的每一條規則）。主題的樣式表由本站的模板引入，照下面〈判斷條件與後果〉「能決定對方樣式放進哪一層」那一種條件，也可以把主題放進較低的 layer，但改主題的載入方式會影響 blog 的每一頁、每一頁都要重量，所以這次沒有選這條路，改用 `:where()` 壓低範圍重設的特定性；範圍重設是只作用在練習區裡、把瀏覽器預設與主題的外距和字級清掉的那幾條規則。只清瀏覽器預設的整條包進 `:where()`，特定性是 0；要蓋過主題元素規則的把元素留在 `:where()` 外面，特定性跟主題對應的那一條相同，靠排在後面勝出。帶 `!important` 的自訂樣式則改成不套用到練習區（[CSS 規則沒生效時的量測與成因：範圍重設的特定性與宿主樣式、container-type 與 subgrid、捲動陰影的覆蓋漸層](/work-log/css-silent-override-measurement/)）。

## 判斷條件與後果

能決定對方樣式放進哪一層時（自己載入第三方的 CSS、主題的樣式表由自己的模板引入），把對方放進較低的 layer、自己留在 layer 外面或較高的 layer：勝負由 layer 的順序決定，自己的規則可以只用最簡單的選擇器，對方改了選擇器也不影響。代價是改載入方式會影響同一份 CSS 的每一個頁面，要在每一種頁面上量一次。

管不到對方的載入方式、而對方沒有分層時，自己的 CSS 放進 layer 會輸給對方每一條沒分層的規則；這時有兩種做法。宿主只有一種、它的選擇器特定性量得到時，用特定性處理：每一條元件規則加同一個根 class 前綴，讓特定性高過宿主對應的規則。元件要嵌進多種宿主、宿主的特定性事先不知道，或宿主帶 `!important` 時，前綴追不上，用 Shadow DOM 隔開，宿主的規則選不到 shadow root 裡的元素。改得了宿主的 CSS、只是管不到它的載入方式時，還有一種做法是讓宿主的規則排除元件的範圍（本站在帶 `!important` 的自訂樣式上就是這樣做），元件的規則不必跟它比特定性。

對方的宣告帶 `!important` 時，把它放進較低的 layer 反而讓它更強，因為 `!important` 在 layer 之間的順序是反過來的；改得了對方的 CSS 時，處置在對方那一邊（讓那幾條規則排除元件的範圍），改不了時用 Shadow DOM 或 iframe 隔開，兩種都不靠 layer 的順序。
