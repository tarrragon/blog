---
title: "7.4 Observability pipeline、metrics 與 tracing"
date: 2026-04-22
description: "把 structured log、metric、trace 與 profile 組成可操作的診斷系統"
weight: 4
---

Observability pipeline 的核心責任是把服務訊號整理成可查詢、可聚合、可關聯的診斷資料。Structured log 描述單次事件，metric 描述趨勢，trace 描述跨元件路徑，profile 描述 runtime 成本；它們的責任不同，但應使用一致的識別欄位串起來。

## 本章目標

學完本章後，你將能夠：

1. 分辨 log、metric、trace 與 profile 各自回答什麼問題
2. 設計穩定的 correlation 欄位
3. 讓 Go 服務輸出適合聚合的診斷訊號
4. 控制敏感資料不要流入觀測管線
5. 了解 dashboard 與 alert 為什麼不應依賴自由文字

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

## 【觀察】診斷資料要先可關聯，再談漂亮

如果 log、metric、trace 各自長得很漂亮，但欄位對不起來，排障時還是會很痛苦。observability pipeline 的第一個要求，不是格式華麗，而是能把同一筆請求、同一個事件、同一條 goroutine 路徑串起來。

通常會先建立幾個穩定欄位：

- request_id
- event_id
- trace_id
- span_id
- user_id 或 tenant_id

## 【判讀】不同訊號回答不同問題

- log：這次發生了什麼。
- metric：這類事件發生得多不多、快不快、慢不慢。
- trace：它在多個元件之間怎麼走。
- profile：CPU、記憶體、goroutine 與等待成本落在哪裡。

如果某個問題要靠自由文字 log 去猜，通常代表欄位設計還不夠穩。

## 【策略】敏感資料要在產生端就攔住

不要期待下游收集平台自己知道哪些欄位不該出現。Go 服務應該在輸出 log 或 trace attribute 前就決定哪些資訊可以外送。

常見要注意的資料有：

- token
- email
- 身分證號
- raw payload
- 內部路徑與配置

## 【執行】結構化 log 是 pipeline 的起點

當 Go 服務使用結構化 log 時，最重要的是欄位穩定與語意清楚。這些 log 後面可能會被：

- 集中式 log system 搜尋
- metric extraction 轉成趨勢指標
- alert rule 用來偵測異常

所以 log 欄位不要常常改名，也不要把分類資訊藏在自由文字裡。

## 【延伸】診斷和容量規劃要串在一起

觀測資料不只是事後排障，也會反過來影響容量規劃與 release 判斷。當你看到 goroutine 數、queue lag、DB latency 或 retry rate 持續變高，就代表系統邊界已經開始吃緊。

## 本章不處理

本章不會綁定特定 observability SaaS。教材重點會放在 Go 服務如何輸出穩定訊號，讓不同收集平台都能使用。

## 和 Go 教材的關係

這一章承接的是 Go 的結構化日誌與 runtime 診斷；如果你要先回看語言教材，可以讀：

- [Go：結構化日誌](../../go/03-stdlib/slog/)
- [Go 進階：pprof 基礎診斷流程](../03-runtime-profiling/pprof/)
- [Go 進階：結構化日誌欄位設計](../06-production-operations/log-fields/)
- [Go 進階：健康檢查與診斷 endpoint](../06-production-operations/health-diagnostics/)
