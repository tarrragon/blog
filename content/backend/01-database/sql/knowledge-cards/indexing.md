---
title: "Index（索引）"
date: 2026-08-31
description: "執行計畫顯示走索引或全表掃描，需要確認索引的結構、取捨與設計依據時"
aliases: ["/sql/knowledge-cards/indexing/"]
weight: 5
tags: ["sql", "index", "performance", "knowledge-card"]
---

為了避免每次篩選都逐列掃描整張表，資料庫會額外維護一份保存欄位值與列位置的查找結構——index（索引）。索引與資料表本體分開存放並由引擎自動維護；[Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/) 決定每次查詢是否採用索引，採用結果顯示在 [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/) 中。

缺乏索引時，引擎須掃描整張資料表才能找出符合條件的列；在常見的列式儲存與 B-Tree 二級索引結構下，具備索引時引擎會先在索引定位再回主表讀取目標列（叢集索引如 MySQL InnoDB 主鍵或 SQLite `WITHOUT ROWID` 表的主鍵查找則無須額外回表）。建立索引後引擎仍未使用它，常見原因涵蓋以下幾類：[Query Statistics（統計資訊）](/backend/01-database/sql/knowledge-cards/query-statistics/) 過時導致最佳化器估錯成本；查詢條件把索引欄位包進函式、隱式轉型或未命中複合索引前導欄，使引擎無法直接比對索引鍵（見 [Sargable（可走索引的條件形狀）](/backend/01-database/sql/knowledge-cards/sargable/)）；即使統計完全最新，條件命中的列數比例（選擇率）過高而使最佳化器判定順序掃描更便宜（見 [Cardinality 與 Selectivity（基數與選擇率）](/backend/01-database/sql/knowledge-cards/cardinality-and-selectivity/)）；以及索引的比較規則（collation）與查詢條件不一致（見 [SQL.15 字串比較與 collation：相等、排序、LIKE 與索引可用性](/backend/01-database/sql/string-comparison-and-collation/)）。

## 跟其他概念的關係

索引是影響查詢代價的關鍵變數，且不會出現在查詢文字裡。同一段 SQL 在有無索引下產出相同結果但耗時可能相差數個量級，體現宣告式語言將結果描述與存取路徑分離的設計。

索引的代價由寫入端承擔：每次對 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/) 執行 `INSERT`、`UPDATE` 或 `DELETE`，引擎都須同步更新所有受影響的索引，因此在同一張表疊加過多索引會加速讀取卻拖慢寫入。

## 可觀察訊號與例子

SQLite 的執行計畫以 `SCAN` 與 `SEARCH` 區分存取方式：`SCAN 訂單` 代表全表掃描，`SEARCH 顧客 USING AUTOMATIC COVERING INDEX` 代表透過索引定位（`AUTOMATIC`、`COVERING` 與 `BLOOM FILTER` 的意義見 [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/)）。

## 判斷條件與後果

索引欄位與複合索引順序的挑選取決於實際執行的查詢條件與排序形狀，而不只是資料表有哪些欄位。複合索引 `(顧客編號, 下單日)` 支援「依顧客編號」或「依顧客編號加下單日」的查找，對「僅依下單日」的查找則幫助有限。

針對特定查詢形態，可使用兩種特化索引：查詢只關注資料表特定子集合（例如未軟刪除的生效列或待處理佇列）時，可建立附帶 `WHERE` 條件的 [Partial Index（部分索引）](/backend/knowledge-cards/partial-index/) 縮小體積並結合 `UNIQUE` 實現條件式唯一；查詢固定對欄位套用正規化函式（如 `LOWER(email)`）時，可建立運算式索引（expression index）讓對應條件命中索引查找（實測與軟刪除應用見 [1.21 資安、權限與合規決定的資料表設計：軟刪除與唯一約束、多租戶子表與列級安全性、RBAC 與非同步任務複查、存取憑證撤銷與優先序、個資分離與不可變稽核、角色預設權限與逾時護欄](/backend/01-database/security-and-compliance-schema-decisions/)）。
