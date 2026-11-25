---
title: "SQL 知識卡"
date: 2026-08-31
description: "查 SQL 文章裡某個術語指什麼時"
aliases: ["/sql/knowledge-cards/"]
weight: 90
tags: ["sql", "knowledge-card"]
---

本目錄收 SQL 文章用到而不在讀者定位基線內的術語。文章負責推導，卡負責這些詞各指什麼。

| 卡                                                                                                                  | 定義與重點                                                 |
| ------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/)                                              | 欄位固定、由若干列構成的集合，表是其一種                   |
| [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/)                                      | 引擎決定的執行步驟樹，查詢代價的唯一觀察介面               |
| [Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/)                        | 挑選執行方式的元件，依據是估計代價                         |
| [Outer Join（外連接）](/backend/01-database/sql/knowledge-cards/outer-join/)                                        | 保留配不到對象的列，補 NULL                                |
| [Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/)                                                 | 額外維護的查找結構，讀取變快而寫入變慢                     |
| [NULL（空值）](/backend/01-database/sql/knowledge-cards/null/)                                                      | 值的缺席；比較為三值邏輯、分組時自成一組                   |
| [Aggregate Function（聚合函數）](/backend/01-database/sql/knowledge-cards/aggregate-function/)                      | 把一組列收斂成一個值；可加與不可加的處理不同               |
| [Subquery（子查詢）](/backend/01-database/sql/knowledge-cards/subquery/)                                            | 獨立的算一次，引用外層的逐列各算一次                       |
| [Schema（命名空間義）](/backend/01-database/sql/knowledge-cards/schema-namespace/)                                  | 資料庫底下的一層容器，與「表結構」所指不同層               |
| [Query Statistics（統計資訊）](/backend/01-database/sql/knowledge-cards/query-statistics/)                          | 引擎另外統計並儲存的摘要，最佳化器的估計依據               |
| [DDL 與 DML（定義結構與動資料）](/backend/01-database/sql/knowledge-cards/ddl-dml/)                                 | 改結構與改資料兩類語句，權限與代價形狀都不同               |
| [DataFrame（資料框）](/backend/01-database/sql/knowledge-cards/dataframe/)                                          | 表在記憶體裡的表示，列有順序、運算在單一行程內完成         |
| [Relational Algebra（關聯代數）](/backend/01-database/sql/knowledge-cards/relational-algebra/)                      | 作用在關係上並產出關係的一組運算，SQL 的底層理論           |
| [Constraint（約束）](/backend/01-database/sql/knowledge-cards/constraint/)                                          | 由資料庫在每次寫入時檢查的規則，決定查詢可依賴的前提       |
| [Sargable（可走索引的條件形狀）](/backend/01-database/sql/knowledge-cards/sargable/)                                | 條件能否翻成索引上的一次查找；欄位被函式包住即無法查找     |
| [Cartesian Product（笛卡兒積）](/backend/01-database/sql/knowledge-cards/cartesian-product/)                        | 兩份資料每列兩兩配對；缺少連接條件時的運算起點             |
| [Database Engine（資料庫引擎）](/backend/01-database/sql/knowledge-cards/database-engine/)                          | 接收查詢並算出結果的軟體；各項決定跨引擎的後果不同         |
| [Semantic Model（語意模型）](/backend/01-database/sql/knowledge-cards/semantic-model/)                              | 定義查詢文字對應哪批結果列的規則；各家一致，與執行方式分離 |
| [Cardinality 與 Selectivity（基數與選擇率）](/backend/01-database/sql/knowledge-cards/cardinality-and-selectivity/) | 集合相異值數量與條件保留比例；最佳化器是否採用索引的依據   |
| [Semi-join 與 Anti-join（半連接與反連接）](/backend/01-database/sql/knowledge-cards/semi-join-and-anti-join/)       | 配對後只輸出左側欄位；`EXISTS` 與 `NOT EXISTS` 底下的運算  |
| [Exclusion Constraint（排除約束）](/backend/01-database/sql/knowledge-cards/exclusion-constraint/)                  | 兩列在指定比較下不能同時成立；唯一鍵的推廣                 |
