---
title: "SQL.18 外鍵與參照完整性：宣告、生效與查詢得到的保證"
date: 2026-09-02
description: "外鍵擋下哪些寫入與 NULL 的放行、SQLite、PostgreSQL 與 MySQL 讓宣告與生效分開的位置與查法、約束生效後查詢省掉的判斷、父列刪除時子列的去向，以及外鍵涵蓋不到的寫入與規則"
aliases: ["/sql/foreign-key-and-referential-integrity/"]
weight: 19
tags: ["sql", "foreign-key", "constraint", "referential-integrity", "ddl"]
---

外鍵是一條寫在表結構上的宣告：這一欄的值，在另一張表裡找得到對應的那一列。資料庫在每一次寫入時檢查它，所以它涵蓋的是整張表，以及往後的每一筆資料。外鍵這條保證有一個名字叫**參照完整性**——「參照」指一欄指向另一張表的某一列，「完整」指那個指向落得到實處。

查詢的文字之外還有幾樣東西在決定結果——名字實際指向誰、送出的人被允許做什麼、引擎打算花多久。約束介入得比那幾樣都早：它決定資料能長成什麼樣，於是決定一段查詢會遇到哪幾種列。

本篇走完這條保證的全貌：它擋下哪些寫入、什麼時候才算生效、生效之後查詢省掉哪一步、父列消失時它怎麼維持，以及它涵蓋不到的地方。這條約束該不該加是資料表設計的取捨，本篇只處理加了之後寫入與查詢的行為有什麼改變。

本篇的表在[共用資料庫](/backend/01-database/sql/sample-bookstore-database/)上重建，差別是這一次把約束寫進結構裡；顧客表的三個人是佳穎、宗翰、雅文，而只有佳穎下過單。後面談替既有的表補約束時，另外用到一張出貨表。指不到父列的那一列，下文叫**孤兒列**。

## 外鍵擋下的寫入與 NULL 的放行

外鍵管的是兩張表之間的一個指向，而破壞這個指向的寫入來自兩邊。子表這一側是填進一個指不到的值，父表那一側是把還被指著的那一列刪掉。

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

上面兩則錯誤訊息裡的約束名不同。第一則是評價表自己那條，第二則是訂單表那條——刪顧客這個動作在訂單表上觸發檢查，所以擋下它的約束掛在訂單表上。**外鍵的錯誤訊息因此要分兩層讀**：訊息指名的表，未必是剛才那句 SQL 寫到的表。

有一個值在子表與父表兩邊都放行：`NULL`。單欄的外鍵讀作「這一欄有值的時候，那個值找得到對應」，所以空著的那一欄不參與檢查。**跨多欄的外鍵預設另有一種讀法**——標準的預設 `MATCH SIMPLE` 只要其中一欄是 `NULL` 就整條放行，另外幾欄有值也不查。要它回到逐欄都算的讀法得寫 `MATCH FULL`，而這個寫法只在 PostgreSQL 上生效。同一列 `(999, NULL)` 寫進兩欄外鍵、而 `999` 在父表裡不存在時，各引擎的結果是：

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

在 SQLite 與 MySQL 上要擋下混著空與非空的組合，得在每一欄各自加 `NOT NULL`。訂單編號留空的評價插得進去，而它是一則指不到任何訂單的評價——[SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/) 裡「NOT IN」的錯法要回零列，要的正是這樣一列。要連訂單編號留空的評價也擋掉，評價表的訂單編號另外要有 `NOT NULL`。

`NULL` 放行這件事在一種結構裡是必要的：外鍵指回自己所在的那張表。員工表的主管欄指向同一張表的另一列時，一列的上層是同一張表的另一列，而最頂層那一列的主管欄只能留空。這個結構的查詢要把同一張表擺兩次，兩次出現需要各自的名字，[SQL.7 表的出現與別名：表名的指稱、別名的作用範圍與自連接](/backend/01-database/sql/table-occurrence-and-alias/) 寫自連接為什麼非取名不可，並把它處理的關係分成前後配對、同組比較與層級關係三種形態——員工與主管屬於層級關係。

## 宣告與生效分開的位置：連線設定、約束狀態、語法形態與儲存引擎

