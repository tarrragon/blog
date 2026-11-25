---
title: "SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯"
date: 2026-08-31
description: "連接造成聚合多算的機制與計數、加總、平均、中位數各自的修法，以及外連接補出來的 NULL 在 count、等號比較、NOT IN 與 NOT EXISTS 上的行為"
aliases: ["/sql/join-changes-rows-and-nulls/"]
weight: 7
tags: ["sql", "null", "join", "aggregate", "count", "not-in"]
---

連接完成後的中間關係會產生兩項結構變化：一對多配對造成的列數增加，以及外連接配對失敗引入的空值。本篇處理這兩類變化引發的靜默錯誤：

- 一對多連接造成的列數膨脹，以及計數、加總、平均與中位數各自的正確寫法。
- 外連接補出的 `NULL` 如何讓 `count(*)` 與 `count(欄位)` 回傳不同結果。
- 三值邏輯下 `= NULL` 與 `IS NULL` 的差別，以及子查詢含 `NULL` 時 `NOT IN` 與 `NOT EXISTS`（含不等號比較）的行為邊界。
- 列數膨脹與空值的共同結構來源與建表前提。

`FROM` 執行完畢後產出的 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/) 是一個新的中間集合，不再等同於任何一張來源表：它的列數可能比來源表多，也會多出原本來源表沒有的空值，而後續所有子句都在這個新關係上執行。本篇從這個關係成形之後談起；多張表逐一連接時左運算元的累積過程，見 [SQL.4 鏈式連接的左運算元：累積方式與外連接的保護範圍](/backend/01-database/sql/join-left-operand-accumulates/)。

列數增加與出現空值各引發一類不報錯的查詢錯誤。**列數膨脹**指連接複製了來源列，使聚合計算的對象變成連接後的列而得出偏高的結果；**比較 `NULL` 的錯誤**指拿 `NULL` 參與比較運算時得到「未知」而非真或假，導致 `WHERE` 裡的等號與 `NOT IN` 回傳零列，或使 `NOT EXISTS` 子查詢裡的不等號多留下一列。

## 列數膨脹與各類聚合的修法

以下數的單位都是「列」，即資料表裡橫向的一筆資料——三張訂單對應三列，與每列包含幾個欄位無關。

在 [SQL 各篇共用的範例資料庫：一家小書店的顧客、訂單與評價表](/backend/01-database/sql/sample-bookstore-database/) 中，訂單表原有 101 與 102 兩列，且只有訂單 101 有一則評價，因此訂單表左連接評價表後仍是兩列。為訂單 101 新增第二則評價後，連接結果變成三列：

```sql
SELECT count(*) FROM 訂單 LEFT JOIN 評價 ON 評價.訂單編號 = 訂單.訂單編號;
-- 共用資料：2

INSERT INTO 評價 VALUES (9002, 101, 3);

SELECT count(*) FROM 訂單 LEFT JOIN 評價 ON 評價.訂單編號 = 訂單.訂單編號;
-- 替 101 再加一則評價之後：3
```

訂單表的列數未變，連接後的關係卻多了一列。原因是連接逐列配對：訂單 101 配到兩則評價，在結果裡便出現兩次，各自帶著其中一則評價。

後續的聚合運算作用在這個新關係的列上，而非原本的訂單表。直接用 `count(*)` 計算佳穎的訂單數會得出錯誤結果：

```sql
SELECT 顧客.姓名, count(*) AS 看起來的訂單數,
       count(DISTINCT 訂單.訂單編號) AS 實際訂單數
FROM 顧客 JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號
LEFT JOIN 評價 ON 評價.訂單編號 = 訂單.訂單編號
GROUP BY 顧客.姓名;
-- 佳穎 | 3 | 2
```

佳穎實際只有兩張訂單，`count(*)` 卻回傳 3；SQLite、DuckDB 與 PostgreSQL 的結果完全相同。列數膨脹難以察覺，是因為多出的數量看起來合乎常理，且只隨評價筆數緩慢增加，沒有異常的數值跳躍或錯誤訊息。

避免列數膨脹的判斷方式是先確認聚合要計算的單位（例如訂單本身，而非連接後的評價配對列）。決定分組粒度的選鍵方法見 [SQL.9 分組鍵的選擇：鍵與一組所代表的對象](/backend/01-database/sql/grouping-key-decides-the-unit/)；將計算單位拉回目標層次的寫法，依聚合函數的數學性質分為計數、加總與不可加聚合。

**計數**可以使用 `count(DISTINCT 訂單編號)`，將計數單位鎖定在唯一的訂單識別碼上。

