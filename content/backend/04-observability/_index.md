---
title: "模組四：可觀測性平台"
date: 2026-04-22
description: "整理 log、metric、trace、dashboard 與 alert 的後端操作實務"
weight: 4
---

可觀測性模組的核心目標是說明服務如何把 [log schema](/backend/knowledge-cards/log-schema/)、[metrics](/backend/knowledge-cards/metrics/) 與 [trace context](/backend/knowledge-cards/trace-context/) 轉成可操作的診斷系統。語言教材會處理標準 logger、執行環境訊號、[Diagnostic Endpoint](/backend/knowledge-cards/diagnostic-endpoint/) 與 [trace context](/backend/knowledge-cards/trace-context/) 邊界；本模組負責平台、資料流與操作規則。

## Vendor / Platform 清單

實作時的常用選擇見 [vendors](/backend/04-observability/vendors/) — T1 收錄 OpenTelemetry / Prometheus / Grafana Stack / Datadog / Elastic Stack / Honeycomb / AWS CloudWatch / GCP Cloud Operations / Sentry，每個 vendor 有定位、適用場景、取捨與預計實作話題的骨架。Error tracking 是獨立子維度（Sentry），跟 metrics / logs / traces 三角互補。

## 暫定分類

| 分類                                            | 內容方向                                                                                                                                                      |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Log](/backend/knowledge-cards/log) aggregation | [log schema](/backend/knowledge-cards/log-schema)、索引、查詢、保留策略                                                                                       |
| [Metrics](/backend/knowledge-cards/metrics)     | counter、gauge、[histogram](/backend/knowledge-cards/histogram)、cardinality、Prometheus                                                                      |
| Tracing                                         | [span](/backend/knowledge-cards/span)、[trace id](/backend/knowledge-cards/trace-id)、[trace context](/backend/knowledge-cards/trace-context/)、OpenTelemetry |
| [Dashboard](/backend/knowledge-cards/dashboard) | SLI、[SLO](/backend/knowledge-cards/sli-slo)、容量趨勢、服務健康                                                                                              |
| [Alert](/backend/knowledge-cards/alert)         | alert rule、noise control、[runbook](/backend/knowledge-cards/runbook)、[on-call](/backend/knowledge-cards/on-call) workflow                                  |

## 選型入口

可觀測性選型的核心判斷是團隊缺少哪一種操作訊號。當工程師需要還原事件脈絡時先看 log；需要趨勢與容量判斷時先看 metrics；需要跨服務路徑時先看 tracing；需要共同操作入口時先看 dashboard；需要主動通知時先看 alert。

Log aggregation 適合查單一事件與錯誤脈絡；metrics 適合觀察 error rate、latency、[throughput](/backend/knowledge-cards/throughput/) 與 [queue](/backend/knowledge-cards/queue) lag；tracing 適合拆解跨服務 request path；dashboard 適合整合 [SLI/SLO](/backend/knowledge-cards/sli-slo/) 與容量趨勢；alert 適合把需要動作的異常送到負責者面前，並連到 [alert runbook](/backend/knowledge-cards/alert-runbook/)。

接近真實網路服務的例子包括 checkout 變慢、queue lag 上升、[WebSocket](/backend/knowledge-cards/websocket/) 斷線增加、Redis [timeout](/backend/knowledge-cards/timeout) 增加與下游 API 錯誤率上升。這些場景的共同問題是從症狀回到原因，因此本模組會先處理欄位、關聯、[metric cardinality](/backend/knowledge-cards/metric-cardinality/)、查詢、視覺化與告警規則。

## 跟可靠性與事故模組的串接

可觀測性是 04 → 06 → 08 閉環的起點，但閉環是雙向的：

- **04 → 08**：訊號（log spike、SLO burn rate、error rate）觸發告警、進入事故響應流程。判讀邊界由 04 定義、響應節奏由 08 定義。
- **04 → 06**：SLO / SLI 量測由 04 提供、是 6.6 SLO 政策與 6.4 chaos hypothesis 的 baseline。沒有可信訊號就沒有可信驗證。
- **06 → 04**：驗證需求驅動訊號設計 — chaos experiment 需要新 metric、load test 需要新 dashboard、SLO 政策需要新 alert rule。
- **08 → 04**：每次事故 postmortem 揭露偵測缺口（symptom-based alert 缺、訊號太晚、cardinality 不足），回寫到 04 訊號治理（7.13 / 04.4）。
- **詳細閉環說明**：見 [8.11 Observability / Reliability / Incident Response 閉環](/backend/08-incident-response/observability-reliability-incident-loop/)。

## 與語言教材的分工

語言教材處理如何產生穩定欄位與執行環境訊號。Backend observability 模組處理收集、儲存、查詢、視覺化、告警與跨服務關聯。

## 跨語言適配評估

可觀測性使用方式會受語言的 logger 生態、[trace context](/backend/knowledge-cards/trace-context/)、exception/error model、執行環境 metrics 與 instrumentation SDK 影響。同步 runtime 要保留 request context 與 thread-local 邊界；async runtime 要確認 [trace context](/backend/knowledge-cards/trace-context/) 能跨 task 傳遞；輕量並發 runtime 要觀察 task/goroutine 數量、queue lag 與下游等待。動態語言要特別管理 log schema 穩定性；強型別語言則要避免過度包裝導致 trace 與 error chain 斷裂。

## 章節列表

| 章節                                                                | 主題                                 | 關鍵收穫                                   |
| ------------------------------------------------------------------- | ------------------------------------ | ------------------------------------------ |
| [4.1](/backend/04-observability/log-schema/)                        | log schema 與搜尋規劃                | 設計欄位、索引與查詢方式                   |
| [4.2](/backend/04-observability/metrics-basics/)                    | metrics 與 SLI/SLO                   | 用 counter、gauge、histogram 描述服務健康  |
| [4.3](/backend/04-observability/tracing-context/)                   | tracing 與 context link              | 追蹤跨服務 request path                    |
| [4.4](/backend/04-observability/dashboard-alert/)                   | dashboard 與 alert 設計              | 讓告警能對應 runbook 與容量趨勢            |
| [4.5](/backend/04-observability/attacker-view-observability-risks/) | 攻擊者視角（紅隊）：可觀測性弱點判讀 | 用盲區、告警失真與資料暴露風險檢查觀測系統 |
