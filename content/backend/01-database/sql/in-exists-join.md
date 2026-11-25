---
title: "SQL.8 IN、EXISTS 與 JOIN：列數、可取用的欄位與 NULL 的處理"
date: 2026-08-31
description: "以成員判斷、存在性判斷與連接實作同一需求的列數差異、可取用欄位與相關子查詢的差別、選用的判斷標準，以及子查詢含 NULL 時 NOT IN 與 NOT EXISTS 的分岔"
aliases: ["/sql/in-exists-join/"]
weight: 9
tags: ["sql", "in", "exists", "join", "subquery", "semi-join"]
---

SQL 的 `IN`、`EXISTS` 與 `JOIN` 在存在性查詢中常回傳相同名單，但對應的關聯運算與結果列數各不相同。本篇以「找出下過單的顧客」並排三種寫法的列數差異，從求值階段銜接半連接與反連接，比較三者可取用的欄位範圍並給出選用依據；文末分析子查詢含 `NULL` 時 `NOT IN` 與 `NOT EXISTS` 的分岔。

尋找「在另一張表有對應紀錄的列」時，`IN`、`EXISTS` 與 `JOIN` 在許多資料集上會回傳相同結果，看似可以互換，但三者對應的關聯運算不同，產出的列數也未必一致。區分它們的核心依據是：除了確認對應列是否存在之外，輸出是否需要取用被比對資料表的欄位。

## 同一題用 IN、EXISTS 與 JOIN 各寫一次

在 [SQL 各篇共用的範例資料庫：一家小書店的顧客、訂單與評價表](/backend/01-database/sql/sample-bookstore-database/) 中，共有三位顧客，只有佳穎有兩張訂單。查詢目標是找出下過單的顧客。

使用 `IN` 檢查顧客編號是否存在於 [Subquery（子查詢）](/backend/01-database/sql/knowledge-cards/subquery/) 回傳的清單中：

```sql
SELECT 姓名 FROM 顧客 WHERE 顧客編號 IN (SELECT 顧客編號 FROM 訂單);
-- 佳穎
```

使用 `EXISTS` 檢查訂單表是否存在至少一筆屬於該顧客的紀錄（子查詢常寫成 `SELECT 1`，因 `EXISTS` 只檢驗子查詢是否產出至少一列、不取用投影值）：

```sql
SELECT 姓名 FROM 顧客
WHERE EXISTS (SELECT 1 FROM 訂單 WHERE 訂單.顧客編號 = 顧客.顧客編號);
-- 佳穎
```

使用 `JOIN` 把顧客表與訂單表合併成新的 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/)：

```sql
SELECT 顧客.姓名 FROM 顧客 JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號;
-- 佳穎、佳穎
```

針對同一項查詢目標，`IN` 與 `EXISTS` 回傳一列，`JOIN` 則回傳兩列，佳穎重複出現了兩次。

## 列數：條件與連接的差別

`IN` 與 `EXISTS` 寫在 `WHERE` 子句中，屬於列層級的篩選條件。篩選條件對來源表的每一列只做保留或排除，因此顧客表原有三列，通過篩選後最多只會剩下三列，絕不會增加列數。

`JOIN` 寫在 `FROM` 子句中，參與新關係的建構。佳穎有兩張訂單，逐列配對後她在連接結果裡便出現兩次（見 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)）。必須額外加上 `DISTINCT`，結果才會與 `IN`、`EXISTS` 相同：

```sql
SELECT DISTINCT 顧客.姓名 FROM 顧客 JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號;
-- 佳穎
```

撰寫 `JOIN` 後需要補上 `DISTINCT` 來消除重複，本身就是一個訊號：該查詢只需要確認對應紀錄是否存在，`JOIN` 卻額外執行了一對多的展開。這類情境下，`IN` 或 `EXISTS` 更直接表達查詢意圖，因為它們不會產生重複列。

