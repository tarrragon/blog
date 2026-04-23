---
title: "HTTP Client"
date: 2026-04-23
description: "說明服務呼叫外部 HTTP 依賴時需要管理 timeout、連線與重試"
weight: 127
---

HTTP client 的核心概念是「application 對外部 HTTP 服務發出 request 的呼叫邊界」。這個邊界需要管理 [timeout](../timeout/)、[deadline](../deadline/)、[connection pool](../connection-pool/)、[retry policy](../retry-policy/)、[TLS](../tls-mtls/)、錯誤分類與觀測欄位。

## 概念位置

HTTP client 是常見下游依賴入口。它可能呼叫付款、通知、搜尋、身份驗證、第三方 API 或內部微服務；每個 client 都會把外部延遲與失敗帶回 application。

## 可觀察訊號與例子

系統需要整理 HTTP client 的訊號是下游 API 變慢後，上游 request latency 與 worker 等待同步上升。付款 API timeout 時，checkout 要能快速分類錯誤、限制重試並保留使用者流程。

## 設計責任

HTTP client 要定義連線池、timeout、[retry budget](../retry-budget/)、[backoff](../exponential-backoff/)、[jitter](../jitter/)、[circuit breaker](../circuit-breaker/)、[authentication](../authentication/)、TLS 與 [log](../log-schema/) / [metrics](../metrics/) / [trace](../trace-context/) 欄位。不同下游應有獨立設定與觀測名稱。
