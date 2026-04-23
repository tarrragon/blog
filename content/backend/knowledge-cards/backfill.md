---
title: "Backfill"
date: 2026-04-23
description: "說明如何為既有資料補上新欄位、新索引或新衍生狀態"
weight: 82
---

Backfill 的核心概念是「為既有資料補上新結構或新衍生結果」。它常出現在 migration、新功能上線、資料修復、搜尋索引重建與報表補算。

## 概念位置

Backfill 是資料遷移的執行階段。它會消耗資料庫、cache、queue、CPU 與網路資源，因此需要速率限制、checkpoint、監控與停止條件。

## 可觀察訊號與例子

系統需要 backfill 的訊號是新欄位對新資料有效，但舊資料尚未填滿。會員資料新增 `country_code` 後，需要從地址或外部資料補算舊會員欄位。

## 設計責任

Backfill 要分批執行，並記錄進度、錯誤、重試與資料差異。高風險 backfill 應先抽樣驗證，再逐步擴大範圍。
