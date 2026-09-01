---
title: "Subquery（子查詢）"
date: 2026-08-31
description: "看到括號裡還有一個 SELECT、想知道它什麼時候算、算幾次時"
weight: 8
tags: ["sql", "subquery", "correlated", "knowledge-card"]
---

Subquery 是寫在另一個查詢裡面的查詢。它分兩種，而分法只看一件事：**它有沒有引用外層的欄位。** 這個差別決定它算幾次，也決定了它的代價——完整的量測在 [query plan](/sql/knowledge-cards/query-plan/) 那一層。

## 概念位置

**獨立子查詢**與外層無關，可以整段剪下來單獨執行。它算一次，把結果交給外層。`WHERE 顧客編號 IN (SELECT 顧客編號 FROM 訂單)` 裡的括號就是這一種——訂單表那一份清單先算好，外層再拿它比對。

**相關子查詢**引用了外層的欄位，離開外層就跑不動。它對外層的每一列各執行一次。`WHERE EXISTS (SELECT 1 FROM 訂單 WHERE 訂單.顧客編號 = 顧客.顧客編號)` 是這一種——括號裡的 `顧客.顧客編號` 來自外層，所以每一位顧客各問一次。

讀陌生查詢時這是一個可以直接看的訊號：**括號裡出現外層的表名，它就是逐列被問一次的**。兩種子查詢交出的都是值而不是一個 [relation](/sql/knowledge-cards/relation/)，這一點決定了下一節那個錯誤訊息。

## 可觀察訊號與例子

子查詢交出的是值，不是表。`SELECT 姓名, 訂單.金額 FROM 顧客 WHERE 顧客編號 IN (SELECT ... FROM 訂單)` 會回 `no such column: 訂單.金額`——訂單這張表沒有進到外層的 `FROM` 裡。

要帶欄位出來有另一條路：把相關子查詢寫在 `SELECT` 裡，`SELECT 姓名, (SELECT 金額 FROM 訂單 WHERE 訂單.顧客編號 = 顧客.顧客編號 ORDER BY 訂單編號 LIMIT 1) FROM 顧客`。它一次只交得出一個值，所以要多欄或多列時仍然回到連接。

## 設計責任

相關子查詢的逐列執行在沒有索引時代價很高——外層每一列都讓內層掃一次全表。有索引之後每一次從掃全表變成定位，同一段查詢可以差幾百倍。

獨立子查詢有另一個陷阱：它的結果裡出現任何一個 NULL，外層的 `NOT IN` 就整段失效而不報錯。推導與實測在 [1.6](/sql/join-changes-rows-and-nulls/)。
