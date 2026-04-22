---
title: "模組四：可觀測性平台"
date: 2026-04-22
description: "整理 log、metric、trace、dashboard 與 alert 的後端操作實務"
weight: 4
---

# 模組四：可觀測性平台

可觀測性模組的核心目標是說明服務如何把 log、metric、trace 轉成可操作的診斷系統。語言教材會處理標準 logger、runtime 訊號、diagnostics endpoint 與 trace context 邊界；本模組負責平台、資料流與操作規則。

## 暫定分類

| 分類 | 內容方向 |
|------|----------|
| Log aggregation | log schema、索引、查詢、保留策略 |
| Metrics | counter、gauge、histogram、cardinality、Prometheus |
| Tracing | span、trace id、context propagation、OpenTelemetry |
| Dashboard | SLI、SLO、容量趨勢、服務健康 |
| Alert | alert rule、noise control、runbook、on-call workflow |

## 與語言教材的分工

語言教材處理如何產生穩定欄位與 runtime 訊號。Backend observability 模組處理收集、儲存、查詢、視覺化、告警與跨服務關聯。

## 相關語言章節

- [Go：log/slog](../../go/03-stdlib/slog/)
- [Go 進階：pprof 基礎診斷流程](../../go-advanced/03-runtime-profiling/pprof/)
- [Go 進階：結構化日誌欄位設計](../../go-advanced/06-production-operations/log-fields/)
- [Go 進階：Observability pipeline、metrics 與 tracing](../../go-advanced/07-distributed-operations/observability-pipeline/)
