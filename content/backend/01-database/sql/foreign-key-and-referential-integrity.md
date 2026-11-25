---
title: "SQL.18 外鍵與參照完整性：宣告、生效與查詢得到的保證"
date: 2026-09-02
description: "外鍵攔截的寫入與 NULL 放行規則、SQLite、PostgreSQL 與 MySQL 中宣告與生效分離的位置與查法、約束生效後查詢省去的防禦判斷、父列刪除時的 ON DELETE 選項，以及外鍵不涵蓋的既有資料、跨庫參照、業務規則與狀態語意變更"
aliases: ["/sql/foreign-key-and-referential-integrity/"]
weight: 19
tags: ["sql", "foreign-key", "constraint", "referential-integrity", "ddl"]
---

外鍵（foreign key）在寫入當下強制維護參照完整性，使後續查詢能省去原本必須自行防禦的資料假設。本篇涵蓋以下面向：

- 外鍵攔截哪些寫入，以及 `NULL` 在單欄與複合外鍵下的放行規則。
- SQLite、PostgreSQL 與 MySQL 中宣告與生效分離的位置，以及系統目錄查法與延遲檢查（`DEFERRABLE`）。
- 約束生效前後查詢可省去的假設，以及 `NOT NULL` 與外鍵各自的保證。
- 父列被刪除時 `ON DELETE` 各選項的語意、稽核留存考量與和 `NOT NULL` 的衝突。
- 外鍵不涵蓋的邊界（既有資料、跨庫參照、未開檢查的連線、一般業務規則與狀態轉換對關聯語意的影響），以及關鍵字宣告被執行的程度。

外鍵是宣告在資料表結構上的規則：子表某一欄的值，必須能在父表找到對應的紀錄。資料庫在每次寫入時強制檢查這條規則，涵蓋範圍包括往後的每一筆資料。這項保證稱為**參照完整性**（referential integrity）——「參照」指欄位指向另一張表的列，「完整」指該指向必對應到實際存在的紀錄。在查詢文字之外影響結果的各項機制（識別字規則、權限、最佳化器、collation、引擎寬鬆度與部署形態）裡，約束介入得最早：它在資料寫入時即限定了允許寫入的資料形態，進而決定往後每段查詢可能遇到的列集合。本篇專注於外鍵加上後的寫入與查詢行為，不討論建表時是否應加外鍵的架構取捨。

以下範例在[SQL 各篇共用的範例資料庫：一家小書店的顧客、訂單與評價表](/backend/01-database/sql/sample-bookstore-database/)上重建並加上約束（顧客為佳穎、宗翰、雅文，僅佳穎有訂單）。後續說明既有的表補約束時另建出貨表，說明狀態變更時另建任務清單表。指向不存在父列的子表紀錄稱為**孤兒列**。

## 外鍵擋下的寫入與 NULL 的放行

外鍵強制維護父表與子表之間的參照指向，破壞指向的寫入來自兩個方向：在子表插入或更新一個父表不存在的值，或在父表刪除仍被子表參照的列：

```sql
CREATE TABLE 訂單 (訂單編號 INT PRIMARY KEY,
                   顧客編號 INT REFERENCES 顧客(顧客編號), 下單日 TEXT, 金額 INT);
CREATE TABLE 評價 (評價編號 INT PRIMARY KEY,
                   訂單編號 INT REFERENCES 訂單(訂單編號), 星等 INT);
```

```text
-- PostgreSQL 18
INSERT INTO 評價 VALUES (9003, 999, 4);
ERROR:  insert or update on table "評價" violates foreign key constraint "評價_訂單編號_fkey"
DETAIL:  Key (訂單編號)=(999) is not present in table "訂單".

DELETE FROM 顧客 WHERE 顧客編號 = 1;
ERROR:  update or delete on table "顧客" violates foreign key constraint "訂單_顧客編號_fkey" on table "訂單"
DETAIL:  Key (顧客編號)=(1) is still referenced from table "訂單".
```

兩則錯誤訊息裡的約束名稱不同：第一則屬於評價表，第二則屬於訂單表——刪除顧客觸發的是訂單表上的參照檢查，因此阻擋該操作的是宣告在訂單表上的約束。判讀外鍵錯誤訊息時須注意：訊息中指名的資料表未必是原 SQL 語句操作的那張表。

