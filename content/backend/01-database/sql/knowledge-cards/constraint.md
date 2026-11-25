---
title: "Constraint（約束）"
date: 2026-09-01
description: "需要確認資料保證應依賴資料庫約束而非資料現況，或確認某一欄是否可能出現 NULL 時"
aliases: ["/sql/knowledge-cards/constraint/"]
weight: 14
tags: ["sql", "constraint", "null", "ddl", "knowledge-card"]
---

Constraint（約束）是宣告在資料表或欄位上的規則，由資料庫在每一次寫入 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/) 時強制檢查，違反規則的寫入立即失敗。與應用程式層檢查不同，應用層只覆蓋經過該段程式碼的路徑，資料庫約束則涵蓋所有寫入來源，包含手動維護、遷移腳本與其他服務。

基本約束各自提供不同保證：`NOT NULL` 保證欄位不為空；`UNIQUE` 保證欄位值不重複；`PRIMARY KEY` 結合 `NOT NULL` 與 `UNIQUE` 並作為列識別鍵；`FOREIGN KEY` 保證欄位值存在於父表；`CHECK` 保證單列滿足指定布林條件（如金額不為負）。

除了上述單欄或跨表的基本規則，還有三類進階約束形態：PostgreSQL 的 [Exclusion Constraint（排除約束）](/backend/01-database/sql/knowledge-cards/exclusion-constraint/) 保證任兩列在指定比較運算下不可同時成立（例如兩段時間不可重疊，`UNIQUE` 是所有運算子皆為 `=` 的特例）；若唯一性只需套用在資料表的子集合（例如軟刪除帳號表僅對 `deleted_at IS NULL` 的生效列強制信箱唯一），PostgreSQL 與 SQLite 可透過附帶 `WHERE` 條件的唯一 [Partial Index（部分索引）](/backend/knowledge-cards/partial-index/) 達成條件式唯一約束；宣告多欄複合外鍵時，SQL 預設的 `MATCH SIMPLE` 規則只要子表複合外鍵任一欄位為 `NULL` 即略過外鍵檢查，因此多租戶複合外鍵的子表租戶鍵須同步設為 `NOT NULL`（完整設計實例在 [1.21 資安、權限與合規決定的資料表設計：軟刪除與唯一約束、多租戶子表與列級安全性、RBAC 與非同步任務複查、存取憑證撤銷與優先序、個資分離與不可變稽核、角色預設權限與逾時護欄](/backend/01-database/security-and-compliance-schema-decisions/)）。

## 約束與查詢可省略的防禦判斷

查詢能否省略某項防禦檢查，取決於約束是否已把前提固定。以 [NULL（空值）](/backend/01-database/sql/knowledge-cards/null/) 為例：子查詢結果若出現 `NULL`，`NOT IN` 會靜默回傳空集合；外層比對欄位若為 `NULL`，`NOT IN` 亦會濾除該列而與 `NOT EXISTS` 分岔，因此否定成員判斷預設使用 `NOT EXISTS`，唯有外層比對欄位與子查詢欄位兩側皆已宣告 `NOT NULL` 約束時才可豁免。豁免依據必須是約束而非單次觀察——目前資料不含空值只證明當下如此，約束才保證未來持續成立。

同理，`UNIQUE` 讓查詢端在寫連接前即可確認鍵值不會觸發一對多列數膨脹（見 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)），`FOREIGN KEY` 搭配 `NOT NULL` 則保證內連接不會因孤兒列或空鍵而遺失資料。

## 跟其他概念的關係

約束屬於資料表結構定義，由 [DDL 與 DML（定義結構與動資料）](/backend/01-database/sql/knowledge-cards/ddl-dml/) 中的 DDL 建立與修改。這項歸屬帶來兩個後果：建立約束需要結構變更權限，與常態讀寫帳號分離；對既有資料表補加約束時，若既有列已違反規則，建約束操作會失敗。

約束與 [Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/) 職責不同，儘管多數引擎以索引實作 `UNIQUE`。索引負責加快查找速度，移除索引只影響效能；約束負責保證資料正確性，移除約束會使違法資料得以寫入。

這條分工有一處延伸：約束資訊有時也會被 [Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/) 用於簡化執行步驟。在五千列資料表上執行對 `recordDate` 做等值比對的 `EXISTS` 子查詢（`WHERE EXISTS (SELECT 1 FROM ... WHERE recordDate = ...)`），將 `recordDate` 索引由 `UNIQUE` 改為普通索引後，以 `EXPLAIN`（輸出逐行虛擬機指令，比 `EXPLAIN QUERY PLAN` 更底層）檢視 SQLite 3.51.0 位元碼，會看見多出一層內迴圈以備讀取下一筆。這項差別在 `EXPLAIN QUERY PLAN` 看不出來，在此資料量下也未產生顯著耗時差；同組查詢在 DuckDB 1.5.5 上的執行計畫則與是否有 `UNIQUE` 無關。因此約束是否影響執行計畫取決於各家引擎實作，而非約束本身的保證範圍（跨引擎差異分級在 [SQL.19 引擎寬鬆度與可攜性：各家對同一組寫法的差異、分級與處理時機](/backend/01-database/sql/engine-leniency-and-portability/)）。

## 延伸閱讀：空值規則、外鍵實作與授權分層

- `NULL` 的三值邏輯與 `NOT IN` 失效推導：[NULL（空值）](/backend/01-database/sql/knowledge-cards/null/) 與 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)
- 約束能攔截的錯誤類型與邊界：[SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/)
- 外鍵宣告與生效分離的位置：[SQL.18 外鍵與參照完整性：宣告、生效與查詢得到的保證](/backend/01-database/sql/foreign-key-and-referential-integrity/)
- DDL 權限與常態運行帳號的切分：[SQL.16 SQL 的權限模型：角色、GRANT 的授權單位與最小權限](/backend/01-database/sql/privilege-model/)
