---
title: "SQL.1 宣告式的紅利與代價：書寫、求值與執行順序各自由誰決定"
date: 2026-08-31
description: "SQL 宣告式設計帶來的書寫、求值與執行順序分工、有無統計資訊時引擎對不同書寫順序產出的執行計畫、語意模型依求值順序拒絕聚合放進 WHERE 的機制，以及結果驗證與執行代價驗證的分工"
aliases: ["/sql/declarative-not-procedural/"]
weight: 2
tags: ["sql", "declarative", "query-plan", "optimizer"]
---

這篇說明 SQL 作為宣告式語言的核心特性與後果：區分書寫順序、求值順序與執行順序各自的控制方；比較剛建好、尚未統計的資料庫與執行 `ANALYZE` 之後，兩種資料表排列順序產出的執行計畫；以聚合函數放進 `WHERE` 為例，說明語意模型依求值順序拒絕不合法寫法的機制；最後區分結果正確性與執行代價兩種驗證各自依賴的對象。

在 SQL 裡，寫查詢的人描述目標結果集合——包含參與的資料表、配對條件與保留的列——而不指定讀取順序、配對演算法或臨時索引。與逐步執行的程式對照，這個差別最明顯：使用 pandas 或其他 [DataFrame（資料框）](/backend/01-database/sql/knowledge-cards/dataframe/) 介面找出下過單的顧客時，程式碼按序指定載入資料表、依條件篩選與合併，程式就照該順序執行。

描述與實作分離帶來兩面影響。好處是同一段 SQL 查詢在資料量從一萬列成長到一億列、或更換硬體與索引配置時都不必改寫，因為底層演算法不在查詢文字裡；代價則是讀查詢文字的人無法直接得知引擎的讀取順序與執行耗時，同樣的查詢結果換兩種寫法送進引擎，底層執行方式可能完全不同。

## 書寫順序、求值順序與執行順序

**書寫順序**是子句在查詢文字上的排列先後：`SELECT` 位於最前面，`FROM` 接在後面，`WHERE`、`GROUP BY`、`HAVING`、`ORDER BY` 依序往下。這個順序服務閱讀，讓查詢接近自然語言的敘述結構。

**求值順序**是[Semantic Model（語意模型）](/backend/01-database/sql/knowledge-cards/semantic-model/)規定的邏輯運算先後：先由 `FROM` 決定參與運算的資料集合，再由 `WHERE` 篩選列，接著由 `GROUP BY` 分組、`HAVING` 篩選組，再由 `SELECT` 計算要輸出的欄位，最後由 `ORDER BY` 排序。寫在查詢最前面的 `SELECT`，在求值順序裡排在 `HAVING` 之後、`ORDER BY` 之前。

**執行順序**是引擎實際採取的操作次序，由 [Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/) 決定。最佳化器受一條約束限制：輸出的多重列集合（含重複列次數與 `ORDER BY` 指定的順序）必須與語意模型算出來的一致。在這條約束之內，最佳化器可以任意重排讀取順序、更換配對演算法或建立臨時資料結構。

書寫順序、求值順序與執行順序各自獨立，是宣告式設計的直接結果。由於書寫順序與執行順序分開決定，僅從 `FROM` 子句裡資料表的先後位置無法推論引擎的讀取順序。

## 執行計畫的依據：統計資訊與書寫順序

以書店的兩張資料表觀察最佳化器的決策方式：顧客表有五十列，訂單表有二十萬列，查詢目標是計算兩表配對後的訂單筆數，將同一查詢寫成兩種資料表排列順序：

```sql
SELECT count(*) FROM 訂單 JOIN 顧客 ON 訂單.顧客編號 = 顧客.顧客編號;
SELECT count(*) FROM 顧客 JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號;
```

兩段查詢都回傳 `200000`。在 SQLite 查看 [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/) 要執行 `EXPLAIN QUERY PLAN`（SQLite 的 `EXPLAIN` 輸出的是逐行位元碼，而非執行計畫），而計畫內容取決於引擎是否具備這兩張表的統計資訊。

建立這組實測資料表的語句如下：

```sql
CREATE TABLE 顧客 (顧客編號 INT, 姓名 TEXT);
CREATE TABLE 訂單 (訂單編號 INT, 顧客編號 INT, 金額 INT);

WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i+1 FROM n WHERE i < 50)
INSERT INTO 顧客 SELECT i, '顧客' || i FROM n;

WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i+1 FROM n WHERE i < 200000)
INSERT INTO 訂單 SELECT i, i % 50 + 1, i % 900 FROM n;
```

在剛建好、尚未收集統計資訊的資料庫上，SQLite 對兩段查詢產出兩個不同的計畫：

```text
-- EXPLAIN QUERY PLAN SELECT count(*) FROM 訂單 JOIN 顧客 ON 訂單.顧客編號 = 顧客.顧客編號;
|--SCAN 訂單
|--BLOOM FILTER ON 顧客 (顧客編號=?)
`--SEARCH 顧客 USING AUTOMATIC COVERING INDEX (顧客編號=?)

-- EXPLAIN QUERY PLAN SELECT count(*) FROM 顧客 JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號;
|--SCAN 顧客
|--BLOOM FILTER ON 訂單 (顧客編號=?)
`--SEARCH 訂單 USING AUTOMATIC COVERING INDEX (顧客編號=?)
```

