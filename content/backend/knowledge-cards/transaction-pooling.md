---
title: "Transaction Pooling"
date: 2026-05-22
description: "說明 connection pooler 的 transaction 綁定模式如何壓縮連線並改變 session 語意"
weight: 327
---

Transaction Pooling 的核心概念是 connection pooler 把後端連線的綁定縮到單一 transaction 期間 — transaction 一結束，後端連線就還回池子給其他 client 用。它把連線壓縮做到最大，代價是 session 狀態無法跨 transaction 保留。它和 [Connection Pool](/backend/knowledge-cards/connection-pool/) 是同一條線上的不同精細度，並和 [Transaction Boundary](/backend/knowledge-cards/transaction-boundary/) 直接耦合。

## 概念位置

Transaction Pooling 位在 application 與資料庫之間的 [Connection Pool](/backend/knowledge-cards/connection-pool/) 內。相對於 session pooling（連線綁定整個 client session）與 statement pooling（綁定單一語句），transaction pooling 在壓縮率與相容性之間取中間值。選它就要把 search_path、prepared statement、暫存表、advisory lock、SET 等 session 層設定全部改成 transaction-scoped。

## 可觀察訊號與例子

適合 transaction pooling 的訊號是大量短連線、client 連線數遠超過資料庫能承受的後端連線上限。要特別注意依賴 session 狀態的功能：用 SET 設定的 [Row-Level Security](/backend/knowledge-cards/row-level-security/) session 變數若不是 transaction-scoped，會漂到下一個 client 的 transaction，造成跨租戶資料外洩。

## 設計責任

設計時要先盤點 application 用到哪些 session 層機制，再決定 pooling 模式。選 transaction pooling 時要把租戶識別、權限變數、時區等設定改用 SET LOCAL 綁在 transaction 內。observability 要看後端連線使用率、client 等待時間，以及和 pooling 模式相關的錯誤。
