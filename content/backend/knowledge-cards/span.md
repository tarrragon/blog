---
title: "Span"
date: 2026-06-22
description: "說明 trace 中一段工作如何記錄耗時、狀態與關聯"
weight: 107
tags: ["backend", "observability"]
---

Span 的核心概念是「[trace](/backend/knowledge-cards/trace/) 中的一段有起止時間的工作」。每個 span 記錄操作名稱、開始與結束時間、狀態（OK / Error）、屬性（service name、http.status_code、db.statement）與事件（exception message）。

## 概念位置

Span 是 tracing 的基本單位。HTTP handler、database query、cache call、[broker](/backend/knowledge-cards/broker/) publish、consumer handle 與外部 API 呼叫都可以形成 span。Span 之間透過 parent-child 關係組成 tree — 共享同一個 [trace id](/backend/knowledge-cards/trace-id/) 的所有 span 構成一條完整的 [trace](/backend/knowledge-cards/trace/)。

Span 有四種 kind：`CLIENT`（發起呼叫）、`SERVER`（接收呼叫）、`PRODUCER`（投遞訊息）、`CONSUMER`（消費訊息）。Kind 影響 trace backend 怎麼計算 service-to-service 的延遲跟依賴方向。

## 使用情境

系統需要 span 的訊號是單一 request 裡有多個步驟，需要知道哪一步變慢或出錯。Checkout trace 中 payment span 佔 80% 時間，問題焦點就落在付款依賴或其網路路徑。

## 設計責任

Span 設計要控制名稱粒度、屬性選擇、錯誤狀態與敏感資料。Span 名稱太粗（所有 HTTP call 都叫 `HTTP`）會看不出瓶頸；太細（每個 URL path parameter 都獨立命名）會讓 span 名稱成為無界維度、影響 trace backend 的聚合效能。

屬性要帶足夠的診斷資訊但避免敏感資料。`http.url` 帶完整 URL 可能含 query parameter 裡的 token；`db.statement` 帶完整 SQL 可能含使用者資料。需要在 SDK 或 collector 層做 redaction。
