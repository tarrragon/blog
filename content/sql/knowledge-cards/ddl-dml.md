---
title: "DDL 與 DML（定義結構與動資料）"
date: 2026-09-01
description: "看到「這個帳號只需要 DML 權限」或遷移文件把兩者分開講時，查這條界線切在哪裡"
weight: 11
tags: ["sql", "ddl", "dml", "privilege", "migration", "knowledge-card"]
---

SQL 的語句按它改動的對象分成兩類。**DDL**（Data Definition Language）改的是結構——`CREATE`、`ALTER`、`DROP`，它動的是有哪些表、每張表有哪些欄位——也就是一個 [relation](/sql/knowledge-cards/relation/) 的欄位組成由什麼決定。**DML**（Data Manipulation Language）改的是結構裡裝的資料——`INSERT`、`UPDATE`、`DELETE`，表還是那張表，變的是裡面有哪些列。`SELECT` 只讀不改，各家文件有的把它算進 DML、有的另立一類。

## 這條線在權限上有實際後果

兩類的[授權](/sql/privilege-model/)是分開的，而它們在日常運行裡的頻率差很多：應用程式跑起來之後幾乎只做 DML，DDL 只在部署或遷移的時候用一次。這讓最小權限有一個明確的切法——常態運行的帳號不給 DDL，遷移用另一個帳號。

代價的形狀也不同。一句 DML 寫錯影響的是那些列，可以用另一句 DML 補回來；一句 DDL 寫錯（`DROP TABLE` 那一類）拿掉的是結構，補救要靠備份。

## 兩類的擋法不在同一層

DML 的權限掛在表上——`GRANT SELECT ON 顧客`。DDL 的權限多數掛在更上面一層：能不能建新表由 [schema](/sql/knowledge-cards/schema-namespace/) 那一層決定，不是由某一張表決定，因為建的時候那張表還不存在。

## 概念位置

這條線切的是語句改動的對象，而 SQL 的其餘概念多數只活在 DML 這一側——[relation](/sql/knowledge-cards/relation/)、[外連接](/sql/knowledge-cards/outer-join/)、分組、[子查詢](/sql/knowledge-cards/subquery/) 全部是在既有結構上取資料的方式。DDL 決定那個結構長什麼樣，它跑完之後才輪到那些概念。

兩類在時間上的分布因此完全不同：DDL 集中在部署那幾分鐘，DML 散在系統活著的每一秒。權限、備份策略與事故的補救方式都跟著這條線分。

## 往下走

授權的單位與最小權限的具體切法在 [1.10 權限的預設是什麼都不給](/sql/privilege-model/)。DDL 權限實際被用到的場合（雙寫、回填、切流、回滾）在 [資料庫轉換實作](/backend/01-database/database-migration-playbook/)。
