---
title: "Cardinality 與 Selectivity（基數與選擇率）"
date: 2026-09-02
description: "遇到低基數欄位索引失效，或需要確認最佳化器依什麼指標決定是否使用索引時"
aliases: ["/sql/knowledge-cards/cardinality-and-selectivity/"]
weight: 19
tags: ["sql", "cardinality", "selectivity", "index", "query-optimizer", "knowledge-card"]
---

Cardinality（基數）指一個集合包含的成員數量。在 SQL 裡這個定義用於兩個對象：一份 [Relation（關係）](/backend/01-database/sql/knowledge-cards/relation/) 的基數是它的總列數，一個欄位的基數是該欄位去掉重複值後的相異值個數。

「基數」在站內其他領域另有三種不同指稱：資料建模領域指兩張表之間的關聯比例（一對一、一對多、多對多）；查詢結果層面指一段查詢回傳的列數（見 [Query Cardinality Explosion](/backend/knowledge-cards/cardinality-explosion/)）；監控領域指一個指標的標籤組合總數。本卡與最佳化器使用的是開頭所列的集合計數定義。

Selectivity（選擇率）指某個篩選條件保留下來的列佔總列數的比例。選擇率是條件的屬性而非欄位的屬性：寫在同一欄上的 `狀態 = '已完成'` 與 `狀態 = '已取消'`，選擇率可能相差一個量級以上（〈同一索引在不同選擇率下的計畫差異〉實測約十九倍，95% 對 5%）。

在欄位值均勻分布的前提下，等值條件 `欄 = 某值` 的選擇率約等於欄位基數的倒數。資料分布不均時這項估算會失準，這正是 [Query Statistics（統計資訊）](/backend/01-database/sql/knowledge-cards/query-statistics/) 需要額外記錄高頻值出現頻率的原因。

## 同一索引在不同選擇率下的計畫差異

在二十萬列的訂單表上，`狀態` 欄只有兩個相異值（已完成佔 95%、已取消佔 5%），`顧客編號` 欄有五萬個相異值。兩欄各建索引並執行 `ANALYZE` 後，對 PostgreSQL 18 執行三段等值查詢：

```text
-- PostgreSQL 18
SELECT 備註 FROM 訂單 WHERE 狀態 = '已完成';     -- Seq Scan（索引沒被用）
SELECT 備註 FROM 訂單 WHERE 狀態 = '已取消';     -- Index Scan using ix狀態
SELECT 備註 FROM 訂單 WHERE 顧客編號 = 12345;    -- Index Scan using ix顧客
```

同一個 `ix狀態` 索引面對相同形狀的條件，因為選擇率不同而產生相反的執行計畫。走一般索引須先查索引定位再回原表取 `備註` 欄，命中 95% 的列時，大量隨機回主表讀取（回表，table lookup）的成本高於直接順序全表掃描。

PostgreSQL 最佳化器使用的統計摘要可透過 `pg_stats` 查閱：

```text
SELECT attname, n_distinct, most_common_freqs FROM pg_stats WHERE tablename = '訂單';
 狀態     |       2    | {0.94996667,0.050033335}
 顧客編號 | -0.25113   |
```

`n_distinct` 是估計基數，`most_common_freqs` 是各高頻值的估計選擇率。這兩個數字來自抽樣估算，每次執行 `ANALYZE` 都會在小數位微幅變動；`顧客編號` 欄的負數 `-0.25113` 代表相異值個數佔總列數的比例（約 0.25 × 200,000 = 50,000）。由於這些數值是最近一次統計時的估計值，資料分布變動後同一段查詢即使文字未改也可能切換執行計畫（見 [Query Statistics（統計資訊）](/backend/01-database/sql/knowledge-cards/query-statistics/)）。

## 同一份統計在各家引擎的計畫差異

將相同的資料表與索引建於 SQLite 3.51 並執行 `ANALYZE` 後，三段查詢全數走索引，包含命中 95% 的條件。SQLite 的 `sqlite_stat1` 記錄的是同一份分布事實：

```text
訂單 / ix狀態 → 200000 100000     -- 二十萬列，每個相異值平均十萬列
訂單 / ix顧客 → 200000 4          -- 二十萬列，每個相異值平均四列
```

低基數確實使多數等值條件的選擇率偏高，但選擇率多高才放棄索引由各家最佳化器的成本模型自行決定，不同引擎門檻不同。跨引擎成立的是選擇率高低，而非固定的執行計畫。

## 跟其他概念的關係

以選擇率評估是否走索引的成本模型，建立在列式儲存（row-oriented storage）與獨立索引結構的前提下：走索引需額外回表讀取非索引欄位。欄式儲存引擎（例如 DuckDB 或讀取 Parquet 檔案）按欄讀取並透過區塊最大最小值跳過不符區段，沒有逐列回表成本，對應的效能手段是資料排序與分區。

在列式引擎裡，選擇率與 [Sargable（可走索引的條件形狀）](/backend/01-database/sql/knowledge-cards/sargable/) 是 [Index（索引）](/backend/01-database/sql/knowledge-cards/indexing/) 查找的兩項獨立條件。Sargable 決定條件形狀是否能轉成索引查找（欄位被函式包住時無法查找，但若查詢所需欄位全在索引中，引擎仍可能以 `Index Only Scan` 或 `SCAN ... USING COVERING INDEX` 掃描索引以避免回表）；選擇率決定查找後保留多少比例的列（即使形狀合規，命中比例過高時最佳化器仍可能改採全表掃描）。兩項條件同時滿足時，索引查找才能帶來速度收益。

基數也決定連接展開後的列數。以低基數欄位作為連接鍵時，單列會配到對側所有相同鍵值的列，列數隨表長平方成長，這正是 [Cartesian Product（笛卡兒積）](/backend/01-database/sql/knowledge-cards/cartesian-product/) 區分積與列數膨脹的關鍵量。

## 延伸閱讀：統計收集、執行計畫與結果集治理

- 統計資訊的收集指令與過時訊號：[Query Statistics（統計資訊）](/backend/01-database/sql/knowledge-cards/query-statistics/)
- 最佳化器依統計產出步驟樹的方式：[Query Optimizer（查詢最佳化器）](/backend/01-database/sql/knowledge-cards/query-optimizer/) 與 [Query Plan（執行計畫）](/backend/01-database/sql/knowledge-cards/query-plan/)
- 索引與資料分布對查詢耗時的實測：[SQL.17 查詢的代價：資料分布、索引與寫法各自的影響](/backend/01-database/sql/cost-lives-in-the-plan/)
- 正式環境結果集列數暴增的治理：[Query Cardinality Explosion](/backend/knowledge-cards/cardinality-explosion/)
