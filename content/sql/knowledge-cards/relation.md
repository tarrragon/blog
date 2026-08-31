---
title: "Relation（關係）"
date: 2026-08-31
description: "看到 SQL 教材說「組成一個關係」而不確定它指的是不是資料表時"
weight: 1
tags: ["sql", "relational-model", "knowledge-card"]
---

Relation 是一組欄位固定、由若干列構成的資料集合。SQL 裡的資料表是它的一種，而 [query plan](/sql/knowledge-cards/query-plan/) 裡每個運算子的輸入與輸出同樣是關係——`JOIN` 收兩個關係產出一個，`WHERE` 收一個產出一個，[outer join](/sql/knowledge-cards/outer-join/) 也是這組運算裡的一個。

中文的「關係」在日常語言裡指人或事物之間的聯繫，與這裡的意思無關。這個詞是 relation 的譯名，指的是那個集合本身。

## 概念位置

關係是 SQL 各種操作的共同單位，所以查詢可以層層套疊：一個 `JOIN` 的輸出可以當成下一個 `JOIN` 的輸入，子查詢的輸出可以當成外層的來源。這個性質讓 [query optimizer](/sql/knowledge-cards/query-optimizer/) 有重排的空間——只要輸出的關係一樣，中間怎麼組合都合法。

它與「資料表」的差別在於是否落地。資料表是存起來的關係，而查詢中途產生的關係只存在於計算過程裡，沒有名字也不寫進磁碟。

## 可觀察訊號與例子

`FROM a LEFT JOIN b` 走完之後手上的東西就是一個關係：欄位是 `a` 與 `b` 的欄位合起來，列數由配對結果決定。它沒有對應的資料表，而後續的 `WHERE` 與 `GROUP BY` 照樣對它操作。

## 設計責任

把中間結果當成關係來讀，可以讓多層查詢的判讀變成逐層檢查每一層的欄位與列。反過來，把每個 `JOIN` 都想成「兩張表配對」會在第三張表之後失準，因為那時左邊已經不是表。
