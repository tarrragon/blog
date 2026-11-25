---
title: "SQL.16 SQL 的權限模型：角色、GRANT 的授權單位與最小權限"
date: 2026-08-31
description: "PostgreSQL 新角色的預設權限、讀寫操作各自授權與收回的方式、建立物件所需的 schema 層權限，以及應用程式帳號套用最小權限的前提與邊界"
aliases: ["/sql/privilege-model/"]
weight: 17
tags: ["sql", "privilege", "grant", "role", "least-privilege", "postgresql"]
---

這篇以 PostgreSQL 18 說明 SQL 的權限模型與最小權限原則：先示範新建角色的預設權限與 `LOGIN` 屬性的分工；說明 `GRANT` 與 `REVOKE` 以角色、資料表與動作為單位的授權與收回方式；區分資料表存取權與在 schema 層建立物件的權限；最後說明應用程式依用途分帳號並套用最小權限的效益與成立前提。

`GRANT` 與 `REVOKE` 是 SQL 標準定義的授權語句，用來宣告哪些角色被允許對哪些物件執行哪些操作。SQL 權限模型的預設狀態是全面拒絕（deny by default），所有權限都必須逐項顯式授予，而非先開放再收回。在這個模型下，一個帳號能執行的操作完全等於它被授予的權限集合。

以下實測輸出皆取自 PostgreSQL 18。SQLite 是嵌在應用程式行程內的函式庫，沒有伺服器行程驗證連線身分，存取控制由作業系統的檔案權限負責，因此本篇討論的 SQL 層級角色與 `GRANT` 授權在 SQLite 中不存在。部署形態造成的完整構造差異見 [SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異](/backend/01-database/sql/deployment-shape-and-sql-constructs/)。

## 新建角色的預設權限

在 [SQL 各篇共用的範例資料庫：一家小書店的顧客、訂單與評價表](/backend/01-database/sql/sample-bookstore-database/) 上新增一個專供報表查詢的角色。PostgreSQL 以「角色（role）」同時涵蓋使用者與群組：具 `LOGIN` 屬性的角色可以建立連線，不具該屬性的角色作為群組使用，兩者套用相同的授權機制。先建立一個可登入但尚未授權任何權限的角色：

```sql
CREATE ROLE 報表 LOGIN PASSWORD '...';
SET ROLE 報表;
SELECT * FROM 顧客;
-- ERROR: permission denied for table 顧客
```

該角色可以成功登入資料庫，但對任何資料表皆無讀取權限。在這個模型裡，連線資格由 `LOGIN` 屬性控制，資料存取能力由 `GRANT` 授權控制，兩者各自獨立。

由資料表擁有者授予 `SELECT` 權限後，報表角色才能讀取顧客表：

```sql
RESET ROLE;                     -- 切回表的擁有者；以報表的身分執行這條 GRANT 會回 permission denied
GRANT SELECT ON 顧客 TO 報表;
SET ROLE 報表;
SELECT 姓名 FROM 顧客;
-- 佳穎、宗翰、雅文
```

## 授權的單位：角色、表與動作

剛建立的報表角色只被授予了顧客表的 `SELECT` 權限。同一角色執行寫入或刪除時，引擎會直接拒絕：

```sql
INSERT INTO 顧客 VALUES (4,'柏宇');   -- permission denied for table 顧客
DELETE FROM 顧客 WHERE 顧客編號=1;    -- permission denied for table 顧客
```

兩條語句回傳的錯誤訊息與完全未授權時一致。SQL 的授權單位由三個元素組成：目標角色、目標物件（資料表）與具體動作。`SELECT`、`INSERT`、`UPDATE` 與 `DELETE` 各自獨立，授予讀取不會連帶開放寫入。授權語句裡的資料表名稱同樣受識別字規則約束，例如在 PostgreSQL 中 `GRANT SELECT ON Orders` 實際授權的對象是小寫的 `orders`（見 [SQL.14 識別字的規則：各家的大小寫摺疊、引號與保留字](/backend/01-database/sql/identifier-rules/)）。

