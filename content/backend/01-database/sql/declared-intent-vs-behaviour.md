---
title: "SQL.21 關鍵字的宣告與引擎的行為：宣告落空的形態與查證"
date: 2026-09-01
description: "LEFT JOIN、CROSS JOIN、DISTINCT、COALESCE 與表別名各自向閱讀者宣告的預期、宣告落空時後續維護者付出的代價，以及將關鍵字換成最弱版本重跑的查證動作與邊界"
aliases: ["/sql/declared-intent-vs-behaviour/"]
weight: 22
tags: ["sql", "join", "distinct", "intent", "maintenance"]
---

`LEFT JOIN`、`CROSS JOIN`、`DISTINCT`、`COALESCE` 與表別名都會向後續維護者傳達資料形態的預期，但資料庫引擎只執行操作、不查核這些預期是否兌現。本篇涵蓋以下內容：

- 各關鍵字的宣告意義與常見的宣告落空形態。
- 被 `WHERE` 撤銷的 `LEFT JOIN`、帶等值條件的 `CROSS JOIN`、配對已有約束保證時的 `LEFT JOIN`，以及用來壓掉連接重複的 `DISTINCT` 實測案例。
- 將關鍵字降級為最弱版本重跑的查證動作與適用邊界。

一段 SQL 同時面對兩個對象：引擎讀取的是操作行為（算出哪批列），維護者讀取的是關鍵字宣告（撰寫者選用 `LEFT`、`CROSS`、`DISTINCT` 或特定別名，代表他對資料形態的預期）。引擎只負責執行操作，從不驗證這些宣告是否兌現。

多數宣告落空不會在查詢輸出或測試裡現形，其中已被約束保證的 `LEFT JOIN` 或壓掉連接重複的 `DISTINCT` 從 [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/) 也觀察不到異狀；被 `WHERE` 撤銷的 `LEFT JOIN` 與帶等值條件的 `CROSS JOIN` 則須主動比對執行計畫（例如確認 PostgreSQL 是否已改寫為內連接）才能察覺。付出代價的是後續接手修改的人，他會依錯誤的宣告推導出錯誤的前提。與這類落差相鄰的兩個議題各有專篇：查詢語法合法但未對應業務需求（回傳錯誤答案）見 [SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/)；同一段查詢在不同引擎組態下的行為差異見 [SQL.19 引擎寬鬆度與可攜性：各家對同一組寫法的差異、分級與處理時機](/backend/01-database/sql/engine-leniency-and-portability/)。

以下範例執行於[SQL 各篇共用的範例資料庫：一家小書店的顧客、訂單與評價表](/backend/01-database/sql/sample-bookstore-database/)（顧客為佳穎、宗翰、雅文，僅佳穎有訂單 101 金額 300 與 102 金額 500）。閱讀本篇前應具備以下前置機制：`LEFT JOIN` 的保護範圍見 [SQL.4 鏈式連接的左運算元：累積方式與外連接的保護範圍](/backend/01-database/sql/join-left-operand-accumulates/)，條件放 `ON` 或 `WHERE` 的差異見 [SQL.5 ON 與 WHERE：連接條件與篩選條件各自的職責](/backend/01-database/sql/on-describes-where-filters/)，連接造成列數膨脹見 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)。

## 各個關鍵字的宣告與落空的形態

每個關鍵字都向後續閱讀者傳達特定資料預期：`LEFT JOIN` 宣告預期存在右表配不到的左表列且這些列須保留；`CROSS JOIN` 宣告需要兩表所有配對組合；`DISTINCT` 宣告目標欄位本身存在重複值且需去重；`COALESCE` 宣告該欄位可能出現 [NULL（空值）](/backend/01-database/sql/knowledge-cards/null/)；表別名（如 `FROM 訂單 AS 早`）宣告該次出現代表較早的訂單。這些宣告沒有語法成本，引擎也不會查核其真實性。

宣告落空常見於以下形態：

- **被同段查詢的其他子句撤銷**：例如 `LEFT JOIN` 搭配濾除空值的 `WHERE`。
- **描述引擎未執行的操作**：例如 `CROSS JOIN` 加上等值條件。
- **描述約束已排除的資料情形**：例如外鍵與 `NOT NULL` 已保證配對時的 `LEFT JOIN`。
- **指向錯誤成因但偶然得出正確結果**：例如用 `DISTINCT` 壓掉連接造成的重複列。
- **別名與條件方向相反**：例如名為 `早` 的別名實際代表較晚訂單（範例見 [SQL.7 表的出現與別名：表名的指稱、別名的作用範圍與自連接](/backend/01-database/sql/table-occurrence-and-alias/)）。

