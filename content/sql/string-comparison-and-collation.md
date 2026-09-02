---
title: "1.14 字串的相等與大小由 collation 決定"
date: 2026-09-02
description: "同一段等值條件在各家回不同的列的原因、LIKE 與等號何時分岔，以及索引與條件的比較規則要對得上"
weight: 14
tags: ["sql", "collation", "like", "string", "index", "portability"]
---

兩個字串相不相等，答案由一條叫 **collation** 的規則給出——前提是兩邊都是字串型別。型別先發言：PostgreSQL 18 上 `'a '::char(2) = 'a'` 為真而 `'a '::text = 'a'::text` 為假，同一條 collation，差別在 `char(n)` 的等號自己會剝掉尾隨空白。下文談的都是兩邊都是變長字串的情形。collation 是掛在資料庫、表或欄位上的一份比較規則，它規定兩個字串怎麼判相等、以及誰排在前面——大小寫算不算差異、重音符號算不算差異、字元的先後怎麼定。這條規則不在查詢的文字裡，所以同一段 `WHERE 姓名 = 'anna'` 在不同的地方會回不同的列。

大小寫這件事在 SQL 裡落在兩個彼此獨立的層。[1.13](/sql/identifier-rules/) 處理的是**名字**送進引擎會被怎麼摺疊，這一篇處理的是**值**被拿去比較時套的是哪一把尺。兩層的規則互不影響：PostgreSQL 把沒加引號的表名摺成小寫，卻不會把 `'Anna'` 這個值摺成小寫。

本篇的顧客表有五列：`Anna`、`anna`、`ANNA`、`Ánna`、`佳穎`。

## 同一段等值條件，三家回不同的列

每一家的預設規則對大小寫與重音的規定不同，所以同一個等值條件在三家上命中的列不是同一批：

```text
WHERE 姓名 = 'anna'

SQLite 3.51        anna
PostgreSQL 18      anna
MySQL 8.4          Anna, anna, ANNA, Ánna
```

MySQL 的預設 collation 是 `utf8mb4_0900_ai_ci`，名字裡的 `ai` 與 `ci` 就是它的規定：accent-insensitive 與 case-insensitive——重音與大小寫都不算差異，所以 `Ánna` 與 `anna` 在這條規則底下是同一個值。SQLite 與 PostgreSQL 的預設把這兩者都算差異，於是只有逐字相同的那一列命中。

**這三個答案都正確**，因為「相等」的定義本來就由那條規則給，而查詢的文字沒有選過它。一段在 MySQL 上寫好的登入查詢搬到 PostgreSQL，比對帳號的那一段會突然變成大小寫敏感，而它照樣執行、照樣回一批形狀正確的列。

## SQLite 的 LIKE 與它自己的等號不一致

`LIKE` 是另一個做字串比較的運算子，而它套的規則未必與 `=` 相同：

```text
                    SQLite 3.51        PostgreSQL 18      MySQL 8.4
= 'anna'            anna               anna               Anna, anna, ANNA, Ánna
LIKE 'anna'         Anna, anna, ANNA   anna               Anna, anna, ANNA, Ánna
```

PostgreSQL 與 MySQL 的兩列一致，SQLite 的兩列分岔：它的 `=` 逐位元組比較，而它的 `LIKE` 預設不分大小寫。所以在 SQLite 上把 `=` 換成 `LIKE`（例如為了加一個 `%`）會順帶換掉比較規則，而這件事沒有任何提示。

SQLite 這個不分大小寫的範圍限定在 ASCII 字母：`LIKE 'ánna'` 在同一批資料上回零列，`Ánna` 沒有被當成同一個字串。所以那條規則的完整敘述是「A 到 Z 這二十六個字母摺疊，其餘逐位元組」，而不是「不分大小寫」。

