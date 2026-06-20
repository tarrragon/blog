---
title: "Bulkhead 資源隔離"
date: 2026-06-20
description: "防止一個慢依賴佔滿所有資源 — 連線池、goroutine pool、佇列的隔離設計"
weight: 4
tags: ["devops", "traffic-management", "bulkhead", "isolation", "resilience"]
---

Bulkhead 是把服務的資源（連線池、執行緒、佇列）按依賴或功能分區隔離的模式。一個依賴變慢時只消耗自己分區的資源，不會拖垮其他依賴的請求處理。

## 為什麼需要隔離

沒有隔離時，一個慢依賴（回應時間從 50ms 變成 5 秒）會佔住越來越多的連線和 goroutine。當連線池耗盡，連帶其他正常依賴的請求也無法送出 — 一個依賴的問題變成全局的問題。

## 隔離方式

### 連線池隔離

每個外部依賴用獨立的 HTTP client 和連線池。依賴 A 的連線池滿了不影響依賴 B。

### Goroutine pool 隔離

用 semaphore 或 worker pool 限制對每個依賴的並行請求數。Go 的 `golang.org/x/sync/semaphore` 是簡單的實作。

### 佇列隔離

每個依賴有獨立的請求佇列。佇列滿時快速失敗（回 503），不排隊等待。

## 和熔斷器的配合

Bulkhead 隔離資源、circuit breaker 切斷流量。兩者配合：bulkhead 防止資源被慢依賴佔完，circuit breaker 在失敗累積後直接停止對該依賴的請求。

## 下一步路由

- 熔斷器 → [熔斷器](/devops/03-traffic-management/circuit-breaker/)
- 背壓 → [背壓](/devops/03-traffic-management/backpressure/)
- Rate limiting → [Rate Limiting](/devops/03-traffic-management/rate-limiting/)