採用這些寫法的查詢在現有資料上皆回傳正確答案，但會誤導後續修改者：加一個輸出欄位就讓 `DISTINCT` 失效，改寫 `SELECT` 時仍因未動到的 `WHERE` 而找不到被保護的顧客，或依錯誤宣告做出錯誤的資料狀態判斷。

## 被 WHERE 撤銷的 LEFT JOIN

當 `WHERE` 對右表欄位施加拒絕 `NULL` 的條件時，`LEFT JOIN` 保留未配對列的宣告會在執行時被撤銷。以書店找出下過超過 200 元訂單的顧客為例，若寫成以下 `LEFT JOIN`：

```sql
SELECT 顧客.姓名
FROM 顧客 LEFT JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號
WHERE 訂單.金額 > 200;
-- 佳穎、佳穎

-- 同一段把 LEFT JOIN 換成 JOIN，其餘不動
SELECT 顧客.姓名
FROM 顧客 JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號
WHERE 訂單.金額 > 200;
-- 佳穎、佳穎
```

`LEFT JOIN` 宣告保留沒有訂單的顧客，但 `WHERE 訂單.金額 > 200` 把宗翰與雅文補上 `NULL` 的列全數排除（機制見 [SQL.5 ON 與 WHERE：連接條件與篩選條件各自的職責](/backend/01-database/sql/on-describes-where-filters/)），使實際執行結果等同於內連接。

後續維護者讀到 `LEFT JOIN`，以為沒有訂單的顧客也在結果集裡，於是加上 `COALESCE(訂單.金額, 0)` 企圖顯示零元：

```sql
SELECT 顧客.姓名, COALESCE(訂單.金額, 0) AS 金額   -- 他加的欄位：沒有訂單的顧客顯示 0
FROM 顧客 LEFT JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號
WHERE 訂單.金額 > 200;                              -- 他沒有動的那一行
-- 佳穎 300
-- 佳穎 500
```

查詢執行後依然只出現佳穎，宗翰與雅文並未現身，原因隱藏在維護者未曾修改的 `WHERE` 子句裡。

## CROSS JOIN 加等值條件與內連接的計畫

比較同一批資料的兩列時，部分寫法會先寫 `CROSS JOIN` 再於 `WHERE` 補上等值條件：

```sql
SELECT 今天.訂單編號
FROM 訂單 昨天 CROSS JOIN 訂單 今天
WHERE 今天.顧客編號 = 昨天.顧客編號 AND 今天.金額 > 昨天.金額;
```

`CROSS JOIN` 向閱讀者傳達「展開全部組合」的意圖，但在加入等值條件後，[Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/) 產出的執行計畫與標準 `JOIN ... ON` 完全一致：

```sql
SELECT 今天.訂單編號
FROM 訂單 昨天 JOIN 訂單 今天
  ON 今天.顧客編號 = 昨天.顧客編號 AND 今天.金額 > 昨天.金額;
-- 102（CROSS JOIN 那一段也回 102）
```

```text
-- CROSS JOIN 加 WHERE 等值（SQLite 3.51，共用的範例資料庫，沒有另外建索引）
|--SCAN 昨天
|--BLOOM FILTER ON 今天 (顧客編號=?)
`--SEARCH 今天 USING AUTOMATIC COVERING INDEX (顧客編號=?)

-- JOIN ... ON 同一個條件
|--SCAN 昨天
|--BLOOM FILTER ON 今天 (顧客編號=?)
`--SEARCH 今天 USING AUTOMATIC COVERING INDEX (顧客編號=?)
```

`AUTOMATIC` 代表 SQLite 因訂單表缺少 `顧客編號` [Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/) 而臨時建立覆蓋索引（covering index，索引本身已含查詢所需全部欄位、無須回表），兩段查詢連這項計畫決定都逐字相同。[Cartesian Product（笛卡兒積）](/backend/01-database/sql/knowledge-cards/cartesian-product/) 說明了等值條件存在時引擎不會先展開全部配對。

這個落空的誤導方向與 `LEFT JOIN` 相反：被撤銷的 `LEFT JOIN` 會向維護者傳達保留未配對列的假訊號，帶等值條件的 `CROSS JOIN` 則會讓維護者以為查詢具平方級複雜度，白費心力改寫一段實質上已是內連接的查詢（效能驗證見 [SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/)）。將它改為 `JOIN ... ON` 省下的是維護者的疑慮，而非執行時間。

## 配對已有保證時的 LEFT JOIN

當表結構已確保每張訂單皆指向有效顧客時，以 `LEFT JOIN` 連接訂單與顧客仍能正常執行：

```sql
SELECT 訂單.訂單編號, 顧客.姓名
FROM 訂單 LEFT JOIN 顧客 ON 顧客.顧客編號 = 訂單.顧客編號;
```

`LEFT JOIN` 宣告「訂單可能找不到對應顧客」，但每筆訂單皆具備對應顧客，這項宣告從未生效：

