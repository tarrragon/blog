---
title: "SQL.17 查詢的代價：資料分布、索引與寫法各自的影響"
date: 2026-08-31
description: "同一組寫法在索引與資料分布改變後的實測排名，以及比較兩段查詢該補上哪些條件"
aliases: ["/sql/cost-lives-in-the-plan/"]
weight: 18
tags: ["sql", "cost", "query-plan", "index", "performance"]
---

同一段 SQL 的代價由資料分布與可用的索引決定，不由寫法決定。同一組寫法的快慢排名會隨著索引改變而對調，而分組、自連接與 `EXISTS` 三段查詢的文字一個字都沒有動。


## 找重複 email 的分組、自連接與 EXISTS 寫法

一張 `Person` 表，欄位是 `id` 與 `email`，要找出重複出現的 email。

**用分組。** 把列按 email 收成組，問這一組有幾列：

```sql
SELECT email FROM Person GROUP BY email HAVING count(*) > 1;
```

**用自連接。** 把表配對，找出 email 相同而 id 不同的兩列（[SQL.7 表的出現與別名：表名的指稱、別名的作用範圍與自連接](/backend/01-database/sql/table-occurrence-and-alias/)）：

```sql
SELECT DISTINCT p1.email FROM Person p1
JOIN Person p2 ON p1.email = p2.email AND p1.id <> p2.id;
```

**用 `EXISTS`。** 對每一列問「有沒有另一列 email 跟我一樣」（[SQL.8 IN、EXISTS 與 JOIN：列數、可取用的欄位與 NULL 的處理](/backend/01-database/sql/in-exists-join/)）：

```sql
SELECT DISTINCT email FROM Person p
WHERE EXISTS (SELECT 1 FROM Person q WHERE q.email = p.email AND q.id <> p.id);
```

## 有無索引時分組、自連接與 EXISTS 的實測時間與計畫

分組、自連接、`EXISTS` 三種寫法都給出正確答案。以下的時間都在 SQLite 3.51 上量，資料庫沒有跑過 `ANALYZE`，同一句各跑二十次取最小值。計時器的解析度是一毫秒，量到的時間落在它以下時，下面表格對應的那一格只寫得出「不到 1」。

**這一組數字的形狀依賴引擎的存取路徑**：SQLite 逐列處理、相關子查詢編成逐列的巢狀執行，所以加一個索引能把下面表格裡 `EXISTS` 那一格代表的每次查找成本整個換掉。DuckDB 是向量化的引擎——它一次處理一批列而不是一列一列走——處理同一組查詢的方式與 SQLite 不同，三種寫法在它上面的差距形狀也不同。要看的是「代價由資料與可用的存取路徑決定」這個結論，不是下面表格列出的這幾個絕對值。

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

沒有索引時最慢的是 `EXISTS`，有索引時它掉到與分組同一個量級——同一段查詢差了三個量級。分組與自連接兩欄之間沒有這種變化：分組本來就貼著計時器的解析度，加了索引之後量不出來；自連接快了百分之十幾（217 對 186 毫秒）。這個差距小到要先排除雜訊，所以另外重建資料重跑了五輪，每一輪照樣各跑二十次取最小值：五輪都是有索引的那一欄較快，而幅度都遠不到一個量級。**三段查詢的文字一個字都沒有改。**

計畫說明了 `EXISTS` 那一格從沒有索引到有索引的時間變化。沒有索引時：

```text
|--SCAN p
|--CORRELATED SCALAR SUBQUERY 1
|  `--SCAN q
`--USE TEMP B-TREE FOR DISTINCT
```

`CORRELATED` 表示那個子查詢引用了外層的欄位，所以它對外層的每一列各執行一次，而每一次都是 `SCAN q`——掃過整張表。外層那七千列，每一列都讓內層把整張七千列的表掃過一遍。

有索引之後同一段查詢：

```text
|--SCAN p USING COVERING INDEX ix
`--CORRELATED SCALAR SUBQUERY 1
   `--SEARCH q USING COVERING INDEX ix (email=?)
```

子查詢仍然逐列執行，而每一次從 `SCAN`（掃全表）變成 `SEARCH`（透過[索引](/backend/01-database/sql/knowledge-cards/indexing/)定位）。逐列執行這個結構沒變，變的是每一次的單價。`COVERING` 的意思寫在 [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/) 那張卡；索引本身的代價落在寫入端，這一點寫在 [Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/) 那張卡。

## 重複次數改變時分組與自連接的實測

另一組量測換一個變數：五萬列資料，其中一個 email 的重複次數從十次加到兩千次，都沒有索引。三份資料各自這樣造（`k` 依序是 10、200、2000）：

```sql
CREATE TABLE Person (id INTEGER PRIMARY KEY, email TEXT);

WITH RECURSIVE n(i) AS (SELECT 0 UNION ALL SELECT i+1 FROM n WHERE i < 50000-k-1)
INSERT INTO Person SELECT i, 'u' || i || '@x.com' FROM n;

WITH RECURSIVE n(i) AS (SELECT 0 UNION ALL SELECT i+1 FROM n WHERE i < k-1)
INSERT INTO Person SELECT 1000000 + i, 'hot@x.com' FROM n;
```

