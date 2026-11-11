---
title: "HTTP Client"
date: 2026-04-23
description: "說明服務呼叫外部 HTTP 依賴時需要管理 timeout、連線與重試"
weight: 128
---

HTTP client 的核心概念是「application 對外部 HTTP 服務發出 request 的呼叫邊界」。這個邊界需要管理 [timeout](/backend/knowledge-cards/timeout/)、[deadline](/backend/knowledge-cards/deadline/)、[connection pool](/backend/knowledge-cards/connection-pool/)、[retry policy](/backend/knowledge-cards/retry-policy/)、[TLS](/backend/knowledge-cards/tls-mtls/)、錯誤分類與觀測欄位。

## 跟其他概念的關係

HTTP client 是常見下游依賴入口。它可能呼叫付款、通知、搜尋、身份驗證、第三方 API 或內部微服務；每個 client 都會把外部延遲與失敗帶回 application。 可先對照 [Timeout](/backend/knowledge-cards/timeout/)。

## 可觀察訊號與例子

系統需要整理 HTTP client 的訊號是下游 API 變慢後，上游 request latency 與 worker 等待同步上升。付款 API timeout 時，checkout 要能快速分類錯誤、限制重試並保留使用者流程。

## 判斷條件與後果

HTTP client 的每一項設定缺席時，下游的延遲與失敗以不同形式回到 application。沒有 timeout 時，下游變慢讓 worker 一直等，上游的 request latency 跟著上升；連線池沒有上限時，下游變慢期間連線數持續增加；retry 沒有 [retry budget](/backend/knowledge-cards/retry-budget/)、[backoff](/backend/knowledge-cards/exponential-backoff/) 與 [jitter](/backend/knowledge-cards/jitter/) 時，已經過載的下游還收到成倍的重試；沒有 [circuit breaker](/backend/knowledge-cards/circuit-breaker/) 時，下游持續失敗的期間每個請求仍等到 timeout 才失敗。[authentication](/backend/knowledge-cards/authentication/) 或 TLS 設定錯誤時每個請求都失敗，錯誤分類沒有把這一類跟下游故障分開時，它會被重試，而重試不會成功。所有下游共用一組設定與觀測名稱時，付款 API 變慢會佔住通知 API 也在用的連線與 worker，[log](/backend/knowledge-cards/log-schema/) / [metrics](/backend/knowledge-cards/metrics/) / [trace](/backend/knowledge-cards/trace-context/) 上也分不出是哪一個下游，所以每個下游有自己的設定與觀測名稱。