同一段 `REFERENCES` 送進不同的引擎，會落在不同的狀態。宣告與生效在連線的設定、約束自己的狀態、語法的形態、表的儲存引擎這幾個位置各自分開過一次，而它們讓人察覺宣告與生效已經分岔的難易程度差很多。

**連線的設定**。SQLite 認得 REFERENCES 這段語法、也把約束記進結構裡，而檢查預設關閉，開關掛在每一條連線上：

```text
-- SQLite 3.51，未開 PRAGMA
INSERT INTO 評價 VALUES (9003, 999, 4);   -- 成功，孤兒列進來了

-- 同一個檔案，開了之後
PRAGMA foreign_keys = ON;
INSERT INTO 評價 VALUES (9004, 888, 4);
Error: stepping, FOREIGN KEY constraint failed (19)
```

開關打開之後，開關關著時插進去的那筆孤兒列（9003）仍然在表裡——檢查發生在寫入的當下，對已經在裡面的資料沒有追溯力。把孤兒列找出來的指令是 `PRAGMA foreign_key_check`：

```sql
PRAGMA foreign_key_check;
-- table | rowid | parent | fkid
-- 評價  | 2     | 訂單   | 0
--   違反者所在的表、那一列的 rowid、被指向的表，以及那是這張表上的第幾條外鍵（從 0 起算）
--   評價編號宣告成 INT PRIMARY KEY 而不是 INTEGER PRIMARY KEY，所以 rowid 是另一個隱藏欄位，不等於評價編號
```

**約束自己的狀態**。PostgreSQL 的 `NOT VALID` 讓一條外鍵掛上去而略過既有的列，往後的寫入照常檢查。這個狀態是給大表補約束用的（既有列的檢查另用 `VALIDATE CONSTRAINT` 分開跑，避免長時間鎖表），而它留下的中間態是：表上有這條約束，表裡有孤兒列。

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

**語法的形態**。MySQL 認得欄位層的 `REFERENCES`，解析完把它丟掉，不留下任何約束，`SHOW WARNINGS` 也是空的。同一段文字在 PostgreSQL 與 SQLite 底下建得出約束，在 MySQL 底下建不出來，而 MySQL 在建表時沒有給任何警告。

**表的儲存引擎**。同一家 MySQL 裡還有一條讓宣告消失的路，而它多半不是有人刻意選的——舊系統的建表模板、從舊備份還原回來的表、或複製過來的一段舊 DDL，都會把儲存引擎一起帶進來。表層的 `FOREIGN KEY` 寫法建在 MyISAM 上，語法照收、警告照樣是空的，約束同樣沒有留下。兩條路要改的地方不同：欄位層的寫法要改寫成表層的 `FOREIGN KEY`，MyISAM 要換成 InnoDB。

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

這幾個位置的共同點是**外鍵只在寫入的那一刻現身**：查詢的文字裡沒有一個字提到約束，讀的時候也沒有差別。所以「這條保證在不在」要另外查，查的地方是系統目錄。**系統目錄記的是宣告存不存在，生不生效要另外查**：SQLite 在 `PRAGMA foreign_keys` 關著的時候照樣列出那條外鍵，而孤兒列插得進去；PostgreSQL 的 `NOT VALID` 外鍵同樣列在 `information_schema.table_constraints` 裡。

```sql
-- 宣告存不存在
-- PostgreSQL
SELECT table_name, constraint_name FROM information_schema.table_constraints
 WHERE constraint_type = 'FOREIGN KEY';
-- MySQL
SELECT TABLE_NAME, CONSTRAINT_NAME FROM information_schema.REFERENTIAL_CONSTRAINTS
 WHERE CONSTRAINT_SCHEMA = 't';
-- SQLite：每張表各查一次
PRAGMA foreign_key_list(評價);
-- 0|0|訂單|訂單編號|訂單編號|NO ACTION|NO ACTION|NONE    開關關著的時候也列得出來

-- 生不生效
-- SQLite：這條連線的開關
PRAGMA foreign_keys;
-- 0 是關、1 是開
-- PostgreSQL：convalidated 是 f 的外鍵是 NOT VALID，既有的列沒有檢查過
SELECT conname, convalidated FROM pg_constraint WHERE contype = 'f';
-- 出貨_訂單編號_fkey | f
-- 訂單_顧客編號_fkey | t
-- 評價_訂單編號_fkey | t
```

