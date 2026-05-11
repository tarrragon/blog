---
title: "Fallback Read"
date: 2026-05-11
description: "說明讀取路徑切換失敗時如何暫時回到舊資料語意或舊讀取來源"
weight: 143
tags: ["backend", "knowledge-card", "database", "migration"]
---

Fallback read 的核心概念是「新讀取路徑尚未穩定時，暫時回到舊資料語意或舊讀取來源」。它連接 [read compatibility](/backend/knowledge-cards/read-compatibility/)、[fallback](/backend/knowledge-cards/fallback/) 與 [rollback-window](/backend/knowledge-cards/rollback-window/)，讓 cutover 失敗時可以先限制在讀取判讀層。

## 概念位置

Fallback read 位在 [cutover / switchover](/backend/knowledge-cards/cutover-switchover/)、[schema migration](/backend/knowledge-cards/schema-migration/) 與 [rollback strategy](/backend/knowledge-cards/rollback-strategy/) 之間。它不是完整 rollback，而是保留新資料結構、暫時把讀取判斷交回舊語意或舊來源。

## 可觀察訊號

系統需要 fallback read 的訊號是：

- 新欄位讀取後 mismatch 升高
- 客服後台、報表或使用者可見查詢結果漂移
- 寫入路徑已經收斂，但讀取模型或索引尚未穩定
- release gate 允許暫停 cutover，但尚未需要資料修補

## 接近真實網路服務的例子

訂單服務把付款狀態拆到 `payment_state` 後，客服後台若發現新欄位判讀 mismatch 升高，可以先回到舊 `status` 的付款語意讀取，讓客服分類回到基線，同時保留 backfill 與 validation query 繼續查證。

## 設計責任

Fallback read 要定義觸發條件、讀取優先順序、可維持多久、哪些入口適用，以及何時重新嘗試 cutover。它要與 [validation query](/backend/knowledge-cards/validation-query/) 和 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 對齊，避免讀取回退變成沒有證據的永久分岔。
