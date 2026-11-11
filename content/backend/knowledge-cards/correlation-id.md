---
title: "Correlation ID"
date: 2026-06-22
description: "說明跨事件或跨服務的關聯識別碼如何支援排障"
weight: 105
tags: ["backend", "observability"]
---

Correlation ID 的核心概念是「把同一個業務流程中的多筆紀錄關聯起來的識別碼」。它是 [log schema](/backend/knowledge-cards/log-schema/) 的核心欄位，可以跨 request、queue message、background job、log、trace 與外部 API 呼叫。

## 跟其他概念的關係

Correlation ID 跟 [trace id](/backend/knowledge-cards/trace-id/) 的定位不同。Trace id 偏向一次技術呼叫路徑（一個 HTTP request 經過多個服務）；correlation ID 可以代表更長的業務流程（一筆訂單從建立到付款到出貨，跨越多個獨立 request）。

Correlation ID 是 [log schema](/backend/knowledge-cards/log-schema/) 的核心欄位。Log 帶 correlation ID 時，跨服務跟跨 async 邊界的事件可以用同一個 ID 查出完整業務流程。見 [4.1 log schema](/backend/04-observability/log-schema/)。

## 使用情境

系統需要 correlation ID 的訊號是事故排查需要跨同步與非同步邊界。訂單建立 request、付款事件、寄信 job 與出貨事件共享同一 correlation ID，讓客服跟工程師追到完整流程。

## 判斷條件與後果

Correlation ID 是否串得起一個業務流程，取決於它在哪裡建立、傳到哪裡、欄位名稱是否一致。入口（API gateway 或第一個服務）沒有建立，也沒有接收 upstream 帶來的值時，每個服務各自產生一個 ID，訂單建立、付款事件與出貨 job 的 log 之間沒有共同的值可查。ID 只寫進 log、沒有放進 message header、trace context 與外部呼叫時，流程在跨過 queue 或外部 API 的那一步斷開，原因是非同步的 consumer 只拿得到訊息本身帶的欄位。各服務的欄位名稱漂移成 `request_id`、`req_id`、`requestId` 時，值都在，一條查詢卻找不全，排查的人要先知道每個服務各用哪個名字。這個 ID 會出現在 log、header 與外部呼叫裡，拿 email 或電話這類敏感資料當 ID 時，敏感資料跟著擴散到每一個收得到 ID 的系統。