```sql
SELECT count(*), count(顧客.姓名)   -- count(*) 數列數，count(欄位) 只數那一欄不是 NULL 的列
FROM 訂單 LEFT JOIN 顧客 ON 顧客.顧客編號 = 訂單.顧客編號;
-- 2  2：沒有任何一列是 LEFT 補出來的
```

若後續維護者相信這項宣告，順手沿用該段連接檢查孤兒訂單：

```sql
SELECT 訂單.訂單編號
FROM 訂單 LEFT JOIN 顧客 ON 顧客.顧客編號 = 訂單.顧客編號
WHERE 顧客.姓名 IS NULL;            -- 配不到顧客的訂單，姓名會是 LEFT 補上的 NULL
-- 零列
```

回傳零列有兩種截然不同的成因：資料表確實沒有孤兒訂單，或該 `LEFT` 宣告所設想的情形根本不存在，單看查詢輸出無法區分。真正保證配對必然存在的是已生效的 [Constraint（約束）](/backend/01-database/sql/knowledge-cards/constraint/)（`NOT NULL` 加外鍵）；當查詢關鍵字與表約束互相矛盾時，閱讀者容易只憑眼前的查詢文字做判斷，忽略定義在 schema 檔案裡的約束。

## 收掉連接重複的 DISTINCT

顧客表與訂單表連接後，佳穎因有兩張訂單而出現兩次。若要取得下過單的顧客名單，加上 `DISTINCT` 可得到正確輸出：

```sql
SELECT DISTINCT 姓名 FROM 顧客 JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號;
-- 佳穎
```

`DISTINCT` 宣告的是「`姓名` 欄位本身含有重複值」，但在顧客表裡佳穎只有一列，重複是由連接展開造成的（見 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)）。這項宣告把成因指錯方向，只因恰好去重而回傳正確結果。

只要後續需求多加一個訂單欄位，這個修法就會立刻失效：

```sql
SELECT DISTINCT 姓名, 金額 FROM 顧客 JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號;
-- 佳穎 300
-- 佳穎 500
```

`DISTINCT` 作用在整個輸出列上，兩列金額不同便不再合併，先前的寫法失去預期效果，維護者必須重新追查重複列的真正來源。

## 查證宣告的動作：把關鍵字換成最弱的版本再跑一次

單讀查詢文字無法判斷關鍵字宣告是否實際發揮作用。最直接的查證方式是將目標關鍵字降級為最弱版本後重跑查詢，觀察輸出是否改變——在軟體測試領域，這對應於 [Mutation Testing（突變測試）](/testing/knowledge-cards/mutation-testing/)：改寫後在現有資料上結果不變稱為突變「存活」，進一步確認它是否在所有資料上都等價（equivalent mutant），則看能否構造出讓改寫前後輸出不同的反例資料（構造方式見 [SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/)）。

| 宣告                         | 降級版本                 | 結果不變代表的意義           |
| ---------------------------- | ------------------------ | ---------------------------- |
| `LEFT JOIN` / `RIGHT JOIN`   | `JOIN`                   | 在現有資料上行為等同內連接   |
| `CROSS JOIN` 加 `WHERE` 等值 | `JOIN ... ON` 同一個條件 | 實質上是內連接（限等值條件） |
| `DISTINCT`                   | 移除                     | 現有資料中該欄位組原本無重複 |
| `COALESCE(欄位, 預設值)`     | 直接使用該欄位           | 該欄位在現有資料上不含空值   |

若降級後結果改變，只代表該關鍵字在目前查詢中確有作用，尚不代表它的宣告指向正確成因——例如移除 `DISTINCT` 後結果變多，原因是連接展開了列數，而非顧客表姓名重複。因此結果改變後仍須確認「變化成因與關鍵字宣告的預期是否一致」。

對於「配對已有約束保證時的 `LEFT JOIN`」，僅靠降級重跑無法分辨它到底是「目前剛好沒有孤兒訂單」還是「外鍵已永久排除孤兒訂單」。此時須直接查詢系統目錄（資料庫內建用來記錄表、欄、約束與權限定義的系統表）確認 [Constraint（約束）](/backend/01-database/sql/knowledge-cards/constraint/) 是否存在且已生效（查法見 [SQL.18 外鍵與參照完整性：宣告、生效與查詢得到的保證](/backend/01-database/sql/foreign-key-and-referential-integrity/)）。

確認關鍵字宣告與實際行為一致後，撰寫查詢時面對的另一個取捨是可讀性與執行效能的關係，[SQL.22 可讀性與執行代價：兩者一致與分岔的情形](/backend/01-database/sql/readable-and-fast-mostly-align/) 實測兩者同向與分岔的情形及對應調整層級。
