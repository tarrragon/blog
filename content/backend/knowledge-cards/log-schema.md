---
title: "Log Schema"
date: 2026-06-22
description: "說明結構化 log 欄位如何支援搜尋、關聯與事故排查"
weight: 32
tags: ["backend", "observability"]
---

Log schema 的核心概念是「用穩定欄位描述 [log](/backend/knowledge-cards/log/) 事件」。結構化 log 應包含時間、等級、服務名稱、事件名稱、錯誤類型、[request id](/backend/knowledge-cards/request-id/)、[correlation id](/backend/knowledge-cards/correlation-id/)、tenant、資源 ID 與處理結果。

## 概念位置

Log schema 是可觀測性的事件明細層。[Metrics](/backend/knowledge-cards/metrics/) 提供趨勢，[trace](/backend/knowledge-cards/trace/) 提供跨服務路徑，log 提供單一事件的上下文與細節。三者透過共享欄位（[trace id](/backend/knowledge-cards/trace-id/)、correlation id）互相連結。

Log schema 的穩定性決定了查詢的效率 — 跨服務使用不同的欄位名稱記錄同一概念時，查詢需要窮舉所有變體。見 [4.1 log schema 與搜尋規劃](/backend/04-observability/log-schema/)。

## 使用情境

系統需要 log schema 的訊號是事故時查詢依賴全文搜尋或逐台機器翻查。Checkout 失敗時，穩定欄位讓團隊用 order_id、payment_id、request_id 在秒級內追出同一流程的所有紀錄。

## 設計責任

Log schema 要控制欄位名稱（跨服務統一）、錯誤分類（error type / error code 有界而非 free-form message）、敏感資料遮罩（API key / token / PII 在寫入前 redact）與索引成本（高 cardinality 欄位不全部建索引）。高流量服務還要管理 log level、[sampling](/backend/knowledge-cards/sampling/)、[retention](/backend/knowledge-cards/retention/) 與查詢成本。
