---
title: "SQL.2 子句的求值順序：每一步可用的欄位、語意模型擋下的寫法與各家引擎放寬的寫法"
date: 2026-08-31
description: "從 FROM 到 LIMIT 每一步可用的欄位與值、聚合放進 WHERE、別名用在 WHERE 與列條件放進 HAVING 在各家引擎上的結果，以及這些寫法更換引擎時的表現"
aliases: ["/sql/clause-evaluation-order/"]
weight: 3
tags: ["sql", "clause-order", "having", "group-by", "alias"]
---

SQL 查詢的邏輯求值順序固定從 `FROM` 開始、最後執行 `LIMIT`，這條順序決定了每一個子句能讀取哪些欄位與值。本篇依序檢視各步驟的可用欄位，以聚合函數放進 `WHERE` 示範模型層限制，再以 `WHERE` 引用 `SELECT` 別名與列條件放進 `HAVING` 對照各家引擎的寬鬆反應，並整理分辨模型限制與引擎寬鬆的依據及 `ON`／`WHERE` 的延伸。

求值順序是[Semantic Model（語意模型）](/backend/01-database/sql/knowledge-cards/semantic-model/)規定的子句邏輯先後：`FROM` 決定參與運算的資料集合、`WHERE` 篩選列、`GROUP BY` 分組、`HAVING` 篩選組、`SELECT` 計算要輸出的欄位、`ORDER BY` 排序、`LIMIT` 截取前幾列。這個順序與書寫順序不同，寫在查詢開頭的 `SELECT` 在求值順序裡排在 `HAVING` 之後、`ORDER BY` 之前。引擎實際執行時的次序是另一層（執行順序），由最佳化器決定，書寫、求值與執行三種順序的分工見 [SQL.1 宣告式的紅利與代價：書寫、求值與執行順序各自由誰決定](/backend/01-database/sql/declarative-not-procedural/)。

求值順序規定了每一步可用的欄位與值，引擎據此拒絕引用尚未產生之值的寫法。引擎拒絕的成因依更換引擎時結果是否改變分為兩類：**模型層限制**指語意模型在該步驟尚未算出那個值，更換任何引擎都會拒絕；**引擎寬鬆**指語意模型在該步驟未定義該值，但部分引擎替寫查詢的人補上一個決定，更換引擎時結果就會改變。在拒絕該寫法的引擎上，模型層限制與引擎寬鬆產出的錯誤訊息外觀相同。

## 求值順序各步驟可用的欄位與值

`FROM` 完成後產出的中間結果是一個 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/)，其欄位來自來源表。`WHERE` 只能引用這些欄位，逐列判定保留或排除。本篇把 `FROM` 視為單一產出步驟；涉及多張表時，`FROM` 依書寫順序逐一合併資料表，這個累積過程如何決定每個 `ON` 可引用的欄位，見 [SQL.4 鏈式連接的左運算元：累積方式與外連接的保護範圍](/backend/01-database/sql/join-left-operand-accumulates/)。

`GROUP BY` 讓中間結果的運算單位從列轉成組，這是求值順序裡結構變化最大的一步。分組之前每一列各自獨立，分組之後每一組成為單一單位，組內個別列的欄位值不再直接可供引用。

`HAVING` 篩選的對象是分組後的組，因此可以使用 [Aggregate Function（聚合函數）](/backend/01-database/sql/knowledge-cards/aggregate-function/)，此時每一組的計數、總和與最大值均已可計算。接著 `SELECT` 計算最終輸出的欄位並建立欄位別名。`ORDER BY` 針對 `SELECT` 算完的輸出排序，因此可以引用欄位別名。`LIMIT` 排在最後，截取排序後的結果；未寫 `ORDER BY` 而直接使用 `LIMIT` 時，因為前面沒有任何步驟規定列序，回傳的列沒有順序保證。

## 模型層的限制：把聚合放進 WHERE

在 [SQL 各篇共用的範例資料庫：一家小書店的顧客、訂單與評價表](/backend/01-database/sql/sample-bookstore-database/) 中，三位顧客只有佳穎有兩張訂單。若要找出下過一張以上訂單的顧客，把「訂單張數大於一」寫進 `WHERE`：

```sql
SELECT 顧客編號 FROM 訂單 WHERE COUNT(*) > 1 GROUP BY 顧客編號;
```

SQLite 回傳 `misuse of aggregate: COUNT()`，DuckDB 回傳 `WHERE clause cannot contain aggregates`。將同一個條件移至 `HAVING` 則兩家引擎都通過：

```sql
SELECT 顧客編號, COUNT(*) AS 張數 FROM 訂單 GROUP BY 顧客編號 HAVING COUNT(*) > 1;
-- 兩個引擎都回 (1, 2)：顧客編號 1 的佳穎，兩張訂單
```

