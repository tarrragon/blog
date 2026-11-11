---
title: "Facet Query"
date: 2026-04-23
description: "說明分面查詢如何提供分類統計與篩選體驗"
weight: 163
---

Facet query 的核心概念是「在搜尋結果上提供可聚合的分類維度」。它讓使用者能快速依品牌、分類、價格區間等條件縮小結果。 可先對照 [Search Index](/backend/knowledge-cards/search-index/)。

## 跟其他概念的關係

常與 [search index](/backend/knowledge-cards/search-index/) 與 [full-text search](/backend/knowledge-cards/full-text-search/) 搭配，提升查詢互動性。

## 判斷條件與後果

Facet query 在每次搜尋時對結果集合做聚合，所以分面欄位的數量與每個欄位的值有多少種，直接加在每一次查詢的成本上。分面欄位越多、結果集合越大，同一次搜尋的回應越慢，原因是每多一個分面就多一次聚合計算。資料更新之後 [search index](/backend/knowledge-cards/search-index/) 還沒更新時，分面上的數量與實際結果對不上，使用者點進一個分類，看到的筆數跟分面上標示的不同。