| 重複次數 | 配對數    | 分組 | 自連接 |
| -------- | --------- | ---- | ------ |
| 10       | 90        | 8 ms | 30 ms  |
| 200      | 39,800    | 8 ms | 32 ms  |
| 2000     | 3,998,000 | 8 ms | 232 ms |

分組完全不動。自連接則在重複次數兩千那一列漲了七倍多。

**要看的是配對數那一欄。** 自連接把每一對重複的 email 實際配出來再靠 `DISTINCT` 收掉，而配對數是 n(n−1)，隨 n 平方成長——重複次數翻十倍，配對數漲的是一百倍。自連接那一欄的時間沒有跟著漲一百倍，是因為五萬列的掃描本身有一筆固定成本，重複次數還小的時候那筆成本蓋過了配對；等配對數大到四百萬，它才浮上檯面。

分組那一欄不管重複多少次都是同一個值，因為它從頭到尾沒有展開任何配對。**分組與自連接在這裡的差別是結構上的，不是調校問題。**


## 寫法影響代價的邊界：條件把索引欄包進函式

本篇的結論有一個邊界，出現在條件把索引欄包進函式的時候。資料沿用〈有無索引時分組、自連接與 EXISTS 的實測時間與計畫〉那一節有索引的七千列：

```sql
EXPLAIN QUERY PLAN SELECT * FROM Person WHERE lower(email) = 'hot@x.com';
-- `--SCAN Person
-- 索引 ix 存的是 email 本身，條件問的是 lower() 算完的結果，
-- 引擎在索引上找不到那個值，只能掃全表、逐列算完再比

EXPLAIN QUERY PLAN SELECT * FROM Person WHERE email = 'hot@x.com';
-- `--SEARCH Person USING COVERING INDEX ix (email=?)
-- 條件直接比 email，引擎在索引上查找
```

兩個條件只在 email 一律以小寫存放時回同一批列——這份資料是，兩段都回兩千列；`lower()` 那一段另外會配到大小寫寫法不同的 email。這時寫法決定的是引擎**能不能用**那個索引，而不是它在幾條可行的存取路徑裡挑哪一條——所以它是本篇結論的前提：哪幾條存取路徑可行由條件的形狀決定，挑哪一條才由資料與索引決定。[Sargable（可走索引的條件形狀）](/backend/01-database/sql/knowledge-cards/sargable/) 給判斷一個條件能不能走索引的標準，以及讓條件走得了索引的改寫方向：把函數條件改寫成範圍（`date(下單日) = X` 寫成 `下單日 >= X AND 下單日 < 次日`）、把運算從索引欄移到比較式的另一個運算元上，或者對運算式本身建索引。

## 比較兩段查詢的快慢：要補上的條件與向引擎要計畫的做法

補上四項再問：**資料有多大、分布長什麼樣、有哪些索引、引擎有沒有[統計資訊](/backend/01-database/sql/knowledge-cards/query-statistics/)。** 最後一項是 [SQL.1 宣告式的紅利與代價](/backend/01-database/sql/declarative-not-procedural/) 實測過的——同一段查詢在跑過 `ANALYZE` 之前與之後拿到不同的計畫；那一篇也從 SQL 這個語言的性質推了一次，代價為什麼一開始就落在查詢文字之外。

資料量決定像自連接那筆固定掃描成本這種常數項會不會被放大。分布決定會不會踩到某個寫法的最壞情況——上面的自連接就是被重複程度打敗的。索引決定每一次查找的單價，而加索引前後的那組量測裡，索引的有無讓同一段查詢差了三個量級。

資料量、分布與索引都是資料庫當下的狀態，查詢的文字裡讀不到，所以「哪種寫法比較快」是一個要向引擎問的問題，不是比較兩段文字就答得出來的問題。而且要問兩次：一次拿到現在這個狀態下的計畫，一次改動其中一項（加索引、換資料量）之後再拿一次，看它變不變。問一次只拿得到一個狀態下的答案，而加索引前後的那張表證明狀態換了排名就換，重複次數那張表證明分組與自連接的差距會隨資料的分布放大。各家的問法不同，SQLite 是 `EXPLAIN QUERY PLAN`，PostgreSQL 是 `EXPLAIN`。本篇的計畫只有三四行，真實系統的計畫有巢狀節點與估計列數，[PostgreSQL Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/) 給`EXPLAIN`、`EXPLAIN ANALYZE`、`auto_explain` 三層工具的分工，以及四個計畫選錯的 production case：該走索引而走了全表掃描、該用 hash join 而用了 nested loop、缺少多欄位統計而估錯列數、該平行執行而沒有。

代價既然由資料與索引決定，查詢的文字就可以先為讀它的人而寫。[SQL.21 可讀性與執行代價：兩者一致與分岔的情形](/backend/01-database/sql/readable-and-fast-mostly-align/) 並排了三組——寫法差異免費的、條件形狀讓兩者分岔的、以及拆開之後在四萬列上快三十多倍的——並給出分岔時該動查詢還是動 schema 的判斷標準。