`NULL` 在子表寫入與父表檢查中皆會放行。單欄外鍵的語意是「當該欄有值時，該值必須存在於父表」，因此空值不觸發比對。跨多欄的複合外鍵在預設 `MATCH SIMPLE` 規則下，只要其中任一欄為 `NULL` 即整條放行，其餘有值的欄位也不比對。若要要求多欄全有值或全為空，須宣告 `MATCH FULL`；在本篇實測的 PostgreSQL 18、SQLite 3.51 與 MySQL 8.4 中，僅 PostgreSQL 實際強制執行該語法。將 `(999, NULL)`（`999` 不存在於父表）插入兩欄外鍵時，各引擎的反應如下：

```sql
-- 父表以 (a, b) 兩欄為主鍵，999 在父表裡不存在
CREATE TABLE 父 (a INT, b INT, PRIMARY KEY (a, b));
CREATE TABLE 子_預設 (a INT, b INT, FOREIGN KEY (a, b) REFERENCES 父 (a, b));
CREATE TABLE 子_完整 (a INT, b INT, FOREIGN KEY (a, b) REFERENCES 父 (a, b) MATCH FULL);

-- 預設 MATCH SIMPLE：有一欄是 NULL，整條放行，另一欄不查
INSERT INTO 子_預設 VALUES (999, NULL);
-- PostgreSQL 18：收下

-- 宣告成 MATCH FULL：逐欄都算
INSERT INTO 子_完整 VALUES (999, NULL);
-- PostgreSQL 18：拒絕，MATCH FULL does not allow mixing of null and nonnull key values
-- SQLite 3.51（已開 PRAGMA foreign_keys）、MySQL 8.4：收下 MATCH FULL 這個語法，照樣放行同一列
```

在 SQLite 與 MySQL 上要攔截混雜空值與非空值的組合，須在每個外鍵欄位各自加上 `NOT NULL`。同理，在單欄外鍵上若未加 `NOT NULL`，訂單編號留空的評價仍可寫入（這正是 [SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/) 中導致 `NOT IN` 回傳零列的資料形態），必須加上 `NOT NULL` 才能一併攔截。

允許 `NULL` 在自我參照（self-referencing）結構裡是必要條件：例如員工表的主管欄參照同一張表的員工編號時，最頂層主管沒有上層，其主管欄必須允許為空。查詢這類層級結構時需使用自連接並以別名區分兩次出現，見 [SQL.7 表的出現與別名：表名的指稱、別名的作用範圍與自連接](/backend/01-database/sql/table-occurrence-and-alias/)。

## 宣告與生效分開的位置：連線設定、約束狀態、語法形態與儲存引擎

相同的 `REFERENCES` 語法送進不同引擎時，可能出現「已宣告但未生效」的落差，具體發生在連線設定、約束狀態、語法形態與儲存引擎四個位置。

**連線設定（SQLite）。** SQLite 解析並儲存 `REFERENCES` 宣告，但預設關閉外鍵檢查，檢查開關依附在每條連線上各自設定：

```text
-- SQLite 3.51，未開 PRAGMA
INSERT INTO 評價 VALUES (9003, 999, 4);   -- 成功，孤兒列進來了

-- 同一個檔案，開了之後
PRAGMA foreign_keys = ON;
INSERT INTO 評價 VALUES (9004, 888, 4);
Error: stepping, FOREIGN KEY constraint failed (19)
```

開啟開關後，先前在關閉狀態寫入的孤兒列（9003）依然留在表中，因為檢查只作用於新寫入且不追溯既有資料。找出既有孤兒列須執行 `PRAGMA foreign_key_check`：

```sql
PRAGMA foreign_key_check;
-- table | rowid | parent | fkid
-- 評價  | 2     | 訂單   | 0
--   違反者所在的表、那一列的 rowid、被指向的表，以及那是這張表上的第幾條外鍵（從 0 起算）
--   評價編號宣告成 INT PRIMARY KEY 而不是 INTEGER PRIMARY KEY，所以 rowid 是另一個隱藏欄位，不等於評價編號
```