在 [Relational Algebra（關聯代數）](/backend/01-database/sql/knowledge-cards/relational-algebra/) 中，`IN` 與 `EXISTS` 對應的運算是半連接（semi-join）：比對兩張表後只保留左側表的列，每列至多出現一次。否定式的 `NOT EXISTS` 保留左側表配不到任何對應列的紀錄，稱為反連接（anti-join），完整定義見 [Semi-join 與 Anti-join（半連接與反連接）](/backend/01-database/sql/knowledge-cards/semi-join-and-anti-join/)。

## 可取用的欄位：被比對的資料表是否位於 FROM 中

當需求改成「列出每位顧客的訂單金額」，結果必須包含訂單表的欄位，`JOIN` 是最直接的寫法：

```sql
SELECT 顧客.姓名, 訂單.金額 FROM 顧客 JOIN 訂單 ON 訂單.顧客編號 = 顧客.顧客編號;
-- 佳穎 300 / 佳穎 500
```

若改用 `IN` 並在 `SELECT` 引用訂單表的欄位，引擎會直接報錯：

```sql
SELECT 姓名, 訂單.金額 FROM 顧客 WHERE 顧客編號 IN (SELECT 顧客編號 FROM 訂單);
-- SQLite: no such column: 訂單.金額
-- DuckDB: Referenced table "訂單" not found!
```

錯誤訊息指出 `訂單` 不在主查詢的 `FROM` 子句中。`WHERE` 裡的子查詢是獨立區塊，只將比對用的值清單交回外層，訂單表並未併入外層關係，因此外層無法存取它的任何欄位。

若只需要從另一張表取出單一純量值，還可以在 `SELECT` 裡撰寫引用外層欄位的相關子查詢（correlated subquery，見 [Subquery（子查詢）](/backend/01-database/sql/knowledge-cards/subquery/)）。依子查詢是否引用外層欄位可區分兩種結構：前面「下過單的顧客」的 `IN` 子查詢未引用外層欄位，可單獨執行，稱為獨立子查詢；`EXISTS` 子查詢引用了外層的 `顧客.顧客編號`，脫離外層便無法執行，稱為相關子查詢。以下為寫在 `SELECT` 裡的相關純量子查詢：

```sql
SELECT 姓名, (SELECT 金額 FROM 訂單 WHERE 訂單.顧客編號 = 顧客.顧客編號
              ORDER BY 訂單編號 LIMIT 1) FROM 顧客;
-- 佳穎 300 / 宗翰 NULL / 雅文 NULL
```

純量相關子查詢每次只能回傳單一欄位的單一值，需要多欄或多列時仍須使用 `JOIN`，且其逐列執行的代價須透過執行計畫確認（見 [SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/)）。

回到列出每位顧客各筆訂單金額的需求，結果中佳穎出現兩次是正確的，因為需求本身就是每張訂單佔一列，列數依訂單展開符合目標。

## 選用的判斷標準：是否需要輸出被比對資料表的欄位

選用三種寫法的判斷標準是查詢是否需要輸出被比對資料表的欄位。需要該表欄位時使用 `JOIN`，唯有它能將該表帶入 `FROM`，同時須檢查連接後的列數變化——後續若接聚合函數，`sum` 與 `count` 會算在展開後的列上（各種聚合的處理方式見 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)）。

