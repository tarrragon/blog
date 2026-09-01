---
title: "1.13 代價由資料與索引決定，不由寫法決定"
date: 2026-08-31
description: "同一組寫法在索引與資料分布改變後的實測排名，以及比較兩段查詢該補上哪些條件"
weight: 13
tags: ["sql", "cost", "query-plan", "index", "performance"]
---

同一段 SQL 的代價由資料分布與可用的索引決定，不由寫法決定。同一組寫法的快慢排名會隨著索引改變而對調，而三段查詢的文字一個字都沒有動。


## 三種寫法都對

一張 `Person` 表，欄位是 `id` 與 `email`，要找出重複出現的 email。

**用分組。** 把列按 email 收成組，問這一組有幾列：

```sql
SELECT email FROM Person GROUP BY email HAVING count(*) > 1;
```

**用自連接。** 把表配對，找出 email 相同而 id 不同的兩列（[1.7](/sql/table-occurrence-and-alias/)）：

```sql
SELECT DISTINCT p1.email FROM Person p1
JOIN Person p2 ON p1.email = p2.email AND p1.id <> p2.id;
```

**用 `EXISTS`。** 對每一列問「有沒有另一列 email 跟我一樣」（[1.8](/sql/in-exists-join/)）：

```sql
SELECT DISTINCT email FROM Person p
WHERE EXISTS (SELECT 1 FROM Person q WHERE q.email = p.email AND q.id <> p.id);
```

## 加一個索引，同一組寫法的快慢排名重排

三個都給出正確答案。以下的時間都在 SQLite 3.51 上量，資料庫沒有跑過 `ANALYZE`，同一句各跑二十次取最小值。計時器的解析度是一毫秒，落在它以下的格子只寫得出「不到 1」。

**這一組數字的形狀依賴引擎的存取路徑**：SQLite 逐列處理、相關子查詢編成逐列的巢狀執行，所以加一個索引能把 `EXISTS` 那一格的單價整個換掉。DuckDB 是向量化的引擎——它一次處理一批列而不是一列一列走——本分類其餘各篇拿它做三家對照；它處理同一組查詢的方式與 SQLite 不同，三種寫法在它上面的差距形狀也不同。要看的是「代價由資料與可用的存取路徑決定」這個結論，不是這幾個絕對值。

資料是這樣造的：

```sql
CREATE TABLE Person (id INTEGER PRIMARY KEY, email TEXT);

WITH RECURSIVE n(i) AS (SELECT 0 UNION ALL SELECT i+1 FROM n WHERE i < 4999)
INSERT INTO Person SELECT i, 'u' || i || '@x.com' FROM n;

WITH RECURSIVE n(i) AS (SELECT 0 UNION ALL SELECT i+1 FROM n WHERE i < 1999)
INSERT INTO Person SELECT 100000 + i, 'hot@x.com' FROM n;

-- 有索引的那一欄另外跑：CREATE INDEX ix ON Person(email);
```

七千列，其中一個 email 重複兩千次。**同一段查詢在別的機器或別的版本上絕對值會不同，要看的是同一欄之內的相對關係。**

| 寫法     | `email` 沒有索引 | `email` 有索引 |
| -------- | ---------------- | -------------- |
| 分組     | 1 ms             | 不到 1 ms      |
| 自連接   | 217 ms           | 186 ms         |
| `EXISTS` | 1378 ms          | 1 ms           |

沒有索引時最慢的是 `EXISTS`，有索引時它掉到與分組同一個量級——同一段查詢差了三個量級。分組與自連接兩欄之間沒有這種變化：分組本來就貼著計時器的解析度，加了索引之後量不出來；自連接快了百分之十幾，五輪量測的方向一致而幅度遠不到一個量級。**三段查詢的文字一個字都沒有改。**

計畫說明了 `EXISTS` 那一格的變化。沒有索引時：

```text
SCAN p
CORRELATED SCALAR SUBQUERY 1
SCAN q
USE TEMP B-TREE FOR DISTINCT
```

`CORRELATED` 表示那個子查詢引用了外層的欄位，所以它對外層的每一列各執行一次，而每一次都是 `SCAN q`——掃過整張表。外層那七千列，每一列都讓內層把整張七千列的表掃過一遍。

有索引之後同一段查詢：

