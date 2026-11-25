---
title: "NULL（空值）"
date: 2026-08-31
description: "需要查閱 NULL 在比較運算、聚合計數與 GROUP BY 分組中各自的規則時"
aliases: ["/sql/knowledge-cards/null/"]
weight: 6
tags: ["sql", "null", "three-valued-logic", "knowledge-card"]
---

NULL（空值）表示欄位缺少值。它不同於數字 0 或空字串——後兩者皆為實際存在的值，NULL 代表值的缺席。NULL 來自兩個源頭：寫入資料時未填值，或 [Outer Join（外連接）](/backend/01-database/sql/knowledge-cards/outer-join/) 替未配對列補上的空欄位。

NULL 在比較、計數與分組三個操作中的行為與一般值不同，須分別確認。

## 跟其他概念的關係

- **比較（三值邏輯）**：拿 `NULL` 與任何值（包含另一個 `NULL`）以 `=`、`<>`、`>`、`<` 比較，結果既非真也非假，而是第三種真值「未知」。`WHERE` 只保留評估為真的列，未知與假皆會被濾除。檢查空值須使用回傳二元真假的 `IS NULL` 與 `IS NOT NULL`。
- **計數**：`count(*)` 計算總列數，`count(欄位)` 只計算該欄位非 `NULL` 的列數，兩者差額即空值列數。
- **分組**：`GROUP BY` 將所有鍵值為 `NULL` 的列歸併為同一組。經過外連接產出的 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/) 若直接以補空值的右表欄位分組，所有未配對列會被併成同一組。

## 可觀察訊號與例子

書店範例資料中只有佳穎有訂單；以 `LEFT JOIN` 連接顧客與訂單後，宗翰與雅文的訂單欄位為 `NULL`。以等號比對空值會靜默回傳零列，改用 `IS NULL` 才得到正確列：

```sql
WHERE 訂單.訂單編號 = NULL     -- 0 列，沒有錯誤訊息
WHERE 訂單.訂單編號 IS NULL    -- 宗翰、雅文
```

在分組上則相反：以 `訂單.顧客編號` 分組時，宗翰與雅文因鍵值皆為 `NULL` 而在 MySQL、SQLite 與 DuckDB 上一致被併為同一組。最隱蔽的失效形態出現在 `NOT IN`：只要子查詢回傳任何一個 `NULL`，外層整段查詢在各引擎都會靜默回傳零列（完整推導與 `NOT EXISTS` 邊界見 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)）。

## 判斷條件與後果

當子查詢讀取的欄位缺少 `NOT NULL` [Constraint（約束）](/backend/01-database/sql/knowledge-cards/constraint/) 時，否定成員判斷若寫成 `NOT IN`，未來只要寫入一筆空值就會靜默回傳零列；此外，若外層比對欄位本身允許為空，即使子查詢欄位具 `NOT NULL`，`NOT IN` 仍會濾除該空值列而 `NOT EXISTS` 會保留它。唯有外層比對欄位與子查詢欄位兩側皆已宣告 `NOT NULL` 約束，兩種寫法的結果才維持一致。

欄位是否允許 `NULL` 是建表時的設計取捨：允許為空貼合「資料缺席」的事實，但往後每段碰到該欄的查詢都須防範三值邏輯；禁止為空則簡化查詢，但須決定缺值時的表達方式（遷移成本與實測見 [1.16 Schema 設計決定的查詢代價：可空性、排序鍵唯一性、表寬、一對多的切法、比較規則、外鍵執法，以及從另一張表取值時的複製與引用](/backend/01-database/design-decisions-price-every-query/)）。

外連接後使用 `IS NULL` 辨別未配對列時，須挑選「配對成功時必定非空」的欄位（通常是右表主鍵或連接鍵）；若誤用原本就允許為空的右表欄位，會把「配對成功但該欄本來為空」的列一併選入。