**約束狀態（PostgreSQL 的 `NOT VALID`）。** PostgreSQL 允許以 `NOT VALID` 為既有大表加上外鍵並略過既有列檢查，只針對新寫入強制執行，日後再透過 `VALIDATE CONSTRAINT` 補檢（避免加約束當下長時間鎖表）。這個中間狀態會讓資料表同時帶有外鍵宣告與既有的孤兒列：

```sql
-- PostgreSQL 18，出貨表裡已經有一列指向不存在的訂單 777
CREATE TABLE 出貨 (出貨編號 INT PRIMARY KEY, 訂單編號 INT);
INSERT INTO 出貨 VALUES (1, 102), (2, 777);

ALTER TABLE 出貨 ADD CONSTRAINT 出貨_訂單編號_fkey
  FOREIGN KEY (訂單編號) REFERENCES 訂單(訂單編號) NOT VALID;
-- 成功，777 那一列沒有被檢查

INSERT INTO 出貨 VALUES (3, 888);
-- ERROR:  insert or update on table "出貨" violates foreign key constraint "出貨_訂單編號_fkey"

ALTER TABLE 出貨 VALIDATE CONSTRAINT 出貨_訂單編號_fkey;
-- ERROR:  insert or update on table "出貨" violates foreign key constraint "出貨_訂單編號_fkey"
-- DETAIL:  Key (訂單編號)=(777) is not present in table "訂單".
```

**語法形態（MySQL 8.4 及之前版本的欄位層宣告）。** MySQL 8.4（及之前版本）解析欄位層的 `REFERENCES` 語法後會直接忽略，不建立任何約束，且 `SHOW WARNINGS` 為空（MySQL 9.0 起才開始強制執行欄位層 `REFERENCES`）。同一段在 PostgreSQL 與 SQLite 生效的 DDL，在 MySQL 8.4 中不生效且不發警告。

**儲存引擎（MySQL 的 MyISAM）。** 即使改寫成表層的 `FOREIGN KEY`，若資料表因沿用舊範本、還原舊備份或複製舊 DDL 而使用 `MyISAM` 儲存引擎，MySQL 同樣接受語法、不發警告且不建立外鍵。在 MySQL 上必須同時使用表層 `FOREIGN KEY` 語法與 `InnoDB` 儲存引擎，外鍵才會實際生效：

```sql
-- MySQL 8.4，資料庫名 t；顧客表同共用資料，並以顧客編號為主鍵
-- 欄位層的 REFERENCES：建表成功，SHOW WARNINGS 是空的
CREATE TABLE 訂單 (訂單編號 INT PRIMARY KEY,
                   顧客編號 INT REFERENCES 顧客(顧客編號), 下單日 TEXT, 金額 INT);
INSERT INTO 訂單 VALUES (103, 999, '2026-03-10', 200);
-- 成功，孤兒列進來了

-- 表層的 FOREIGN KEY，建在預設的 InnoDB 上
CREATE TABLE 訂單_表層 (訂單編號 INT PRIMARY KEY, 顧客編號 INT, 下單日 TEXT, 金額 INT,
                        FOREIGN KEY (顧客編號) REFERENCES 顧客(顧客編號));
INSERT INTO 訂單_表層 VALUES (103, 999, '2026-03-10', 200);
-- ERROR 1452 (23000): Cannot add or update a child row: a foreign key constraint fails

-- 同樣的表層寫法建在 MyISAM 上：建表成功，SHOW WARNINGS 是空的
CREATE TABLE 訂單_MyISAM (訂單編號 INT PRIMARY KEY, 顧客編號 INT, 下單日 TEXT, 金額 INT,
                          FOREIGN KEY (顧客編號) REFERENCES 顧客(顧客編號)) ENGINE=MyISAM;
INSERT INTO 訂單_MyISAM VALUES (103, 999, '2026-03-10', 200);
-- 成功，孤兒列進來了

SELECT TABLE_NAME FROM information_schema.REFERENTIAL_CONSTRAINTS
 WHERE CONSTRAINT_SCHEMA = 't';
-- 訂單_表層    三張表裡只有這一張留下了約束
```

