---
title: "1.15 外鍵寫下保證，各家引擎決定它生不生效"
date: 2026-09-02
description: "外鍵保證什麼、宣告與生效在哪幾個位置分開，以及有了它之後查詢可以省掉哪一步"
weight: 15
tags: ["sql", "foreign-key", "constraint", "referential-integrity", "ddl"]
---

外鍵是一條寫在表結構上的宣告：這一欄的值，在另一張表裡找得到對應的那一列。資料庫在每一次寫入時檢查它，所以它涵蓋的是整張表，以及往後的每一筆資料。這條保證有一個名字叫**參照完整性**——「參照」指一欄指向另一張表的某一列，「完整」指那個指向落得到實處。

本分類把這個語言拆成三支，本篇屬於問「文字之外還有誰在決定」的那一支（[章節](/sql/#章節)）。同一支的其餘各篇寫識別字、權限與最佳化器怎麼在查詢的文字之外介入，而這一方介入得更早：它決定資料能長成什麼樣，於是決定一段查詢會遇到什麼。

本篇走完這條保證的全貌：它擋下哪些寫入、什麼時候才算生效、生效之後查詢省掉哪一步、父列消失時它怎麼維持，以及它涵蓋不到的地方。這條約束該不該加是設計那一側的取捨，本篇只處理加了之後語言這一側發生什麼。

本篇的表在[共用資料庫](/sql/#各篇共用的範例資料庫)的三張表上重建，差別是這一次把約束寫進結構裡。指不到父列的那一列，下文叫**孤兒列**。

## 一條宣告擋下兩個方向的寫入

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

兩則訊息裡的約束名不同。第一則是評價表自己那條，第二則是訂單表那條——刪顧客這個動作在訂單表上觸發檢查，所以擋下它的約束掛在訂單表上。**外鍵的錯誤訊息因此要分兩層讀**：訊息指名的表，未必是剛才那句 SQL 寫到的表。

有一個值兩邊都放行：`NULL`。外鍵讀作「這一欄有值的時候，那個值找得到對應」，所以空著的那一欄不參與檢查。訂單編號留空的評價插得進去，而它是一則指不到任何訂單的評價——[1.11](/sql/well-formed-is-not-correct/) 第三種錯法要的正是這樣一列。要連這一種也擋掉，欄位上另外要有 `NOT NULL`。

## 宣告寫下了，生效是另一回事

同一段 `REFERENCES` 送進不同的引擎，會落在不同的狀態。宣告與生效在幾個位置各自分開過一次，而它們留下的訊號強度差很多。

**連線的設定**。SQLite 認得這段語法、也把約束記進結構裡，而檢查預設關閉，開關掛在每一條連線上：

```text
-- SQLite 3.51，未開 PRAGMA
INSERT INTO 評價 VALUES (9003, 999, 4);   -- 成功，孤兒列進來了

-- 同一個檔案，開了之後
PRAGMA foreign_keys = ON;
INSERT INTO 評價 VALUES (9004, 888, 4);
Error: stepping, FOREIGN KEY constraint failed (19)
```

開關打開之後，先前那筆孤兒列仍然在表裡——檢查發生在寫入的當下，對已經在裡面的資料沒有追溯力。查它的指令是 `PRAGMA foreign_key_check`，回的是違反者所在的表、那一列的 rowid、被指向的表，以及那是表上的第幾條外鍵。

**約束自己的狀態**。PostgreSQL 的 `NOT VALID` 讓一條外鍵掛上去而略過既有的列，往後的寫入照常檢查。這個狀態是給大表補約束用的（既有列的檢查另用 `VALIDATE CONSTRAINT` 分開跑，避免長時間鎖表），而它留下的中間態是：表上有這條約束，表裡有違反它的列。

**語法的形態**。MySQL 認得欄位層的 `REFERENCES`，解析完把它丟掉，不留下任何約束，`SHOW WARNINGS` 也是空的：

```text
-- MySQL 8.4，訂單.顧客編號 寫了欄位層的 REFERENCES
INSERT INTO 訂單 VALUES (101, 999, 300);       -- 成功
SELECT CONSTRAINT_NAME FROM information_schema.REFERENTIAL_CONSTRAINTS
 WHERE CONSTRAINT_SCHEMA = 't';                -- 0 列

-- 同一件事改寫成表層的 FOREIGN KEY
ERROR 1452 (23000): Cannot add or update a child row: a foreign key constraint fails
```

同一段文字在 PostgreSQL 與 SQLite 底下建得出約束，在 MySQL 底下建不出來，而 MySQL 在建表時沒有給任何警告。

**表的儲存引擎**。同一家 MySQL 裡還有第二條讓宣告消失的路：改用表層的 `FOREIGN KEY` 寫法之後，把表建在 MyISAM 上，語法照收、警告照樣是空的，而 `information_schema.REFERENTIAL_CONSTRAINTS` 仍然回零列，指不到顧客的訂單插得進去。這兩條路的差別在於要改哪裡才修得好——一條要改寫法，另一條要換儲存引擎。

這幾個位置的共同點是**外鍵只在寫入的那一刻現身**：查詢的文字裡沒有一個字提到約束，讀的時候也沒有差別。所以「這條保證在不在」要另外查，而查法在系統目錄那一側——PostgreSQL 用 `information_schema.table_constraints`、MySQL 用 `information_schema.REFERENTIAL_CONSTRAINTS`、SQLite 用 `PRAGMA foreign_key_list(表名)`。**建表語句裡看得到宣告，這幾張表裡看得到的才是生效的那些。**

生效之後還有一個「什麼時候檢查」的維度。預設是每一句寫入當場檢查，而 PostgreSQL 的 `DEFERRABLE INITIALLY DEFERRED` 把檢查推到交易提交的那一刻——中間的每一句都通過，`COMMIT` 才回 `violates foreign key constraint`。互相指向的兩張表要一起寫入時需要這個推遲，代價是錯誤浮現的位置離寫錯的那一句遠了一整個交易。

## 生效之後，查詢可以少做哪些事

一條保證的價值落在它讓哪些判斷不必再做。同一組表的兩個版本擺在一起看得清楚：一邊的 `訂單.顧客編號` 帶著 `NOT NULL REFERENCES 顧客(顧客編號)`，另一邊什麼都沒有，而沒有約束的那一版收了一張顧客編號留空的訂單。

```text
-- SQLite 3.51
                              有約束    沒有約束
內連接之後的列數 / 訂單列數    2 / 2      2 / 3
沒下過單的顧客（用 NOT IN）    宗翰、雅文  0 列
```

沒有約束的那一邊，兩段查詢各自出了一種錯，而兩種都不報錯。內連接掉了一列——顧客編號是空的那張訂單配不到任何顧客，於是它從結果裡消失，而總數看起來仍然像一份完整的訂單清單。`NOT IN` 整段回空集合——子查詢交出的那一欄含一個 [`NULL`](/sql/knowledge-cards/null/)，展開之後那一項的真值是未知，整串連乘因此判不出真。兩種錯誤的完整推導在 [1.6](/sql/join-changes-rows-and-nulls/) 的「一列可以變成好幾列」與「NOT IN 碰到一個 NULL 就整個失效」兩節。

有約束的那一邊，兩段查詢都對，而它們的寫法一個字都沒改。**改變的是那兩個判斷的前提從觀察變成了保證**：翻遍現在的訂單表沒有一筆顧客編號是空的，只證明此刻如此；`NOT NULL` 證明的是往後也不會有，而查詢要活得比這一批資料久（[Constraint](/sql/knowledge-cards/constraint/)）。

這裡有兩條約束在做不同的事，分開記各自買到什麼。**`NOT NULL` 買的是「這一欄有值」**，它管掉上面兩種錯——沒有空缺，內連接就掉不了列，`NOT IN` 也碰不到那個 `NULL`。**外鍵買的是「這個值指得到人」**，它管的是另一批推論：連過去必定配得到一列、子表的每一列都能歸屬到某個父列、`JOIN` 與 `LEFT JOIN` 在這個方向上回同一批列。兩條都在的時候，「這個連接會掉列嗎」這個問題不必查資料就答得出來。

這些推論的代價落在寫入那一側：每插進一列，資料庫要去父表確認那個值在不在，所以外鍵是拿寫入的工作換讀取的保證。這筆交換要用量測來判，而讀代價的工具在 [1.14](/sql/cost-lives-in-the-plan/)。

## 父列被刪掉的時候，子列的去向要在宣告裡說

擋下刪除是預設，而它把問題丟回給寫入的那一方：顧客要停用了，他的訂單怎麼辦。這個決定寫在外鍵的宣告裡，跟著約束走而不是跟著每次刪除走。

```sql
訂單編號 INT REFERENCES 訂單(訂單編號) ON DELETE CASCADE   -- 子列一起刪掉
訂單編號 INT REFERENCES 訂單(訂單編號) ON DELETE SET NULL  -- 子列留著，這一欄清空
```

在 PostgreSQL 18 上刪掉訂單 102：`CASCADE` 那張表的對應列跟著消失，`SET NULL` 那張表的列留著而訂單編號變成空的。預設的行為（`NO ACTION`）則是整個刪除被擋下。

**選哪一種由子列離開父列之後還有沒有意義決定。** 一則評價離開它評的那張訂單之後說不出在評什麼，所以它適合跟著走；一筆出貨紀錄即使訂單被撤銷仍然是發生過的事實，清空指向比刪掉它更貼近實情。而 `CASCADE` 的射程要先算清楚——它會沿著外鍵一路傳下去，刪一個顧客可能連帶刪掉他的訂單、那些訂單的評價，以及再往下的每一層。

`SET NULL` 與同一欄上的 `NOT NULL` 要求的條件互相排斥，而建表的時候兩者並存不會被擋下。PostgreSQL 18 收下這張表，衝突到刪除父列的那一刻才浮現，訊息指的是那個清空的動作違反了 `NOT NULL`：

```text
ERROR:  null value in column "訂單編號" of relation "評價" violates not-null constraint
DETAIL:  Failing row contains (9001, null).
CONTEXT:  SQL statement "UPDATE ONLY "public"."評價" SET "訂單編號" = NULL WHERE ..."
```

**這是本篇那條分界的又一個實例：宣告收下了，做得到做不到要等到執行的那一刻。** 而 `NOT NULL` 買掉的正是掉列與 `NOT IN` 那兩類錯誤，所以這裡要選一邊——留下子列的代價是那一欄重新可能為空，關於它的推論回到觀察那一級。

## 這條保證涵蓋不到的地方

外鍵的檢查發生在寫入的那一刻，所以它的射程由「哪些寫入經過它」決定。

**既有的資料不在射程裡。** 補一條外鍵到已經有孤兒列的表上，這個動作本身會失敗：

```text
-- PostgreSQL 18，出貨表裡有一列的訂單編號是 777
ALTER TABLE 出貨 ADD FOREIGN KEY (訂單編號) REFERENCES 訂單(訂單編號);
ERROR:  insert or update on table "出貨" violates foreign key constraint "出貨_訂單編號_fkey"
DETAIL:  Key (訂單編號)=(777) is not present in table "訂單".
```

這則錯誤說的是資料裡已經有違反它的列，而約束加得上去的條件，是既有的每一列都已經滿足它。給有流量的大表補約束的完整順序在 [資料庫轉換實作](/backend/01-database/database-migration-playbook/)。

**同一個資料庫之外的指向不在射程裡。** 外鍵認的是另一張表，所以一個指向別的服務的識別碼、或指向物件儲存的一個鍵，資料庫無從檢查。這一類的完整性要在別的層落地，各層各擋得住誰在 [不變式的強制層選擇](/ddd/invariant-enforcement-layers/)。

**業務規則不在射程裡。** 外鍵回答的問題只有一個：這個值在那張表裡找不找得到。「評價要在出貨之後」「同一張訂單只能退款一次」這一類的規則裡沒有這個形狀，`CHECK` 與應用層各自接住其中一部分。

第三項連著上一支的分工：[1.11](/sql/well-formed-is-not-correct/) 說「答案對不對」這一層有一部分判準交得出去，而交得出去的界線落在**判斷需要什麼**——在寫入的那一刻用該筆資料本身、或它指向的那一列就判得完的，寫得成約束。外鍵是這條界線上最靠外的那一種：它要讀另一張表的內容才判得出來，而讀的範圍到那一列為止。

## 換掉其中一項就走到另一篇

本篇建立的模型裡有幾件事可以各自換掉：這條宣告生不生效、它宣告的是哪一種保證、被指向的那一側消失時怎麼辦，以及父表與子表是不是同一張表。

**把「引擎每次寫入都查證的宣告」換成「引擎從不查證的宣告」**：`LEFT JOIN` 的 `LEFT` 也宣告了一件事——預期有配不到的列——而引擎照著算完就結束，宣告落空時查詢仍然回正確答案。[1.16 關鍵字宣告意圖，引擎只執行行為](/sql/declared-intent-vs-behaviour/) 把這一類收在一起，並給一個查證宣告的動作。兩篇合起來是同一個問題的兩邊：一段文字說的話，什麼時候會被執行。

**把外鍵換成別種約束**：`NOT NULL`、`UNIQUE`、`CHECK` 各保證不同的事，而它們共用同一條性質——豁免的條件必須是一條約束而不是一次觀察。[Constraint（約束）](/sql/knowledge-cards/constraint/) 寫五種各自買到什麼，以及為什麼它們住在 [DDL](/sql/knowledge-cards/ddl-dml/) 那一側。

**把「保證在」換成「保證不在」**：那時連接可能掉列、`NOT IN` 可能整段失效，而兩者都不報錯。[1.6 連接產出的是新的關係](/sql/join-changes-rows-and-nulls/) 寫這兩種錯誤的機制，以及列數膨脹怎麼讓後續的聚合算出太大的數字。

**把父表與子表換成同一張表**：外鍵指得回自己所在的那張表，於是一列的上層是同一張表的另一列，而最頂層那一列的那一欄留空。這個結構的查詢要把同一張表擺兩次，而兩次出現需要各自的名字。[1.7 查詢裡的表是一個具名的出現](/sql/table-occurrence-and-alias/) 寫自連接為什麼非取名不可，並把它處理的關係分成三種形態。

**把「這條約束該不該加」當成問題**：那是設計的決定，在強制完整性與演進自由度之間取捨，而正式核心域與跨域整合的答案不同。[Schema Design](/backend/01-database/schema-design/) 的主鍵與外鍵策略那一段寫這個取捨，並把「宣告不等於執法」列成設計時要先確認的一項。
