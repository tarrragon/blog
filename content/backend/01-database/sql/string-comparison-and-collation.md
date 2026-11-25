---
title: "SQL.15 字串比較與 collation：相等、排序、LIKE 與索引可用性"
date: 2026-09-02
description: "同一段字串等值條件在各家引擎命中不同列的原因、SQLite 中 LIKE 與等號比較規則分岔的行為、collation 對排序與分頁的影響、索引與條件比較規則對齊的方式，以及規則宣告在各層的涵蓋範圍"
aliases: ["/sql/string-comparison-and-collation/"]
weight: 16
tags: ["sql", "collation", "like", "string", "index", "portability"]
---

字串比較規則（collation）決定資料庫如何判定字串相等與先後順序，影響等值條件、`LIKE`、排序與索引可用性。本篇涵蓋以下面向：

- SQLite、PostgreSQL 與 MySQL 在預設 collation 下執行同一段等值條件的輸出差異。
- SQLite 中 `LIKE` 與 `=` 套用不同規則的原因與統一作法。
- 三家引擎對同一批字串的排序順序，以及不區分大小寫的比較規則對分頁全序的影響。
- 索引比較規則與查詢條件不一致導致全表掃描的成因與修法。
- 將規則宣告於資料庫、資料表、欄位、查詢條件或寫入正規化等不同層級的涵蓋範圍。

本篇處理字串**值**在比較時套用的規則，與物件**名稱**的大小寫處理相互獨立：PostgreSQL 會將未加引號的表名摺疊為小寫，但預設不會將字串值 `'Anna'` 摺疊為 `'anna'`。表名與欄名的規則見 [SQL.14 識別字的規則：各家的大小寫摺疊、引號與保留字](/backend/01-database/sql/identifier-rules/)。

當比較的兩側皆為字串型別時，兩個字串是否相等由 **collation** 決定。資料型別本身也會影響比較行為：例如 PostgreSQL 18 上 `'a '::char(2) = 'a'` 為真，而 `'a '::text = 'a'::text` 為假，原因在於定長型別 `char(n)` 比較時會忽略尾隨空白。以下討論限定在兩側皆為變長字串的情形。collation 定義在資料庫、資料表或欄位層級，規定兩個字串是否區分大小寫、是否區分重音符號，以及字元之間的排列先後。由於這條規則未寫在查詢文字中，同一段 `WHERE 姓名 = 'anna'` 在不同引擎或資料庫設定下會命中不同的列。

以下實測使用的顧客表共有五列：`Anna`、`anna`、`ANNA`、`Ánna`、`佳穎`。

## 等值比較在各家引擎的預設 collation 下命中的列

三家引擎的預設 collation 對大小寫與重音的處理不同，執行同一段等值查詢得到的列集如下：

```text
WHERE 姓名 = 'anna'

SQLite 3.51        anna
PostgreSQL 18      anna
MySQL 8.4          Anna, anna, ANNA, Ánna
```

MySQL 8.4 的預設 collation 是 `utf8mb4_0900_ai_ci`，其中 `ai` 代表 accent-insensitive（不區分重音）、`ci` 代表 case-insensitive（不區分大小寫），因此 `Ánna` 與 `anna` 視為相等。SQLite 與 PostgreSQL 預設同時區分大小寫與重音，只命中逐字相同的 `anna`。

這三組輸出各自符合所屬引擎的規則定義，因為查詢文字並未指定比較規則。若將原本在 MySQL 上運作的帳號比對查詢遷移至 PostgreSQL，等值比較會靜默轉為區分大小寫，查詢照常執行且不報錯，但比對行為已改變。

## SQLite 中 LIKE 與等號套用的不同比較規則

`LIKE` 與 `=` 同屬字串比較運算子，但在 SQLite 中兩者預設套用不同的比較規則：

```text
                    SQLite 3.51        PostgreSQL 18      MySQL 8.4
= 'anna'            anna               anna               Anna, anna, ANNA, Ánna
LIKE 'anna'         Anna, anna, ANNA   anna               Anna, anna, ANNA, Ánna
```

PostgreSQL 與 MySQL 的兩列結果一致，SQLite 則出現分岔：SQLite 的 `=` 逐位元組比較，而 `LIKE` 預設對 ASCII 字母不區分大小寫。在 SQLite 中為了加上 `%` 萬用字元而把 `=` 改成 `LIKE`，會連帶切換比較規則而不產生任何提示。

SQLite `LIKE` 的大小寫摺疊僅限於 ASCII 的 A 到 Z 二十六個字母：對同一張表執行 `LIKE 'ánna'` 回傳零列，`Ánna` 不被視為相等。因此 SQLite 的 `LIKE` 預設規則精確來說是「ASCII A–Z 摺疊、其餘字元逐位元組比對」，而非全面不區分大小寫。