```text
SCAN p USING COVERING INDEX ix
CORRELATED SCALAR SUBQUERY 1
SEARCH q USING COVERING INDEX ix (email=?)
```

子查詢仍然逐列執行，而每一次從 `SCAN`（掃全表）變成 `SEARCH`（透過[索引](/sql/knowledge-cards/indexing/)定位）。逐列執行這個結構沒變，變的是每一次的單價。

## 分組的代價只隨資料量走

另一組量測換一個變數：五萬列資料，其中一個 email 的重複次數從十次加到兩千次，都沒有索引。

| 重複次數 | 配對數    | 分組    | 自連接   |
| -------- | --------- | ------- | -------- |
| 10       | 90        | 19.1 ms | 88.5 ms  |
| 200      | 39,800    | 18.3 ms | 90.4 ms  |
| 2000     | 3,998,000 | 21.3 ms | 606.6 ms |

分組完全不動。自連接則在最後一段漲了將近七倍。

**要看的是配對數那一欄。** 自連接把每一對重複的 email 實際配出來再靠 `DISTINCT` 收掉，而配對數是 n(n−1)，隨 n 平方成長——重複次數翻十倍，配對數漲的是一百倍。時間欄沒有跟著漲一百倍，是因為五萬列的掃描本身有一筆固定成本，重複次數還小的時候那筆成本蓋過了配對；等配對數大到四百萬，它才浮上檯面。

分組那一欄不管重複多少次都在二十毫秒上下，因為它從頭到尾沒有展開任何配對。**這是結構上的差別，不是調校問題。**

## 所以「哪個比較快」要怎麼問

補上四項再問：**資料有多大、分布長什麼樣、有哪些索引、引擎有沒有[統計資訊](/sql/knowledge-cards/query-statistics/)。** 最後一項是 [1.1](/sql/declarative-not-procedural/) 實測過的——同一段查詢在跑過 `ANALYZE` 之前與之後拿到不同的計畫。

資料量決定常數項會不會被放大。分布決定會不會踩到某個寫法的最壞情況——上面的自連接就是被重複程度打敗的。索引決定每一次查找的單價，而上面那組量測裡，索引的有無讓同一段查詢差了三個量級。

這三項都在資料庫那一側，所以「哪個比較快」是一個要向引擎問的問題，不是比較兩段文字就答得出來的問題。而且要問兩次：一次拿到現在這個狀態下的計畫，一次改動其中一項（加索引、換資料量）之後再拿一次，看它變不變。問一次只拿得到一個狀態下的答案，而上面那兩張表證明狀態換了排名就換。各家的問法不同，SQLite 是 `EXPLAIN QUERY PLAN`，PostgreSQL 是 `EXPLAIN`。


## 換掉其中一項會變成什麼

本篇把索引的有無、資料的重複程度與量測用的引擎都當成可以抽換的條件，抽換任何一項，代價的判讀就要重算。

**往回問代價為什麼一開始就落在文字之外**：那是宣告式這個選擇的直接後果。[1.1 宣告式的紅利與代價](/sql/declarative-not-procedural/) 從語言的性質推一次，並把書寫、求值、執行三種順序分開。

**這個結論有一個有界的例外**：條件把索引欄位包進函式裡的時候，寫法決定的是引擎能不能用那個索引，而非它在幾條路裡挑哪一條。[Sargable（可走索引的條件形狀）](/sql/knowledge-cards/sargable/) 給判斷標準與三種改寫方向。

**問這件事對怎麼寫查詢意味著什麼**：代價既然由資料與索引決定，那查詢的文字該為誰而寫。[1.15 好讀的寫法多數時候也是引擎好走的](/sql/readable-and-fast-mostly-align/) 量了三組——寫法差異免費的、條件形狀讓兩者分岔的、以及拆開反而快二十幾倍的——並給出分岔時該動查詢還是動 schema 的判準。

**把計畫上那些字讀懂**：`SCAN` 與 `SEARCH` 差在哪、`COVERING` 是什麼意思，由 [Query Plan（執行計畫）](/sql/knowledge-cards/query-plan/) 與 [Index（索引）](/sql/knowledge-cards/indexing/) 兩張卡承擔。索引的代價落在寫入端這一點也在後者。

**把引擎換成真實系統**：本篇的計畫只有三四行，真實系統的計畫有巢狀節點與估計列數。[PostgreSQL Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/) 給三層工具的分工與四個 production case。
