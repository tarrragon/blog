---
title: "Outer Join（外連接）"
date: 2026-08-31
description: "需要確認 LEFT、RIGHT 與 FULL 各自的保護方向，或連接後部分資料列從結果消失時"
aliases: ["/sql/knowledge-cards/outer-join/"]
weight: 4
tags: ["sql", "join", "outer-join", "knowledge-card"]
---

內連接（`INNER JOIN` 或簡寫 `JOIN`）合併兩張資料表時會直接捨棄配對不到對象的列；outer join（外連接）則保留這些未配對列，並在對側欄位補上 `NULL`，讓它們得以留在產出的 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/) 之中。

在書店範例資料中，佳穎有兩張訂單，宗翰與雅文沒有訂單。使用內連接查詢顧客與訂單時只回傳佳穎兩列；改用 `LEFT JOIN` 則保留全部三位顧客：

```text
佳穎  101
佳穎  102
宗翰  NULL
雅文  NULL
```

這種保留左側未配對列並在右側補 `NULL` 的行為稱為**保護**。需求為「找出沒有下過訂單的顧客」時，答案全屬於補 `NULL` 的列，內連接無法取得這些列。外連接依保護方向分為三種：`LEFT` 保護左運算元，`RIGHT` 保護右運算元，`FULL` 同時保護兩側。

## 跟其他概念的關係

外連接產出的結果仍是一份 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/)，可直接作為下一個連接的輸入。當查詢的 `WHERE` 條件已保證補 `NULL` 列不可能通過篩選時，[Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/) 會自動將外連接簡化為內連接執行。

外連接補上的 [NULL（空值）](/backend/01-database/sql/knowledge-cards/null/) 來自配對失敗，與來源表原本就缺填的空值不同。後續以 `IS NULL` 篩選未配對列時，必須選用右表不可為空的欄位（通常是主鍵或連接鍵），避免把「配對成功但該欄原本為空」的列混淆進來。

## 可觀察訊號與例子

外連接的保護會被 `WHERE` 裡引用右表欄位的條件抵銷。在書店的顧客與訂單 `LEFT JOIN` 加上 `WHERE 訂單.金額 > 100` 後，宗翰與雅文的金額欄為 `NULL`，評估 `NULL > 100` 得到未知而被濾除，結果退化為與內連接相同。

判斷某個 `WHERE` 條件是否保留外連接保護，只需把「右表欄位全為 `NULL` 的列」代入條件：評估為真則保護留存，為假或未知則保護取消。因此 `IS NULL` 保留保護，`IS NOT NULL` 取消保護。

## 判斷條件與後果

在保留被保護表全部列的前提下限定對側配對範圍，條件寫進 `ON`；要對連接完成後的整批結果做過濾（包含以 `IS NULL` 找出未配對列），條件寫進 `WHERE`。內連接不保護未配對列，兩種位置結果相同，差異只在執行外連接時顯現。

在多張表串接的鏈式查詢裡混用 `LEFT` 與 `RIGHT` 會中途反轉保護方向：鏈尾 `RIGHT JOIN` 只保護最右側單一資料表，把前方整段累積的列全數降級為非保護側。將需要完整保留的主表置於 `FROM` 最上方並往下統一串接 `LEFT JOIN`，才能在整條連接鏈上維持單一且可追蹤的保護方向。
