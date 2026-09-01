---
title: "SQL 知識卡"
date: 2026-08-31
description: "查 SQL 文章裡某個術語指什麼時"
weight: 90
tags: ["sql", "knowledge-card"]
---

本目錄收 SQL 文章用到而不在讀者定位基線內的術語。文章負責推導，卡負責這些詞各指什麼。

| 卡                                                                         | 回答                                                       |
| -------------------------------------------------------------------------- | ---------------------------------------------------------- |
| [Relation（關係）](/sql/knowledge-cards/relation/)                         | 欄位固定、由若干列構成的集合，表是其一種                   |
| [Query Plan（執行計畫）](/sql/knowledge-cards/query-plan/)                 | 引擎決定的執行步驟樹，查詢代價的唯一出口                   |
| [Query Optimizer（查詢最佳化器）](/sql/knowledge-cards/query-optimizer/)   | 挑選執行方式的元件，依據是估計代價                         |
| [Outer Join（外連接）](/sql/knowledge-cards/outer-join/)                   | 保留配不到對象的列，補 NULL                                |
| [Index（索引）](/sql/knowledge-cards/indexing/)                            | 額外維護的查找結構，讀取變快而寫入變慢                     |
| [NULL（空值）](/sql/knowledge-cards/null/)                                 | 值的缺席；比較是第三種答案、分組時自成一組                 |
| [Aggregate Function（聚合函數）](/sql/knowledge-cards/aggregate-function/) | 把一組列收成一個值；可加與不可加的處理不同                 |
| [Subquery（子查詢）](/sql/knowledge-cards/subquery/)                       | 獨立的算一次，引用外層的逐列各算一次                       |
| [Schema（命名空間義）](/sql/knowledge-cards/schema-namespace/)             | 資料庫底下的一層容器，與「表結構」那個所指不同層           |
| [Query Statistics（統計資訊）](/sql/knowledge-cards/query-statistics/)     | 引擎另外數出來存著的摘要，最佳化器的估計依據它             |
| [DDL 與 DML](/sql/knowledge-cards/ddl-dml/)                                | 改結構與改資料兩類語句，權限與代價形狀都不同               |
| [DataFrame（資料框）](/sql/knowledge-cards/dataframe/)                     | 表在記憶體裡的表示，列有順序、運算在自己的行程             |
| [Relational Algebra（關聯代數）](/sql/knowledge-cards/relational-algebra/) | 作用在關係上並產出關係的一組運算，SQL 的底層               |
| [Constraint（約束）](/sql/knowledge-cards/constraint/)                     | 由資料庫在每次寫入時檢查的規則，判斷標準的豁免條件從這裡來 |
| [Sargable（可走索引的條件形狀）](/sql/knowledge-cards/sargable/)           | 條件能不能翻成索引上的一次查找；欄位被包住就走不了         |
