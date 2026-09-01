---
title: "NULL（空值）"
date: 2026-08-31
description: "查 NULL 在比較、計數與分組裡各自怎麼表現時"
weight: 6
tags: ["sql", "null", "three-valued-logic", "knowledge-card"]
---

NULL 表示這個位置沒有值。它與零、空字串都不同——那兩者是值，NULL 是值的缺席。它出現在兩種來源：資料本身就沒填，或 [outer join](/sql/knowledge-cards/outer-join/) 替配不到的列補上。

它的行為在三個地方與一般的值不同，而三處各自有一組要記的規則。

## 概念位置

**比較：拿 NULL 去比對任何值，答案是第三種——未知。** 真、假、未知這三種答案合起來叫三值邏輯，SQL 的每一個條件都在這套邏輯裡求值。 `NULL = NULL` 的結果既不是真也不是假。而 `WHERE` 只留下判斷為真的列，所以「未知」與「假」在那一步的下場相同：列被丟掉。判斷有沒有值要用 `IS NULL` 與 `IS NOT NULL`，它們問的是位置有沒有值、答案只有真假兩種。

**計數：`count(*)` 數列，`count(欄位)` 只數那一欄有值的列。** 兩者的差額就是空缺的數量。

**分組：`GROUP BY` 把 NULL 當成一個值來分。** 所有那一欄是 NULL 的列會收進同一組——這是 NULL 少數表現得像一般值的地方。連接產出的那個 [relation](/sql/knowledge-cards/relation/) 因此可能有一整組列共用同一個空缺。

## 可觀察訊號與例子

書店的三位顧客裡只有佳穎下過單。`LEFT JOIN` 之後宗翰與雅文的訂單欄是 NULL，而用等號去找他們回零列且不報錯：

```sql
WHERE 訂單.訂單編號 = NULL     -- 0 列，沒有錯誤訊息
WHERE 訂單.訂單編號 IS NULL    -- 宗翰、雅文
```

分組那一側的表現相反。按訂單表的顧客編號分組，宗翰與雅文因為都是 NULL 而被收進同一組——MySQL、SQLite 與 DuckDB 的結果一致。

最難發現的是 `NOT IN`：子查詢的結果裡只要有一個 NULL，整段查詢回零列而三個引擎都不報錯。推導、實測與 `NOT EXISTS` 的安全範圍在 [1.5](/sql/join-changes-rows-and-nulls/)。

## 設計責任

**否定式的成員判斷一律用 `NOT EXISTS`**，除非能保證子查詢那一欄不會有 NULL——而那個保證要來自欄位的[約束](/sql/knowledge-cards/constraint/)，不是來自習慣。

判斷空缺的來源也要分開。`IS NULL` 為真時，可能是這一列沒配到對象，也可能是配到了而那個欄位本來就空。兩者在結果裡長得一樣，要靠選對欄位來分——用連接鍵那一欄判斷「有沒有配到」最可靠，因為它在配得上的時候必定有值。
