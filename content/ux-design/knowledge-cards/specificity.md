---
title: "Specificity（特定性）"
date: 2026-11-25
description: "一條 CSS 規則明明套到了元素、計算後的值卻是另一條規則的值，或想用 !important、多加一個 id 讓自己的規則勝出之前，用來判斷兩條規則誰贏、為什麼贏，以及提高特定性會連帶蓋掉哪些規則"
weight: 16
tags: ["ux-design", "knowledge-card", "css", "specificity", "cascade"]
---

Specificity（特定性）是瀏覽器在兩條 CSS 宣告搶同一個元素的同一個屬性時比較的值：數選擇器裡 id 有幾個、class／屬性選擇器／偽類有幾個、元素／偽元素有幾個，寫成 (id, class, 元素) 三位數，從左邊那一位開始比，大的勝出。`#nav a` 是 (1,0,1)，`.menu .item a` 是 (0,2,1)，`#nav a` 勝出，因為 id 那一位先分出大小，後面兩位不必再比。三個函式式的偽類有自己的算法：`:where()` 一律算 0；`:is()`、`:not()`、`:has()` 取參數裡最高的那一個。特定性只影響規則之間的勝負；勝出的規則裡寫的值，常常是一個 [Design Token（具名設計值）](/ux-design/knowledge-cards/design-token/)。統計與醫學檢驗也有 specificity，那個詞指真陰性率，中文寫作「特異度」，跟這張卡講的不是同一件事。

## 跟其他概念的關係

特定性是 CSS 層疊（cascade）選出勝出宣告時的其中一關，排在它前面的關卡先分出勝負時，特定性不必比。層疊依序比：宣告的來源與重要性（`!important` 的宣告在這一關就勝過一般宣告）、cascade layer 的順序（見 [Cascade Layer（層疊分層）](/ux-design/knowledge-cards/cascade-layer/) 卡）、特定性，最後才是在樣式表裡的先後順序。所以 `!important` 與 cascade layer 都是在特定性之前就決定勝負的機制：帶 `!important` 的宣告不論特定性多低都贏過一般宣告，寫在較高 layer 的規則不論特定性多低都贏過較低 layer 的規則。元素上的 `style` 屬性（行內樣式）在 layer 與特定性之前就勝過樣式表裡的一般宣告，任何選擇器的特定性都贏不過它；樣式表裡帶 `!important` 的宣告才贏得過行內的一般宣告。

用 [Design Token（具名設計值）](/ux-design/knowledge-cards/design-token/) 取值的元件，token 通常定義在元件的根元素上，靠繼承傳到子孫；token 的重新定義（例如手機寬度下改字級）同樣要在層疊裡勝出，所以寫在同一個選擇器、同一份檔案的後面。layer 與特定性的取捨在 [CSS Layers 取代 specificity 戰](/report/css-layers-over-specificity/)。

## 可觀察訊號與例子

特定性成為判讀重點的訊號是「規則有套到，值卻是別人的」：DevTools 的 Styles 面板裡，這條規則的宣告被劃掉，同一個屬性在上方另一條規則裡生效；或量計算後的樣式，值跟自己的規則寫的不同。規則根本沒套上（選擇器沒選到元素）是另一種成因，Styles 面板裡看不到這條規則，兩者的分法在 [CSS 規則沒生效時的量測與成因：範圍重設的特定性與宿主樣式、container-type 與 subgrid、捲動陰影的覆蓋漸層](/work-log/css-silent-override-measurement/)。

2026 年本站 SQL 練習頁的一個例子：困惑筆記區的輸出框是 `<textarea class="sqlp-note-out">`，要用等寬字，而同一區有一條 `.sqlp-note textarea` 替所有文字欄設定字型。`.sqlp-note-out` 是 (0,1,0)，`.sqlp-note textarea` 是 (0,1,1)，`.sqlp-note textarea` 勝出，原本的寫法在輸出框的字型上加了 `!important`。選擇器改寫成 `.sqlp-note .sqlp-note-out`，特定性 (0,2,0) 高過 (0,1,1)，不需要 `!important`（[CSS 改用 token 取值的重構與驗證：逐元素比對計算後的樣式、字級分成尺寸階與功能字級（primitive 與 semantic token）、!important 與提高特定性的 id 選擇器的替代寫法](/work-log/css-token-refactor-verified-by-computed-style-diff/)）。

## 判斷條件與後果

兩條規則衝突、而且都屬於同一份可以改的 CSS 時，讀出要贏過的是哪一條，把自己的選擇器寫到剛好高過它，或跟它同級而寫在它後面：勝負只牽涉這兩條，其他規則的勝負不變；在規則旁註明要贏過的是哪一條，下一個調整那一條的人才知道這兩條的特定性要一起看。

只替部分規則加上 id 或多一層 class 來提高特定性時，那幾條規則也會一起高過元件自己的其他規則。原本靠特定性排好的元件內部規則會被打亂：例如連結按鈕加了 id 之後，它的白字蓋過主要按鈕 hover 時的黑字，主要按鈕 hover 時變成白底白字。所以加權要贏的對象在元件外面（主題或宿主頁面的樣式）時，每一條元件規則統一加同一個前綴，各規則之間的相對特定性才不變。

要贏的宣告帶 `!important`、或在較高的 cascade layer 時，提高特定性贏不了，因為那兩關在特定性之前就分出勝負；處置在對方那一邊（排除元件的範圍、調整 layer 的順序），或用 Shadow DOM 隔開。