**加總**不能用 `DISTINCT` 修正。直接對連接結果執行 `sum(訂單.金額)` 會把訂單 101 的金額重複加總兩次；改寫成 `sum(DISTINCT 金額)` 去掉的是相同數值而非相同訂單，兩張剛好同金額的不同訂單會少算一次。正確做法是先在子查詢裡把造成一對多展開的子表收成每單一列，再與主表連接：

```sql
-- 直接連接再加總：101 配到兩則評價，300 被加了兩次
SELECT sum(訂單.金額) FROM 訂單 LEFT JOIN 評價 ON 評價.訂單編號 = 訂單.訂單編號;
-- 1100

-- 括號裡那一段先把每張訂單的評價收成一列，接上來之後每張訂單在結果裡只有一列
SELECT 訂單.訂單編號, 訂單.金額, 評價數
FROM 訂單
LEFT JOIN (SELECT 訂單編號, count(*) AS 評價數 FROM 評價 GROUP BY 訂單編號) AS 評價統計
  ON 評價統計.訂單編號 = 訂單.訂單編號;
-- 101 | 300 | 2
-- 102 | 500 |
```

每張訂單在這份結果裡只佔一列，對金額加總時每張訂單便只計算一次。

**不可加的聚合**（平均、中位數、百分位）無法先在訂單層算完再合併到顧客層。若先算每張訂單的平均星等再取平均，評價數多與評價數少的訂單會獲得相同權重，得出失真的「平均的平均」；`DISTINCT` 去掉的是重複值而非重複列，同樣無法解決。替訂單 102 新增一則一星評價，讓兩張訂單的評價則數不同：

```sql
INSERT INTO 評價 VALUES (9003, 102, 1);

-- 平均的平均：101 的兩則平均 4、102 的一則平均 1，再平均一次
SELECT avg(每單平均) FROM (SELECT 訂單編號, avg(星等) AS 每單平均 FROM 評價 GROUP BY 訂單編號);
-- 2.5
```

佳穎收到的三則評價為 5、3、1，實際平均是 3，而非 2.5。平均與中位數、百分位的處理方式不同。

平均可以拆成總和與個數兩個可加的量：在子查詢同時計算 `sum` 與 `count`，外層各自加總之後再相除：

```sql
SELECT 顧客.姓名, sum(評價統計.星等總和) * 1.0 / sum(評價統計.則數) AS 平均星等
FROM 顧客
JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號
JOIN (SELECT 訂單編號, sum(星等) AS 星等總和, count(*) AS 則數 FROM 評價 GROUP BY 訂單編號) AS 評價統計
  ON 評價統計.訂單編號 = 訂單.訂單編號
GROUP BY 顧客.姓名;
-- 佳穎 | 3.0
```

`sum` 與 `count` 跨層仍可直接相加，無論經過幾層彙總，最後相除的都是全部評價的星等總和與總則數。乘上 `1.0` 是為了避免整數除法將小數截斷。

中位數與百分位無法拆成可加的量：已知各張訂單的中位數，推不出合併後的中位數，因此必須在目標層次上直接對原始列計算，並確保每筆原始資料只出現一次。計算「每位顧客收到的評價星等中位數」時，顧客接訂單再接評價的結果中每則評價恰好出現一次，可直接計算；若查詢還連接了會複製評價列的表，須先將評價收成每則一列。語法隨引擎而異：PostgreSQL 內建 `percentile_cont`；SQLite 的 `median()` 與 `percentile()` 屬可選擴充，可執行 `SELECT median(1);` 確認手上環境是否支援，不支援時以視窗函數依星等排序後取中間列（偶數筆時取中間兩列的平均）：

```sql
-- 此時佳穎收到的評價是 5、3、1
-- PostgreSQL：percentile_cont 在每一組裡依 ORDER BY 排好之後取 0.5 分位
SELECT 顧客.姓名, percentile_cont(0.5) WITHIN GROUP (ORDER BY 評價.星等) AS 中位數
FROM 顧客
JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號
JOIN 評價 ON 評價.訂單編號 = 訂單.訂單編號
GROUP BY 顧客.姓名;
-- 佳穎 | 3

-- SQLite 沒有 median() 時：名次是那位顧客的評價依星等排序後的位置，則數是那位顧客的評價總數
WITH 排序後 AS (
  SELECT 顧客.姓名, 評價.星等,
         row_number() OVER (PARTITION BY 顧客.顧客編號 ORDER BY 評價.星等) AS 名次,
         count(*)     OVER (PARTITION BY 顧客.顧客編號) AS 則數
  FROM 顧客
  JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號
  JOIN 評價 ON 評價.訂單編號 = 訂單.訂單編號
)
SELECT 姓名, avg(星等) AS 中位數 FROM 排序後
WHERE 名次 IN ((則數 + 1) / 2, (則數 + 2) / 2)   -- 依賴 SQLite 整數除法捨去小數（例如則數為 3 時兩式皆得 2，偶數時為中間兩列；在 `/` 回傳浮點數的引擎須改用整數除法）
GROUP BY 姓名;
-- 佳穎 | 3.0
-- 實測完成後還原訂單 102 無評價的狀態：
-- DELETE FROM 評價 WHERE 評價編號 = 9003;
```

