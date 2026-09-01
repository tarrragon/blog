---
title: "Query Plan（執行計畫）"
date: 2026-08-31
description: "想知道一段查詢實際會怎麼被執行、或被要求「先看計畫」時"
weight: 2
tags: ["sql", "query-plan", "performance", "knowledge-card"]
---

Query plan 是引擎為一段查詢決定的執行步驟，內容是一棵運算子樹：哪張表用什麼方式讀、用哪種演算法做連接、中間結果怎麼傳遞。它由 [query optimizer](/sql/knowledge-cards/query-optimizer/) 產生，而樹上每個節點的輸入與輸出都是一個 [relation](/sql/knowledge-cards/relation/)。

## 概念位置

計畫是查詢文字與實際代價之間唯一的橋。SQL 只描述要什麼結果，所以掃全表或走索引、雜湊連接或巢狀迴圈這些決定都不在查詢的文字裡，要問引擎才知道。連接的兩種演算法差在做法：巢狀迴圈對左邊的每一列去右邊找一次，雜湊連接先把一邊建成雜湊表再逐列去查它。連接要保護哪一側是查詢說了算（見 [outer join](/sql/knowledge-cards/outer-join/)），而用什麼演算法達成它由計畫決定。

同一段查詢的計畫會隨資料量、索引與統計資訊改變，所以計畫是某個時間點某個資料庫狀態下的答案，不是查詢本身的屬性。

## 可觀察訊號與例子



書店把顧客與訂單連起來，`EXPLAIN QUERY PLAN` 在 SQLite 上回三行（查的是 `FROM 訂單 JOIN 顧客`，訂單二十萬列、顧客五十列）：

```text
|--SCAN 訂單
|--BLOOM FILTER ON 顧客 (顧客編號=?)
`--SEARCH 顧客 USING AUTOMATIC COVERING INDEX (顧客編號=?)
```

`SCAN` 與 `SEARCH` 是兩種取法：`SCAN 訂單` 表示二十萬列的訂單表逐列看過，`SEARCH 顧客` 表示對五十列的顧客表透過索引定位而不逐列看。

`AUTOMATIC` 指的是這個索引不存在於資料庫裡，是引擎為了這一次查詢臨時建的——它判斷建索引比全表掃描划算。`COVERING` 指的是索引本身帶著查詢要的欄位，所以定位之後不必再回去讀原本的列。`BLOOM FILTER` 是它加的一道快速排除步驟。

**這三行裡沒有一個字出現在原本的查詢裡。** 查詢只說了要把兩張表按顧客編號連起來，其餘全部是引擎的決定——而它們決定了這段查詢要花多久。

**同一段查詢在別的資料庫狀態下會得到別的計畫**——有沒有統計、有沒有索引都會換掉它。上面那三行對書寫順序也敏感：把兩張表對調寫成 `FROM 顧客 JOIN 訂單`，沒有統計的資料庫會改成掃顧客那張，跑過 `ANALYZE` 之後才收斂回上面這一個。所以讀計畫要連同「當時的資料庫是什麼狀態」一起讀，那組對照在 [1.1](/sql/declarative-not-procedural/) 與 [1.14](/sql/cost-lives-in-the-plan/)。

DuckDB 的 `EXPLAIN` 換一種呈現，回一棵運算子樹，節點標著 `HASH_JOIN`、`SEQ_SCAN` 這類名稱與估計的列數；`EXPLAIN ANALYZE` 另外附上實際跑出來的列數與耗時。

## 設計責任

估計值與實際值差很多的時候，先懷疑統計資訊而不是查詢的寫法——最佳化器是照估計值選的，估計錯了選擇就跟著錯。判讀計畫要對照當時的資料量，把在小資料上量到的計畫套到 production 是常見的誤判來源。