這四個位置的共同特徵是外鍵只於寫入當下觸發，僅讀查詢語句與查詢結果無法判斷約束是否存在。確認約束狀態須查詢系統目錄（資料庫內建用來記錄表、欄、約束與權限定義的系統表），且須將「是否已宣告」與「是否實際生效」分開查證：SQLite 在 `PRAGMA foreign_keys` 關閉時系統目錄仍列出外鍵，PostgreSQL 的 `NOT VALID` 外鍵也列在 `information_schema.table_constraints` 中：

```sql
-- 宣告是否存在
-- PostgreSQL
SELECT table_name, constraint_name FROM information_schema.table_constraints
 WHERE constraint_type = 'FOREIGN KEY';
-- MySQL
SELECT TABLE_NAME, CONSTRAINT_NAME FROM information_schema.REFERENTIAL_CONSTRAINTS
 WHERE CONSTRAINT_SCHEMA = 't';
-- SQLite：每張表各查一次
PRAGMA foreign_key_list(評價);
-- 0|0|訂單|訂單編號|訂單編號|NO ACTION|NO ACTION|NONE    開關關著的時候也列得出來

-- 是否實際生效
-- SQLite：這條連線的開關
PRAGMA foreign_keys;
-- 0 是關、1 是開
-- PostgreSQL：convalidated 是 f 的外鍵是 NOT VALID，既有的列沒有檢查過
SELECT conname, convalidated FROM pg_constraint WHERE contype = 'f';
-- 出貨_訂單編號_fkey | f
-- 訂單_顧客編號_fkey | t
-- 評價_訂單編號_fkey | t
```

約束生效後另有「檢查時點」的維度。外鍵預設在每句寫入語句結束時立即檢查；PostgreSQL 的 `DEFERRABLE INITIALLY DEFERRED` 則將檢查延後至 [Transaction（交易）](/backend/knowledge-cards/transaction/) `COMMIT` 時執行。當兩張表互相以 `NOT NULL` 外鍵參照對方（例如部門指向主管、員工指向所屬部門）時，沒有延遲檢查就無法寫入第一筆資料；代價是錯誤直到 `COMMIT` 才回報，難以從錯誤位置直接定位觸發違規的語句：

```sql
-- PostgreSQL 18，兩條外鍵都宣告成 DEFERRABLE INITIALLY DEFERRED
CREATE TABLE 部門 (部門編號 INT PRIMARY KEY, 主管 INT NOT NULL);
CREATE TABLE 員工 (員工編號 INT PRIMARY KEY,
                   部門編號 INT NOT NULL REFERENCES 部門 DEFERRABLE INITIALLY DEFERRED);
ALTER TABLE 部門 ADD FOREIGN KEY (主管) REFERENCES 員工 DEFERRABLE INITIALLY DEFERRED;

BEGIN;
INSERT INTO 部門 VALUES (1, 10);   -- 員工 10 還不存在，這一句照樣通過
INSERT INTO 員工 VALUES (10, 1);
COMMIT;                            -- 提交時兩條外鍵都滿足

BEGIN;
INSERT INTO 部門 VALUES (2, 20);   -- 通過
COMMIT;
-- ERROR:  insert or update on table "部門" violates foreign key constraint "部門_主管_fkey"
-- DETAIL:  Key (主管)=(20) is not present in table "員工".
--   同樣兩張表不宣告 DEFERRABLE 的話，兩句 INSERT 無論哪一句先寫都當場被擋下
```

## 約束生效之後查詢可以省掉的判斷：NOT NULL 與外鍵各自的保證

約束生效的價值在於消除查詢端必須自行防禦的資料假設。對照兩個版本的訂單表：有約束版在 `顧客編號` 宣告 `NOT NULL REFERENCES 顧客(顧客編號)`，無約束版未加任何約束並寫入一筆顧客編號為 `NULL` 的訂單：

