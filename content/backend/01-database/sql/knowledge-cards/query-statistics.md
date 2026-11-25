---
title: "Query Statistics（統計資訊）"
date: 2026-09-01
description: "看到要求先執行 ANALYZE，或查詢未改動卻突然變慢時，查證統計資訊的內容與用途"
aliases: ["/sql/knowledge-cards/query-statistics/"]
weight: 10
tags: ["sql", "statistics", "analyze", "query-plan", "knowledge-card"]
---

[Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/) 在挑選 [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/) 時不會即時掃描資料表，而是讀取引擎另外儲存的一份摘要——query statistics（統計資訊），記錄每張表的大致列數與各欄位的值分布。這份摘要既不在查詢文字內，也不等於當下的資料表狀態：資料表實際有多少列是一回事，引擎記錄的摘要數值是另一回事。

## 統計資訊的產生方式與時效

SQLite 與 PostgreSQL 都提供 `ANALYZE` 指令來收集統計資訊，PostgreSQL 另由 autovacuum 在背景定期更新。新建的資料庫尚未有統計資訊，而大批資料寫入或刪除之後，既有統計也會與現況脫節。

缺乏統計資訊時，引擎仍會執行查詢，但會退回採用其他預設規則。SQLite 在沒有統計時會依查詢文字中資料表的出現順序決定計畫——**書寫順序只在這類缺乏統計的退路情境下影響計畫，而非正常運作時的依據**。執行 `ANALYZE` 後，兩種資料表先後寫法便會收斂為同一份計畫。

## 統計估算與實際資料表的差別

最佳化器比較的是源自統計摘要的估計代價，執行計畫的品質直接取決於統計的新鮮度，與查詢文字的寫法風格無關：

- 查詢未改動卻在某天變慢，變動點常是資料分布與統計資訊隨寫入累積而偏離，而非查詢語句本身。
- 計畫中的估計列數與實際列數落差過大，指向摘要已與實際分布脫節，更新統計後估算才會回復準確。
- 在小資料集測得的計畫無法直接類推至正式環境，兩邊的資料量與統計分布並不相同。

## 統計資訊與索引的分工

[Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/) 決定引擎是否具備快速的存取路徑，統計資訊則決定最佳化器是否能正確估算該路徑的成本。索引已建立但統計未更新時，最佳化器可能因低估或高估列數而放棄使用索引，排查效能時兩者需一併核對。

## 跟其他概念的關係

統計資訊具體體現了「查詢文字本身不足以決定執行方式」這項設計。查詢宣告目標結果，[Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/) 決定取數方式，而最佳化器估計成本的依據來自這份另外維護的摘要，不在查詢語句或即時資料表內。

同一段 SQL 沒有固定不變的執行計畫：即使資料、索引與查詢都未變動，只要重新收集統計，產出的 [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/) 便可能改變。討論查詢計畫時必須一併指明當時的資料庫狀態。

## 延伸閱讀：統計對計畫與代價的實測

- 有無統計的計畫對照與書寫順序作為退路的成因：[SQL.1 宣告式的紅利與代價：書寫、求值與執行順序各自由誰決定](/backend/01-database/sql/declarative-not-procedural/)
- 統計、索引與資料分布各自影響查詢耗時的實測：[SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/)
