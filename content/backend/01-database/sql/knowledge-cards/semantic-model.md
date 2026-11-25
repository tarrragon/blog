---
title: "Semantic Model（語意模型）"
date: 2026-09-02
description: "文章提到「語意模型規定」「符合語意模型」時，確認那套規則的範圍與保證邊界"
aliases: ["/sql/knowledge-cards/semantic-model/"]
weight: 18
tags: ["sql", "relational-algebra", "semantics", "knowledge-card"]
---

Semantic model（語意模型）是定義「一段 SQL 查詢文字對應算出哪一份 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/)」的規則體系。它只定義最終產出的結果集內容，不規定引擎如何計算或耗時多久。

這套規則源自 [Relational Algebra（關聯代數）](/backend/01-database/sql/knowledge-cards/relational-algebra/)：每個 SQL 子句對應一個作用在 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/) 上的代數運算，整段查詢即為這些運算的組合。關聯代數是理論來源，語意模型則是 SQL 具體採行的求值規則本身。

## 語意模型與執行方式、書寫順序分離

**與執行方式分離。** [Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/) 可任意重排掃描與連接步驟，只受一項約束：最終輸出的關係必須與語意模型定義的結果一致。這項分工正是「執行代價由資料與索引決定、而非寫法決定」的基礎（見 [SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/)）。

**與書寫順序分離。** `SELECT` 寫在語句最開頭，在求值順序上卻排在 `FROM`、`WHERE`、`GROUP BY` 與 `HAVING` 之後，這正是語意模型的邏輯步驟與文字順序不同的典型例子（見 [SQL.2 子句的求值順序：每一步可用的欄位、語意模型擋下的寫法與各家引擎放寬的寫法](/backend/01-database/sql/clause-evaluation-order/)）。

## 語意模型涵蓋與未涵蓋的範圍

語意模型定死的規則在各家 [Database Engine（資料庫引擎）](/backend/01-database/sql/knowledge-cards/database-engine/) 上保持一致：三值邏輯讓含 `NULL` 的條件產生 `UNKNOWN`、外連接配對不到時補 `NULL`、`NOT IN` 展開為一連串不等於的 `AND` 連接、分組將同一鍵值的列收斂為單一列。三值邏輯、外連接補 `NULL` 與 `NOT IN` 展開詳見 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)，分組規則詳見 [SQL.9 分組鍵的選擇：鍵與一組所代表的對象](/backend/01-database/sql/grouping-key-decides-the-unit/)。

在語意模型之外，還有數個外部因素決定查詢的實際結果：識別字大小寫如何摺疊（見 [SQL.14 識別字的規則：各家的大小寫摺疊、引號與保留字](/backend/01-database/sql/identifier-rules/)）、字串比較套用哪條 collation（見 [SQL.15 字串比較與 collation：相等、排序、LIKE 與索引可用性](/backend/01-database/sql/string-comparison-and-collation/)）、表上 [Constraint（約束）](/backend/01-database/sql/knowledge-cards/constraint/) 是否宣告並實際生效（見 [SQL.18 外鍵與參照完整性：宣告、生效與查詢得到的保證](/backend/01-database/sql/foreign-key-and-referential-integrity/)）、引擎是否放寬標準禁止的寫法（見 [SQL.19 引擎寬鬆度與可攜性：各家對同一組寫法的差異、分級與處理時機](/backend/01-database/sql/engine-leniency-and-portability/)）、呼叫端擁有哪些權限（見 [SQL.16 SQL 的權限模型：角色、GRANT 的授權單位與最小權限](/backend/01-database/sql/privilege-model/)），以及單寫入者與多連線並行的部署形態（見 [SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異](/backend/01-database/sql/deployment-shape-and-sql-constructs/)）。這些因素與語意模型的核心差別在於：語意模型跨引擎一致，外部因素則隨引擎與環境而異。

## 跟其他概念的關係

**「符合語意模型」與「符合業務需求」是兩件獨立的事。** 語意模型與 [Constraint（約束）](/backend/01-database/sql/knowledge-cards/constraint/) 之間也有明確分工：約束負責在寫入當下限制資料表允許存進哪些資料，語意模型負責定義從既有資料算出哪批結果列。引擎只依語意模型運算，無法判斷這批結果是否對應真實的業務需求，因為需求本身並未寫進 SQL（見 [SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/)）。列數膨脹、外連接被 `WHERE` 抵銷與 `NULL` 比較落空等靜默錯誤，全都在語意模型完全正確執行的前提下發生。

## 延伸閱讀：理論來源、三種順序與引擎分工

- 規則的理論來源與封閉性：[Relational Algebra（關聯代數）](/backend/01-database/sql/knowledge-cards/relational-algebra/)
- 語意模型與書寫順序、執行順序的切分：[SQL.1 宣告式的紅利與代價：書寫、求值與執行順序各自由誰決定](/backend/01-database/sql/declarative-not-procedural/)
- 語意模型之外的各項引擎決策：[Database Engine（資料庫引擎）](/backend/01-database/sql/knowledge-cards/database-engine/)