```sql
-- SQLite 3.51，已開 PRAGMA foreign_keys
-- 有約束的版本
CREATE TABLE 訂單 (訂單編號 INT PRIMARY KEY,
                   顧客編號 INT NOT NULL REFERENCES 顧客(顧客編號), 下單日 TEXT, 金額 INT);
INSERT INTO 訂單 VALUES (101,1,'2026-03-02',300), (102,1,'2026-03-09',500);
INSERT INTO 訂單 VALUES (103, NULL, '2026-03-10', 200);
-- NOT NULL constraint failed: 訂單.顧客編號
-- 沒有約束的版本（共用資料的建表語句）收下同一列

-- 兩個版本各跑一次
SELECT count(*) FROM 訂單 JOIN 顧客 ON 顧客.顧客編號 = 訂單.顧客編號;
-- 有約束：2，訂單表 2 列
-- 沒有約束：2，訂單表 3 列；103 配不到任何顧客，從結果裡消失

SELECT 姓名 FROM 顧客 WHERE 顧客編號 NOT IN (SELECT 顧客編號 FROM 訂單);
-- 有約束：宗翰、雅文
-- 沒有約束：0 列；子查詢交出 1、1、NULL，與 NULL 比較的那一項是未知
```

在無約束版中，內連接靜默遺失訂單 103、`NOT IN` 因碰到 [NULL（空值）](/backend/01-database/sql/knowledge-cards/null/) 靜默回傳空集合（內連接丟棄未配對列的機制見 [Outer Join（外連接）](/backend/01-database/sql/knowledge-cards/outer-join/)，`NOT IN` 的展開推導見 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)）。在有約束版中，兩段完全相同的查詢都回傳正確結果，因為前提已從「當下資料偶然不含空值」提升為資料庫強制執行的保證（見 [Constraint（約束）](/backend/01-database/sql/knowledge-cards/constraint/)）。

`NOT NULL` 與外鍵各自提供不同的保證。**`NOT NULL`** 保證欄位一定有值，消除內連接因空值掉列的風險，並在與外層比對欄位兩側皆宣告非空時消除 `NOT IN` 遇空值失真的風險（單靠子查詢欄位非空仍無法擋住外層欄位為 `NULL` 時與 `NOT EXISTS` 的分岔）；**外鍵**保證「有值的欄位必定指向父表存在的列」。唯有兩條約束同時存在，才能確定子表每一列都有對應父列，進而保證 `JOIN` 與 `LEFT JOIN` 回傳相同列集合——若只有外鍵而無 `NOT NULL`，顧客編號留空的訂單仍可寫入，導致內連接與外連接結果分歧。`UNIQUE`、`CHECK`、`PRIMARY KEY`（`NOT NULL` 加 `UNIQUE` 並作為列識別鍵）皆遵循同一原則：豁免查詢防禦判斷的依據必須是已生效的約束，而非單次資料觀察（各種約束的保證與歸屬 [DDL 與 DML（定義結構與動資料）](/backend/01-database/sql/knowledge-cards/ddl-dml/) 的原因見 [Constraint（約束）](/backend/01-database/sql/knowledge-cards/constraint/)）。

這項讀取保證的代價由寫入端承擔：每次插入或更新子表都須至父表查核目標值是否存在，實際成本應透過執行計畫與量測評估（見 [SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/)）。是否加設外鍵屬於資料建模的取捨：核心交易資料多由資料庫強制完整性以換取可靠查詢，跨系統整合資料則常改由應用層驗證以避免上游結構先變動導致寫入中斷，寫入成本與外鍵執法的實測對照見 [1.16 Schema 設計決定的查詢代價：可空性、排序鍵唯一性、表寬、一對多的切法、比較規則、外鍵執法，以及從另一張表取值時的複製與引用](/backend/01-database/design-decisions-price-every-query/) 的〈外鍵的宣告與執法〉一節。

## 父列被刪除時子列的去向：ON DELETE 的選項

當父列被刪除時，外鍵預設拒絕刪除；要定義子列的連帶處置，SQL 提供 `ON DELETE` 子句指定以下行為：

```sql
訂單編號 INT REFERENCES 訂單(訂單編號) ON DELETE CASCADE      -- 子列一起刪掉
訂單編號 INT REFERENCES 訂單(訂單編號) ON DELETE SET NULL     -- 子列留著，這一欄清空
訂單編號 INT NOT NULL DEFAULT 0
            REFERENCES 訂單(訂單編號) ON DELETE SET DEFAULT  -- 子列留著，改指一個預先建立、代表「已刪除」的哨兵列
```

