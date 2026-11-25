---
title: "SQL.9 分組鍵的選擇：鍵與一組所代表的對象"
date: 2026-08-31
description: "外連接後誤用右表欄位當分組鍵造成空值併組的後果、輸出非分組欄時 MySQL、DuckDB 與 SQLite 的反應、補進鍵欄位的函數相依要求，以及改用 NOT EXISTS 的存在性查詢"
aliases: ["/sql/grouping-key-decides-the-unit/"]
weight: 10
tags: ["sql", "group-by", "null", "aggregate", "join"]
---

`GROUP BY` 的分組鍵決定結果中每一列代表的業務對象。本篇先示範外連接後誤用右表欄位作分組鍵如何將所有未配對列併成單組，再比較輸出非分組欄位時 MySQL、DuckDB 與 SQLite 的反應；隨後整理選取分組鍵的依據與函數相依條件，並以「找出沒下過單的顧客」界定何時應跳過分組改用 `NOT EXISTS`。

`GROUP BY` 把分組鍵值相同的列歸併成同一組，因此分組鍵決定了每一組代表的業務對象，後續的 `HAVING` 與 `SELECT` 都以該對象為運算單位。選錯分組鍵時查詢往往仍可正常執行並回傳結果，只是每組代表的對象與寫查詢的人預期的不同。

## 外連接之後用右表的欄位當分組鍵

在 [SQL 各篇共用的範例資料庫：一家小書店的顧客、訂單與評價表](/backend/01-database/sql/sample-bookstore-database/) 中，共有三位顧客，只有佳穎下過兩張訂單。若要找出沒下過單的顧客，先做 `LEFT JOIN` 再誤以訂單表的 `顧客編號` 分組：

```sql
SELECT 訂單.顧客編號 AS 分組鍵, count(*) AS 這組幾列,
       count(訂單.顧客編號) AS 有值幾列, group_concat(顧客.姓名) AS 裝了誰   -- group_concat 把一組裡的名字串起來
FROM 顧客 LEFT JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號
GROUP BY 訂單.顧客編號;
```

MySQL、SQLite 與 DuckDB 的輸出結果一致：

```text
分組鍵  這組幾列  有值幾列  裝了誰
NULL    2         0         宗翰,雅文
1       2         2         佳穎,佳穎
```

宗翰與雅文被歸併到同一組。兩人沒有對應訂單，外連接替他們的 `訂單.顧客編號` 補上 [NULL（空值）](/backend/01-database/sql/knowledge-cards/null/)。`GROUP BY` 處理 `NULL` 的規則與比較運算子相反：所有分組鍵為 `NULL` 的列會被視為同一組，因此全部未配對的列共用同一個分組（`NULL` 在比較運算與 `NOT IN` 上的三值邏輯行為見 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)；外連接補出的 `NULL` 與原始空值的區分見 [Outer Join（外連接）](/backend/01-database/sql/knowledge-cards/outer-join/)）。

若接著加上 `HAVING count(訂單.顧客編號) = 0`，該條件確實會選中沒下過單的那一組（因為 `count(欄位)` 只計有值的列，該組計數為零），但選出的單一分組裡同時包著宗翰與雅文兩筆列。

## 輸出非分組欄時各家引擎的反應

從外連接後依 `訂單.顧客編號` 分組的結果只輸出 `顧客.姓名` 時，因為 `姓名` 不在 `GROUP BY` 鍵中且未經聚合，三家引擎出現分岔：

```sql
SELECT 顧客.姓名 FROM 顧客
LEFT JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號
GROUP BY 訂單.顧客編號 HAVING count(訂單.顧客編號) = 0;
```

MySQL 8 預設拒絕執行：

```text
ERROR 1055 (42000): Expression #1 of SELECT list is not in GROUP BY clause and contains
nonaggregated column ... incompatible with sql_mode=only_full_group_by
```

DuckDB 同樣拒絕。SQLite 則接受這段查詢，並從分組鍵為 `NULL` 的組內任意挑選一列回傳，結果只出現宗翰，雅文無聲無息地消失且沒有任何錯誤訊息。

MySQL 與 DuckDB 擋下的是「輸出非分組欄位」這項違規，並未指出分組鍵選錯。若只為了讓查詢通過而把 `顧客.姓名` 補進 `GROUP BY`，三家引擎都會正常執行，且在三位顧客不同名的共用資料上恰好回傳正確答案；一旦新增同名顧客，錯誤便會顯現：

```sql
SELECT 顧客.姓名 FROM 顧客
LEFT JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號
GROUP BY 訂單.顧客編號, 顧客.姓名      -- 鍵仍是訂單表的顧客編號，只補上姓名
HAVING count(訂單.顧客編號) = 0;
-- 共用資料：宗翰、雅文

INSERT INTO 顧客 VALUES (4, '宗翰');   -- 第二位宗翰，同樣沒下過單
-- 同名合併示範完畢後還原初始資料，供後續查詢使用：
-- DELETE FROM 顧客 WHERE 顧客編號 = 4;
-- 重跑同一段查詢：宗翰、雅文
-- 沒下過單的顧客有三位而結果只有兩列：兩位宗翰的鍵都是 (NULL, 宗翰)，被併成一組
```

這個錯誤的根源是分組鍵讓不同顧客共用同一個鍵值，唯有資料出現同名顧客時才會浮現。這段查詢語法完全合法，依 [SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/) 的成因分類屬於寫錯查詢需求。

## 選分組鍵的判斷標準：一組代表的對象

要讓每一組代表一位顧客，分組鍵就必須是顧客表自己的識別欄位：