若要在 SQLite 統一兩者行為，設定 `PRAGMA case_sensitive_like = ON` 可讓 `LIKE` 改為與 `=` 一致的逐位元組比較；反之，在等值條件加上 `COLLATE NOCASE` 可讓 `=` 改採不區分 ASCII 大小寫的規則。無論選擇哪一種，將規則寫明可讓閱讀查詢的人不需先猜測執行引擎即可確認比對語意。

## collation 規定的排序先後

collation 除了決定相等，也決定 `ORDER BY` 的排列次序。對同一批五個名字執行 `ORDER BY 姓名`，三家引擎排出三種不同順序：

```text
ORDER BY 姓名

SQLite 3.51        ANNA, Anna, anna, Ánna, 佳穎
PostgreSQL 18      anna, Anna, ANNA, Ánna, 佳穎
MySQL 8.4          Anna, anna, ANNA, Ánna, 佳穎
```

SQLite 採位元組碼位排序，大寫字母碼位小於小寫字母，因此 `ANNA` 排在最前面。PostgreSQL 依建庫時指定的 collation 排序，實測環境為 `en_US.utf8`（可執行 `SELECT datcollate FROM pg_database` 查詢），依語言規則把同字母大小寫歸為同一群組再決定先後。在 PostgreSQL 改用逐位元組比較的 `C` collation 時，輸出即與 SQLite 相同：

```sql
-- PostgreSQL 18，資料庫的 collation 是 en_US.utf8
SELECT 姓名 FROM 顧客 ORDER BY 姓名;
-- anna, Anna, ANNA, Ánna, 佳穎
SELECT 姓名 FROM 顧客 ORDER BY 姓名 COLLATE "C";
-- ANNA, Anna, anna, Ánna, 佳穎（與 SQLite 的預設順序相同）
```

同一家引擎與同一批資料，只更換 collation 就能改變列序。

MySQL 的輸出反映另一層意義：在 `utf8mb4_0900_ai_ci` 規則下，四個 A 開頭的名字彼此相等，collation 未規定它們之間的先後，因此 `ORDER BY 姓名` 印出的只是進表順序。改由 `GROUP_CONCAT` 帶相同 `ORDER BY` 取出時，這四個名字的順序隨即反轉：

```sql
-- MySQL 8.4，同一張表、同一批資料
SELECT 姓名 FROM 顧客 ORDER BY 姓名;
-- Anna, anna, ANNA, Ánna, 佳穎（進表的順序）
SELECT GROUP_CONCAT(姓名 ORDER BY 姓名) FROM 顧客;
-- Ánna,ANNA,anna,Anna,佳穎（四個 A 開頭的名字倒過來，佳穎仍在最後）
```

兩次輸出都合乎規格，因為這四個值在該 collation 下屬於同分列。在分頁情境裡，忽略大小寫與重音的 collation 會讓原本看似唯一的字串排序鍵出現同分列，進而導致跨頁重複與遺漏（全序條件與決勝鍵設計見 [SQL.12 分頁的排序鍵與接續標記：同分的列、全序與 OFFSET 的代價](/backend/01-database/sql/pagination-needs-a-total-order/)）。

## 索引的比較規則與條件的比較規則

[Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/) 依特定比較規則排列鍵值，因此只能服務採用同一條規則的查詢條件。當索引與條件的規則不符時，小表因引擎本來就走全表掃描而難以觀察到差異；資料成長後，前綴搜尋會出現明顯延遲。以下在二十萬列同結構表上觀測 SQLite 的執行計畫（單一索引 `ixn` 採預設逐位元組規則）：

```text
CREATE INDEX ixn ON 顧客(姓名);            -- 預設規則，逐位元組

WHERE 姓名 = 'anna'          SEARCH ... (姓名=?)      查找
WHERE lower(姓名) = 'anna'   SCAN                     整段掃過
WHERE 姓名 LIKE 'ann%'       SCAN                     整段掃過
```

第二行無法使用索引，是因為欄位被 `lower()` 函式包住，屬於條件形狀不合（見 [Sargable（可走索引的條件形狀）](/backend/01-database/sql/knowledge-cards/sargable/)）。第三行則是規則不符：前綴比對理論上能轉為索引範圍查找，但 SQLite 的 `LIKE` 預設不區分大小寫，而索引 `ixn` 依位元組序建立，規則對不上導致引擎放棄索引。無論調整條件規則或調整索引規則，都能恢復索引範圍查找，但兩者回傳的結果不同：

