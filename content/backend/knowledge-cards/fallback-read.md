---
title: "Fallback Read"
date: 2026-05-11
description: "說明讀取路徑切換失敗時如何暫時回到舊資料語意或舊讀取來源"
weight: 144
tags: ["backend", "knowledge-card", "database", "migration"]
---

Fallback read 的核心概念是「新讀取路徑尚未穩定時，暫時回到舊資料語意或舊讀取來源」。它連接 [read compatibility](/backend/knowledge-cards/read-compatibility/)、[fallback](/backend/knowledge-cards/fallback/) 與 [rollback-window](/backend/knowledge-cards/rollback-window/)，讓 cutover 失敗時可以先限制在讀取判讀層。

## 跟其他概念的關係

Fallback read 位在 [cutover / switchover](/backend/knowledge-cards/cutover-switchover/)、[schema migration](/backend/knowledge-cards/schema-migration/) 與 [rollback strategy](/backend/knowledge-cards/rollback-strategy/) 之間。它保留新資料結構、暫時把讀取判斷交回舊語意或舊來源，比完整 rollback 成本低且破壞性小。

## 可觀察訊號

系統需要 fallback read 的訊號是：

- 新欄位讀取後 mismatch 升高
- 客服後台、報表或使用者可見查詢結果漂移
- 寫入路徑已經收斂，但讀取模型或索引尚未穩定
- release gate 允許暫停 cutover，但尚未需要資料修補

## 接近真實網路服務的例子

訂單服務把付款狀態拆到 `payment_state` 後，客服後台若發現新欄位判讀 mismatch 升高，可以先回到舊 `status` 的付款語意讀取，讓客服分類回到基線，同時保留 backfill 與 validation query 繼續查證。

## 判斷條件與後果

Fallback read 的判斷對象是讀取退回舊語意之後的範圍與期限。觸發條件沒有寫明時，是否回退由當班的人臨場決定，同樣的 mismatch 數字在不同班次得到不同處置。讀取優先順序與適用入口沒有寫明時，同一筆訂單在客服後台讀舊 `status`、在報表讀新 `payment_state`，兩個入口給出不同的付款狀態。可維持多久與重新嘗試 cutover 的條件沒有寫明時，回退一直開著，新舊兩條讀取路徑長期並存，原因是回退本身不產生任何關閉它的訊號；重試的條件寫成 [validation query](/backend/knowledge-cards/validation-query/) 的結果、回退的決定與依據記進 [incident decision log](/backend/knowledge-cards/incident-decision-log/) 時，回退的結束點才查得到。
