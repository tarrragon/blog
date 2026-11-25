---
title: "Database Engine（資料庫引擎）"
date: 2026-09-02
description: "讀到「由引擎決定」或「更換引擎結果不同」時，確認該決定屬於哪一個層次"
aliases: ["/sql/knowledge-cards/database-engine/"]
weight: 17
tags: ["sql", "engine", "portability", "knowledge-card"]
---

Database engine（資料庫引擎）是接收 SQL 查詢文字、依規則執行運算並回傳 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/) 的軟體系統。SQLite、PostgreSQL、MySQL 與 DuckDB 皆為不同的引擎，同一引擎的不同大版本或設定組態也可能表現出不同規則。

判斷更換引擎是否會改變查詢結果，關鍵在於區分引擎在以下各個層次分別做出的決定。

## 引擎做的決定與更換引擎後的影響

- **語法寬鬆與規則接受度**：引擎檢查型別相容與子句組合。標準禁止的寫法在嚴格引擎上報錯，在寬鬆引擎上可能被接受並代為補值，更換引擎時會出現一邊報錯、一邊正常執行的落差（跨引擎四級差異整理在 [SQL.19 引擎寬鬆度與可攜性：各家對同一組寫法的差異、分級與處理時機](/backend/01-database/sql/engine-leniency-and-portability/)，實例見 [SQL.2 子句的求值順序：每一步可用的欄位、語意模型擋下的寫法與各家引擎放寬的寫法](/backend/01-database/sql/clause-evaluation-order/) 與 [SQL.9 分組鍵的選擇：鍵與一組所代表的對象](/backend/01-database/sql/grouping-key-decides-the-unit/)）。
- **識別字解析**：未加引號的表名與欄名是否摺疊為小寫由各引擎自行規定，遷移時容易觸發找不到表的錯誤（整理在 [SQL.14 識別字的規則：各家的大小寫摺疊、引號與保留字](/backend/01-database/sql/identifier-rules/)）。
- **字串比較與空值排序預設**：預設 collation 會同時改變等值命中、排序順序與 `LIKE` 能否走 [Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/)（整理在 [SQL.15 字串比較與 collation：相等、排序、LIKE 與索引可用性](/backend/01-database/sql/string-comparison-and-collation/)）；`ORDER BY` 與視窗內排序對 `NULL` 排最前或最後的預設同樣隨引擎分岔（對照在 [SQL.11 查詢結果的列序：沒有 ORDER BY 時的來源與 ORDER BY 的規定範圍](/backend/01-database/sql/relations-have-no-order/)）。
- **約束執法與儲存引擎**：[Constraint（約束）](/backend/01-database/sql/knowledge-cards/constraint/) 宣告後是否預設生效（例如 SQLite 須逐連線啟用外鍵、MySQL MyISAM 與 InnoDB 儲存引擎行為不同），由引擎實作與組態決定（詳見 [SQL.18 外鍵與參照完整性：宣告、生效與查詢得到的保證](/backend/01-database/sql/foreign-key-and-referential-integrity/)）。
- **權限模型與跨連線協調**：連線角色與 `GRANT` 授權體系（詳見 [SQL.16 SQL 的權限模型：角色、GRANT 的授權單位與最小權限](/backend/01-database/sql/privilege-model/)），以及多連線伺服器提供的建議鎖與 `LISTEN`／`NOTIFY` 原語，取決於引擎的部署形態（詳見 [SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異](/backend/01-database/sql/deployment-shape-and-sql-constructs/)）。
- **最佳化器與並行交易可見性**：僅就 [Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/) 這一層而言，對固定資料執行單一標準查詢時，計畫變化只改變執行代價而不改變結果集合（實測見 [SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/)）；但在多 [Transaction（交易）](/backend/knowledge-cards/transaction/) 同時執行時，SQLite 的單寫入鎖序列模型與 PostgreSQL 的 [MVCC（多版本並行控制）](/backend/knowledge-cards/mvcc/) 快照模型會直接改變先讀後寫的最終結果（實測在 [SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異](/backend/01-database/sql/deployment-shape-and-sql-constructs/)）。

## 跟其他概念的關係

相對於因引擎與組態而異的決定，標準關聯運算規則由 [Relational Algebra（關聯代數）](/backend/01-database/sql/knowledge-cards/relational-algebra/) 與 [Semantic Model（語意模型）](/backend/01-database/sql/knowledge-cards/semantic-model/) 固定，各家一致。三值邏輯、外連接補 `NULL` 與 `NOT IN` 的展開規則屬於這一層，這類靜默錯誤不會隨更換引擎消失（推導整理在 [SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)）。

引擎同樣不負責驗證結果集是否符合提問者的業務需求、應用層查詢預算或外部系統不變式（業務正確性的成因與查證見 [SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/)）。各引擎錯誤訊息的措辭也會隨版本調整，判讀時須對照被拒的規則本身而非逐字比對字串。

## 延伸閱讀：識別字、最佳化器與統計資訊

- 跨引擎識別字規則對照：[SQL.14 識別字的規則：各家的大小寫摺疊、引號與保留字](/backend/01-database/sql/identifier-rules/)
- 挑選執行路徑的元件與步驟樹：[Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/) 與 [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/)
- 最佳化器估算依據的摘要資料：[Query Statistics（統計資訊）](/backend/01-database/sql/knowledge-cards/query-statistics/)