要把它調成一致，`PRAGMA case_sensitive_like = ON` 讓 `LIKE` 跟著 `=` 走；反向的做法是在條件上寫 `COLLATE NOCASE`，讓 `=` 跟著 `LIKE` 走。**選哪一邊都行，而選了要寫出來**——沒寫出來的時候讀查詢的人得先知道它跑在哪一家引擎上，才知道這一句在比什麼。

## 同一條規則也決定排序

collation 規定的另一半是誰排在前面。同一批五個名字，三家排出三種順序：

```text
ORDER BY 姓名

SQLite 3.51        ANNA, Anna, anna, Ánna, 佳穎
PostgreSQL 18      anna, Anna, ANNA, Ánna, 佳穎
MySQL 8.4          Anna, anna, ANNA, Ánna, 佳穎
```

SQLite 那一列是位元組的先後——大寫字母的碼位小於小寫，所以 `ANNA` 整批排在前面。PostgreSQL 這一列取決於資料庫建立時選的 collation，量測用的這個是 `en_US.utf8`（查法是 `SELECT datcollate FROM pg_database`），它照人類語言的習慣把大小寫視為同一個字母的變體、再用大小寫決定同分時的先後。同一段加上 `COLLATE "C"` 之後回的是 `ANNA, Anna, anna, Ánna, 佳穎`，與 SQLite 一致——**同一家引擎、同一批資料，換一條規則就換一種順序**，而 SQLite 的預設順序就是位元組序這件事也因此驗得出來。

MySQL 那一列要換個方式讀。在 `ai_ci` 底下四個 A 開頭的名字**彼此相等**，所以它們之間沒有先後可言——那一列印的是它們進表的順序。**同一個排序鍵改用 `GROUP_CONCAT(姓名 ORDER BY 姓名)` 取回，順序整個倒過來**：同一張表、同一批資料，回來的是 `Ánna, ANNA, anna, Anna, 佳穎`，四個名字整個倒過來。兩次都沒有違反 collation，因為 collation 對這四個之間什麼都沒有規定（[1.11](/sql/order-by-and-pagination/)）。這是 collation 與分頁交會的地方：一條把大小寫與重音都忽略的規則，會讓原本以為唯一的排序鍵變成不唯一。

## 索引的比較規則要跟條件的對得上

索引把值按某一條規則排好，所以它只服務照同一條規則發問的條件。這一類問題在小表上感覺不出來——資料長到某個量之後前綴搜尋開始變慢，而查詢與索引都沒有動過。這一節的計畫也要在夠大的表上才看得出來——五列的表無論條件寫成什麼，引擎都直接掃完，所以下面兩組輸出量在二十萬列的同結構表上。SQLite 上的三種問法，索引是同一個：

```text
CREATE INDEX ixn ON 顧客(姓名);            -- 預設規則，逐位元組

WHERE 姓名 = 'anna'          SEARCH ... (姓名=?)      查找
WHERE lower(姓名) = 'anna'   SCAN                     整段掃過
WHERE 姓名 LIKE 'ann%'       SCAN                     整段掃過
```

第二行是欄位被函式包住，索引上排好的是原值而條件問的是摺過的值，兩者對不起來（[Sargable](/sql/knowledge-cards/sargable/)）。**第三行的成因不同**：前綴比對本來可以翻成索引上的一段範圍，而 `LIKE` 預設不分大小寫，索引卻是逐位元組排的——規則對不上，範圍就算不出來。把兩邊之中的任何一邊換掉都能修好：`PRAGMA case_sensitive_like = ON` 讓條件回到位元組規則，或者 `CREATE INDEX ON 顧客(姓名 COLLATE NOCASE)` 讓索引改用摺疊規則，兩種做法之後同一段查詢都變成 `SEARCH ... (姓名>? AND 姓名<?)`。

PostgreSQL 上是同一件事的另一種外觀：

