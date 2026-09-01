---
title: "1.10 權限的預設是什麼都不給"
date: 2026-08-31
description: "角色與 GRANT 的授權單位、建立物件擋在 schema 這一層，以及最小權限成立的前提"
weight: 10
tags: ["sql", "privilege", "grant", "role", "least-privilege", "postgresql"]
---

`GRANT` 與 `REVOKE` 是 SQL 的一部分，與 `SELECT` 一樣由標準定義。它們管的是誰被允許對哪個物件做哪件事，而預設是什麼都不允許——權限是一項一項加上去的，不是先給再收回來。這個預設之下，一個帳號能做什麼等於它被授予過什麼，兩者之間沒有隱含的推導。

以下的輸出來自 PostgreSQL 18。SQLite 沒有使用者的概念，整個檔案的存取由檔案系統決定，所以本篇談的授權這一層在 SQLite 上不存在。

## 新建的角色連讀都讀不了

書店的資料裡有三位顧客與兩張訂單，現在要開一個只跑報表的帳號。PostgreSQL 用「角色」這一個概念同時涵蓋使用者與群組——帶 `LOGIN` 屬性的角色可以連線，不帶的當群組用，兩者授權的方式相同。先建一個能登入的角色，什麼權限都還沒給：

```sql
CREATE ROLE 報表 LOGIN PASSWORD '...';
SET ROLE 報表;
SELECT * FROM 顧客;
-- ERROR: permission denied for table 顧客
```

這個角色存在、登得進來、而它讀不到任何一張表。**能連線與能做事是兩件分開的事**：能連線由角色的 `LOGIN` 屬性決定，能做事由授權決定。

給了讀取權之後才讀得到：

```sql
GRANT SELECT ON 顧客 TO 報表;
-- 之後 SELECT 姓名 FROM 顧客 回 佳穎、宗翰、雅文
```

## 授權是逐項的，讀寫各自分開

上面只給了 `SELECT`。同一個角色去寫：

```sql
INSERT INTO 顧客 VALUES (4,'柏宇');   -- permission denied for table 顧客
DELETE FROM 顧客 WHERE 顧客編號=1;    -- permission denied for table 顧客
```

兩個都被擋下來，錯誤訊息與完全沒授權時一模一樣。權限的單位是「哪個角色、對哪張表、做哪一種動作」，`SELECT`、`INSERT`、`UPDATE`、`DELETE` 各自獨立，給一項不會順帶給另一項。

查得到目前有哪些授權：

```sql
SELECT grantee, privilege_type FROM information_schema.role_table_grants
WHERE table_name = '顧客';
```

`REVOKE SELECT ON 顧客 FROM 報表` 之後，那個角色又回到 `permission denied`。

## 建立物件的權限擋在 schema，不擋在 table

`GRANT SELECT` 給的是對既有表的存取，與「能不能建新的表」無關。報表角色去建表：

```sql
CREATE TABLE 偷建的 (x INT);
-- ERROR: permission denied for schema public
```

被擋的層次不同——這次擋在 [schema](/sql/knowledge-cards/schema-namespace/) 而不是 table。PostgreSQL 15 之後 `public` schema 預設不再開放給所有人建立物件，在那之前這個操作會成功。**同一段 SQL 在不同版本上的結果不同，而差別在預設值而不在語法。**

## 最小權限在這裡的具體意思

應用程式連資料庫用的帳號，開的權限涵蓋它實際會執行的動作就夠。一個只跑報表的程式從來不寫入，所以它的帳號有沒有 `INSERT` 對它的功能沒有差別；處理訂單的程式不會刪顧客，所以那一項也一樣。遷移是唯一需要 [DDL](/sql/knowledge-cards/ddl-dml/) 的場合，而它不是常態運行的一部分——那些權限跟著它自己的帳號走，平常沒有任何一條應用程式的連線用它登入。

這樣分的效益在事故發生時才顯示出來。應用程式如果用超級使用者連線，一個注入漏洞的可觸及範圍是整個資料庫，包含刪表與讀取其他應用的資料；同一個漏洞在只有 `SELECT` 權限的帳號上，可觸及範圍縮到被授予 `SELECT` 的那幾張表的讀取。**漏洞一樣，可觸及的範圍差很多，而差別在事發前就決定好了。** 這個推論的前提是應用程式的每一種用途各用一個資料庫帳號；所有用途共用一個帳號、由應用層自己做授權的架構下，資料庫這一層的最小權限就使不上力，防線要落在別處。

授權查得到、也審計得到，所以「這個帳號能做什麼」是一個有明確答案的問題，不必靠讀應用程式的程式碼推測。

## 換掉其中一項會變成什麼

本篇的可動項是：授權的動作種類、物件的層次，以及一個帳號承擔幾種用途。

**把「誰被允許動它」換成「它叫什麼名字」**：權限管的物件由識別字指認，而那個名字送進引擎會先被改寫一次。[1.9 識別字送進引擎之後會被改寫](/sql/identifier-rules/) 拿 PostgreSQL、SQLite 與 DuckDB 三家對照摺疊規則與引號的作用，以及為什麼同一段建表語句換引擎之後可能指向不同的名字。

**把權限這一層放回整個資料層的攻擊面**：授權只是其中一層。[backend 模組一的攻擊者視角](/backend/01-database/red-team-data-layer/) 走注入、授權繞過、資料外洩、競態與資源耗盡五類，其中前三類各附一則真實事件對照，另有一段把失敗代價從資料外洩延伸到業務中斷。

**把常態運行換成遷移**：那是 DDL 權限實際被用到的場合，而它不掛在任何一條應用程式的連線上。[資料庫轉換實作](/backend/01-database/database-migration-playbook/) 走雙寫、回填、切流與回滾的完整流程。