生效之後還有一個「什麼時候檢查」的維度。預設是每一句寫入當場檢查，而 PostgreSQL 的 `DEFERRABLE INITIALLY DEFERRED` 把檢查推到交易提交的那一刻——中間的每一句都通過，`COMMIT` 才回 `violates foreign key constraint`。互相指向的兩張表要一起寫入時需要這個推遲——部門有一欄指向它的主管、員工有一欄指向所屬部門，兩欄都不能是空的時候，兩張表都得先有對方的一列才寫得進去。這種形態下沒有推遲就沒有第一筆資料。代價是錯誤浮現的位置離寫錯的那一句遠了一整個交易。

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

一條保證的價值落在它讓哪些判斷不必再做。同一組表的兩個版本擺在一起看得清楚：一邊的 `訂單.顧客編號` 帶著 `NOT NULL REFERENCES 顧客(顧客編號)`，另一邊什麼都沒有，而沒有約束的那一版收了一張顧客編號留空的訂單。

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

沒有約束的那一版，內連接與 `NOT IN` 這兩段查詢各自出了一種錯，而兩種都不報錯。內連接掉了一列，而總數看起來仍然像一份完整的訂單清單；`NOT IN` 整段回空集合，因為子查詢交出的那一欄含一個 [`NULL`](/backend/01-database/sql/knowledge-cards/null/)。內連接為什麼丟掉配不到對象的列，在 [Outer Join（外連接）](/backend/01-database/sql/knowledge-cards/outer-join/)；`NOT IN` 的完整推導在 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/) 的「子查詢含 NULL 時的 NOT IN 與 NOT EXISTS」一節。

有約束的那一邊，兩段查詢都對，而它們的寫法一個字都沒改。**改變的是那兩個判斷的前提從觀察變成了保證**：翻遍現在的訂單表沒有一筆顧客編號是空的，只證明此刻如此；`NOT NULL` 證明的是往後也不會有，而查詢要活得比這一批資料久（[Constraint](/backend/01-database/sql/knowledge-cards/constraint/)）。

這裡有兩條約束在做不同的事，分開記各自買到什麼。**`NOT NULL` 買的是「這一欄有值」**，它管掉上面兩種錯——沒有空缺，內連接就掉不了列，`NOT IN` 也碰不到那個 `NULL`。**外鍵買的是「這個值指得到人」**，它管的是另一批推論：這一欄有值的列，連過去必定配得到一列。子表的每一列都歸屬到某個父列、`JOIN` 與 `LEFT JOIN` 在這個方向上回同一批列，這兩項要兩條約束都在才成立——只有外鍵的時候，顧客編號留空的訂單照樣寫得進去，`LEFT JOIN` 留下它而 `JOIN` 丟掉它。兩條都在的時候，「這個連接會掉列嗎」這個問題不必查資料就答得出來。`UNIQUE` 保證值不重複、`CHECK` 保證值滿足一個自己寫的條件、`PRIMARY KEY` 是 `NOT NULL` 加 `UNIQUE` 再加上「這是辨識一列的依據」，而這幾種約束共用同一條性質——豁免一個判斷的條件必須是一條約束，不能是一次觀察；各自買到什麼、以及它們為什麼住在 [DDL](/backend/01-database/sql/knowledge-cards/ddl-dml/) 那一側，在 [Constraint（約束）](/backend/01-database/sql/knowledge-cards/constraint/)。

這些推論的代價落在寫入那一側：每插進一列，資料庫要去父表確認那個值在不在，所以外鍵是拿寫入的工作換讀取的保證。這筆交換要用量測來判，而讀代價的工具在 [SQL.17 查詢的代價](/backend/01-database/sql/cost-lives-in-the-plan/)。要不要加這條外鍵約束，則是設計的決定：它在強制完整性與演進自由度之間取捨：正式的核心資料通常由資料庫強制，換取每一次讀取都能信任的推論；跨系統整合的資料常改由應用層保護，因為上游的結構可能先變，外鍵會讓那一次變動變成寫入失敗——[Schema Design](/backend/01-database/schema-design/) 的「Table 與 Relation」一節寫這個取捨，並提醒宣告與執法要分開看。

