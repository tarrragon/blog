---
title: "DDL 與 DML（定義結構與動資料）"
date: 2026-09-01
description: "遇到帳號只需 DML 權限，或遷移規範將結構變更與資料操作分開管理時"
aliases: ["/sql/knowledge-cards/ddl-dml/"]
weight: 11
tags: ["sql", "ddl", "dml", "privilege", "migration", "knowledge-card"]
---

SQL 語句依修改對象分為兩大類：**DDL**（Data Definition Language，資料定義語言）修改資料庫結構，包含 `CREATE`、`ALTER`、`DROP`，決定存在哪些資料表、欄位與 [Constraint（約束）](/backend/01-database/sql/knowledge-cards/constraint/)；**DML**（Data Manipulation Language，資料操作語言）修改資料表內部的列內容，包含 `INSERT`、`UPDATE`、`DELETE`（列與欄的定義見 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/)）。唯讀的 `SELECT` 在部分文件中歸入 DML，另一些文件則單獨歸類為 DQL（Data Query Language）。

## 權限切分與誤操作代價

DDL 與 DML 的授權各自獨立（見 [SQL.16 SQL 的權限模型：角色、GRANT 的授權單位與最小權限](/backend/01-database/sql/privilege-model/)），且在系統生命週期中的執行頻率懸殊：常態運行的應用程式幾乎只執行 DML，DDL 只出現在部署或資料庫遷移期間。因此最小權限的標準作法是常態應用程式帳號不授予 DDL 權限，由獨立的遷移帳號負責結構變更。

兩類語句誤寫時的補救成本也不同：DML 誤改特定列時常可用反向 DML 或 [Transaction（交易）](/backend/knowledge-cards/transaction/)回滾補救；DDL 誤刪結構（例如 `DROP TABLE`）則須仰賴備份還原。

## 授權層級的差異

DML 權限授於資料表層級（例如 `GRANT SELECT ON 顧客`）；建立新資料表等 DDL 權限則多半授於更上層的 [Schema（命名空間義）](/backend/01-database/sql/knowledge-cards/schema-namespace/) 層級，因為建表當下目標資料表尚未存在。

## 跟其他概念的關係

DDL 先定義出資料表結構，後續在 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/) 上執行的 [Outer Join（外連接）](/backend/01-database/sql/knowledge-cards/outer-join/)、分組與 [Subquery（子查詢）](/backend/01-database/sql/knowledge-cards/subquery/) 全都運作在該結構之上的 DML 與查詢操作中。由於 DDL 集中在部署階段、DML 持續發生在日常請求中，帳號切分、備份策略與事故復原程序都依這條分界規劃。

## 延伸閱讀：權限模型與資料庫遷移

- 角色授權單位與最小權限實例：[SQL.16 SQL 的權限模型：角色、GRANT 的授權單位與最小權限](/backend/01-database/sql/privilege-model/)
- 運用 DDL 執行雙寫、回填、切流與回滾的流程：[1.6 資料庫轉換實作：雙寫、回填、切流與回滾](/backend/01-database/database-migration-playbook/)
