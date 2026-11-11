---
title: "Stale Read"
date: 2026-05-13
description: "讀取到落後於最新寫入版本的舊資料"
weight: 257
---

Stale read 的核心概念是「讀到的資料不是最新提交狀態」。它的責任是揭露一致性延遲在讀路徑的實際影響，常用於 [eventual-consistency](/backend/knowledge-cards/eventual-consistency/) 與 [bounded-staleness](/backend/knowledge-cards/bounded-staleness/) 的風險判讀。

## 跟其他概念的關係

Stale read 常出現在 [replication-lag](/backend/knowledge-cards/replication-lag/) 拉開的 read replica、跨區同步、[cache-aside](/backend/knowledge-cards/cache-aside/) 與異步 [projection](/backend/knowledge-cards/projection/)。它需要先定義可接受窗口與超標處置、是否構成錯誤取決於業務容忍度；判讀粒度跟 [consistency-level](/backend/knowledge-cards/consistency-level/) 跟 [bounded-staleness](/backend/knowledge-cards/bounded-staleness/) 對齊。

## 可觀察訊號與例子

需要 stale read 判讀的訊號是「使用者剛完成操作，下一次查詢卻看不到結果」。例如付款成功後，訂單狀態頁仍顯示未付款，通常是讀路徑落後寫入收斂。

## 判斷條件與後果

一次 stale read 是否算錯誤，取決於讀到它的人當下依它做什麼判斷。使用者剛付款就查訂單、看到「未付款」時，他把收斂延遲讀成付款失敗；同樣的延遲出現在後台的日報表上，沒有人依它做即時決定，就只是延遲。前一種情形的處置分兩邊：技術上讓這次讀取不落後，例如剛寫入的使用者讀回主庫，或用版本比對確認讀到的是寫入之後的版本，也可以把延遲容忍寫進設計；產品上把狀態轉換呈現出來（顯示「付款確認中」），使用者看到的是處理中的狀態，而非一筆看起來錯誤的資料。
