---
title: "1.10 代價由資料與索引決定，不由寫法決定"
date: 2026-08-31
description: "想判斷兩種寫法哪個比較快、或練習題都通過了卻不知道實際會不會慢時"
weight: 10
tags: ["sql", "cost", "query-plan", "index", "performance"]
---

「這兩種寫法哪個比較快」這個問題問得不完整。同一段 SQL 的代價由資料分布與可用的索引決定，而兩者都不在查詢的文字裡。補上這兩項之後才有答案，而答案會隨它們改變——包括排名整個對調。

本篇用一道有標準答案的題目把這件事量出來。

## 題目與三種寫法

一張 `Person` 表，欄位是 `id` 與 `email`，要找出重複出現的 email。

**用分組。** 把列按 email 收成組，問這一組有幾列：

```sql
SELECT email FROM Person GROUP BY email HAVING count(*) > 1;
```

**用自連接。** 把表配對，找出 email 相同而 id 不同的兩列（[1.8](/sql/table-occurrence-and-alias/)）：

```sql
SELECT DISTINCT p1.email FROM Person p1
JOIN Person p2 ON p1.email = p2.email AND p1.id <> p2.id;
```

**用 `EXISTS`。** 對每一列問「有沒有另一列 email 跟我一樣」（[1.9](/sql/in-exists-join/)）：

```sql
SELECT DISTINCT email FROM Person p
WHERE EXISTS (SELECT 1 FROM Person q WHERE q.email = p.email AND q.id <> p.id);
```

三個都給出正確答案。以下的時間都在 SQLite 上量，資料是七千列，其中一個 email 重複兩千次。

## 加一個索引，排名整個對調

| 寫法     | `email` 沒有索引 | `email` 有索引 |
| -------- | ---------------- | -------------- |
| 分組     | 2.1 ms           | 1.2 ms         |
| 自連接   | 535 ms           | 1116 ms        |
| `EXISTS` | 3026 ms          | 5.6 ms         |

沒有索引時最慢的是 `EXISTS`，有索引時它變成第二快，而且快了五百多倍。自連接則往相反方向走，加了索引反而慢了一倍。**三段查詢的文字一個字都沒有改。**

計畫說明了 `EXISTS` 那一格的變化。沒有索引時：

```text
SCAN p
CORRELATED SCALAR SUBQUERY 1
SCAN q
```

`CORRELATED` 表示那個子查詢引用了外層的欄位，所以它對外層的每一列各執行一次，而每一次都是 `SCAN q`——掃過整張表。七千列各掃七千列。

有索引之後同一段查詢：

```text
SCAN p USING INDEX ix
CORRELATED SCALAR SUBQUERY 1
SEARCH q USING INDEX ix (email=?)
```

子查詢仍然逐列執行，而每一次從 `SCAN`（掃全表）變成 `SEARCH`（透過[索引](/sql/knowledge-cards/indexing/)定位）。逐列執行這個結構沒變，變的是每一次的單價。

## 分組的代價與重複程度無關

另一組量測換一個變數：五萬列資料，其中一個 email 的重複次數從十次加到兩千次。

| 重複次數 | 配對數    | 分組    | 自連接   |
| -------- | --------- | ------- | -------- |
| 10       | 90        | 18.5 ms | 86.8 ms  |
| 200      | 39,800    | 17.6 ms | 89.4 ms  |
| 2000     | 3,998,000 | 19.0 ms | 957.2 ms |

分組完全不動。自連接在重複次數翻十倍時漲了十倍，因為它把將近四百萬個配對實際做出來，再靠 `DISTINCT` 收掉。

**這是一個結構上的差別，不是調校問題。** 自連接的工作量隨重複程度的平方成長，分組的工作量只隨資料量成長。哪一種資料會讓它們分岔，看的是重複的程度——而那是資料的性質，不是查詢的。

## 所以「哪個比較快」要怎麼問

補上三項再問：**資料有多大、分布長什麼樣、有哪些索引。**

資料量決定常數項會不會被放大。分布決定會不會踩到某個寫法的最壞情況——上面的自連接就是被重複程度打敗的。索引決定每一次查找的單價，而它能讓同一段查詢差三個數量級。

這三項都在資料庫那一側，所以問這個問題的正確方式是去問引擎，而不是比較兩段文字。做法是把兩種寫法各跑一次 `EXPLAIN`，看它們的[計畫](/sql/knowledge-cards/query-plan/)差在哪；再改變其中一項（加索引、換資料量），看計畫變不變。

## 練習平台驗的是另一半

練習題的資料量小到任何寫法都在幾毫秒內完成，所以通過與否只反映結果集對不對——也就是描述得對不對這一半。代價那一半在那個環境裡沒有東西可以量。

練習題的定位就落在這裡：先把描述練對，代價要另外練。而練代價的方式就是上面那一套——同一題寫兩種、把計畫調出來看、改變資料分布再看一次。三個步驟都不需要真實的 production 系統，一個本機的資料庫加幾萬列造出來的資料就夠。

有一件事值得先知道：**猜通常會猜錯。** `EXISTS` 沒有把配對展開，看起來應該是三者裡最省的一種；而在沒有索引的那一欄，它比自連接慢了將近六倍。這就是「代價不在文字裡」的具體樣子——從查詢的形狀推不出它的代價，推得再仔細也一樣。

## 往下走

**代價為什麼會落在文字之外**：[1.1 宣告式的紅利與代價](/sql/declarative-not-procedural/) 寫這個分工從哪裡來，以及書寫順序、求值順序與執行順序為什麼是三件事。

**計畫裡那些名詞各指什麼**：[Query Plan（執行計畫）](/sql/knowledge-cards/query-plan/) 與 [Index（索引）](/sql/knowledge-cards/indexing/) 給 `SCAN` 與 `SEARCH` 的分別、覆蓋索引的意思，以及索引的代價落在寫入端。

**在真實系統上讀計畫**：[PostgreSQL Query Optimization](/backend/01-database/vendors/postgresql/query-optimization/) 給 `EXPLAIN ANALYZE` 與 `auto_explain` 的分工，以及統計資訊過時、多欄統計缺失這類讓計畫選錯的實際案例。
