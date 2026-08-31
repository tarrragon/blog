---
title: "Aggregate Function（聚合函數）"
date: 2026-08-31
description: "想知道為什麼聚合只能寫在某幾個位置、或連接之後的總和算出來不對時"
weight: 7
tags: ["sql", "aggregate", "group-by", "knowledge-card"]
---

Aggregate function 把一組列收成一個值：`count` 數幾列、`sum` 加總、`avg` 取平均、`max` 與 `min` 取極值。它的輸入是一組列，輸出是一個值——這個形狀決定了它能寫在哪裡，也決定了它在 [outer join](/sql/knowledge-cards/outer-join/) 之後為什麼容易算錯。

## 概念位置

**「一組」是由 `GROUP BY` 的鍵決定的，所以聚合要等到分組發生之後才有意義。** 這解釋了一個看起來像限制的行為：聚合寫進 `WHERE` 會被拒絕，因為那一步分組還沒發生，沒有組就沒有組的計數。同一件事寫進 `HAVING` 通過，因為那一步分組已經完成。

沒有 `GROUP BY` 的時候整張表算一組，所以 `SELECT count(*) FROM 訂單` 回一列。分組之後手上的單位從列換成組，而每一組仍然是一個 [relation](/sql/knowledge-cards/relation/) 的子集。

## 可觀察訊號與例子

`count(*)` 與 `count(欄位)` 數的不是同一件事：前者數列，後者只數那一欄有值的列。書店的兩張訂單接上評價之後有三列，而其中一列的星等是空的，於是 `count(*)` 回 3、`count(評價.星等)` 回 2。差額就是空缺的數量（見 [NULL](/sql/knowledge-cards/null/)）。

## 設計責任

**連接之後做聚合，算的是連接結果的列，不是來源表的列。** 一列配到多列就被複製一次，所以 `count` 會多、`sum` 會重複加。

處理方式依聚合的性質分兩類。**可加的**（`count`、`sum`）可以用 `count(DISTINCT 鍵)` 把單位拉回來，或先把展開的那一層各自彙總成一列再接上去。**不可加的**（`avg`、中位數、百分位）兩條路都不通——先彙總再平均會變成平均的平均，權重錯了。這一類要把分子與分母一起帶出來（子查詢裡同時算 `sum` 與 `count`，接上來之後再相除）。

`max` 與 `min` 是例外：它們對重複不敏感，複製幾次結果都一樣。
