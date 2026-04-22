---
title: "7.4 Observability pipeline、metrics 與 tracing"
date: 2026-04-22
description: "把 structured log、metric、trace 與 profile 組成可操作的診斷系統"
weight: 4
---

Observability pipeline 的核心責任是把服務訊號整理成可查詢、可聚合、可關聯的診斷資料。Structured log 描述單次事件，metric 描述趨勢，trace 描述跨元件路徑，profile 描述 runtime 成本；它們的責任不同，但應使用一致的識別欄位串起來。

## 前置章節

- [Go 入門：log/slog：結構化日誌](../../go/03-stdlib/slog/)
- [Go 進階：pprof 基礎診斷流程](../03-runtime-profiling/pprof/)
- [Go 進階：結構化日誌欄位設計](../06-production-operations/log-fields/)
- [Go 進階：健康檢查與診斷 endpoint](../06-production-operations/health-diagnostics/)

## 後續撰寫方向

1. Log、metric、trace、profile 分別回答哪些問題。
2. `request_id`、`event_id`、`trace_id`、`span_id` 與 `correlation_id` 如何分工。
3. OpenTelemetry 導入時，Go 程式碼應保留哪些清楚邊界。
4. Sensitive data policy 如何套用到 log、trace attribute 與 error event。
5. Dashboard 與 alert 應依賴穩定欄位，而不是自由文字。

## 本章不處理

本章不會綁定特定 observability SaaS。教材重點會放在 Go 服務如何輸出穩定訊號，讓不同收集平台都能使用。