```sql
-- 改條件的規則：LIKE 改成分大小寫，回到位元組規則
PRAGMA case_sensitive_like = ON;
EXPLAIN QUERY PLAN SELECT * FROM 顧客 WHERE 姓名 LIKE 'ann%';
-- SEARCH ... (姓名>? AND 姓名<?)
-- 本篇五列的顧客表上回 anna

-- 改索引的規則：LIKE 維持預設的不分大小寫，另建一個按摺疊規則排的索引；SQLite 的索引一定要取名字
PRAGMA case_sensitive_like = OFF;
CREATE INDEX ixn_nocase ON 顧客(姓名 COLLATE NOCASE);
EXPLAIN QUERY PLAN SELECT * FROM 顧客 WHERE 姓名 LIKE 'ann%';
-- SEARCH ... (姓名>? AND 姓名<?)
-- 本篇五列的顧客表上回 Anna, anna, ANNA
```

PostgreSQL 在 `en_US.utf8` 預設 collation 下也會發生同樣的現象：`ann` 前綴在語言排序中不對應單一連續區間，`LIKE 'ann%'` 因而退回逐列過濾：

```text
WHERE 姓名 = 'anna'          Index Cond: (姓名 = 'anna')          查找
WHERE lower(姓名) = 'anna'   Filter: (lower(姓名) = 'anna')       逐列過濾
WHERE 姓名 LIKE 'ann%'       Filter: (姓名 ~~ 'ann%')             逐列過濾
```

PostgreSQL 的修法同樣是讓索引與條件規則一致：前綴搜尋建立 `text_pattern_ops` 索引以支援逐字元範圍查找，`lower(姓名)` 則建立運算式索引：

```sql
-- 前綴搜尋：text_pattern_ops 讓這個索引逐字元比較，不照資料庫的 en_US.utf8
CREATE INDEX ON 顧客(姓名 text_pattern_ops);
EXPLAIN SELECT * FROM 顧客 WHERE 姓名 LIKE 'ann%';
-- Index Cond: (姓名 ~>=~ 'ann' AND 姓名 ~<~ 'ano')：前綴翻成一段範圍

-- 欄位被函式包住：索引直接建在 lower(姓名) 上
CREATE INDEX ON 顧客(lower(姓名));
EXPLAIN SELECT * FROM 顧客 WHERE lower(姓名) = 'anna';
-- Index Cond: (lower(姓名) = 'anna')
```

比較規則一致只是索引能被使用的條件之一；此外條件形狀必須符合 Sargable，且最佳化器還會依條件預估篩出的列數比例決定是否採用索引（見 [Cardinality 與 Selectivity（基數與選擇率）](/backend/01-database/sql/knowledge-cards/cardinality-and-selectivity/)）。

## 將 collation 宣告在資料庫、表、欄位或條件上的涵蓋範圍

在單一引擎與單一資料庫環境下，預設 collation 往往隱而不見；當系統遷移至其他引擎、移至不同預設規則的新資料庫，或個別欄位被單獨指定規則時，行為差異才會顯現。需要跨引擎運作時，collation 是必須盤點的預設差異之一（識別字規則見 [SQL.14 識別字的規則：各家的大小寫摺疊、引號與保留字](/backend/01-database/sql/identifier-rules/)，跨引擎預設差異的分級與對策見 [SQL.19 引擎寬鬆度與可攜性：各家對同一組寫法的差異、分級與處理時機](/backend/01-database/sql/engine-leniency-and-portability/)）。

collation 可宣告在資料庫、資料表與欄位三層，涵蓋範圍由外而內、優先權由內覆蓋外：建庫時指定的規則作為所有未另行宣告欄位的預設，建表時指定的規則覆蓋資料庫層，欄位上宣告的規則覆蓋資料表層。因此確認某欄實際套用的規則時，須從欄位定義往外查至資料表與資料庫層，直到找到最內層的顯式設定。

**宣告在欄位層**（例如 `姓名 VARCHAR(50) COLLATE utf8mb4_0900_as_cs`，其中 `as_cs` 代表區分重音與大小寫）最貼近資料語意，後續所有查詢與索引都會自動套用該規則。**宣告在查詢條件層**（例如 `WHERE 姓名 = 'anna' COLLATE NOCASE`）只作用於該單句查詢，適合例外性的逐字比對需求，代價是無法使用依欄位預設規則建立的索引。**寫入時正規化**則不依賴 collation 設定：在寫入資料時將字串轉為小寫並另存一欄，查詢與索引皆對該正規化欄位執行單純的等值比對。跨引擎帳號比對需求常採這種作法，把比較規則固定在寫入階段，使讀取與索引在不同引擎上行為一致。

這項選擇與 [Constraint（約束）](/backend/01-database/sql/knowledge-cards/constraint/) 依循同一原則：需要對往後所有查詢一致生效的規則，應固定在資料表結構上，而非仰賴每一段查詢各自補寫。兩者的差別在於約束在寫入階段攔截違法資料，collation 則在讀取與比較階段定義相等與排序。
