---
title: "Query Optimizer（查詢最佳化器）"
date: 2026-08-31
description: "釐清查詢的執行順序由誰決定，或查詢未改動卻突然變慢時"
aliases: ["/sql/knowledge-cards/query-optimizer/"]
weight: 3
tags: ["sql", "optimizer", "performance", "knowledge-card"]
---

Query optimizer（查詢最佳化器）是資料庫引擎裡負責挑選執行方式的元件。它讀入查詢後產出一份 [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/)，並可在不違反唯一一項限制的前提下任意重排執行步驟：最終輸出的 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/) 必須與 [Semantic Model（語意模型）](/backend/01-database/sql/knowledge-cards/semantic-model/) 所定義的結果一致。

最佳化器估算各個候選計畫代價的依據，是另外儲存的一份 [Query Statistics（統計資訊）](/backend/01-database/sql/knowledge-cards/query-statistics/)。這份摘要既不在查詢文字內，也不直接等於資料表本身；統計越接近目前資料分布，代價估計就越準確。

## 跟其他概念的關係

查詢最佳化器的存在是 SQL 宣告式設計的直接產物。查詢只宣告結果的形狀，不指定執行流程，因此需要由最佳化器替每一次查詢決定掃描與連接順序。

最佳化器比較候選方案時依賴估計代價，而估計值來自 [Query Statistics（統計資訊）](/backend/01-database/sql/knowledge-cards/query-statistics/)（每張表的大致列數與各欄值分布）。因此計畫品質取決於統計的新舊程度，與查詢文字的寫法工整度無關。最佳化器的產出是一份 [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/)，運算子樹上每個節點的輸入與輸出都是一個 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/)。

## 可觀察訊號與例子

書店資料庫的顧客表有 50 列、訂單表有 200,000 列。同一個連接分別寫成 `FROM 訂單 JOIN 顧客` 與 `FROM 顧客 JOIN 訂單`，在執行過 `ANALYZE` 的資料庫上，SQLite 兩次都產出相同的計畫：掃描 200,000 列的訂單表，並對 50 列的顧客表做索引查找。**書寫位置決定語意，實際執行方式由最佳化器另外決定。**

若資料庫沒有統計資訊，SQLite 會退回依照文字中資料表的出現順序掃描。這組有與沒有統計的完整對照實驗，記錄於 [SQL.1 宣告式的紅利與代價：書寫、求值與執行順序各自由誰決定](/backend/01-database/sql/declarative-not-procedural/)。

可用資源改變時，計畫也會隨之更新。替 `訂單(顧客編號)` 建立 [Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/) 後，同一段查詢的計畫從三行縮為兩行：`SCAN 顧客` 接 `SEARCH 訂單 USING COVERING INDEX ix`，引擎不再建立臨時索引。

最佳化器也能執行等價轉換，例如在確認查詢的其他條件已排除外連接補 `NULL` 的列後，將特定的 [Outer Join（外連接）](/backend/01-database/sql/knowledge-cards/outer-join/) 轉成內連接。

## 判斷條件與後果

查詢文字未修改卻在某天變慢時，變動點常是資料分布與統計資訊，而非查詢語句。最佳化器依據估計值挑選計畫，統計陳舊會直接導致計畫退化，因此排查起點應先確認統計是否過期。

只有在統計已經最新、但最佳化器仍選錯計畫的情況下，才考慮使用查詢提示（hint）或改寫來引導。這類強制手段會將查詢固定在單一執行方案上，往後資料量或分布變化時將失去自動調整的能力。