在 PostgreSQL 18 刪除訂單 102 後，三種宣告的子表各自產生對應結果：

```sql
-- 三張評價表照上面三行宣告，各有一列 (9001, 102, 4)；訂單 0 是事先備好的哨兵列
DELETE FROM 訂單 WHERE 訂單編號 = 102;

SELECT * FROM 評價_連帶刪除;   -- ON DELETE CASCADE：0 列
SELECT * FROM 評價_清空;       -- ON DELETE SET NULL：9001 |   | 4，訂單編號變成空的
SELECT * FROM 評價_改指哨兵;   -- ON DELETE SET DEFAULT：9001 | 0 | 4，改指哨兵列
```

在標準 SQL 與 PostgreSQL 中，拒絕刪除有 `RESTRICT` 與 `NO ACTION` 兩種宣告：`RESTRICT` 在 `DELETE` 語句當下立即阻擋且不可延遲；`NO ACTION`（未寫 `ON DELETE` 時的預設）在語句結束時檢查，搭配 `DEFERRABLE` 可延後至交易提交時驗證。在同一個交易內先刪父列再刪子列，僅有宣告為 `DEFERRABLE` 的 `NO ACTION` 能順利提交；MySQL InnoDB 則將 `NO ACTION` 視為與 `RESTRICT` 等同，且不支援 `DEFERRABLE` 延遲檢查。

選用哪個 `ON DELETE` 選項取決於兩道判斷。第一道是**子列脫離父列後是否仍具備獨立意義**：訂單評價脫離訂單便失去意義，適合 `CASCADE`；出貨紀錄即使訂單撤銷仍是已發生的物流事實，清空參照（`SET NULL`）比刪除更符合業務事實。

第二道優先權更高的判斷是**子列是否負有法規或稽核保留義務**。帳務交易紀錄雖依附於帳戶，但受稽核留存規定限制而不能隨父列消失：採用 `CASCADE` 會沿著外鍵關聯自動連鎖刪除——刪除一位顧客可能連帶移除訂單、評價與更下層的明細，而 `DELETE` 語句文字只提及顧客表；採用 `RESTRICT` 會直接阻擋刪除父列，`SET DEFAULT` 則改指代表「已刪除」的哨兵列以保留紀錄且不留空值。此外，`ON DELETE` 只在實際執行 `DELETE` 時觸發；系統若採軟刪除（以 `UPDATE` 寫入 `deleted_at`），外鍵的連帶處置不會觸發（軟刪除與唯附寫稽核表設計見 [1.21 資安、權限與合規決定的資料表設計：軟刪除與唯一約束、多租戶子表與列級安全性、RBAC 與非同步任務複查、存取憑證撤銷與優先序、個資分離與不可變稽核、角色預設權限與逾時護欄](/backend/01-database/security-and-compliance-schema-decisions/)）。在 SQLite 執行「重建資料表（`DROP TABLE` 舊表）」式 schema 升級時，若連線維持開啟 `PRAGMA foreign_keys = ON`，含 `ON DELETE CASCADE` 的子表會在卸除舊表時遭連帶清空，這類遷移程序須照 [SQLite Schema Migration and Versioning](/backend/01-database/vendors/sqlite/schema-migration-versioning/) 的步驟處理。

`ON DELETE SET NULL` 與同一欄位的 `NOT NULL` 互相矛盾，但建表階段引擎不會阻擋，衝突直到實際刪除父列時才發生：

```sql
-- PostgreSQL 18
CREATE TABLE 評價 (評價編號 INT PRIMARY KEY,
                   訂單編號 INT NOT NULL REFERENCES 訂單(訂單編號) ON DELETE SET NULL, 星等 INT);
-- 建表成功
INSERT INTO 評價 VALUES (9001, 101, 5);
DELETE FROM 訂單 WHERE 訂單編號 = 101;
-- ERROR:  null value in column "訂單編號" of relation "評價" violates not-null constraint
-- DETAIL:  Failing row contains (9001, null, 5).
-- CONTEXT:  SQL statement "UPDATE ONLY "public"."評價" SET "訂單編號" = NULL WHERE ..."
```