```sql
SELECT 顧客.姓名 FROM 顧客
LEFT JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號
GROUP BY 顧客.顧客編號, 顧客.姓名
HAVING count(訂單.顧客編號) = 0;
-- 宗翰、雅文
```

改用 `顧客.顧客編號` 後，三家引擎全部回傳兩列。宗翰與雅文各有非空的顧客編號，因此各自成組，且每組的訂單計數皆為零。

選擇分組鍵的判斷標準是先明確界定「每一組代表什麼業務對象」，並以該對象的唯一識別欄位作為分組鍵。若無法指出每組應代表的對象，通常代表該需求不需要使用分組（例如屬於單列篩選或存在性判斷）。

此外，`SELECT` 中所有未包進聚合函數的欄位都必須出現在 `GROUP BY` 裡，或由已宣告的主鍵／非空唯一約束證明與分組鍵具備**函數相依**（functional dependency，範例書店表未宣告主鍵，因此 MySQL 與 DuckDB 會要求補進 `顧客.姓名`，否則回報 `ERROR 1055` 或同類錯誤）。補進 `GROUP BY` 的欄位必須滿足這項性質：每一個分組鍵值只能對應到該欄位的單一值，MySQL 錯誤訊息裡的 `not functionally dependent on columns in GROUP BY clause` 指的正是這個性質。一個 `顧客編號` 只對應一個 `姓名`，因此補進 `姓名` 不改變分組粒度（反方向不需成立，兩位同名的宗翰仍因顧客編號不同而各自成組）。反之，`下單日` 不由 `顧客編號` 唯一決定；若把 `下單日` 補進 `GROUP BY`，同一位顧客的每個下單日都會被拆成獨立分組，計數語意悄悄變成「該顧客在該日的訂單數」，且引擎不報錯：

```sql
SELECT 顧客.姓名, 訂單.下單日, count(訂單.顧客編號) AS 張數 FROM 顧客
LEFT JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號
GROUP BY 顧客.顧客編號, 顧客.姓名, 訂單.下單日;
-- 佳穎 | 2026-03-02 | 1
-- 佳穎 | 2026-03-09 | 1      佳穎被拆成兩組
-- 宗翰 |            | 0
-- 雅文 |            | 0
-- 拿掉下單日、只按顧客編號與姓名分組時：佳穎 | 2、宗翰 | 0、雅文 | 0
```

因此，不由分組鍵唯一決定的欄位不可單純補進 `GROUP BY`，而應以聚合函數包裹（例如 `max(下單日)`），讓它成為每組的彙總值而非新的切分維度。

分組鍵決定每組由哪些列構成；計算完成後是否保留原本的明細列，則是分組與視窗函數的分界，兩者的輸出對照見 [SQL.10 分組與視窗函數：各自的產出、選用的依據與 LAG、LEAD 的相鄰列](/backend/01-database/sql/window-keeps-rows-grouping-collapses/)。

## 不需要分組的查詢：存在性判斷

將分組鍵修正為 `顧客.顧客編號` 雖可得到正確答案，但在挑選分組鍵之前，應先確認這項查詢是否需要分組。

從業務事實出發：沒消費過的顧客在訂單表裡沒有任何一列。直接對訂單表分組計數，無法查出訂單數為零的顧客：

```sql
SELECT 顧客編號, count(*) FROM 訂單 GROUP BY 顧客編號;
-- (1, 2)
```

結果只有佳穎。宗翰與雅文在訂單表沒有任何列，分組結果不會產生代表他們的組，自然也不會出現計數為零的列。外連接搭配 `count(訂單.訂單編號)` 查到的「零」是 `LEFT JOIN` 先補出全為 `NULL` 的假訂單列、再由 `count(欄位)` 數出來的人工產物，並非資料本身的特性。計數前提是有列可數，而這項需求的目標對象恰好一列都沒有，這才是分組寫法從起點就繞遠路的原因。

直接對應「找出在訂單表找不到對應紀錄的顧客」的 SQL 寫法是存在性判斷：

```sql
SELECT 姓名 FROM 顧客
WHERE NOT EXISTS (SELECT 1 FROM 訂單 WHERE 訂單.顧客編號 = 顧客.顧客編號);
-- 宗翰、雅文
```

這段查詢不涉及分組與計數，直接對應業務敘述。同一需求也可寫成外連接加 `IS NULL`，兩者結果一致：

```sql
SELECT 顧客.姓名 FROM 顧客
LEFT JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號
WHERE 訂單.訂單編號 IS NULL;   -- 訂單編號只有在外連接補出來的列上是 NULL
-- 宗翰、雅文
```

兩者差別在描述路徑：`NOT EXISTS` 直接表達不存在對應紀錄，外連接版本則先保留每位顧客再篩出補 `NULL` 的列（條件歸屬的推導見 [SQL.5 ON 與 WHERE：連接條件與篩選條件各自的職責](/backend/01-database/sql/on-describes-where-filters/)）。

`GROUP BY` 的用途是切換運算單位，適用於單看一列無法判斷的彙總需求（例如統計每位顧客的訂單張數、找出評價超過兩則的訂單）。是否需要分組的判斷依據與 [SQL.2 子句的求值順序：每一步可用的欄位、語意模型擋下的寫法與各家引擎放寬的寫法](/backend/01-database/sql/clause-evaluation-order/) 一致：若篩選條件無須彙總同組多列即可成立，直接留在 `WHERE` 即可，不需使用 `GROUP BY`。`IN`、`EXISTS` 與 `JOIN` 各自表達的語意，以及 `NOT IN` 在子查詢含 `NULL` 時回傳零列的風險，見 [SQL.8 IN、EXISTS 與 JOIN：列數、可取用的欄位與 NULL 的處理](/backend/01-database/sql/in-exists-join/)。
