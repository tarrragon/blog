---
title: "4.3 tracing 與 context link"
date: 2026-06-22
description: "整理 trace id、span 與跨服務 context propagation"
weight: 3
tags: ["backend", "observability"]
---

## 大綱

- [trace](/backend/knowledge-cards/trace/) / [span](/backend/knowledge-cards/span/) 模型
- [trace context](/backend/knowledge-cards/trace-context/) propagation
- context 斷鏈的常見邊界與修復
- [sampling](/backend/knowledge-cards/sampling/) 策略的 tracing 面（SSoT 在 [4.7](/backend/04-observability/cardinality-cost-governance/#sampling-策略)）
- service graph 與依賴發現
- 反模式

## 概念定位

[Trace](/backend/knowledge-cards/trace/) 是把一次 request 在多個服務、queue 與背景任務中的路徑串起來的診斷訊號，責任是讓團隊從症狀追到跨服務等待點。

Log 回答「某個服務發生了什麼」；metric 回答「某個服務的健康趨勢」；trace 回答「一次 request 跨多個服務時，時間花在哪、錯誤發生在哪一段」。三者互補，trace 的獨特價值在於它串起跨服務的因果鏈 — 沒有 trace，事故定位只能靠人工比對不同服務的 log timestamp。

本章處理的是 context propagation — 怎麼讓 [trace context](/backend/knowledge-cards/trace-context/) 在 HTTP call、queue 投遞、背景任務啟動等邊界上正確傳遞。Context 斷掉時，trace 從「完整路徑」退化成幾段需要人工拼接的局部紀錄，跨服務診斷的時間成本會從秒級回退到分鐘甚至小時級。

## Trace 與 Span 的結構

### Span 是 trace 的基本單位

一個 [span](/backend/knowledge-cards/span/) 代表一段有起止時間的工作。每個 span 記錄：操作名稱（`POST /api/orders`）、開始與結束時間、狀態（OK / Error）、屬性（service name、http.status_code、db.statement）與事件（exception、log message）。

Span 之間透過 parent-child 關係組成 tree。一個 HTTP request 進入 API gateway 時建立 root span，gateway 呼叫 order service 時建立 child span，order service 查 DB 時建立另一個 child span。整棵 tree 共享同一個 [trace id](/backend/knowledge-cards/trace-id/)，讓所有 span 可以被聚合成一次 request 的完整路徑。

### Trace 是 span tree

一個 [trace](/backend/knowledge-cards/trace/) 是所有共享同一個 trace id 的 span 的集合。在 waterfall view 中，trace 呈現為時間軸上的巢狀條狀圖 — root span 在最上面，child span 依序往下排列，每段的長度代表耗時。

Waterfall view 的診斷價值是「一眼看到時間花在哪」。如果 checkout API 的 total latency 是 800ms，waterfall 會顯示 payment service 佔了 600ms — 問題定位從「整個 checkout 慢」縮小到「payment service 慢」，後續 debug 只需要看 payment service 的 log 跟 metric。

## Context Propagation

### 什麼是 trace context

[Trace context](/backend/knowledge-cards/trace-context/) 是跨服務傳遞 trace 身份的資料。最小的 trace context 包含 trace id（標識整條 trace）跟 parent span id（標識上游 span）。下游服務收到 trace context 後，建立新的 child span 並繼承 trace id，讓兩端的 span 歸屬同一條 trace。

W3C Trace Context 標準定義了 HTTP header 的傳遞格式：`traceparent` header 帶 trace id + parent span id + trace flags，`tracestate` header 帶 vendor-specific 的附加資訊。OpenTelemetry SDK 預設使用 W3C 格式；部分 vendor 有自己的 header 格式（Datadog 用 `x-datadog-trace-id`、AWS X-Ray 用 `X-Amzn-Trace-Id`），需要在 collector 或 SDK 層做格式轉換。

### Propagation 的傳遞機制

HTTP call 是最常見的 propagation 路徑 — SDK 的 HTTP client middleware 自動把 trace context 注入 request header，下游 SDK 的 HTTP server middleware 自動從 header 提取 context。大部分 OpenTelemetry SDK 的 auto-instrumentation 會自動處理這一層，開發者不需要手動注入。

gRPC 用 metadata（等同 HTTP header）傳遞，機制類似。

Message queue 的 propagation 需要把 trace context 放進 message 的 header 或 metadata。Kafka 用 record header、RabbitMQ 用 message properties、NATS 用 message header。Producer 端注入、consumer 端提取。Queue 的 propagation 比 HTTP 複雜的原因是 consumer 可能在 producer 之後很久才消費 — context 的時間跨度可能從毫秒擴大到分鐘或小時。

### Context 斷鏈的常見邊界

Context propagation 在以下邊界容易斷裂：

**Thread / goroutine / task 邊界**：同步 runtime 通常用 thread-local 存放 context，新開 thread 不會自動繼承。Go 用 `context.Context` 顯式傳遞，相對不容易遺漏；Java 用 ThreadLocal，啟動新 thread 或提交到 thread pool 時 context 需要手動傳遞或用 agent auto-instrumentation。Async runtime（Node.js 的 AsyncLocalStorage、Python 的 contextvars）各有自己的 context 傳播機制。

**Queue / event 邊界**：producer 把 trace context 注入 message header，consumer 提取並建立新 span。如果 producer 端的 SDK 沒有自動注入（例如用了原生 Kafka client 而非 instrumented client），context 就斷了。跨 queue 的 trace 在 waterfall view 中會出現時間斷層 — producer span 結束到 consumer span 開始之間可能有秒級到分鐘級的等待。

**Background job / cron 邊界**：cron job 或 scheduled task 沒有上游 request，沒有 trace context 可繼承。這類工作需要在啟動時建立 root span，並把 job name、schedule、trigger reason 作為 span 屬性，讓 trace 至少可以追蹤 job 內部的行為。

**跨語言 / 跨 vendor 邊界**：不同語言的 SDK 或不同 vendor 的 instrumentation 可能用不同的 header 格式。W3C Trace Context 標準解決了格式問題，但混用 vendor-specific SDK 時（例如一個服務用 Datadog agent、另一個用 OTel SDK），需要在 collector 層做 context format 轉換。

### 斷鏈的修復策略

修復斷鏈的目標是讓 trace 在邊界處重新接上，不需要人工拼接。

**Queue 邊界**：確保 producer 跟 consumer 都使用 instrumented client（OTel SDK 的 messaging instrumentation），而非原生 client。Instrumented client 自動處理 header 注入跟提取。Consumer 端建立的 span 用 `CONSUMER` kind 標記，waterfall view 會顯示 queue 等待時間。

**Thread pool 邊界**：Java 生態用 `Context.wrap()` 包裝提交到 thread pool 的 Runnable/Callable；Go 生態用 `context.Context` 作為第一個函數參數傳遞（這是 Go 的慣例，不需要額外處理）。Auto-instrumentation agent 可以自動處理常見 thread pool（Java 的 ExecutorService、Node.js 的 worker_threads）。

**跨 vendor 邊界**：在 collector 層（OTel Collector）統一轉換 header 格式。Collector 的 receiver 支援多種格式輸入，exporter 統一輸出 W3C 格式。這層轉換在 [4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/) 的 collector 中介段處理。

## Trace 與 Log / Metric 的關聯

### Correlation id 統一

[Trace id](/backend/knowledge-cards/trace-id/) 應該同時出現在 log 的結構化欄位中。當 log 的 `trace_id` 欄位帶著跟 trace 相同的值，debug 工作流就能從 trace waterfall 跳到某個 span 對應的 log，或從 log 跳到完整的 trace view。

實作方式是在 logger 初始化時，把當前 span 的 trace id 注入 log 的 context fields。OTel SDK 的 log bridge 可以自動做這件事；沒有自動橋接的框架需要手動把 `span.SpanContext().TraceID()` 寫進 log 的 [correlation id](/backend/knowledge-cards/correlation-id/) 欄位。

### Exemplar：metric 到 trace 的跳板

Metric 是聚合訊號，本身不帶單一 request 的 trace id。Exemplar 是附加在 metric 資料點上的代表性 trace id — 當某個 histogram bucket 收到一個資料點時，附帶記錄產生這個資料點的 trace id。

Dashboard 上看到 latency p99 升高時，可以從 exemplar 跳到一個具體的高延遲 trace，看 waterfall 定位慢在哪。Exemplar 是 metric 到 trace 的橋樑，讓聚合訊號（metric）跟個別案例（trace）連接起來。

## Service Graph 與依賴發現

Trace 資料聚合後可以自動生成 service graph — 哪些服務在呼叫哪些服務、call 的頻率、延遲分布、錯誤率。這個 graph 跟手動維護的 architecture diagram 不同：它來自實際流量，反映的是「現在真的在發生什麼」而非「設計時預期會發生什麼」。

Service graph 的價值在於依賴發現。新服務加入後，如果有 trace instrumentation，它會自動出現在 graph 上。舊服務之間新增的依賴（例如 A 開始直接呼叫 C、繞過 B）也會被 graph 反映。手動維護的 wiki 通常落後實際狀況數週到數月。

Service graph 的完整性取決於 trace 的覆蓋率。如果某些服務沒有 instrumentation 或 sampling 率太低，graph 上會出現斷點或邊權不準。把 service graph 的完整性（「有多少比例的服務有 trace」）作為觀測覆蓋率的一個指標，能推動 instrumentation 的漸進覆蓋。

詳見 [4.13 service topology](/backend/04-observability/service-topology/)。

## 核心判讀

判讀 tracing 時，先看 propagation 是否完整，再看 sampling 是否保留可除錯樣本。

重點訊號包括：

- [trace id](/backend/knowledge-cards/trace-id/) 是否能和 log、metric 共享 [correlation id](/backend/knowledge-cards/correlation-id/)
- async / queue / background job 是否能保留 parent-child 關係
- sampling 是否能在高流量下保留錯誤與高延遲樣本（策略矩陣見 [4.7](/backend/04-observability/cardinality-cost-governance/#sampling-策略)）
- service graph 是否能由 trace 聚合而來，並降低 wiki 手動維護成本
- trace context 在跨語言 / 跨 vendor 邊界是否用 W3C 標準統一

## 判讀訊號

- Request 跨服務後 trace 斷鏈、靠人重組
- Async / queue 邊界 context 沒傳遞
- 採樣率太低、production debug 找不到對應 trace
- Trace id 跟 log / metric 對不上、無共同 correlation key
- Service graph 不存在或半年沒人看
- 多個 vendor SDK 混用、header 格式不一致
- Background job / cron 沒有 root span、trace 無法追蹤

## 反模式

| 反模式                            | 表面現象                                  | 修正方向                                            |
| --------------------------------- | ----------------------------------------- | --------------------------------------------------- |
| 只 instrument HTTP、忽略 queue    | Queue 消費後的 span 都是孤兒              | Producer / consumer 都用 instrumented client        |
| Thread pool 不傳 context          | 平行處理的 span 不歸屬任何 trace          | 用 Context.wrap() 或語言慣例傳遞 context            |
| Trace id 沒寫進 log               | 從 log 找不到對應 trace、反向也找不到     | Logger context 注入 trace id                        |
| 混用 vendor header 無轉換         | 部分服務的 span 串不進同一條 trace        | Collector 層統一轉換成 W3C 格式                     |
| 所有 span 都是 root span          | Trace 只有一層、沒有 parent-child 結構    | 確認 SDK 的 context extraction 有正確從 header 繼承 |
| Background job 無 instrumentation | Job 內的 DB / HTTP call 沒有 trace 可追蹤 | Job 啟動時建立 root span、內部操作作為 child span   |

## 交接路由

- [4.4 dashboard-alert](/backend/04-observability/dashboard-alert/)：trace 資料在 dashboard 的呈現跟 alert 設計
- [4.7 cardinality / cost](/backend/04-observability/cardinality-cost-governance/#sampling-策略)：sampling 策略矩陣（Head / Tail / Adaptive / Exemplar）與保留決策
- [4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/)：sampling 在 collector 的集中治理、跨 vendor header 轉換
- [4.13 service topology](/backend/04-observability/service-topology/)：trace 訊號聚合成依賴圖
- [4.17 telemetry data quality](/backend/04-observability/telemetry-data-quality/)：sampling bias 跟 trace 完整性的資料品質
- [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)：trace 查詢作為即席診斷的一種模式
