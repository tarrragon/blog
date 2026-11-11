---
title: "Transaction Pooling"
date: 2026-05-22
description: "說明 connection pooler 的 transaction 綁定模式如何壓縮連線並改變 session 語意"
weight: 328
---

Transaction Pooling 的核心概念是 connection pooler 把後端連線的綁定縮到單一 transaction 期間 — transaction 一結束，後端連線就還回池子給其他 client 用。它把連線壓縮做到最大，代價是 session 狀態無法跨 transaction 保留。它和 [Connection Pool](/backend/knowledge-cards/connection-pool/) 是同一條線上的不同精細度，並和 [Transaction Boundary](/backend/knowledge-cards/transaction-boundary/) 直接耦合。

## 跟其他概念的關係

Transaction Pooling 位在 application 與資料庫之間的 [Connection Pool](/backend/knowledge-cards/connection-pool/) 內。相對於 session pooling（連線綁定整個 client session）與 statement pooling（綁定單一語句），transaction pooling 在壓縮率與相容性之間取中間值。選它就要把 search_path、prepared statement（PgBouncer 1.21 起可另行追蹤、1.24 起預設開啟，見 [Prepared Statement](/backend/knowledge-cards/prepared-statement/)）、暫存表、advisory lock、SET 等 session 層設定全部改成 transaction-scoped。

## 可觀察訊號與例子

適合 transaction pooling 的訊號是大量短連線、client 連線數遠超過資料庫能承受的後端連線上限。要特別注意依賴 session 狀態的功能：用 SET 設定的 [Row-Level Security](/backend/knowledge-cards/row-level-security/) session 變數若不是 transaction-scoped，會漂到下一個 client 的 transaction，造成跨租戶資料外洩。

## 判斷條件與後果

Transaction pooling 下，同一個 client 的前後兩個 transaction 可能拿到不同的後端連線，依賴 session 狀態的機制在 transaction 結束後不再對這個 client 成立，或留在連線上被下一個 client 拿到。Application 用到哪些 session 層機制沒有先盤點時，換成 transaction pooling 之後的錯誤是間歇的，只在連線剛好被換掉時出現，所以盤點的結果決定是否能選這個模式。租戶識別、權限變數與時區用 SET 設定時，設定留在連線上漂到下一個 client 的 transaction；改用 SET LOCAL 時，設定的效力只到 transaction 結束，連線還回池子之前已經清除。後端連線使用率與 client 等待時間看得出池子的大小是否夠用；和 pooling 模式相關的錯誤（例如找不到 prepared statement 或暫存表）代表還有 session 狀態沒有改成 transaction-scoped。
