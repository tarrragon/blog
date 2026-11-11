---
title: "Span"
date: 2026-06-22
description: "說明 trace 中一段工作如何記錄耗時、狀態與關聯"
weight: 108
tags: ["backend", "observability"]
---

Span 的核心概念是「[trace](/backend/knowledge-cards/trace/) 中的一段有起止時間的工作」。每個 span 記錄操作名稱、開始與結束時間、狀態（OK / Error）、屬性（service name、http.status_code、db.statement）與事件（exception message）。

## 跟其他概念的關係

Span 是 tracing 的基本單位。HTTP handler、database query、cache call、[broker](/backend/knowledge-cards/broker/) publish、consumer handle 與外部 API 呼叫都可以形成 span。Span 之間透過 parent-child 關係組成 tree — 共享同一個 [trace id](/backend/knowledge-cards/trace-id/) 的所有 span 構成一條完整的 [trace](/backend/knowledge-cards/trace/)。

Span 有四種 kind：`CLIENT`（發起呼叫）、`SERVER`（接收呼叫）、`PRODUCER`（投遞訊息）、`CONSUMER`（消費訊息）。Kind 影響 trace backend 怎麼計算 service-to-service 的延遲跟依賴方向。

## 使用情境

系統需要 span 的訊號是單一 request 裡有多個步驟，需要知道哪一步變慢或出錯。Checkout trace 中 payment span 佔 80% 時間，問題焦點就落在付款依賴或其網路路徑。

## 判斷條件與後果

Span 的名稱粒度、錯誤狀態與屬性內容，決定 trace backend 是否聚合得出瓶頸，以及 trace 裡是否留下敏感資料。Span 名稱太粗（所有 HTTP call 都叫 `HTTP`）時，不同依賴的延遲混在同一個名稱底下，看不出瓶頸；太細（每個 URL path parameter 都獨立命名）時，span 名稱成為無界維度，影響 trace backend 的聚合效能。錯誤沒有標在 span 的狀態上時，失敗的步驟在 trace 裡跟成功的步驟看起來一樣，要逐一讀屬性或 log 才找得到。

屬性帶的診斷資訊越完整，夾帶敏感資料的機會越大：`http.url` 帶完整 URL 可能含 query parameter 裡的 token；`db.statement` 帶完整 SQL 可能含使用者資料。這些值寫進 trace backend 之後，能讀 trace 的人都讀得到，所以 redaction 在寫進 trace backend 之前、於 SDK 或 collector 層做。
