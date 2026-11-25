---
title: "Relational Algebra（關聯代數）"
date: 2026-09-01
description: "看到子句對應特定運算、或想追溯 SQL 語意規則的底層來源時"
aliases: ["/sql/knowledge-cards/relational-algebra/"]
weight: 13
tags: ["sql", "relational-algebra", "relation", "knowledge-card"]
---

Relational algebra（關聯代數）是一組作用在 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/) 上、並且產出關係的運算集合。核心運算包括選取（挑列）、投影（挑欄）、[Cartesian Product（笛卡兒積）](/backend/01-database/sql/knowledge-cards/cartesian-product/)（兩份資料每列兩兩配對）、連接（在積之上加條件篩選），以及聯集、差集與更名。連接本身是積與選取的組合；同一層還有兩個常用導出運算——[Semi-join 與 Anti-join（半連接與反連接）](/backend/01-database/sql/knowledge-cards/semi-join-and-anti-join/)，配對後僅保留左側資料。SQL 的各個子句即是這組代數運算的語法表層，而非另一套獨立規則。

## 封閉性與查詢的巢狀組合

每個關聯代數運算的輸入是關係，輸出仍是關係，這項封閉性讓運算得以連續串接，使中間結果與原始資料表享有相同地位。這項性質帶來兩項直接結果：子查詢可以出現在任何接受關係的位置，閱讀多層查詢時也能逐層檢查每一步的欄位與列數。

封閉性同時解釋了 [Outer Join（外連接）](/backend/01-database/sql/knowledge-cards/outer-join/) 的結果為何能直接進入下一個連接：補上 `NULL` 後的輸出依然是一個合法的關係。

## SQL 與關聯代數的差異

SQL 在基本關聯代數之上加入了擴充關聯代數（extended relational algebra）的**分組聚合**運算（對應 `GROUP BY` 與聚合函數，並另延伸出保留明細列的視窗函數），並額外引入三項集合代數原本不包含的機制：重複列（代數的關係為集合，SQL 的表為多重集合，因此需要 `DISTINCT`）、[NULL（空值）](/backend/01-database/sql/knowledge-cards/null/) 與三值邏輯，以及列序（排序）。這三處正好是 SQL 最常發生靜默錯誤的位置，因為它們超出了基本集合規則的保護範圍。

## 跟其他概念的關係

[SQL：這個語言為什麼長這樣](/backend/01-database/sql/) 中講解 [Semantic Model（語意模型）](/backend/01-database/sql/knowledge-cards/semantic-model/) 的篇章，其判斷標準全部源自關聯代數：子句求值順序、鏈式連接的左運算元、條件放在 `ON` 或 `WHERE`、分組鍵的選取，每項都是運算組合規則的推論，而非語法設計的隨意規定。掌握底層代數後，面對陌生查詢就能逐步推導，不必依賴死記。

同一套運算換成記憶體內程式庫介面，即對應到 [DataFrame（資料框）](/backend/01-database/sql/knowledge-cards/dataframe/)，這也是 SQL 與 pandas 多數操作能互相對映的原因。

## 延伸閱讀：連接後的關係變化與跨介面對應

- 連接產出的新關係如何改變列數與引入空值：[SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)
- 同一組操作在 SQL 與 DataFrame 兩個介面上的對照與三處斷裂點：[8.4 SQL 子句與 pandas 方法的對應：篩選、連接、分組彙總、視窗函數，以及空值、索引與順序的語意差異](/programming/python/basic/08-data-analysis/same-relational-algebra/)