在這裡宣告與執行再次分開。由於 `NOT NULL` 是消除內連接掉列與 `NOT IN` 回零列的前提，若選擇以 `SET NULL` 保留子列，該欄位即重新允許空值，查詢端便不能再依賴非空保證。

## 外鍵涵蓋不到的寫入與規則

外鍵只於通過檢查的寫入當下驗證父列是否存在，因此有以下幾類情形不在外鍵的保護範圍內。

**既有資料不涵蓋。** 對已含孤兒列的資料表直接補加外鍵會立即失敗：

```text
-- PostgreSQL 18，出貨表裡有一列的訂單編號是 777
ALTER TABLE 出貨 ADD FOREIGN KEY (訂單編號) REFERENCES 訂單(訂單編號);
ERROR:  insert or update on table "出貨" violates foreign key constraint "出貨_訂單編號_fkey"
DETAIL:  Key (訂單編號)=(777) is not present in table "訂單".
```

加約束成功的前提是表內所有既有列已滿足規則；對線上大表分階段清理與補約束的流程見 [1.6 資料庫轉換實作：雙寫、回填、切流與回滾](/backend/01-database/database-migration-playbook/) 的〈加約束（CHECK / FK / NOT NULL 收緊）〉一節。

**跨資料庫與外部儲存參照不涵蓋。** 外鍵只作用於同一資料庫內的資料表，指向外部微服務識別碼或物件儲存鍵值的欄位無法靠外鍵驗證。單一應用內部的驗證分層見 [不變式的強制層次](/software-design/ddd/invariant-enforcement-layers/)，跨服務的一致性機制（如 Saga 與 Outbox）見 [1.3 Transaction 與一致性邊界](/backend/01-database/transaction-boundary/)。

**未啟用檢查的連線寫入不涵蓋。** 在 SQLite 將 `PRAGMA foreign_keys` 設於個別連線的設計下，遷移工具、測試腳本或第三方程式若開啟未啟用該選項的新連線，其寫入會繞過外鍵檢查。因此 SQLite 外鍵實際保護的是「已開啟開關的連線寫入」，而非整個資料庫檔案。

**跨列與跨表的業務規則不涵蓋。** 外鍵只檢查值是否存在於父表，無法表達「同一張訂單只能退款一次」（須在退款表的訂單編號上宣告 `UNIQUE`）或「評價時間必須晚於出貨時間」（`CHECK` 僅能讀寫入當下該單列、不支援子查詢，須改用觸發器或應用層檢查）。這與 [SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/) 的分界一致：約束依檢查當下可讀取的資訊範圍劃分能力——`CHECK` 讀單列、`UNIQUE` 讀單欄或複合欄位既有值、外鍵讀父表對應列、PostgreSQL 排除約束另讀同表非等值跨列比較（如區間重疊），超出此範圍的業務規則須由觸發器或應用層負責。

**父列狀態變更對子表語意的影響不涵蓋。** 外鍵只驗證被指向的父列是否存在，不驗證該列狀態欄位改變後，引用它的規則如何解讀新狀態。以任務相依清單為例，規格定義「前置任務完成或放棄時不再阻擋後續任務」，`現在能做` 檢視表照此規則實作：

```sql
-- 本段於 SQLite 3.43.2 與 3.53.0 實測（僅用到基本檢視表與子查詢）
PRAGMA foreign_keys = ON;
CREATE TABLE 任務 (任務編號 INTEGER PRIMARY KEY, 名稱 TEXT,
                   狀態 TEXT NOT NULL CHECK (狀態 IN ('待辦','完成','放棄')));
CREATE TABLE 任務相依 (任務編號 INT REFERENCES 任務(任務編號),
                       前置任務編號 INT REFERENCES 任務(任務編號),
                       PRIMARY KEY (任務編號, 前置任務編號));
-- 前置任務還是「待辦」的，才擋住後續任務
CREATE VIEW 現在能做 AS
SELECT t.任務編號, t.名稱 FROM 任務 t
WHERE t.狀態 = '待辦'
  AND NOT EXISTS (SELECT 1 FROM 任務相依 d JOIN 任務 p ON p.任務編號 = d.前置任務編號
                  WHERE d.任務編號 = t.任務編號 AND p.狀態 = '待辦');
INSERT INTO 任務 VALUES (1,'整理報稅資料','待辦'),(2,'申報所得稅','待辦');
INSERT INTO 任務相依 VALUES (2,1);              -- 申報要等資料整理好
SELECT * FROM 現在能做;
-- 1|整理報稅資料
```

