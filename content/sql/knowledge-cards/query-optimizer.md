---
title: "Query Optimizer（查詢最佳化器）"
date: 2026-08-31
description: "想知道是誰決定了執行順序、或為什麼同一段查詢換個時間變慢時"
weight: 3
tags: ["sql", "optimizer", "performance", "knowledge-card"]
---

Query optimizer 是引擎裡負責挑選執行方式的元件。它讀進查詢，產出一個 [query plan](/sql/knowledge-cards/query-plan/)，而它可以任意重排步驟，只受一個約束：輸出的 [relation](/sql/knowledge-cards/relation/) 要與語意模型算出來的一致。

## 概念位置

最佳化器的存在是 SQL 宣告式性質的直接結果。查詢只描述要什麼結果，所以「怎麼算」這個決定必須有人做，而做這個決定的就是它。

它的選擇依據是估計的代價，而估計來自統計資訊——每張表大概多少列、某個欄位的值大概怎麼分布。所以它的判斷品質取決於那些統計有多新，與查詢寫得多好無關。它的產物是一份 [query plan](/sql/knowledge-cards/query-plan/)，而樹上每個節點處理的都是一個 [relation](/sql/knowledge-cards/relation/)。

## 可觀察訊號與例子


書店的顧客表五十列、訂單表二十萬列。同一個連接寫成 `FROM 訂單 JOIN 顧客` 與 `FROM 顧客 JOIN 訂單`，SQLite 兩次回報一模一樣的計畫——都掃二十萬列那張、對五十列那張做查找。**書寫位置決定語意，執行方式由最佳化器另外決定。**

換掉可用的資源，同一段查詢的計畫也會變。訂單表的顧客編號欄沒有索引時，計畫寫著 `SEARCH 訂單 USING AUTOMATIC COVERING INDEX`——引擎臨時建了一個；建好索引之後變成 `SEARCH 訂單 USING COVERING INDEX ix`，改用現成的那一份。

它也可以做等價變換，例如把某些 [outer join](/sql/knowledge-cards/outer-join/) 轉成內連接，前提是查詢的其他部分已經讓外連接補的那些列不可能出現在結果裡。

## 設計責任

查詢原本很快而某天變慢、寫法卻沒動過的時候，統計資訊過時是首要嫌疑。定期更新統計、或在資料量大幅變動後手動觸發，比改寫查詢更常解決問題。

反過來，最佳化器選錯而統計是新的時候，才輪到用提示或改寫去引導它，而那些手段會把原本自動適應資料變化的查詢釘死在一個選擇上。
