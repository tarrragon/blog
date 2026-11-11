---
title: "Backfill"
date: 2026-04-23
description: "說明如何為既有資料補上新欄位、新索引或新衍生狀態"
weight: 83
---

Backfill 的核心概念是「為既有資料補上新結構或新衍生結果」。它常出現在 migration、新功能上線、資料修復、搜尋索引重建與報表補算。 可先對照 [Backpressure](/backend/knowledge-cards/backpressure/)。

## 跟其他概念的關係

Backfill 是資料遷移的執行階段。它會消耗資料庫、cache、queue、CPU 與網路資源，因此需要速率限制、checkpoint、監控與停止條件。 可先對照 [Backpressure](/backend/knowledge-cards/backpressure/)。

## 可觀察訊號與例子

系統需要 backfill 的訊號是新欄位對新資料有效，但舊資料尚未填滿。會員資料新增 `country_code` 後，需要從地址或外部資料補算舊會員欄位。

## 判斷條件與後果

Backfill 一次處理全部舊資料時，它和線上流量爭用同一組資料庫、cache 與 queue，批次越大線上請求的延遲越高，中途失敗也只能從頭重跑。分批執行並記錄進度時，每批的資源用量有上限，中斷後從最後完成的批次接續。沒有記錄錯誤、重試與資料差異時，跑完之後查不出哪些舊資料補算失敗、補算結果是否和來源一致。補算邏輯本身寫錯時，錯誤值會覆蓋全部舊資料，影響範圍等於 backfill 的範圍，所以高風險的 backfill 先抽樣驗證，再逐步擴大範圍。