## 外連接補出來的 NULL：count(*) 與 count(欄位) 的差別

在訂單 101 有兩則評價（9001、9002）、訂單 102 無評價的狀態下，外連接配對不到對象時會補出原本來源表裡不存在的 [NULL（空值）](/backend/01-database/sql/knowledge-cards/null/)。`LEFT`、`RIGHT` 與 `FULL` 各自在哪一側補空值，定義見 [Outer Join（外連接）](/backend/01-database/sql/knowledge-cards/outer-join/)。`count(*)` 與 `count(欄位)` 對這些空值的計算結果不同：

```sql
SELECT count(*) AS 全部列, count(評價.星等) AS 有星等的列
FROM 訂單 LEFT JOIN 評價 ON 評價.訂單編號 = 訂單.訂單編號;
-- 3 | 2
```

`count(*)` 計算全部的列數，`count(欄位)` 只計算該欄位不為 `NULL` 的列數，兩者的差額正好是空值列數。在單表查詢裡若原始欄位少有空值，這個差異不易顯現；經過外連接後，補出的 `NULL` 會讓兩者立刻分開。

## NULL 的比較結果與 IS NULL

查詢沒下過單的顧客時，若用等號比對 `NULL`，查詢會靜默回傳空集合：

```sql
SELECT 顧客.姓名 FROM 顧客
LEFT JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號
WHERE 訂單.訂單編號 = NULL;
-- 0 列，而且沒有任何錯誤訊息

-- 同一段改成 IS NULL
SELECT 顧客.姓名 FROM 顧客
LEFT JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號
WHERE 訂單.訂單編號 IS NULL;
-- 宗翰、雅文
```

寫成 `= NULL` 在 SQLite、DuckDB 與 PostgreSQL 上都回傳零列且不報錯。`IS NULL` 必須寫在 `WHERE` 而非 `ON`，因為它篩選的是連接完成後、已補上 `NULL` 的結果列（[SQL.5 ON 與 WHERE：連接條件與篩選條件各自的職責](/backend/01-database/sql/on-describes-where-filters/) 推導了 `ON` 與 `WHERE` 的職責邊界）。

`= NULL` 永遠無法配對的原因，在於 `NULL` 代表缺失或未知的值，拿未知的值與任何值做比較運算，結果同樣是未知：

```sql
SELECT (NULL = NULL), (NULL IS NULL);
-- NULL | 1        SQLite 用 1 表示真
```

`NULL = NULL` 的評估結果是真與假之外的第三種真值（未知）。`WHERE` 只保留評估結果為真的列，未知與假在篩選階段都會遭到排除。

`IS NULL` 與 `IS NOT NULL` 是專門檢查空缺的運算子，評估結果只有真與假兩種；相較之下，`=` 或 `<>` 遇見 `NULL` 時永遠回傳未知而無法使條件成立。因此檢查欄位是否為空對應的語法即為 `IS NULL` 與 `IS NOT NULL`。

## 子查詢含 NULL 時的 NOT IN 與 NOT EXISTS

同一套三值邏輯（見 [NULL（空值）](/backend/01-database/sql/knowledge-cards/null/)）在 `NOT IN` 上會產生更隱蔽的失效形態。用 `NOT IN` 找出沒下過單的顧客，在共用資料上看似正常：

```sql
SELECT 姓名 FROM 顧客 WHERE 顧客編號 NOT IN (SELECT 顧客編號 FROM 訂單);
-- 共用資料：宗翰、雅文
```

當訂單表新增一筆顧客編號為 `NULL` 的紀錄（例如尚未綁定顧客的訂單）後，重跑同一段查詢，SQLite、DuckDB 與 PostgreSQL 全部回傳零列且不報錯：