兩段查詢的差別在於分組是否已經發生。執行 `WHERE` 時引擎處理的是逐筆訂單列，「這一組有幾張訂單」在該步驟尚不存在，因此這是語意模型的結構限制，而非特定引擎缺少功能。這項限制與引擎寬鬆度無關；各家引擎對不合標準寫法的放寬差異與分級，見 [SQL.19 引擎寬鬆度與可攜性：各家對同一組寫法的差異、分級與處理時機](/backend/01-database/sql/engine-leniency-and-portability/)。

## 引擎寬鬆：WHERE 用 SELECT 的別名

依照求值順序，`WHERE` 排在 `SELECT` 之前，此時欄位別名尚未建立。SQL 標準據此禁止在 `WHERE` 引用 `SELECT` 別名，PostgreSQL 也遵循標準拒絕這類寫法。

SQLite 與 DuckDB 則放寬了這項限制。查詢佳穎這筆顧客紀錄時，把 `姓名` 欄取別名為 `客戶` 並在 `WHERE` 引用：

```sql
SELECT 姓名 AS 客戶 FROM 顧客 WHERE 客戶 = '佳穎';
-- SQLite 與 DuckDB 都回 ('佳穎',)；PostgreSQL 報 column "客戶" does not exist
```

各家引擎放寬的範圍須逐家確認，無法單憑求值順序推導。`GROUP BY` 與 `HAVING` 同樣排在 `SELECT` 之前，SQLite 與 DuckDB 在這兩個子句也接受 `SELECT` 建立的別名：

```sql
SELECT substr(下單日,1,7) AS 月份, count(*) AS 張數
FROM 訂單 GROUP BY 月份;   -- GROUP BY 引用的是 SELECT 那一步才取的別名
-- SQLite：2026-03 | 2
```

因此求值順序只能標示出可能受限的候選位置；某家引擎對哪些子句放寬、放寬到什麼程度，須查核各引擎的規則。

引擎的放寬建立在語意模型之上，並未取代原本的欄位解析規則。當來源表已有同名欄位時，`WHERE` 優先綁定來源表欄位而非 `SELECT` 別名。用一張含 `x` 與 `y` 兩欄的表實測，把 `y` 取別名為 `x` 後在 `WHERE` 寫 `x = 1`：

```sql
CREATE TABLE t (x INT, y INT);
INSERT INTO t VALUES (1, 2), (2, 1);

SELECT y AS x FROM t WHERE x = 1;
-- 2
```

若 `WHERE` 綁定別名，比對條件會是 `y = 1` 並回傳第二列的 `1`；實際回傳 `2`，代表 SQLite 與 DuckDB 都優先以來源欄位 `x` 比對。只有在來源表缺少同名欄位時，引擎才會退回以 `SELECT` 別名解析該名稱。

## 列的條件放進 HAVING：DuckDB、MySQL 與 SQLite 各自的反應

把聚合放進 `WHERE` 時各家引擎都會拒絕；反過來把屬於單列的條件放進 `HAVING` 時，各家反應分岔，其中 SQLite 不會報錯。

為了觀察不同組別的差異，在共用資料上新增訂單 103 並重設評價表，使訂單 101 有五星與三星各一則、訂單 102 有兩則五星、訂單 103 有一則三星：

```sql
INSERT INTO 訂單 VALUES (103, 2, '2026-03-20', 400);
DELETE FROM 評價;
INSERT INTO 評價 VALUES (1,101,5),(2,101,3),(3,102,5),(4,102,5),(5,103,3);
```

查詢目標是找出有兩則以上五星評價的訂單。正確寫法把星等這個列層級條件放進 `WHERE`：

```sql
SELECT 訂單編號, count(*) FROM 評價
WHERE 星等 = 5 GROUP BY 訂單編號 HAVING count(*) >= 2;
-- 102 | 2
```

結果只有訂單 102，因為訂單 101 的兩則評價中只有一則是五星。求值流程很清楚：`WHERE` 先排除三星的那兩列，剩下三列進入分組，訂單 101 該組剩一列、訂單 102 該組有兩列，最後 `HAVING` 篩掉訂單 101。

把星等條件移進 `HAVING`：

```sql
SELECT 訂單編號, count(*) FROM 評價
GROUP BY 訂單編號 HAVING 星等 = 5 AND count(*) >= 2;
```

DuckDB 拒絕並回報 `column 星等 must appear in the GROUP BY clause`，因為分組後一組內存在多個星等值，模型未定義「這一組的星等」。MySQL 8 同樣拒絕，而且在名稱解析階段就中止：

```text
ERROR 1054 (42S22): Unknown column '星等' in 'having clause'
```

