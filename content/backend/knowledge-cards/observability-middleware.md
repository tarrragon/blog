---
title: "Observability Middleware"
date: 2026-04-23
description: "說明請求進入 handler 前後如何補上觀測欄位"
weight: 1
---

Observability Middleware 的核心概念是「在 request 進入與離開 handler 的過程中，補上可觀測欄位與上下文」。 可先對照 [Offline Catch-up](/backend/knowledge-cards/offline-catchup/)。

## 跟其他概念的關係

Observability Middleware 位在 transport layer 與業務 handler 之間。它通常負責 request id、trace context、log context 與 timing。 可先對照 [Offline Catch-up](/backend/knowledge-cards/offline-catchup/)。

## 可觀察訊號

系統需要 observability middleware 的訊號是很多 handler 都需要相同的追蹤欄位與可查詢上下文。

## 接近真實網路服務的例子

request id 注入、trace context 傳遞、latency 記錄與結束時的操作 log，都屬於 observability middleware 的責任。

## 判斷條件與後果

Observability Middleware 是 request id、trace context 與 log context 進入各個 handler 的共同入口，它在哪一處斷掉，之後的觀測資料就從那一處失去關聯。context 沒有往下傳遞時，handler 寫的 log 不帶 request id，trace 在這一段斷開，同一次 request 的紀錄串不起來。middleware 包裝錯誤時丟掉原本的 error chain，上層只看得到包裝後的訊息，原始的錯誤類型與發生位置都不見了。log、metric、trace 各自命名欄位時，同一個 request 在三種資料裡用不同的鍵，從 metric 的異常找到對應的 trace 與 log，只能靠人工比對時間。
