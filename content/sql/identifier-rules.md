---
title: "1.9 識別字送進引擎之後會被改寫"
date: 2026-08-31
description: "各家對大小寫的摺疊規則、引號的作用與保留字，以及兩種一致做法之間的中間地帶"
weight: 9
tags: ["sql", "identifier", "naming", "postgresql", "portability"]
---

表名與欄名寫進查詢之後，引擎會先按自己的規則處理一次，才拿去對照真正存在的名字。這道改寫各家不同，所以同一段 SQL 在不同引擎上指向的可能是不同的名字——或者什麼都指不到。

這與命名慣例是兩件事。取什麼名字是設計問題（見下方路由），這裡談的是取好的名字送進引擎會發生什麼。改寫的後果在單一引擎上看不見，換一個引擎才浮現：一段建表語句在原本那個引擎上建好了表，同樣的名字搬到另一個引擎去查卻找不到——名字在送進引擎的路上會先被改寫一次，而兩個引擎改寫的規則不一樣。

## PostgreSQL 把沒加引號的名字摺成小寫

在 PostgreSQL 上建一張大小寫混合的表，名字加了引號：

```sql
CREATE TABLE "Orders" ("OrderId" INT);
SELECT * FROM Orders;
-- ERROR: relation "orders" does not exist
```

錯誤訊息把發生的事直接印出來了：查詢裡寫的是 `Orders`，而引擎去找的是 `orders`。沒加引號的識別字一律被摺成小寫，之後才拿去比對。

反過來也成立。建表時不加引號，存進去的就是摺過的版本：

```sql
CREATE TABLE MixedCase (x INT);
-- 實際存進系統目錄的表名是 mixedcase
```

所以 `CREATE TABLE MixedCase` 與 `SELECT * FROM mixedcase` 互相對得上，而 `CREATE TABLE "MixedCase"` 與 `SELECT * FROM MixedCase` 對不上。**加引號的效果是關掉這道摺疊，要求逐字比對。**

## SQLite 與 DuckDB 完全不區分大小寫

同一組測試搬到 SQLite 與 DuckDB，四種寫法全部成功：不加引號查小寫、不加引號照原樣、加引號一致、加引號不一致——`SELECT * FROM orders`、`FROM Orders`、`FROM "Orders"`、`FROM "orders"` 都找得到那張表。

這兩個引擎對識別字的大小寫不敏感，連引號都不會讓它變敏感。

這造成一個很難發現的可攜性問題：在 SQLite 上開發、程式碼裡大小寫混著寫，一路都正常；搬到 PostgreSQL 之後，凡是建表時加了引號而查詢時沒加的地方全部找不到表。錯誤出現的時機離寫下它的時機很遠。

## 保留字要加引號，這一項各家一致

`select`、`order`、`group` 這些是語法的一部分，直接拿來當表名會在剖析階段就失敗：

```sql
CREATE TABLE select (x INT);
-- SQLite:    near "select": syntax error
-- DuckDB:    Parser Error: syntax error at or near "select"
-- PostgreSQL: syntax error at or near "select"
```

加上引號之後三者都接受，因為引號告訴剖析器這是一個名字而不是關鍵字。

保留字清單各家不完全相同，而且會隨版本增加——今天合法的名字在下個大版本可能變成保留字。這是「所有識別字一律加引號」這個慣例的主要理由。採用這個慣例的代價是每個名字都變長，而且從此大小寫必須逐字一致。

## 中文識別字三家都收

`CREATE TABLE 顧客 (姓名 TEXT)` 與 `SELECT 姓名 FROM 顧客` 在 SQLite、DuckDB 與 PostgreSQL 上都不用加引號就能跑。摺疊規則對中文沒有作用，因為那些字沒有大小寫。

## 兩種一致的做法，中間地帶最危險

**全部不加引號、名字一律用小寫加底線。** 這是 PostgreSQL 生態的主流，摺疊不會改變任何東西，換引擎也不受影響。代價是撞到保留字時仍然要加引號。

**全部加引號。** 名字逐字保存，保留字不成問題。代價是每個名字都要引號、大小寫從此一字不能錯，而且在不區分大小寫的引擎上這個約束不會被驗證出來。

中間地帶——有些地方加、有些地方不加、名字又是大小寫混合的——在單一引擎上可能一直正常，換引擎時整批失效。**選哪一種都行，混用不行。**

## 換掉其中一項會變成什麼

本篇的可動項是：加不加引號、送進哪一家引擎，以及名字本身取什麼。

**把「名字怎麼被處理」換成「名字該怎麼取」**：本篇談的是取好之後送進引擎會發生什麼，取名本身是設計問題。[Schema Design 的「Naming 與一致性」段](/backend/01-database/schema-design/#naming-與一致性)給表、欄、外鍵、布林、時間戳、索引各自的慣例，以及縮寫不一致、隱性意義這幾種反模式。

**把「名字指到誰」換成「誰被允許動它」**：同一張表，一個問它叫什麼、一個問誰能讀寫。[1.10 權限的預設是什麼都不給](/sql/privilege-model/) 寫角色與 `GRANT` 的模型，以及新建的角色在拿到授權之前連讀都讀不了。

**把識別字規則放回四方並置的位置**：查詢的文字不足以決定結果，識別字規則是補上差額的其中一方。[模組頁的推導源頭](/sql/)那一段列出四方，而最佳化器那一方的完整推導在 [1.1](/sql/declarative-not-procedural/)。
