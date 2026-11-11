---
title: "Log Schema"
date: 2026-06-22
description: "說明結構化 log 欄位如何支援搜尋、關聯與事故排查"
weight: 33
tags: ["backend", "observability"]
---

Log schema 的核心概念是「用穩定欄位描述 [log](/backend/knowledge-cards/log/) 事件」。結構化 log 應包含時間、等級、服務名稱、事件名稱、錯誤類型、[request id](/backend/knowledge-cards/request-id/)、[correlation id](/backend/knowledge-cards/correlation-id/)、tenant、資源 ID 與處理結果。

## 跟其他概念的關係

Log schema 是可觀測性的事件明細層。[Metrics](/backend/knowledge-cards/metrics/) 提供趨勢，[trace](/backend/knowledge-cards/trace/) 提供跨服務路徑，log 提供單一事件的上下文與細節。三者透過共享欄位（[trace id](/backend/knowledge-cards/trace-id/)、correlation id）互相連結。

Log schema 的穩定性決定了查詢的效率 — 跨服務使用不同的欄位名稱記錄同一概念時，查詢需要窮舉所有變體。見 [4.1 log schema 與搜尋規劃](/backend/04-observability/log-schema/)。

## 使用情境

系統需要 log schema 的訊號是事故時查詢依賴全文搜尋或逐台機器翻查。Checkout 失敗時，穩定欄位讓團隊用 order_id、payment_id、request_id 在秒級內追出同一流程的所有紀錄。

## 判斷條件與後果

Log schema 的四項欄位約定各自對應一種查詢或成本上的失效。欄位名稱跨服務不統一時，同一個概念（`user_id` 與 `userId`）在查詢裡要窮舉所有寫法，漏掉一個就漏掉那個服務的紀錄。錯誤分類寫成 free-form message、而不是有界的 error type 或 error code 時，同一種錯誤因訊息裡夾帶的 ID 或數值變成無數個不同字串，無法依錯誤類型統計。API key、token 或 PII 沒有在寫入前 redact 時，讀得到 log 的人都讀得到這些值，而且它們依 log 的保存期限一直留著。高 cardinality 欄位全部建索引時，索引的儲存與寫入成本隨欄位值的數量成長。高流量服務的 log level、[sampling](/backend/knowledge-cards/sampling/) 與 [retention](/backend/knowledge-cards/retention/) 直接決定查詢成本：寫入量乘上保存期限就是儲存量，查詢要掃的資料量也隨它放大。