當「整理報稅資料」拆成兩個子步驟並將原任務改標為「放棄」時：

```sql
INSERT INTO 任務 VALUES (3,'收集扣繳憑單','待辦'),(4,'下載醫療收據','待辦');
UPDATE 任務 SET 狀態 = '放棄' WHERE 任務編號 = 1;
SELECT * FROM 現在能做;
-- 2|申報所得稅
-- 3|收集扣繳憑單
-- 4|下載醫療收據
PRAGMA foreign_key_check;   -- 沒有輸出：外鍵全部完整
```

「整理報稅資料」尚未完成，「申報所得稅」卻已出現在可執行清單中：外鍵全部完整、每筆寫入皆合法、檢視表也忠實執行規則，但因為「放棄」被相依規則解讀為解除阻擋，結果反而出錯。若改將原任務保持「待辦」，讓兩個新步驟成為它的前置任務，原任務轉為彙整節點，則「申報所得稅」的相依語意維持正確：

```sql
-- 從拆分之前的狀態重來：開一條新的連線（重新執行 sqlite3 :memory:），先跑前一段建表與初始資料區塊，再接這一段
-- 原任務維持「待辦」
INSERT INTO 任務 VALUES (3,'收集扣繳憑單','待辦'),(4,'下載醫療收據','待辦');
INSERT INTO 任務相依 VALUES (1,3),(1,4);
SELECT * FROM 現在能做;
-- 3|收集扣繳憑單
-- 4|下載醫療收據
UPDATE 任務 SET 狀態 = '完成' WHERE 任務編號 IN (3,4);
SELECT * FROM 現在能做;
-- 1|整理報稅資料
UPDATE 任務 SET 狀態 = '完成' WHERE 任務編號 = 1;
SELECT * FROM 現在能做;
-- 2|申報所得稅
```

這段案例揭示了外鍵結構與業務狀態語意屬於兩層獨立資訊：`CREATE TABLE` 裡指向該表的外鍵只檢查父列存在與否，無法反映業務規格中各種關聯對新狀態的解讀規則（例如前置放棄解除阻擋、父項目封存導致子項目被 [Soft Delete（軟刪除）](/backend/knowledge-cards/soft-delete/) 隱藏）。

若要將這類狀態語意檢查自動化，常見作法是在資料庫透過觸發器擋下違法狀態轉換，或在應用層統一由領域方法處理狀態變更並搭配「狀態 × 關聯」測試（[狀態轉換與稽核軌跡](/software-design/ddd/state-transition-and-audit-trail/) 討論應用層領域方法的設計）。面對上述衝突時，可依業務語意改用維持原狀態的拆分結構、新增具獨立語意的狀態（如「已拆分」），或於同一交易內重寫指向它的關聯。

## 文字的宣告被執行的程度：外鍵、引擎補上的決定與 LEFT JOIN

在 SQL 宣告是否會被引擎強制驗證的光譜上，外鍵位居最明確的一端：只要在系統目錄確認宣告存在且生效，資料庫即強制執行。光譜另一端是 `LEFT JOIN` 等查詢關鍵字：它宣告預期存在未配對列，但引擎從不驗證該宣告是否兌現，宣告落空時仍回傳正確結果，見 [SQL.21 關鍵字的宣告與引擎的行為：宣告落空的形態與查證](/backend/01-database/sql/declared-intent-vs-behaviour/)。介於兩者之間的是引擎寬鬆度（如 MySQL 靜默忽略欄位層 `REFERENCES`），這類跨引擎差異的分級與處理時機見 [SQL.19 引擎寬鬆度與可攜性：各家對同一組寫法的差異、分級與處理時機](/backend/01-database/sql/engine-leniency-and-portability/)。
