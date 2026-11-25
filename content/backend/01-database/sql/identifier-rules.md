---
title: "SQL.14 識別字的規則：各家的大小寫摺疊、引號與保留字"
date: 2026-08-31
description: "表名與欄名送進引擎後的改寫規則、PostgreSQL 與 SQLite、DuckDB 在引號與大小寫上的差別、MySQL 的反引號與 ANSI_QUOTES，以及全部不加引號、全部加引號與混用在更換引擎時的後果"
aliases: ["/sql/identifier-rules/"]
weight: 15
tags: ["sql", "identifier", "naming", "postgresql", "portability"]
---

SQL 表名與欄名送進資料庫引擎前會先經過名稱改寫，各家引擎的大小寫摺疊與引號規則並不相同。本篇示範 PostgreSQL 未加引號的小寫摺疊與加引號的逐字比對，並對照 SQLite、DuckDB 的不區分大小寫行為與遷移失效時機；接著整理保留字衝突、各家引號語法（含 MySQL 反引號與 `ANSI_QUOTES`）與中文識別字表現，文末比較全部不加引號、全部加引號與混用三種做法的取捨。

本篇處理的是名稱送進引擎後的解析行為，不討論資料表與欄位的命名設計慣例——表、欄、外鍵、布林、時間戳與索引的命名規範及反模式見 [1.2 Schema Design 與資料建模](/backend/01-database/schema-design/#naming-與一致性)。識別字規則是查詢文字之外影響結果的項目之一；其餘外部因素各有專篇：授權單位與最小權限見 [SQL.16 SQL 的權限模型：角色、GRANT 的授權單位與最小權限](/backend/01-database/sql/privilege-model/)，執行順序與最佳化器規劃見 [SQL.1 宣告式的紅利與代價：書寫、求值與執行順序各自由誰決定](/backend/01-database/sql/declarative-not-procedural/)，寫入端外鍵與參照完整性見 [SQL.18 外鍵與參照完整性：宣告、生效與查詢得到的保證](/backend/01-database/sql/foreign-key-and-referential-integrity/)，字串值相等與排序比較見 [SQL.15 字串比較與 collation：相等、排序、LIKE 與索引可用性](/backend/01-database/sql/string-comparison-and-collation/)，跨引擎寬鬆度分級見 [SQL.19 引擎寬鬆度與可攜性：各家對同一組寫法的差異、分級與處理時機](/backend/01-database/sql/engine-leniency-and-portability/)，單寫入者與多連線伺服器的並行差異見 [SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異](/backend/01-database/sql/deployment-shape-and-sql-constructs/)。

當表名與欄名寫進查詢並送進引擎時，引擎會先依自身規則改寫識別字，再拿改寫後的名稱去系統目錄（資料庫內建用來記錄表、欄、約束與權限定義的系統表）比對物件。由於各家改寫規則不同，同一段建表與查詢語句在原本的引擎上正常運作，遷移到另一家引擎時可能指向不同物件或直接查無此表。

## PostgreSQL 的大小寫摺疊與引號

在 PostgreSQL 上建立一張表名加了雙引號且大小寫混合的資料表，再以未加引號的名稱查詢：

```sql
CREATE TABLE "Orders" ("OrderId" INT);
SELECT * FROM Orders;
-- ERROR: relation "orders" does not exist
```

錯誤訊息呈現了引擎內部的改寫：查詢寫的是 `Orders`，引擎實際查找的是 `orders`。PostgreSQL 會把所有未加雙引號的識別字摺疊為小寫，再進行比對。

這條規則同樣作用於建表階段。建表時未加引號，存入系統目錄的即是摺疊成小寫後的名稱：

```sql
CREATE TABLE MixedCase (x INT);
-- 實際存進系統目錄的表名是 mixedcase
```

建表與查詢兩側若都未加引號，兩邊經過同一道小寫摺疊，名稱就能對應；若建表加了引號而查詢未加，兩邊便對不上：

```sql
-- PostgreSQL，兩組各在一個空的資料庫上跑
CREATE TABLE MixedCase (x INT);     -- 存成 mixedcase
SELECT * FROM mixedcase;            -- 找得到

CREATE TABLE "MixedCase" (x INT);   -- 加了引號，存成 MixedCase
SELECT * FROM MixedCase;            -- 摺成 mixedcase 去找
-- ERROR: relation "mixedcase" does not exist
```

在 PostgreSQL 中，替識別字加上雙引號的作用是關閉小寫摺疊，改採逐字比對。

這道摺疊規則只作用於物件名稱，不作用於資料值。即使 PostgreSQL 將未加引號的 `Orders` 摺成 `orders`，比對字串值 `'Anna'` 與 `'anna'` 時採用的是獨立的 collation 規則，預設判定兩者不相等。字串值的比較規則見 [SQL.15 字串比較與 collation：相等、排序、LIKE 與索引可用性](/backend/01-database/sql/string-comparison-and-collation/)。

## SQLite 與 DuckDB 對識別字大小寫的處理

將同一張 `"Orders"` 資料表移至 SQLite 與 DuckDB 執行，無論查詢是否加引號或大小寫是否一致，四種寫法全數找得到資料表：

```sql
CREATE TABLE "Orders" ("OrderId" INT);

SELECT * FROM orders;     -- 不加引號、查小寫
SELECT * FROM Orders;     -- 不加引號、照原樣
SELECT * FROM "Orders";   -- 加引號、大小寫一致
SELECT * FROM "orders";   -- 加引號、大小寫不一致
-- SQLite、DuckDB：四句都找得到
-- PostgreSQL：只有加引號、大小寫一致的那一句找得到，其餘三句都回 relation "orders" does not exist
```

SQLite 與 DuckDB 對識別字大小寫不敏感，即使加上雙引號也不會開啟大小寫區分。

這種差異會造成延遲浮現的可攜性故障：開發階段在 SQLite 上混用大小寫與引號時所有測試都通過，直到部署或遷移至 PostgreSQL，所有「建表加引號但查詢未加」或大小寫不一致的位置才全面報錯找不到資料表。

## 保留字與各家的引號寫法

`select`、`order`、`group` 等關鍵字屬於 SQL 語法結構，直接作為未加引號的表名會在剖析階段失敗：

```sql
CREATE TABLE select (x INT);
-- SQLite:    near "select": syntax error
-- DuckDB:    Parser Error: syntax error at or near "select"
-- PostgreSQL: syntax error at or near "select"
```

加上引號可以向剖析器標明該字串是識別字而非關鍵字，但各家採用的引號字元並不一致：

```sql
CREATE TABLE "select" (x INT);
-- SQLite、DuckDB、PostgreSQL：接受
-- MySQL：ERROR 1064 語法錯誤，它預設把雙引號當成字串

CREATE TABLE `select` (x INT);   -- MySQL 的識別字要用反引號

SET SESSION sql_mode = CONCAT(@@sql_mode, ',ANSI_QUOTES');
CREATE TABLE "order" (x INT);    -- 開了 ANSI_QUOTES 之後，MySQL 的雙引號才代表識別字
```

同一份 DDL 若需同時支援 MySQL 與其他引擎，必須依引擎調整引號或直接避開保留字。

各家引擎的保留字清單並不完全重疊，新大版本也可能新增保留字，使原本合法的未加引號名稱在升級後變成語法錯誤。這也是部分工具與團隊選擇「所有識別字一律加引號」的主要原因，代價則是查詢文字變長，且日後每個名稱的大小寫皆須逐字一致。

## 中文識別字在各家引擎上的處理

`CREATE TABLE 顧客 (姓名 TEXT)` 與 `SELECT 姓名 FROM 顧客` 在 SQLite、DuckDB 與 PostgreSQL 上皆可直接執行，不需加引號。中文字元沒有大小寫之分，大小寫摺疊規則對其不產生影響。

## 引號的做法：全部不加、全部加與混用

處理識別字引號有兩種一致的策略，以及容易失效的混用狀態。

**全部不加引號，識別字一律採用小寫加底線（snake_case）。** 這是 PostgreSQL 生態的主流作法：小寫摺疊不會改變任何字元，跨引擎遷移時也不會因大小寫失配報錯；限制是遇到保留字時仍須改名或單獨加引號。

**全部加引號。** 名稱逐字保存且可避開保留字衝突；代價是每個識別字都須帶引號、大小寫必須逐字一致，且在 SQLite 或 DuckDB 等不區分大小寫的引擎上，大小寫寫錯不會被驗證出來，要等到遷移至區分大小寫的引擎才暴露。

**混用加引號與不加引號、同時使用混合大小寫**，在單一不敏感引擎上看似正常，遷移至嚴格執行摺疊規則的引擎時會成批失效。選擇全部不加或全部加皆有清楚的行為邊界，混用則會埋下跨引擎斷點。