```text
WHERE 姓名 = 'anna'          Index Cond: (姓名 = 'anna')          查找
WHERE lower(姓名) = 'anna'   Filter: (lower(姓名) = 'anna')       逐列過濾
WHERE 姓名 LIKE 'ann%'       Filter: (姓名 ~~ 'ann%')             逐列過濾
```

`en_US.utf8` 的排序規則與位元組序不同，所以 `ann` 這個前綴在索引上不對應一段連續的區間。PostgreSQL 給的出口是另建一個按位元組排的索引：`CREATE INDEX ON 顧客(姓名 text_pattern_ops)` 之後同一段變成 `Index Cond: (姓名 ~>=~ 'ann' AND 姓名 ~<~ 'ano')`，而 `lower(姓名)` 那一行則由運算式索引 `CREATE INDEX ON 顧客(lower(姓名))` 接住，變成 `Index Cond: (lower(姓名) = 'anna')`。

三種修法的共同形狀是**讓索引與條件套同一條規則**，而它們把改動放在不同的一邊：改條件、改索引的 collation、或另建一個按別的規則排的索引。

## 規則的住址決定它涵蓋到哪裡

預設值在單一環境底下是隱形的——查詢跑得對，沒有人會去問「相等」現在是怎麼定義的。它在三個時刻現形：換一家引擎、換一個資料庫（同一家引擎的不同資料庫可以有不同的 collation）、以及有人在一欄上單獨指定了規則而其餘欄位沒有。

所以規則的住址要選定。**寫在欄位上**是最貼近資料的一種：`姓名 VARCHAR(50) COLLATE utf8mb4_0900_as_cs`（`as_cs` 是 accent-sensitive、case-sensitive）把這一欄的比較規則固定住，往後每一段查詢、每一個索引都套它。**寫在條件上**（`WHERE 姓名 = 'anna' COLLATE NOCASE`）只涵蓋那一句。上面那個登入的例子裡兩種住址各有位置：帳號欄整欄要不分大小寫，那是欄位的事；而某支後台工具要逐字比對，那是那一句的事。代價是寫在條件上的那一句走不了按預設規則建的索引。

判準與[約束](/sql/knowledge-cards/constraint/)那一條同源：一個保證要涵蓋往後的每一次使用，它就得寫在結構上，而不是靠每一句查詢各自記得。差別在於約束擋的是寫入，collation 決定的是讀出來的時候什麼算相等。

## 換掉其中一項就走到另一篇

本篇底下有三樣可以各自換掉：比較的對象是值還是名字、規則寫在哪一層、問的是相等還是先後。

**把值換成名字**：同一種大小寫問題落在識別字那一層時，規則與這裡完全不同——PostgreSQL 摺疊沒加引號的名字，SQLite 連引號都不讓名字變敏感。[1.13 識別字送進引擎之後會被改寫](/sql/identifier-rules/) 寫各家的摺疊規則與引號的作用。

**把「什麼算相等」換成「誰排在前面」**：collation 同時規定這兩件事，而排序那一半在排序鍵不唯一的時候會留下沒有規定的部分。[1.11 輸出的順序只有 ORDER BY 決定](/sql/order-by-and-pagination/) 寫同分的列為什麼會在分頁時重複出現。

**把「條件對不對」換成「這個條件走不走得了索引」**：本篇的比較規則是索引派不派得上用場的其中一個條件，而條件的形狀是另一個。[Sargable（可走索引的條件形狀）](/sql/knowledge-cards/sargable/) 寫欄位被包住為什麼翻不成查找，[Cardinality 與 Selectivity](/sql/knowledge-cards/cardinality-and-selectivity/) 寫形狀對了之後還要看留下多少列。

**把單一引擎換成要同時支援好幾家**：那時預設值的差異變成要逐項盤點的清單，而 collation 只是其中一項。[1.13](/sql/identifier-rules/) 的「SQLite 與 DuckDB 完全不區分大小寫」一節寫這一類差異換引擎才浮現的形態，而把各方並置的是[模組頁的推導源頭](/sql/#推導源頭)。
