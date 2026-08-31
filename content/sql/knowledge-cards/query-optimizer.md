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

同一個連接寫成兩種順序，SQLite 兩次都選擇先掃小表，與誰寫在前面無關。這是重排的直接證據：書寫位置決定語意，執行方式由最佳化器另外決定。

它也可以做等價變換，例如把某些 [outer join](/sql/knowledge-cards/outer-join/) 轉成內連接，前提是查詢的其他部分已經讓外連接補的那些列不可能出現在結果裡。

## 設計責任

查詢原本很快而某天變慢、寫法卻沒動過的時候，統計資訊過時是首要嫌疑。定期更新統計、或在資料量大幅變動後手動觸發，比改寫查詢更常解決問題。

反過來，最佳化器選錯而統計是新的時候，才輪到用提示或改寫去引導它，而那些手段會把原本自動適應資料變化的查詢釘死在一個選擇上。
