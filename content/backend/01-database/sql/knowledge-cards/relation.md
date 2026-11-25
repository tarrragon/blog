---
title: "Relation（關係）"
date: 2026-08-31
description: "看到 SQL 教材寫「組成一個關係」時，確認它的定義與資料表、中間結果的差別"
aliases: ["/sql/knowledge-cards/relation/"]
weight: 1
tags: ["sql", "relation", "knowledge-card"]
---

Relation（關係）是一組欄位固定、由若干列構成的資料集合。本系列採用台灣慣用語：**列**（row）指橫向的一筆資料，**欄**（column）指縱向的一個欄位位置；簡體中文的 SQL 資料慣用「行」稱呼列、用「列」稱呼欄，兩套名詞剛好對調。資料庫裡的表是關係的一種，查詢過程中產生的中間結果同樣是關係——例如 [Outer Join（外連接）](/backend/01-database/sql/knowledge-cards/outer-join/) 產出的結果集合，便比來源表多了補上 `NULL` 的列。

中文的「關係」在日常語境常指事物之間的聯繫，與關聯式模型的意義不同。在 SQL 領域裡，它是英文 relation 的譯名，特指這種由欄與列構成的集合本身。

## 跟其他概念的關係

**把中間結果也視為關係，才能逐層拆解多層查詢。** 以書店資料庫的 `FROM 顧客 LEFT JOIN 訂單` 為例，連接完成後會產生一份具備姓名與訂單編號兩個欄位、共 4 列的中間集合（佳穎 2 列，宗翰與雅文各 1 列且訂單編號為 `NULL`）。這份中間結果沒有實體資料表對應，也沒有名稱，更不會寫入磁碟，但後續的 `WHERE` 與 `GROUP BY` 全部作用在這份中間結果上，而非原本那兩張來源表。

這項封閉性質讓查詢得以層層巢狀組合：前一個連接的輸出可直接作為下一個連接的輸入，[Subquery（子查詢）](/backend/01-database/sql/knowledge-cards/subquery/) 的輸出也能作為外層查詢的資料來源。正因每層的輸入與輸出結構一致，[Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/) 才有重排運算步驟的空間——只要最終產出的關係相同，中間的組合方式皆屬合法。

[Outer Join（外連接）](/backend/01-database/sql/knowledge-cards/outer-join/) 屬於 [Relational Algebra（關聯代數）](/backend/01-database/sql/knowledge-cards/relational-algebra/) 延伸運算之一，其產出的關係比來源表多了未配對時補 `NULL` 的列。

## 可觀察訊號與例子

判斷目前處理的集合是否仍等同於原始資料表，可直接檢視列數、欄位與 [NULL（空值）](/backend/01-database/sql/knowledge-cards/null/) 狀態。經過連接後，列數可能因一對多配對而增加，欄位由兩張表合併而成，也可能出現來源表原本沒有的 `NULL`。只要上述任一項成立，目前操作的對象便已不再是原表。

## 判斷條件與後果

閱讀多層查詢時，逐層核對每一步產出的欄位與列數才能確認當前操作對象；將每個 `JOIN` 簡化理解為「兩張表配對」，到了第三張表就會失準，因為此時連接的左運算元已是前兩層累積而成的新關係。
