---
title: "Schema（命名空間義）"
date: 2026-08-31
description: "遇到 permission denied for schema，或需區分 schema 指表結構還是命名空間時"
aliases: ["/sql/knowledge-cards/schema-namespace/"]
weight: 9
tags: ["sql", "schema", "namespace", "postgresql", "knowledge-card"]
---

在 PostgreSQL 這類資料庫裡，schema 是資料庫底下的一層命名空間，資料表、索引與序列等物件都歸屬於某個 schema，預設命名空間為 `public`。它與 [SQL.16 SQL 的權限模型：角色、GRANT 的授權單位與最小權限](/backend/01-database/sql/privilege-model/) 採分層控制：對表的授權控制讀寫該表的權限，對 schema 的授權則控制能否在該命名空間內建立新物件——而資料表本身是一種 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/)。

**Schema 在工程討論中另有一個常見含義，指「資料表結構」**，即資料庫有哪些表、每張表有哪些欄位、型別與 [Constraint（約束）](/backend/01-database/sql/knowledge-cards/constraint/)。兩者屬於不同層次：命名空間是容納物件的容器，表結構則是物件本身的設計規格。討論 schema migration 時指表結構，遇到 `permission denied for schema public` 時則指命名空間。

## 跟其他概念的關係

授權的分層直接反映在錯誤訊息上。角色被拒絕讀取某張表時，引擎回傳 `permission denied for table 顧客`；同一個角色被拒絕在該命名空間建表時，引擎回傳 `permission denied for schema public`。攔截層級不同，需要授予的權限對象也不同。最常被放在 schema 內的物件是資料表，也就是一種 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/)。

PostgreSQL 15 起，`public` schema 預設不再開放所有使用者建立物件，在 15 以前則預設允許。同一段建表 SQL 在不同主版本上產生不同結果，差異來自預設權限而非語法變動。

## 可觀察訊號與例子

`information_schema` 本身就是一個內建 schema，內部存放描述各類資料庫物件的系統檢視表。查詢自身表權限時使用的 `information_schema.role_table_grants`，即採用「schema 名稱.表名稱」的兩段式限定寫法。

並非所有 [Database Engine（資料庫引擎）](/backend/01-database/sql/knowledge-cards/database-engine/) 都實作 schema 層。SQLite 沒有 schema 也沒有使用者帳戶，整個資料庫對應單一檔案，存取控制由作業系統的檔案權限負責。

## 判斷條件與後果

判斷文件或錯誤訊息裡的 `schema` 所指層級，依據是它搭配的動詞：與「建立物件」「授權」「限定名稱」並用時指命名空間；與「欄位」「型別」「遷移」「版本」並用時指表結構。

兩者在系統部署上也各自承擔不同職責：命名空間常用於隔離不同租戶或應用的物件，表結構演進則涉及雙寫、回填、切流與回滾等零停機切換流程，詳見 [1.6 資料庫轉換實作：雙寫、回填、切流與回滾](/backend/01-database/database-migration-playbook/)。
