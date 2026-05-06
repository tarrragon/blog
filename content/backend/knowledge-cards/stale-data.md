---
title: "Stale Data"
date: 2026-04-23
description: "說明過期資料在快取、replica 與衍生資料中的產品影響"
weight: 95
---


Stale data 的核心概念是「資料已落後於正式來源，但仍被讀取或展示」。它可能來自 cache、replica、search index、read model、CDN 或前端本地狀態。 可先對照 [Status Page](/backend/knowledge-cards/status-page/)。

## 概念位置

Stale data 是一致性與使用者體驗的交界。某些資料過期可接受，例如推薦列表；某些資料過期會造成交易或安全問題，例如價格、庫存、權限。 可先對照 [Status Page](/backend/knowledge-cards/status-page/)。

## 可觀察訊號與例子

系統需要 stale data 設計的訊號是使用者在不同頁面看到不同狀態。商品列表顯示舊價格，結帳頁顯示新價格，這需要明確定義哪個頁面可以接受延遲。

## 設計責任

Stale data 策略要定義可接受延遲、正式來源、顯示文案、強制刷新與修復流程。高風險資料應避免長時間依賴 stale 副本。