```sql
INSERT INTO 訂單 VALUES (103, NULL, '2026-03-10', 200);

SELECT 姓名 FROM 顧客 WHERE 顧客編號 NOT IN (SELECT 顧客編號 FROM 訂單);
-- 0 列
--   子查詢交出 1、1、NULL，NOT IN 對宗翰（顧客編號 2）展開成 2 <> 1 AND 2 <> 1 AND 2 <> NULL
--   與 1 比較的兩項為真，與 NULL 比較的那一項是未知，AND 的結果是未知，WHERE 不留
```

引擎把 `NOT IN` 展開成一串「不等於」條件的 `AND` 組合。只要子查詢回傳任何一個 `NULL`，與該 `NULL` 比較的項目便為未知，整串 `AND` 的評估結果便無法為真，導致所有列全被 `WHERE` 排除。

改用 `NOT EXISTS` 不受子查詢中的 `NULL` 影響：

```sql
SELECT 姓名 FROM 顧客
WHERE NOT EXISTS (SELECT 1 FROM 訂單 WHERE 訂單.顧客編號 = 顧客.顧客編號);
-- 共用資料：宗翰、雅文
-- 訂單 103 進來之後：宗翰、雅文

-- 刪掉 103：留著的話，金額最高的那段查詢會把它也選進來
DELETE FROM 訂單 WHERE 訂單編號 = 103;
```

`NOT EXISTS` 檢查的是子查詢是否回傳至少一筆配對列，答案只有存在（真）或不存在（假）兩種，顧客編號為 `NULL` 的訂單配不上任何顧客，不影響外層判斷。

這項安全邊界只限於子查詢使用等號配對的情形；子查詢改用不等號比較時，`NULL` 同樣會造成結果錯誤。以「找出每位顧客金額最高的訂單」為例，若寫成「同一位顧客不存在另一張金額更高的訂單」，金額為 `NULL` 的訂單會被一併選出。原因在於子查詢的比較條件變成 `b.金額 > NULL`，對每一列都評估為未知，子查詢一列都找不到，`NOT EXISTS` 於是成立。在共用資料新增一張金額為 `NULL` 的訂單 104 即可驗證：

```sql
INSERT INTO 訂單 VALUES (104, 1, '2026-03-12', NULL);

SELECT a.訂單編號, a.金額 FROM 訂單 a
WHERE NOT EXISTS (SELECT 1 FROM 訂單 b WHERE b.顧客編號 = a.顧客編號 AND b.金額 > a.金額);
-- 102 | 500    子查詢對 102 找不到金額更高的訂單
-- 104 |        子查詢比的是 b.金額 > NULL，對每一張 b 都是未知，一列都找不到
--   101 沒有出現：102 的 500 > 300 為真，子查詢找得到一列

-- 子查詢之外另寫 a.金額 IS NOT NULL，排除金額未填的那一張
SELECT a.訂單編號, a.金額 FROM 訂單 a
WHERE a.金額 IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM 訂單 b WHERE b.顧客編號 = a.顧客編號 AND b.金額 > a.金額);
-- 102 | 500

DELETE FROM 訂單 WHERE 訂單編號 = 104;
```

未在外層加上 `a.金額 IS NOT NULL` 時，佳穎的最高金額訂單會同時回傳 102 與金額未填的 104。

## 列數改變、空缺與 NULL 比較的共同來源

列數膨脹、外連接補出空值與空值的三值比較，三者都源自同一個事實：`FROM` 產出的是新的中間關係，後續每個子句都在這份新關係上運算。若寫查詢的人仍以原始來源表的列數與值域去解讀 `WHERE`、`GROUP BY` 與聚合函數，就會在這幾個位置出錯。

連接後列數是否膨脹、欄位是否可能出現空值，在本篇屬於既定條件，其根本原因取決於更早的建表設計：資料是否拆成一對多張表決定列數膨脹的可能，欄位是否允許為空決定空值能否進入查詢。建表決定造成的查詢成本與聚合雙重展開實測，見 [1.16 Schema 設計決定的查詢代價：可空性、排序鍵唯一性、表寬、一對多的切法、比較規則、外鍵執法，以及從另一張表取值時的複製與引用](/backend/01-database/design-decisions-price-every-query/)。

列數膨脹與 `NULL` 比較錯誤雖然機制不同，共同特徵是引擎不會發出任何錯誤訊息：列數膨脹回傳的欄位結構正常而總和偏高，`= NULL` 與 `NOT IN` 回傳零列而與「確實無資料」外觀相同，`NOT EXISTS` 搭配不等號多出的列也是一筆真實存在的訂單。結果形狀正確為何不構成答案正確的保證，完整討論見 [SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/)。
