---
title: "1.11 代價由資料與索引決定，不由寫法決定"
date: 2026-08-31
description: "三種寫法都對而其中一種特別慢、想知道差別出在寫法還是資料與索引時"
weight: 11
tags: ["sql", "cost", "query-plan", "index", "performance"]
---

同一段 SQL 的代價由資料分布與可用的索引決定，不由寫法決定。三種寫法都對而其中一種明顯慢的時候，慢的原因通常不在那段文字裡——換一個索引，排名就可能對調。


## 三種寫法都對

一張 `Person` 表，欄位是 `id` 與 `email`，要找出重複出現的 email。

**用分組。** 把列按 email 收成組，問這一組有幾列：

```sql
SELECT email FROM Person GROUP BY email HAVING count(*) > 1;
```

**用自連接。** 把表配對，找出 email 相同而 id 不同的兩列（[1.6](/sql/table-occurrence-and-alias/)）：

```sql
SELECT DISTINCT p1.email FROM Person p1
JOIN Person p2 ON p1.email = p2.email AND p1.id <> p2.id;
```

**用 `EXISTS`。** 對每一列問「有沒有另一列 email 跟我一樣」（[1.7](/sql/in-exists-join/)）：

```sql
SELECT DISTINCT email FROM Person p
WHERE EXISTS (SELECT 1 FROM Person q WHERE q.email = p.email AND q.id <> p.id);
```

## 加一個索引，同一組寫法的快慢排名重排

三個都給出正確答案。以下的時間都在 SQLite 3.49 上量，各跑三次取最小值。

**這一組數字的形狀依賴引擎的存取路徑**：SQLite 逐列處理、相關子查詢編成逐列的巢狀執行，所以加一個索引能把 `EXISTS` 那一格的單價整個換掉。向量化的引擎（本分類其餘各篇用來做三家對照的 DuckDB 就是）處理同一組查詢的方式不同，三者的差距形狀也不同。要看的是「代價由資料與可用的存取路徑決定」這個結論，不是這幾個絕對值。

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
| 分組     | 2.1 ms           | 1.1 ms         |
| 自連接   | 533 ms           | 592 ms         |
| `EXISTS` | 3090 ms          | 5.7 ms         |

沒有索引時最慢的是 `EXISTS`，有索引時它變成第二快——同一段查詢快了五百多倍。分組與自連接兩欄之間幾乎不動（自連接那格的方向在不同次量測之間會反轉，差距落在雜訊裡）。**三段查詢的文字一個字都沒有改。**

計畫說明了 `EXISTS` 那一格的變化。沒有索引時：

```text
SCAN p
CORRELATED SCALAR SUBQUERY 1
SCAN q
USE TEMP B-TREE FOR DISTINCT
```

`CORRELATED` 表示那個子查詢引用了外層的欄位，所以它對外層的每一列各執行一次，而每一次都是 `SCAN q`——掃過整張表。七千列各掃七千列。

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

**要看的是配對數那一欄。** 自連接把每一對重複的 email 實際配出來再靠 `DISTINCT` 收掉，而配對數是 n(n−1)——重複次數翻十倍，配對數就漲一百倍。時間欄沒有跟著漲一百倍，是因為五萬列的掃描本身有一筆固定成本，重複次數還小的時候那筆成本蓋過了配對；等配對數大到四百萬，它才浮上檯面。

分組那一欄不管重複多少次都在二十毫秒上下，因為它從頭到尾沒有展開任何配對。**這是結構上的差別，不是調校問題。**

## 所以「哪個比較快」要怎麼問

補上四項再問：**資料有多大、分布長什麼樣、有哪些索引、引擎有沒有統計資訊。** 最後一項是 [1.1](/sql/declarative-not-procedural/) 實測過的——同一段查詢在跑過 `ANALYZE` 之前與之後拿到不同的計畫。

資料量決定常數項會不會被放大。分布決定會不會踩到某個寫法的最壞情況——上面的自連接就是被重複程度打敗的。索引決定每一次查找的單價，而上面那組量測裡它讓同一段查詢差了五百多倍。

這三項都在資料庫那一側，所以問這個問題的正確方式是去問引擎，而不是比較兩段文字。做法是把兩種寫法各要一次計畫（SQLite 用 `EXPLAIN QUERY PLAN`，PostgreSQL 用 `EXPLAIN`），看它們差在哪；再改變其中一項（加索引、換資料量），看計畫變不變。


## 往下走

代價落在文字之外這件事從哪裡來，[1.1 宣告式的紅利與代價](/sql/declarative-not-procedural/) 從語言的性質推一次，並把書寫、求值、執行三種順序分開。

計畫裡的 `SCAN` 與 `SEARCH` 差在哪、`COVERING` 是什麼意思，查 [Query Plan（執行計畫）](/sql/knowledge-cards/query-plan/) 與 [Index（索引）](/sql/knowledge-cards/indexing/) 兩張卡。索引的代價落在寫入端這一點也在後者。

真實系統上的計畫比本篇複雜得多。到 [PostgreSQL Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/) 拿三層工具的分工與四個 production case。
