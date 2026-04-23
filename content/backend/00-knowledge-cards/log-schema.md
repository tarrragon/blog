---
title: "Log Schema"
date: 2026-04-23
description: "說明結構化 log 欄位如何支援搜尋、關聯與事故排查"
weight: 32
---

Log schema 的核心概念是「用穩定欄位描述事件」。結構化 log 不只是一段文字；它應包含時間、等級、服務、事件名稱、錯誤類型、request id、user 或 tenant、資源 ID 與處理結果。

## 概念位置

Log schema 是可觀測性的事件明細層。Metrics 告訴團隊趨勢，trace 告訴團隊路徑，log 則提供單一事件的上下文與細節。

## 可觀察訊號與例子

系統需要 log schema 的訊號是事故時只能全文搜尋或翻多台機器。Checkout 失敗時，穩定欄位可以讓團隊用 order_id、payment_id、request_id 追出同一流程的所有紀錄。

## 設計責任

Log schema 要控制欄位名稱、錯誤分類、敏感資料遮罩與索引成本。高流量服務還要管理 log level、採樣、保留期限與查詢成本。
