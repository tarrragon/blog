---
title: "Database Engine（資料庫引擎）"
date: 2026-09-02
description: "文章說「引擎決定」「換一家引擎就不同」時，查那是哪一個層次的決定"
aliases: ["/sql/knowledge-cards/database-engine/"]
weight: 17
tags: ["sql", "engine", "portability", "knowledge-card"]
---

資料庫引擎是收下查詢的文字、按自己的規則算出結果並交回一份[關係](/backend/01-database/sql/knowledge-cards/relation/)的那個軟體。SQLite、PostgreSQL、MySQL、DuckDB 各是一個引擎，而同一個引擎的不同版本也可能有不同的規則。

本分類反覆說「引擎」在做某件事，說的都是同一件事——差別在它做的是哪一種決定，而那決定了換一家引擎會不會得到不同的結果。

## 引擎做的決定，換引擎的後果各不相同

**接不接受這段文字。** 引擎檢查名字解析得到、型別配得上、子句的組合合乎規則。標準定死的那些各家一致；標準禁止而各家自行放寬的那些不一致，於是同一段查詢在一家報錯、在另一家跑得動（[SQL.2 子句的求值順序：每一步可用的欄位、語意模型擋下的寫法與各家引擎放寬的寫法](/backend/01-database/sql/clause-evaluation-order/) 與 [SQL.9 分組鍵的選擇：鍵與一組所代表的對象](/backend/01-database/sql/grouping-key-decides-the-unit/) 各有一個實例）。

**名字指向哪個物件。** 沒加引號的識別字被摺成什麼樣由引擎決定，各家的規則不同（[SQL.14 識別字的規則：各家的大小寫摺疊、引號與保留字](/backend/01-database/sql/identifier-rules/)）。

**要花多久。** 這由[最佳化器](/backend/01-database/sql/knowledge-cards/query-optimizer/)決定，而它受一個約束：輸出的列集合要與語意模型算出來的一致。所以一段查詢在固定的資料上執行時，換引擎會換掉代價，不換掉答案（[SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/)）。

**並行時各交易看得到哪些寫入。** 好幾個交易同時執行時，一個交易讀到的資料裡包不包含別的交易剛寫入的列，由引擎的並行控制決定：SQLite 讓寫入交易一個接一個執行，PostgreSQL 讓它們並行、依[多版本並行控制](/backend/knowledge-cards/mvcc/)的快照決定每一句看到哪個版本。這一項跟上面幾項不同，它會換掉答案：同一段先讀後寫的 `UPDATE`，在 SQLite 上兩個 worker 認領到不同的列，在 PostgreSQL 預設的隔離等級下可能認領到同一列（[SQL.20 引擎的部署形態與 SQL 構造：SQLite 與 PostgreSQL 在並行寫入、連線協調與身分上的差異](/backend/01-database/sql/deployment-shape-and-sql-constructs/)）。所以「換引擎不換答案」只對單一查詢在固定資料上成立，並行寫入的正確性要另外查。

**回哪一批列。** 這一項由[關聯代數](/backend/01-database/sql/knowledge-cards/relational-algebra/)的組合規則定死，各家一致。三值邏輯、外連接補 `NULL`、`NOT IN` 的展開方式都在這一層，所以那幾類錯誤換引擎不會消失（[SQL.6 連接之後的列數與空缺：列數膨脹、外連接補的 NULL 與三值邏輯](/backend/01-database/sql/join-changes-rows-and-nulls/)）。

## 跟其他概念的關係

**引擎是「文字之外」那幾方裡射程最大的一方**——識別字規則、寬鬆度與設定、[最佳化器](/backend/01-database/sql/knowledge-cards/query-optimizer/)都由它定義與實作，而權限系統是它另外管的一層（[SQL.16 SQL 的權限模型：角色、GRANT 的授權單位與最小權限](/backend/01-database/sql/privilege-model/)）。所以「換一家引擎」這句話涵蓋的變動比它聽起來的多。

引擎不決定的只有一件事：這批列是不是那個問題的答案。那一層沒有機械判定，理由在 [SQL.13 查詢的合法性與答案的正確性：引擎檢查的範圍、答案錯掉的成因與查證方法](/backend/01-database/sql/well-formed-is-not-correct/)。

錯誤訊息的措辭由引擎決定而且會隨版本改，所以各篇引的那些字串是對照用的——判讀看它拒絕了什麼，不看它怎麼說。

## 往下走

各家在同一段查詢上的分歧最集中的地方，在 [SQL.14 識別字的規則：各家的大小寫摺疊、引號與保留字](/backend/01-database/sql/identifier-rules/)。挑執行方式的那個元件在 [Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/)，它產出的那份計畫在 [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/)。它另外存著的那份摘要在 [Query Statistics（統計資訊）](/backend/01-database/sql/knowledge-cards/query-statistics/)。