缺少統計資訊時，引擎無法得知各表列數，只能退回依照查詢文字裡兩張表出現的先後安排順序：`顧客 JOIN 訂單` 會掃描五十列的顧客表，再為二十萬列的訂單表當場建立臨時索引以供查找。

執行一次 `ANALYZE` 讓引擎統計兩張表的列數與分布之後，同樣兩段查詢產出完全相同的計畫：

```text
|--SCAN 訂單
|--BLOOM FILTER ON 顧客 (顧客編號=?)
`--SEARCH 顧客 USING AUTOMATIC COVERING INDEX (顧客編號=?)
```

兩段查詢都掃描二十萬列的訂單表，並對五十列的顧客表做查找，書寫先後不再影響執行順序。

引擎安排執行計畫的依據是 [Query Statistics（統計資訊）](/backend/01-database/sql/knowledge-cards/query-statistics/)——引擎另外掃描並儲存的表列數與資料分布紀錄；書寫順序只是缺乏統計資訊時的退路。執行計畫裡也包含查詢文字未提及的步驟：`AUTOMATIC COVERING INDEX` 是 SQLite 當場替顧客表建立的臨時[Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/)，`BLOOM FILTER` 是引擎加入的過濾步驟，查詢文字並未要求這些操作。

因為執行計畫隨統計資訊變動，書寫順序無法預測哪張表會先被讀取，它決定的是語意。在內連接中左右位置對稱，在外連接中左右位置決定保留哪一側的未配對列：`LEFT JOIN` 保留左運算元的每一列，配對不到時右側欄位補 `NULL`。多張表相連時，左運算元是前方所有連接累積出來的結果，累積過程與在鏈中間放入 `RIGHT JOIN` 的影響見 [SQL.4 鏈式連接的左運算元：累積方式與外連接的保護範圍](/backend/01-database/sql/join-left-operand-accumulates/)。

## 求值順序擋下的寫法：聚合函數放進 WHERE

語意模型的求值順序不顯示在執行計畫中，但在引擎拒絕違規寫法時會直接顯現。以[SQL 各篇共用的範例資料庫：一家小書店的顧客、訂單與評價表](/backend/01-database/sql/sample-bookstore-database/)的訂單表找出下過一張以上訂單的顧客，將聚合函數寫進 `WHERE` 時 SQLite 與 DuckDB 都會拒絕，改寫到 `HAVING` 才通過：

```sql
SELECT 顧客編號 FROM 訂單 WHERE COUNT(*) > 1 GROUP BY 顧客編號;
-- SQLite：misuse of aggregate: COUNT()
-- DuckDB：Binder Error: WHERE clause cannot contain aggregates!

SELECT 顧客編號, COUNT(*) AS 張數 FROM 訂單 GROUP BY 顧客編號 HAVING COUNT(*) > 1;
-- 兩個引擎都回 (1, 2)：顧客編號 1 的佳穎，兩張訂單
```

兩家引擎的錯誤訊息都只指出 `WHERE` 不可包含聚合函數，原因來自求值順序：執行 `WHERE` 時分組尚未發生，組的計數還不存在；`HAVING` 排在 `GROUP BY` 之後，此時每一組的計數已經算完。這條限制由語意模型規定，與查詢風格或各家引擎偏好無關。

求值順序由語意模型固定，不隨引擎改變，因此每一步可用的欄位與值都有明確規則。[SQL.2 子句的求值順序：每一步可用的欄位、語意模型擋下的寫法與各家引擎放寬的寫法](/backend/01-database/sql/clause-evaluation-order/) 逐一說明各子句可用的欄位與值，並區分模型層的限制與各家引擎放寬的行為（包含不報錯但回傳錯誤清單的形態）。

## 結果與代價的分開驗證：輸出與執行計畫各自檢驗的對象

宣告式設計把執行方式交給引擎決定，查詢代價也隨之由引擎與資料庫現況決定。查詢文字不記載掃描全表或走索引、是否建立臨時索引，以及是否將中間結果寫入磁碟；〈執行計畫的依據：統計資訊與書寫順序〉裡執行計畫出現的 `SCAN`、`BLOOM FILTER` 與臨時索引，全部不在查詢文字之中。

因此驗證查詢要分成兩件獨立的工作。**結果是否正確**透過輸出驗證，可從查詢語意與測試資料推導；**執行代價是否可接受**則必須查詢執行計畫，向目標引擎取得，且同一段查詢在不同資料量、索引配置與統計資訊下的計畫會改變。

小量開發資料只能驗證結果是否正確。資料量過小時各種寫法都回應迅速，查詢在開發環境執行通過，只確認了語意描述符合預期；執行代價必須在接近正式環境的資料量與分布上量測。

執行 `ANALYZE` 前後計畫變動的現象，在正式系統上有對應的故障形態：統計資訊過時，或引擎缺少多欄位相關性統計時，最佳化器會依據偏差的估算選出低效計畫。[PostgreSQL Query Optimization：EXPLAIN、auto_explain、pg_hint_plan 與 planner 選錯 plan 的 production case](/backend/01-database/vendors/postgresql/query-optimization/) 整理了這類選錯計畫的實際案例，以及讀解正式環境計畫所用的 `EXPLAIN`、`EXPLAIN ANALYZE` 與 `auto_explain` 工具。
