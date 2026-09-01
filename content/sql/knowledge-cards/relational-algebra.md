---
title: "Relational Algebra（關聯代數）"
date: 2026-09-01
description: "看到「子句其實是某個運算」或想知道 SQL 的規則從哪裡來時，查這一層在底下的是什麼"
weight: 13
tags: ["sql", "relational-algebra", "relation", "knowledge-card"]
---

關聯代數是一組作用在 [relation](/sql/knowledge-cards/relation/) 上、產出 relation 的運算：挑列（選取）、挑欄（投影）、把兩份配起來（連接）、以及聯集、差集、更名。SQL 的子句是這些運算的一層語法外衣，而不是另一套獨立的規則。

## 封閉性是它最重要的性質

每個運算的輸入是關係、輸出還是關係，所以運算可以一個接一個組下去，中間結果與來源表的地位相同。這一條買到兩件事：子查詢可以寫在任何接受關係的位置，而多層查詢的判讀方式是逐層看每一層的欄與列。

它也解釋了為什麼[外連接](/sql/knowledge-cards/outer-join/)的產物可以繼續當下一個連接的輸入——那份補了 NULL 的東西仍然是一個關係。

## SQL 與它並非一對一

SQL 在代數之上多了幾樣代數本身沒有的：重複的列（代數的關係是集合，SQL 的表允許重複，所以才需要 `DISTINCT`）、[NULL](/sql/knowledge-cards/null/) 與三值邏輯、以及排序。這幾樣正好是最容易讀錯的幾處，理由是它們不受代數的規則保護。

## 概念位置

本分類第一支各篇的判斷標準都折算回這一層：子句的先後、連接的左右、條件擺哪一邊、分組的鍵，每一項都是某個運算的組合規則，而不是設計者的偏好。知道規則從代數來，讀不熟的查詢時就有一個可以推的依據，不必靠記憶。

同一套代數換一個介面就是 [DataFrame](/sql/knowledge-cards/dataframe/)，那也是這兩者多數操作對得上的原因。

## 往下走

連接產出的新關係怎麼改變列數與空缺，在 [1.5 連接產出的是新的關係](/sql/join-changes-rows-and-nulls/)。同一組操作在 SQL 與 DataFrame 兩個介面上的對應、以及對應斷掉的三個位置，在 [python 模組八 8.4](/python/08-data-analysis/same-relational-algebra/)。