僅需確認對應紀錄是否存在時，選用 `IN` 或 `EXISTS`。這兩種寫法屬於篩選條件，只保留或排除來源列，意圖比 `JOIN` 加 `DISTINCT` 更明確。至於哪一種執行速度較快，取決於資料分布與 [Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/) 配置：[SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/) 實測分組、自連接與 `EXISTS` 在有無索引下的耗時，加上索引後 `EXISTS` 從最慢縮短至與分組同一量級。若由應用程式將動態參數清單直接展開成 `IN (?, ?, ...)`，另須留意跨引擎語法與參數上限差異：空清單 `IN ()` 在 SQLite 合法且恆假，在 PostgreSQL 則直接語法報錯，超大清單亦受綁定參數上限限制（須改用暫存表或陣列連接）。在多角色權限控制（RBAC）的非同步背景任務認領查詢裡，同一位使用者可能同時擁有多個具備相同權限的角色，使用 `EXISTS` 表達存在性條件能讓結果列數受限於任務表，避免因角色重疊而膨脹（實測對照見 [1.21 資安、權限與合規決定的資料表設計：軟刪除與唯一約束、多租戶子表與列級安全性、RBAC 與非同步任務複查、存取憑證撤銷與優先序、個資分離與不可變稽核、角色預設權限與逾時護欄](/backend/01-database/security-and-compliance-schema-decisions/)）。

## IN 與 EXISTS 的分岔：子查詢含 NULL 時的否定式

作為頂層 `WHERE` 的等值存在性條件時，肯定式的 `IN` 與 `EXISTS` 語意等價；否定式的 `NOT IN` 與 `NOT EXISTS` 則會在資料出現 [NULL（空值）](/backend/01-database/sql/knowledge-cards/null/) 時分岔。

只要子查詢回傳的清單混入任何一個 `NULL`，`NOT IN` 的評估結果就永遠不會為真：出現在清單中的列判為假，未出現在清單中的列因與 `NULL` 比較而判為未知，兩種列全數被 `WHERE` 排除，整段查詢靜默回傳零列；`NOT EXISTS` 則不受影響。在共用資料新增一筆顧客編號為 `NULL` 的訂單即可驗證：

```sql
INSERT INTO 訂單 VALUES (103, NULL, '2026-03-20', 100);   -- 訂單 103 沒有填顧客編號

SELECT 姓名 FROM 顧客 WHERE 顧客編號 NOT IN (SELECT 顧客編號 FROM 訂單);
-- 共用資料：宗翰、雅文
-- 多了訂單 103 之後：零列，不報錯（子查詢交出的清單是 1、1、NULL）

SELECT 姓名 FROM 顧客
WHERE NOT EXISTS (SELECT 1 FROM 訂單 WHERE 訂單.顧客編號 = 顧客.顧客編號);
-- 共用資料與多了訂單 103 之後都是：宗翰、雅文
```

三值邏輯的完整展開與 `NOT EXISTS` 在不等號比較下的邊界，見 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)。由於零列結果與「確實沒有符合資料」在外觀上完全相同，這類錯誤只能靠撰寫者預先掌握規則避免；依 [SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/) 的成因分類，這屬於誤解語意模型，改寫正確後即可永久消除。

因此頂層等值條件的肯定式 `IN` 與 `EXISTS` 語意等價，可依可讀性選用；否定式則因 `NOT IN` 在子查詢清單含 `NULL` 時整批歸零，且當外層比對欄位為 `NULL` 時即使子查詢欄具 `NOT NULL` 仍會靜默濾除該列（`NOT EXISTS` 則會保留），唯有**外層比對欄位與子查詢欄位兩側皆**具備已生效的 `NOT NULL` [Constraint（約束）](/backend/01-database/sql/knowledge-cards/constraint/)，兩者才語意等價。此外，在 PostgreSQL 18 及更早版本中，`NOT IN` 因三值邏輯限制無法轉為可溢寫磁碟的 `Hash Anti Join`，子查詢結果超過 `work_mem` 時容易退化為逐列重掃。僅觀察當下資料不含 `NULL` 不構成保證，因為查詢將持續執行於未來寫入的新資料。

語意等價時優先依可讀性選擇的原則，適用範圍涵蓋整個查詢撰寫階段。[SQL.22 可讀性與執行代價：兩者一致與分岔的情形](/backend/01-database/sql/readable-and-fast-mostly-align/) 進一步實測了哪些寫法差異不增加執行代價，以及哪些情形會使可讀性與效能分岔。