MySQL 的 `HAVING` 只辨識分組鍵、聚合函數與 `SELECT` 別名，`星等` 不屬於這三類，因此直接報未知欄位。這個拒絕與設定無關，即使清空 `sql_mode`，錯誤訊息依然完全相同。

控制寬鬆度的設定是 `ONLY_FULL_GROUP_BY`（自 MySQL 5.7 起預設開啟），它管制的是將非分組欄位放進 `SELECT` 的寫法（`SELECT 訂單編號, 星等 FROM 評價 GROUP BY 訂單編號`）。開啟時 MySQL 回傳 `ERROR 1055` 並在訊息指名該設定；關閉後 MySQL 的行為與 SQLite 相同，從每組任意挑一列的值回傳。

SQLite 接受這段把列條件寫進 `HAVING` 的查詢，並回傳訂單 101 與 102。兩張訂單都被列為有兩則以上五星評價，但訂單 101 實際只有一則五星。SQLite 從訂單 101 該組中取出一列的星等比對，恰好取到五星那一列，整組於是通過篩選。

除了同一 `SELECT` 僅含單一 `min()` 或 `max()` 的情況（SQLite 規格明文保證非分組欄取自該極值所在的列），SQLite 規格不保證從組內挑中哪一列，寫查詢的人不能依賴這個取值結果。

相較於 DuckDB 與 MySQL 當場拒絕，SQLite 接受查詢並回傳錯誤清單的風險更高，因為輸出外觀完全合理：每組一列、欄位齊全、訂單編號都存在於資料表中，沒有任何異常跡象。在嚴格引擎上寫完當下就會報錯的寫法，在寬鬆引擎上會直接產出錯誤結果並流往下游。

同一個放寬機制也有程度較輕的形態：`SELECT 顧客編號, 下單日 FROM 訂單 GROUP BY 顧客編號`，DuckDB 拒絕而 SQLite 從組內任意挑一個日期回傳。非分組欄放進 `SELECT` 導致輸出欄位值不確定，列條件放進 `HAVING` 則讓整份篩選清單錯誤。

## 模型層的限制與引擎寬鬆：分辨的依據與換引擎時的表現

分辨模型層限制與引擎寬鬆的依據，是引擎在該步驟是否持有可補上的值。分組發生前，「這一組的訂單張數」尚未計算，引擎沒有值可補，因此聚合函數放進 `WHERE` 是模型層限制。執行 `WHERE` 時，`SELECT` 別名雖未建立，但它對應的運算式值已經可從來源列取得，差別僅在名稱，因此部分引擎願意把別名對應回原運算式。分組後「這一組的星等」在模型中未定義，但組內各列各自帶有星等值，SQLite 於是挑其中一列補上。`WHERE` 使用別名與列條件放進 `HAVING` 都屬於引擎寬鬆：語意模型未規定的決定，由引擎代為補上。

兩類限制在更換引擎時呈現不同表現。觸犯模型層限制的寫法在任何引擎上首次執行都會被拒絕；依賴引擎寬鬆的寫法在原引擎能正常執行，遷移到其他引擎時才浮現差異。其中從組內任挑一列的寬鬆行為最難察覺：在兩家同樣寬鬆的引擎之間遷移（例如 SQLite 與關閉 `ONLY_FULL_GROUP_BY` 的 MySQL），兩邊都不報錯，但挑出的列可能不同。

## 求值順序在連接上的實例：條件放 ON 還是 WHERE

將條件放在相鄰的兩個求值步驟，即使兩種寫法都合乎語法且不報錯，保留下來的列仍可能不同。這個現象在連接查詢上再次出現：`ON` 是 `FROM` 步驟內的配對條件，`WHERE` 是下一個步驟的篩選條件。在外連接中，同一個條件放進 `ON` 或 `WHERE` 會改變未配對列是否保留。[SQL.5 ON 與 WHERE：連接條件與篩選條件各自的職責](/backend/01-database/sql/on-describes-where-filters/) 以同一組書店資料並排兩種擺法的結果，並提供將補 `NULL` 的列代入條件的測試方式。由於這項差異由語意模型規定，SQLite、PostgreSQL 與 MySQL 對同一寫法會回傳相同的列，即使更換引擎也不會因此報錯。依 [SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/) 的成因分類，將外連接條件誤放 `WHERE` 屬於誤解語意模型；更換引擎才浮現的則是引擎寬鬆，如同〈列的條件放進 HAVING：DuckDB、MySQL 與 SQLite 各自的反應〉中 SQLite 接受列條件寫進 `HAVING` 的案例。關於連接起手式與連接種類的選擇，見 [SQL.3 連接的起手式：配對條件的位置與連接種類的選擇](/backend/01-database/sql/join-starts-from-the-relationship/)。
