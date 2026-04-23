---
title: "模組四：可觀測性平台"
date: 2026-04-22
description: "整理 log、metric、trace、dashboard 與 alert 的後端操作實務"
weight: 4
---

可觀測性模組的核心目標是說明服務如何把 [log schema](../00-knowledge-cards/log-schema/)、[metrics](../00-knowledge-cards/metrics/) 與 [trace context](../00-knowledge-cards/trace-context/) 轉成可操作的診斷系統。語言教材會處理標準 logger、runtime 訊號、diagnostics endpoint 與 trace context 邊界；本模組負責平台、資料流與操作規則。

## 暫定分類

| 分類            | 內容方向                                             |
| --------------- | ---------------------------------------------------- |
| Log aggregation | log schema、索引、查詢、保留策略                     |
| Metrics         | counter、gauge、histogram、cardinality、Prometheus   |
| Tracing         | span、trace id、context propagation、OpenTelemetry   |
| Dashboard       | SLI、SLO、容量趨勢、服務健康                         |
| Alert           | alert rule、noise control、runbook、on-call workflow |

## 選型入口

可觀測性選型的核心判斷是團隊缺少哪一種操作訊號。當工程師需要還原事件脈絡時先看 log；需要趨勢與容量判斷時先看 metrics；需要跨服務路徑時先看 tracing；需要共同操作入口時先看 dashboard；需要主動通知時先看 alert。

Log aggregation 適合查單一事件與錯誤脈絡；metrics 適合觀察 error rate、latency、throughput 與 queue lag；tracing 適合拆解跨服務 request path；dashboard 適合整合 [SLI/SLO](../00-knowledge-cards/sli-slo/) 與容量趨勢；alert 適合把需要動作的異常送到負責者面前，並連到 [alert runbook](../00-knowledge-cards/alert-runbook/)。

接近真實網路服務的例子包括 checkout 變慢、queue lag 上升、WebSocket 斷線增加、Redis timeout 增加與下游 API 錯誤率上升。這些場景的共同問題是從症狀回到原因，因此本模組會先處理欄位、關聯、[metric cardinality](../00-knowledge-cards/metric-cardinality/)、查詢、視覺化與告警規則。

## 與語言教材的分工

語言教材處理如何產生穩定欄位與 runtime 訊號。Backend observability 模組處理收集、儲存、查詢、視覺化、告警與跨服務關聯。

## 跨語言適配評估

可觀測性使用方式會受語言的 logger 生態、context propagation、exception/error model、runtime metrics 與 instrumentation SDK 影響。同步 runtime 要保留 request context 與 thread-local 邊界；async runtime 要確認 trace context 能跨 task 傳遞；輕量並發 runtime 要觀察 task/goroutine 數量、queue lag 與下游等待。動態語言要特別管理 log schema 穩定性；強型別語言則要避免過度包裝導致 trace 與 error chain 斷裂。

## 章節列表

| 章節                          | 主題                     | 關鍵收穫                                                     |
| ----------------------------- | ------------------------ | ------------------------------------------------------------ |
| [4.1](log-schema/)            | log schema 與搜尋規劃     | 設計欄位、索引與查詢方式                                      |
| [4.2](metrics-basics/)        | metrics 與 SLI/SLO        | 用 counter、gauge、histogram 描述服務健康                    |
| [4.3](tracing-context/)       | tracing 與 context link   | 追蹤跨服務 request path                                       |
| [4.4](dashboard-alert/)       | dashboard 與 alert 設計   | 讓告警能對應 runbook 與容量趨勢                                |
