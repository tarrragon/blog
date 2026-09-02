---
title: "Semi-join 與 Anti-join（半連接與反連接）"
date: 2026-09-02
description: "看到 EXISTS 或 NOT EXISTS 時，查它在代數裡對應哪個運算、以及列數上限為什麼是左邊那張表的列數"
weight: 20
tags: ["sql", "join", "exists", "relational-algebra", "semi-join", "anti-join", "knowledge-card"]
---

半連接把兩個 [relation](/sql/knowledge-cards/relation/) 配起來之後只留下左邊那一份：結果的欄位全部來自左邊，而左邊的每一列至多出現一次。留下的是在右邊找得到對象的那些列。反連接留下的是另一半——左邊那些在右邊配不到任何對象的列，結果的欄位同樣只有左邊的。

SQL 用 `EXISTS` 與 `NOT EXISTS` 表達這兩個運算，語言本身沒有為它們保留關鍵字：

```sql
-- 半連接：下過單的顧客
SELECT 姓名 FROM 顧客
WHERE EXISTS (SELECT 1 FROM 訂單 WHERE 訂單.顧客編號 = 顧客.顧客編號);

-- 反連接：從未下單的顧客
SELECT 姓名 FROM 顧客
WHERE NOT EXISTS (SELECT 1 FROM 訂單 WHERE 訂單.顧客編號 = 顧客.顧客編號);
```

## 名字裡的「半」指結果只帶走一邊

三個運算作用在同一對關係上，差別在結果帶走什麼。

| 運算   | 結果的欄位   | 結果的列數         | SQL 寫法       |
| ------ | ------------ | ------------------ | -------------- |
| 連接   | 左右兩邊都有 | 可能超過左邊的列數 | `JOIN ... ON`  |
| 半連接 | 只有左邊的   | 至多左邊的列數     | `EXISTS`、`IN` |
| 反連接 | 只有左邊的   | 至多左邊的列數     | `NOT EXISTS`   |

右邊那份資料在這兩個運算裡的角色是條件，它的欄位到不了結果。要把右邊的欄位列出來就得用連接，那條判準在 [1.8](/sql/in-exists-join/)。

## 列數上限省掉去重這一步

半連接問的是配不配得到，所以配到幾筆不影響結果——一位顧客手上有兩張訂單或二十張訂單，`EXISTS` 都只讓她出現一次。同一個問題用連接寫，她會照訂單張數各出現一次，要補 `DISTINCT` 把複製出來的列收掉（[1.6](/sql/join-changes-rows-and-nulls/)）。

需要 `DISTINCT` 因此是一個訊號：這個查詢問的是有沒有，而連接順便做了它不需要的配對。

## 反連接有兩條描述路徑

`NOT EXISTS` 直接說「找不到」。[外連接](/sql/knowledge-cards/outer-join/)那一版先讓左邊每一列都保留下來，再挑出補了 `NULL` 的那些：

```sql
SELECT 顧客.姓名 FROM 顧客
LEFT JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號
WHERE 訂單.訂單編號 IS NULL;
```

兩段回同一批列，路徑不同——一條由條件直接表達，另一條靠外連接補出來的 `NULL` 當標記。

`NOT IN` 的行為與這兩條分岔：子查詢的結果裡出現一個 [NULL](/sql/knowledge-cards/null/)，整段就回零列且不報錯。反連接的安全寫法因此落在 `NOT EXISTS` 與外連接這兩條上（[1.6](/sql/join-changes-rows-and-nulls/)）。

## 概念位置

半連接與反連接跟連接一樣是導出運算：半連接等於連接之後只投影左邊的欄位再去重，反連接等於左邊減去半連接的結果。[關聯代數](/sql/knowledge-cards/relational-algebra/)的正典運算清單因此多半只列到連接，而「有沒有對應資料」這一族問題全部落在這兩個運算上——找出下過單的顧客、找出從未下單的顧客、找出比前一天熱的日子，題目與寫法各異而運算只有這兩個。

它們與[積](/sql/knowledge-cards/cartesian-product/)分別是連接結果大小的兩個極端。積是條件缺席時的上限，列數是兩邊相乘；半連接把上限壓到左邊的列數，因為右邊配到幾列都只算一次。中間那一段是連接，結果的大小由配對的重複程度決定。

## 往下走

`IN`、`EXISTS` 與 `JOIN` 在列數與可取用欄位上的差別、以及選哪一種只問一句話，在 [1.8 IN、EXISTS 與 JOIN 描述的是三件不同的事](/sql/in-exists-join/)。從一句業務描述推到反連接、以及為什麼計數那條路走不通，在 [1.9 分組鍵決定每一組代表什麼](/sql/grouping-key-decides-the-unit/)。同一張表的兩列互相比較時這兩個運算長什麼樣，在 [1.7 查詢裡的表是一個具名的出現](/sql/table-occurrence-and-alias/)。同一組寫法的快慢隨索引與資料分布重排的實測，在 [1.17 代價由資料與索引決定](/sql/cost-lives-in-the-plan/)。
