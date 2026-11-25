---
title: "Query Plan（執行計畫）"
date: 2026-08-31
description: "想確認查詢實際的執行步驟，或被要求先檢視執行計畫時"
aliases: ["/sql/knowledge-cards/query-plan/"]
weight: 2
tags: ["sql", "query-plan", "performance", "knowledge-card"]
---

Query plan（執行計畫）是資料庫引擎替一段查詢決定的實際執行步驟，結構為一棵運算子樹：包含每張表的讀取方式、連接採用的演算法與中間結果的傳遞路徑。計畫由 [Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/) 產生，樹上每個節點的輸入與輸出都是一個 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/)。

## 跟其他概念的關係

執行計畫是查詢文字與實際執行代價之間的核心觀察介面（鎖等待、緩衝區命中與實際 I/O 仍須搭配 `EXPLAIN (ANALYZE, BUFFERS)` 與執行期統計觀測）。SQL 只描述目標結果，因此全表掃描或索引查找、雜湊連接或巢狀迴圈等決定都不會寫在查詢文字內，必須透過引擎輸出計畫才能得知。兩種常見連接演算法的做法不同：巢狀迴圈對左側每一列逐一到右側查找配對，雜湊連接則先將其中一側建成雜湊表，再逐列查詢。連接要保留哪一側未配對的列由查詢語句決定（見 [Outer Join（外連接）](/backend/01-database/sql/knowledge-cards/outer-join/)），而用哪種演算法完成連接由執行計畫決定。

同一段查詢的計畫會隨資料量、[Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/) 與 [Query Statistics（統計資訊）](/backend/01-database/sql/knowledge-cards/query-statistics/) 變動。因此執行計畫反映的是某個時間點、特定資料庫狀態下的結果，而非查詢文字固定的屬性。

## 可觀察訊號與例子

在書店資料庫將顧客表（50 列）與訂單表（200,000 列）連接，對 `FROM 訂單 JOIN 顧客` 執行 SQLite 的 `EXPLAIN QUERY PLAN`，輸出如下：

```text
|--SCAN 訂單
|--BLOOM FILTER ON 顧客 (顧客編號=?)
`--SEARCH 顧客 USING AUTOMATIC COVERING INDEX (顧客編號=?)
```

`SCAN` 與 `SEARCH` 代表兩種讀取方式：`SCAN 訂單` 表示逐列掃描 200,000 列的訂單表；`SEARCH 顧客` 表示對 50 列的顧客表使用索引定位，而不逐列掃描。

輸出中的三個標記各有含義：`AUTOMATIC` 表示該索引原本不存在於資料庫，由引擎為這次查詢臨時建立；`COVERING` 表示索引本身已包含查詢所需的全部欄位，定位後無須再回原表取列；`BLOOM FILTER` 表示引擎額外加入一道快速篩除步驟。

**這三行計畫中的所有執行策略都未寫在原查詢內。** 查詢只指定兩張表以顧客編號連接，其餘讀取與查找步驟全由引擎決定，也直接決定查詢耗時。

**同一段查詢在不同的資料庫狀態下會產出不同計畫**，統計與索引的存在與否皆會改變結果。在沒有統計資訊的 SQLite 資料庫中，將兩張表對調寫成 `FROM 顧客 JOIN 訂單` 會改為優先掃描顧客表；執行 `ANALYZE` 後，兩種寫法才會收斂為相同計畫。因此判讀計畫時必須一併記錄當下的資料庫狀態，完整對照見 [SQL.1 宣告式的紅利與代價：書寫、求值與執行順序各自由誰決定](/backend/01-database/sql/declarative-not-procedural/) 與 [SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/)。

DuckDB 的 `EXPLAIN` 採用不同的呈現格式，會輸出一棵運算子樹，節點標註 `HASH_JOIN`、`SEQ_SCAN` 等名稱與估計列數；`EXPLAIN ANALYZE` 則會實際執行並附上真實列數與耗時。

## 判斷條件與後果

計畫中的估計列數與實際列數落差甚大時，代表最佳化器據以挑選方案的摘要已失真；這類失真源自統計資訊過期，單純改寫查詢文字無法修正估算偏差。此外，判讀計畫必須對應真實規模的資料量，小資料集測得的計畫無法直接類推至正式環境，因為資料量與分布改變後最佳化器會切換演算法。