現有授權紀錄可從系統目錄（資料庫內建用來記錄表、欄、[Constraint（約束）](/backend/01-database/sql/knowledge-cards/constraint/) 與權限定義的系統表）查詢，執行 `REVOKE` 收回後該角色即恢復 `permission denied`：

```sql
RESET ROLE;                     -- 查詢與收回都由表的擁有者執行
SELECT grantee, privilege_type FROM information_schema.role_table_grants
WHERE table_name = '顧客';
-- 表的擁有者：INSERT、SELECT、UPDATE、DELETE、TRUNCATE、REFERENCES、TRIGGER 各一列
-- 報表 | SELECT

REVOKE SELECT ON 顧客 FROM 報表;
SET ROLE 報表;
SELECT * FROM 顧客;
-- ERROR: permission denied for table 顧客
```

## 建立物件的權限與 schema

對既有資料表的 `SELECT` 授權與建立新資料表的權限分屬不同層級。報表角色嘗試建表時會遭到拒絕：

```sql
CREATE TABLE 偷建的 (x INT);
-- ERROR: permission denied for schema public
```

這次拒絕發生在 [Schema（命名空間義）](/backend/01-database/sql/knowledge-cards/schema-namespace/) 層級而非資料表層級。自 PostgreSQL 15 起，`public` schema 預設不再對一般角色開放 `CREATE` 權限（15 版之前預設允許）。同一段 SQL 在不同版本得到相反結果，差別來自版本預設權限而非語法變化。

## 最小權限：應用程式帳號的授權範圍

依最小權限原則，應用程式連線帳號只需授予實際業務操作所需的權限：純報表程式不執行寫入，不需授予 `INSERT`；訂單處理程式不刪除顧客資料，不需授予顧客表的 `DELETE`。僅有資料庫遷移需要執行 [DDL 與 DML（定義結構與動資料）](/backend/01-database/sql/knowledge-cards/ddl-dml/) 中的 DDL，且遷移屬於獨立部署作業，其權限應保留給專用的遷移帳號，不配發給常態運行的應用程式連線（遷移流程見 [1.6 資料庫轉換實作：雙寫、回填、切流與回滾](/backend/01-database/database-migration-playbook/)）。

依用途拆分帳號並縮減權限，效益會在資安事故發生時顯現。當應用程式出現 SQL 注入漏洞（攻擊者將惡意片段混入 SQL 執行）時，若連線帳號具備超級使用者權限，攻擊者可讀取跨應用資料或刪除整張表；若連線帳號僅具備特定資料表的 `SELECT` 權限，漏洞的影響範圍便被鎖定在這些表的讀取權內。這項防護的前提是不同用途各自使用獨立的資料庫帳號；若所有功能共用同一個高權限帳號、改由應用層自行控管授權，資料庫層級的最小權限無法形成邊界，防護責任須由應用層承擔。授權只是資料層防禦的其中一環，完整的注入、授權繞過、資料外洩、競態與資源耗盡分析見 [1.5 攻擊者視角（紅隊）：資料層弱點判讀](/backend/01-database/red-team-data-layer/)。

由於資料庫授權可直接透過 `information_schema.role_table_grants` 等系統目錄查證與稽核，確認某個帳號具備哪些能力有明確的權威依據，不需仰賴閱讀應用程式碼推測。帳號切分之後的進階配置——包含遷移新建表的預設權限（`ALTER DEFAULT PRIVILEGES`）、受控檢視表、唯附寫稽核表，以及角色層級的查詢與等鎖逾時護欄——見 [1.21 資安、權限與合規決定的資料表設計：軟刪除與唯一約束、多租戶子表與列級安全性、RBAC 與非同步任務複查、存取憑證撤銷與優先序、個資分離與不可變稽核、角色預設權限與逾時護欄](/backend/01-database/security-and-compliance-schema-decisions/)。
