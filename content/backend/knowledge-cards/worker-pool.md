---
title: "Worker Pool"
date: 2026-04-23
description: "說明一組 worker 如何限制同時處理量並保護下游資源"
weight: 127
---

Worker pool 的核心概念是「用固定或可控數量的 worker 處理工作」。它讓系統限制同時執行量，避免每個 request 或 message 都直接建立無界工作。 可先對照 [In-Process Channel](/backend/knowledge-cards/in-process-channel/)。

## 跟其他概念的關係

Worker pool 是 application 內部的容量控制工具。它常和 [in-process channel](/backend/knowledge-cards/in-process-channel/)、[queue depth](/backend/knowledge-cards/queue-depth/)、[backpressure](/backend/knowledge-cards/backpressure/)、[bulkhead](/backend/knowledge-cards/bulkhead/)、[dependency isolation](/backend/knowledge-cards/dependency-isolation/) 與 [graceful shutdown](/backend/knowledge-cards/graceful-shutdown/) 一起使用。

## 可觀察訊號與例子

系統需要 worker pool 的訊號是工作可以排隊，但同時執行量需要受控。圖片縮圖、匯出報表、外部 API 同步與 webhook retry 都可以用 worker pool 限制 CPU、連線或下游 API 壓力。

## 判斷條件與後果

Worker pool 的參數決定超出處理能力的工作去了哪裡。worker 數是同時執行量的上限；queue 長度沒有上限時，工作在記憶體裡持續累積，處理不完時程序被 OOM 終止，有上限時多出來的工作被拒絕，壓力回到上游形成 [backpressure](/backend/knowledge-cards/backpressure/)；沒有等待期限時，排隊太久的工作在呼叫方早已逾時之後才執行；shutdown 不等 worker 收尾時，處理到一半的工作直接遺失；沒有錯誤回報與觀測欄位時，分不出工作卡在排隊還是卡在執行。瓶頸在 [connection pool](/backend/knowledge-cards/connection-pool/)、[HTTP client](/backend/knowledge-cards/http-client/) pool 或外部 API quota 時，加大 worker 數只是讓更多 worker 在那些位置排隊，吞吐不變，所以加 worker 之前先確認瓶頸的位置。
