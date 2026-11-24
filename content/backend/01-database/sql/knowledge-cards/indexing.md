---
title: "Index（索引）"
date: 2026-08-31
description: "看到執行計畫寫著走索引或建索引、想知道那是什麼時"
aliases: ["/sql/knowledge-cards/indexing/"]
weight: 5
tags: ["sql", "index", "performance", "knowledge-card"]
---

Index 是為了加快查找而額外維護的一份資料結構，內容是某幾個欄位的值與它們對應的列的位置。它與資料本身分開存放，由引擎自動維護，而 [query optimizer](/backend/01-database/sql/knowledge-cards/query-optimizer/) 決定某次查詢要不要用它——用不用的結果寫在 [query plan](/backend/01-database/sql/knowledge-cards/query-plan/) 裡。

沒有索引時，找出某個條件成立的列要把整張表看過一遍。有索引時，引擎先在索引裡定位，再回頭取那些列。

索引建了而引擎不走它有兩個常見的成因。一個是[統計資訊](/backend/01-database/sql/knowledge-cards/query-statistics/)沒更新——索引決定有沒有一條快的路，統計決定引擎知不知道該走那一條。另一個是條件把索引欄位包進了函式或運算裡，那時引擎沒有可以拿去比對的值，[Sargable](/backend/01-database/sql/knowledge-cards/sargable/) 那張卡寫這個形狀怎麼判、怎麼改。

## 跟其他概念的關係

索引是查詢代價的主要變數之一，而它不出現在查詢的文字裡。同一段 SQL 在有索引與沒索引的資料庫上執行方式完全不同，結果卻一模一樣——這正是宣告式語言的分工：查詢說要什麼，索引與計畫決定怎麼拿。

它的代價落在寫入端。每一次新增、修改或刪除，相關的索引都要跟著更新，所以索引不是加越多越好。同一個 [relation](/backend/01-database/sql/knowledge-cards/relation/) 上建了多個索引，讀取變快而寫入變慢。

## 可觀察訊號與例子

SQLite 的計畫用 `SCAN` 與 `SEARCH` 分開兩種取法：`SCAN 訂單` 表示整張表逐列看過，`SEARCH 顧客 USING AUTOMATIC COVERING INDEX` 表示透過索引定位。

計畫裡那幾個關鍵字（`AUTOMATIC`、`COVERING`、`BLOOM FILTER`）各指什麼，在 [query plan](/backend/01-database/sql/knowledge-cards/query-plan/)。

## 判斷條件與後果

索引由查詢的形狀決定，不由表的形狀決定。要建哪些索引取決於實際會執行哪些查詢，所以它是在知道查詢模式之後才做得準的決定。

複合索引的欄位順序有影響：`(顧客編號, 下單日)` 這個索引對「先按顧客再按日期」的查找有用，對「只按日期」的查找幫助有限。順序要對齊查詢的條件形狀。

查詢只關注表的特定子集合（例如僅查未軟刪除的生效列或待處理佇列）時，可建立附帶 `WHERE` 篩選條件的 [Partial Index（部分索引）](/backend/knowledge-cards/partial-index/)，縮小索引體積並搭配 `UNIQUE` 達成條件式唯一約束；查詢固定以正規化函式比對欄位（例如 `LOWER(email)`）時，可針對該運算式建立表達式索引（expression index），讓帶有相同運算式的條件能命中索引查找（實測與軟刪除應用見 [1.21 資安、權限與合規決定的資料表設計：軟刪除與唯一約束、多租戶子表與列級安全性、RBAC 與非同步任務複查、存取憑證撤銷與優先序、個資分離與不可變稽核、角色預設權限與逾時護欄](/backend/01-database/security-and-compliance-schema-decisions/)）。
