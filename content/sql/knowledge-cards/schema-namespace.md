---
title: "Schema（命名空間義）"
date: 2026-08-31
description: "看到 permission denied for schema、或想確認這個字指的是表結構還是命名空間時"
weight: 9
tags: ["sql", "schema", "namespace", "postgresql", "knowledge-card"]
---

在 PostgreSQL 這類資料庫裡，schema 是資料庫底下的一層命名空間，表、索引、序列這些物件都住在某一個 schema 裡。預設的那一個叫 `public`。它與[權限](/sql/privilege-model/)是分層的：對表的授權管的是讀寫那張表，對 schema 的授權管的是能不能在裡面建立新物件——而表是一種 [relation](/sql/knowledge-cards/relation/)。

**這個字有另一個常見的所指——「表結構」，也就是有哪些表、每張表有哪些欄位、型別與約束是什麼。** 兩者不同層：命名空間是容器，表結構是被裝的東西。談 schema migration 的時候用的是後者，談 `permission denied for schema public` 的時候用的是前者。

## 概念位置

分層在錯誤訊息上看得出來。一個角色被拒絕讀某張表，訊息是 `permission denied for table 顧客`；同一個角色被拒絕建新表，訊息是 `permission denied for schema public`——擋的位置不同，要授的權也不同。被擋住的那些物件裡最常見的是表，而表是一種 [relation](/sql/knowledge-cards/relation/)。

PostgreSQL 15 之後 `public` schema 預設不再開放給所有人建立物件，在那之前這個操作會成功。同一段 SQL 在不同版本上的結果因此不同，而差別在預設值不在語法。

## 可觀察訊號與例子

`information_schema` 本身就是一個 schema，裡面裝著描述其他物件的視圖。查自己有哪些授權用的 `information_schema.role_table_grants` 就是「schema 名.表名」這個兩段式的寫法。

不是每個資料庫都有這一層。SQLite 沒有 schema 也沒有使用者，整個資料庫是一個檔案，存取由檔案系統決定。

## 設計責任

看到這個字先判它在哪一層。判斷方法是看它旁邊的動詞：跟「建立物件」「授權」「限定名稱」一起出現的是命名空間；跟「欄位」「型別」「遷移」「版本」一起出現的是表結構。

兩者在部署上也分工：命名空間常用來把不同租戶或不同應用的物件隔開，而表結構的演進是另一組問題——雙寫、回填、切流與回滾，那些在 [backend 模組一的資料庫轉換實作](/backend/01-database/database-migration-playbook/)。