## 父列被刪除時子列的去向：ON DELETE 的選項

擋下刪除是預設，而它把問題丟回給寫入的那一方：顧客要停用了，他的訂單怎麼辦。這個決定寫在外鍵的宣告裡，跟著約束走而不是跟著每次刪除走。

```sql
訂單編號 INT REFERENCES 訂單(訂單編號) ON DELETE CASCADE      -- 子列一起刪掉
訂單編號 INT REFERENCES 訂單(訂單編號) ON DELETE SET NULL     -- 子列留著，這一欄清空
訂單編號 INT NOT NULL DEFAULT 0
            REFERENCES 訂單(訂單編號) ON DELETE SET DEFAULT  -- 子列留著，改指一個哨兵列
```

在 PostgreSQL 18 上刪掉訂單 102，三種寫法的子列各自落到宣告寫的去向：

```sql
-- 三張評價表照上面三行宣告，各有一列 (9001, 102, 4)；訂單 0 是事先備好的哨兵列
DELETE FROM 訂單 WHERE 訂單編號 = 102;

SELECT * FROM 評價_連帶刪除;   -- ON DELETE CASCADE：0 列
SELECT * FROM 評價_清空;       -- ON DELETE SET NULL：9001 |   | 4，訂單編號變成空的
SELECT * FROM 評價_改指哨兵;   -- ON DELETE SET DEFAULT：9001 | 0 | 4，改指哨兵列
```

擋下刪除的則有兩種寫法而它們不一樣：`RESTRICT` 在那一句 `DELETE` 當場擋下，而且不能推遲；`NO ACTION`（沒寫 `ON DELETE` 時的預設）在每一句結束時檢查，約束宣告成 `DEFERRABLE` 之後才能推到交易提交。同一個交易裡先刪父列、再刪子列，只有宣告成 `DEFERRABLE` 的 `NO ACTION` 過得去。

**子列離開父列之後還有沒有意義，決定它跟著刪掉還是留下。** 一則評價離開它評的那張訂單之後說不出在評什麼，所以它適合跟著走；一筆出貨紀錄即使訂單被撤銷仍然是發生過的事實，清空指向比刪掉它更貼近實情。

**這一列有沒有自己的保留義務，是獨立的另一個問句，而它成立的時候蓋過「還有沒有意義」的答案。** 一筆交易紀錄離開它的帳戶之後同樣說不出在記什麼，只問還有沒有意義會走到 `CASCADE`——而受稽核或法規保留的紀錄不能被任何一次刪除帶走。保留義務成立的時候，答案落在 `RESTRICT` 或 `SET DEFAULT` 上（`RESTRICT` 不准刪父列，`SET DEFAULT` 讓子列改指一個「已刪除」的哨兵列，紀錄留著而那一欄不為空），而只問還有沒有意義的時候，這兩個選項不會被想到。保留義務要優先的理由是 `CASCADE` 的一個性質：**一次刪除實際刪掉多少，由表之間的結構決定，不由那句 `DELETE` 決定**。它沿著外鍵一路傳下去，刪一個顧客連帶刪掉他的訂單、那些訂單的評價，以及再往下的每一層，而那句 SQL 的文字裡只提到顧客。

`SET NULL` 與同一欄上的 `NOT NULL` 要求的條件互相排斥，而建表的時候兩者並存不會被擋下。PostgreSQL 18 收下這張表，衝突到刪除父列的那一刻才浮現，訊息指的是那個清空的動作違反了 `NOT NULL`：

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

**宣告與生效那條分界在這裡又出現一次：宣告收下了，做得到做不到要等到執行的那一刻。** 而 `NOT NULL` 買掉的正是掉列與 `NOT IN` 那兩類錯誤，所以這裡要選一邊——留下子列的代價是那一欄重新可能為空，關於它的推論回到觀察那一級。

## 外鍵涵蓋不到的寫入與規則

外鍵的檢查發生在寫入的那一刻，所以它的射程由「哪些寫入經過它」決定。

