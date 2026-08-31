---
title: "Query Plan（執行計畫）"
date: 2026-08-31
description: "想知道一段查詢實際會怎麼被執行、或被要求「先看計畫」時"
weight: 2
tags: ["sql", "query-plan", "performance", "knowledge-card"]
---

Query plan 是引擎為一段查詢決定的執行步驟，內容是一棵運算子樹：哪張表用什麼方式讀、用哪種演算法做連接、中間結果怎麼傳遞。它由 [query optimizer](/sql/knowledge-cards/query-optimizer/) 產生，而樹上每個節點的輸入與輸出都是一個 [relation](/sql/knowledge-cards/relation/)。

## 概念位置

計畫是查詢文字與實際代價之間唯一的橋。SQL 只描述要什麼結果，所以掃全表或走索引、雜湊連接或巢狀迴圈這些決定都不在查詢的文字裡，要問引擎才知道。連接要保護哪一側是查詢說了算（見 [outer join](/sql/knowledge-cards/outer-join/)），而用什麼演算法達成它由計畫決定。

同一段查詢的計畫會隨資料量、索引與統計資訊改變，所以計畫是某個時間點某個資料庫狀態下的答案，不是查詢本身的屬性。

## 可觀察訊號與例子

SQLite 的 `EXPLAIN QUERY PLAN` 回報一組掃描步驟，例如 `SCAN small` 接著 `SCAN huge`。同一個連接寫成 `FROM huge JOIN small` 與 `FROM small JOIN huge`，兩次都得到同樣的結果——書寫順序不影響它。

DuckDB 的 `EXPLAIN` 回報一棵運算子樹，節點標著 `HASH_JOIN`、`SEQ_SCAN` 這類名稱與估計的列數；`EXPLAIN ANALYZE` 另外附上實際跑出來的列數與耗時。

## 設計責任

估計值與實際值差很多的時候，先懷疑統計資訊而不是查詢的寫法——最佳化器是照估計值選的，估計錯了選擇就跟著錯。判讀計畫要對照當時的資料量，把在小資料上量到的計畫套到 production 是常見的誤判來源。
