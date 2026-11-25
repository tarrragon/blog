---
title: "Aggregate Function（聚合函數）"
date: 2026-08-31
description: "需要確認聚合函數可寫在哪些子句位置，或連接後的總和與計數結果異常時"
aliases: ["/sql/knowledge-cards/aggregate-function/"]
weight: 7
tags: ["sql", "aggregate", "group-by", "knowledge-card"]
---

Aggregate function（聚合函數）將一組列彙總為單一值：`count` 計算列數、`sum` 計算總和、`avg` 計算平均、`max` 與 `min` 取得極值，另有一類將多列字串或值併成清單的順序敏感聚合（如 `GROUP_CONCAT`、`STRING_AGG`、`ARRAY_AGG`）。輸入是一組列、輸出是單一值的結構，決定了它在求值順序中的可用位置，也決定了它在 [Outer Join（外連接）](/backend/01-database/sql/knowledge-cards/outer-join/) 之後容易出現多算的原因。

## 跟其他概念的關係

「一組」由 `GROUP BY` 的分組鍵定義，因此聚合函數只有在分組完成之後才能求值。在 `WHERE` 子句寫入聚合函數會被引擎拒絕，因為該步驟尚未分組、組計數尚不存在；移至 `HAVING` 子句則通過，因為此時分組已完成。

未撰寫 `GROUP BY` 時，整張資料表視為單一分組，因此 `SELECT count(*) FROM 訂單` 回傳一列。分組後結果的運算單位從列轉為組，每一組仍屬於一個 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/) 的子集。

## 可觀察訊號與例子

`count(*)` 與 `count(欄位)` 計算的對象不同：`count(*)` 計算全部列數，`count(欄位)` 只計算該欄位不為 `NULL` 的列數。例如書店的訂單 101 有兩則評價、訂單 102 無評價時，左連接評價表後得到三列，其中一列星等為 `NULL`，因此 `count(*)` 回傳 3、`count(評價.星等)` 回傳 2，差額即為空值列數（見 [NULL（空值）](/backend/01-database/sql/knowledge-cards/null/)）。

## 判斷條件與後果

連接之後執行聚合，引擎計算的是連接產出結果的列，而非原始來源表的列。當一筆主表列配到多筆子表列時，該主表列會被複製多次，導致 `count` 偏高、`sum` 重複加總。

修正方式依聚合函數的數學性質而異：

- **可加聚合（`count`、`sum`）**：計數可改用 `count(DISTINCT 鍵)` 將單位拉回主鍵；加總須先在子查詢把造成一對多展開的子表依鍵彙總成單列，再與主表連接。
- **不可加聚合（`avg`、中位數、百分位）**：不可先在子層取平均再於外層平均（會使筆數不同的組獲得相同權重而得出錯誤結果）。平均須在子查詢同時帶出 `sum` 與 `count`，於外層各自加總後再相除；中位數與百分位則須在目標層次直接對未重複的原始列計算。
- **`max` 與 `min`**：對重複列不敏感，主表列即使被複製多次仍回傳相同的極值。
- **順序敏感聚合（`GROUP_CONCAT`、`STRING_AGG`、`ARRAY_AGG`）**：輸出結果直接取決於組內列的輸入順序，且重複列會重複出現在拼接結果裡；須於函數內顯式指定 `ORDER BY`（必要時加 `DISTINCT` 或先去重），否則順序會隨執行計畫變動。