**既有的資料不在射程裡。** 補一條外鍵到已經有孤兒列的表上，這個動作本身會失敗：

```text
-- PostgreSQL 18，出貨表裡有一列的訂單編號是 777
ALTER TABLE 出貨 ADD FOREIGN KEY (訂單編號) REFERENCES 訂單(訂單編號);
ERROR:  insert or update on table "出貨" violates foreign key constraint "出貨_訂單編號_fkey"
DETAIL:  Key (訂單編號)=(777) is not present in table "訂單".
```

這則錯誤說的是資料裡已經有孤兒列，而約束加得上去的條件，是既有的每一列都已經滿足它。給有流量的大表補約束的完整順序在 [資料庫轉換實作](/backend/01-database/database-migration-playbook/) 的 「Type I：加約束（CHECK / FK / NOT NULL 收緊）」一節。

**同一個資料庫之外的指向不在射程裡。** 外鍵認的是另一張表，所以一個指向別的服務的識別碼、或指向物件儲存的一個鍵，資料庫無從檢查。這一類的完整性要在資料庫以外的層落地。應用程式碼內部的落點分幾層、各層違反規則時發生什麼，在 [不變式的強制層次](/ddd/invariant-enforcement-layers/)——那一篇的作用域是單一物件的規則。跨服務的一致性靠什麼維持（Saga、outbox 這一類），在 [Transaction 與一致性邊界](/backend/01-database/transaction-boundary/)，那一篇談的是一致性，參照完整性要落在哪一層它沒有單獨處理。

**不經過這條連線的寫入不在射程裡。** 這一點是 SQLite 把 `PRAGMA foreign_keys` 開關掛在每一條連線上的直接後果——約束的檢查掛在連線上的時候，遷移工具、測試框架與別人的第三方程式各自開自己的連線，而它們未必開了那個開關。射程因此不是「這個資料庫」，是「經過設定正確的連線的那些寫入」。

**業務規則不在射程裡。** 外鍵回答的問題只有一個：這個值在那張表裡找不找得到。「評價要在出貨之後」「同一張訂單只能退款一次」沒有這個形狀，而兩條規則各自落在不同的機制上：「同一張訂單只能退款一次」要比對退款表裡同一張訂單的其他列，寫成退款表訂單編號上的 `UNIQUE`；「評價要在出貨之後」要讀出貨表裡那張訂單的出貨時間，而 `CHECK` 只讀正要寫入的那一列、不接受子查詢，所以它落在觸發器或應用層。

業務規則那一項接上 [SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/) 的一個結論：「答案對不對」整條交不出去，而它底下的判斷能不能交給機器，看**判斷時要讀什麼**——在寫入那一刻就判得完、而且讀的範圍對得上某一種約束的，寫得成約束：`CHECK` 只讀正要寫入的那一筆，`UNIQUE` 讀同一欄已有的值，外鍵讀另一張表裡被指向的那一列。外鍵是約束裡讀得最遠的一種，而讀的範圍到被指向的那一列為止；「評價要在出貨之後」要讀另一張表的出貨日，同樣在寫入那一刻判得完，卻超出了每一種約束的範圍。

## 文字的宣告被執行的程度：外鍵、引擎補上的決定與 LEFT JOIN

一段文字說的話什麼時候會被執行，外鍵是答案最明確的那一端：它有生效的狀態可查，查得到之後保證就在。`LEFT JOIN` 的 `LEFT` 也宣告了一件事——預期有配不到的列——而引擎從不查證它，照著算完就結束，宣告落空時查詢照樣回正確答案；那一端在 [SQL.20 關鍵字的宣告與引擎的行為：宣告落空的形態與查證](/backend/01-database/sql/declared-intent-vs-behaviour/)。夾在中間的是引擎替文字補上的決定：外鍵在某一家被靜默丟掉就是其中一例，這一類差異按發聲的位置從當場報錯分到完全靜默、並依同一段 SQL 要跑在幾種引擎與設定的組合上，決定哪幾種要在寫的當下就處理掉，在 [SQL.19 引擎寬鬆度與可攜性：各家對同一組寫法的差異、分級與處理時機](/backend/01-database/sql/engine-leniency-and-portability/)。
