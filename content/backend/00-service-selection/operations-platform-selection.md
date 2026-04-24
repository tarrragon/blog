---
title: "0.4 操作平台選型"
date: 2026-04-23
description: "區分 log、metric、trace、dashboard、alert、deployment 與 reliability 的選型邊界"
weight: 4
---

操作平台選型的核心原則是先判斷系統需要哪一種操作能力。[log](/backend/knowledge-cards/log/)、metric、[trace](/backend/knowledge-cards/trace/)、[dashboard](/backend/knowledge-cards/dashboard/)、[alert](/backend/knowledge-cards/alert/)、deployment platform 與 reliability pipeline 都服務於系統運行，但它們回答的問題不同。

## 本章目標

學完本章後，你將能夠：

1. 區分 log、metric、trace、dashboard 與 alert 的用途
2. 判斷部署平台與可靠性驗證流程解決的問題
3. 用事故症狀和操作需求判斷應先補哪種平台能力
4. 把操作平台選型轉成可檢查的工程判斷

---

## 【觀察】操作問題會表現成診斷或交付困難

操作平台需求通常來自事故、擴容、發版或維護壓力。當服務在本機可用，但到生產環境後很難診斷、告警、部署或驗證，問題就已經超出語言本身。

| 需求訊號                   | 代表的工程問題                                          | 優先評估方向                                 |
| -------------------------- | ------------------------------------------------------- | -------------------------------------------- |
| 只知道錯了，看不到上下文   | 操作事件與錯誤脈絡                                      | log aggregation                              |
| 想看趨勢、容量、錯誤率     | 數值訊號與 [SLI/SLO](/backend/knowledge-cards/sli-slo/) | [metrics](/backend/knowledge-cards/metrics/) |
| 跨服務 request path 不清楚 | 呼叫鏈與延遲拆解                                        | tracing                                      |
| 團隊需要共同看服務健康     | 視覺化與操作入口                                        | dashboard                                    |
| 問題發生時需要主動通知     | 告警與 [runbook](/backend/knowledge-cards/runbook/)     | alerting                                     |
| 發版與擴容不穩             | 平台合約與流量入口                                      | deployment platform                          |
| 想驗證系統能承受壓力與失敗 | 可靠性驗證                                              | reliability pipeline                         |

這張表是索引。每種能力都可以採用不同產品與平台，但第一步是判斷你缺的是哪一種操作能力。

## 【判讀】log aggregation 承擔事件脈絡

log aggregation 的核心責任是收集可搜尋的操作事件。當工程師需要知道某個 request、event、worker 或 client 發生了什麼，log 是最直接的診斷入口。

接近真實網路服務的例子包括：

- 查某筆訂單 [webhook](/backend/knowledge-cards/webhook/) 為什麼被拒絕
- 查某個 [queue](/backend/knowledge-cards/queue/) message 重試了幾次
- 查某個 client 連線何時建立、何時斷線

這類平台的主要風險是欄位不穩定與敏感資料外洩。[log schema](/backend/knowledge-cards/log-schema/) 要像 [API Contract](/backend/knowledge-cards/api-contract/) 一樣維持欄位名稱，並在服務輸出前控制 token、payload 與個資。

## 【判讀】metrics 承擔趨勢與容量判斷

metrics 的核心責任是把服務狀態轉成可聚合的數值。當團隊需要看錯誤率、延遲、[throughput](/backend/knowledge-cards/throughput/)、queue lag、goroutine count 或 [cache hit rate](/backend/knowledge-cards/cache-hit-rate/)，metrics 是主要工具。

接近真實網路服務的例子包括：

- API p95 latency 是否持續上升
- queue lag 是否超過 [consumer](/backend/knowledge-cards/consumer/) 處理能力
- Redis [hot key](/backend/knowledge-cards/hot-key/) 是否造成 [timeout](/backend/knowledge-cards/timeout/) 增加

這類平台的主要風險是 cardinality。label 設計要能聚合趨勢，同時避免把 user id、[request id](/backend/knowledge-cards/request-id/) 這類高基數欄位放進 metric。

## 【判讀】tracing 承擔跨服務路徑

tracing 的核心責任是把一次 request 或事件處理串成跨服務路徑。當一個操作會經過 [API Gateway](/backend/knowledge-cards/api-gateway/)、[Request Routing](/backend/knowledge-cards/request-routing/)、service、[database](/backend/knowledge-cards/database/)、queue、worker 和外部 API，trace 可以拆解每一段延遲與錯誤位置。

接近真實網路服務的例子包括：

- checkout request 經過 cart、payment、inventory、shipping 多個服務
- [webhook](/backend/knowledge-cards/webhook/) 進入後觸發 queue，再由 worker 呼叫外部 API
- [BFF](/backend/knowledge-cards/bff/) API 聚合多個下游服務造成延遲不穩

這類平台的主要風險是 context propagation。服務之間要傳遞 [trace id](/backend/knowledge-cards/trace-id/)、[span](/backend/knowledge-cards/span/) context 與 [correlation id](/backend/knowledge-cards/correlation-id/)，否則 trace 會在邊界斷掉。

## 【判讀】dashboard 與 alert 承擔操作決策

dashboard 的核心責任是讓團隊看見服務健康；alert 的核心責任是把需要動作的異常主動送到負責者面前。兩者應該連到同一套 SLI、SLO 與 runbook。

接近真實網路服務的例子包括：

- API error rate 超過 SLO 時通知 [on-call](/backend/knowledge-cards/on-call/)
- queue lag 超過可接受時間時提示擴容 consumer
- [WebSocket](/backend/knowledge-cards/websocket/) disconnect rate 在特定地區突然升高

這類平台的主要風險是噪音。alert 應對應可執行動作；dashboard 應服務排障與容量判斷，圖表呈現則要服務這些操作目標。

## 【判讀】deployment platform 承擔服務交付

deployment platform 的核心責任是讓服務穩定啟動、更新、接流量、擴容與停止。當問題集中在發版、健康檢查、資源限制、流量入口或服務發現，應先評估部署平台能力。

接近真實網路服務的例子包括：

- [rolling update](/backend/knowledge-cards/rolling-update/) 時新版本還沒 ready 就接到流量
- pod 被停止時還有 worker 和長連線尚未清理
- 多個 service instance 需要透過 [load balancer](/backend/knowledge-cards/load-balancer/) 與 [service registry](/backend/knowledge-cards/service-registry/)、[service discovery](/backend/knowledge-cards/service-discovery/) 協作

這類平台的主要風險是程式與平台合約不一致。服務要提供 [readiness](/backend/knowledge-cards/readiness/)、[liveness](/backend/knowledge-cards/health-check-liveness/)、[graceful shutdown](/backend/knowledge-cards/graceful-shutdown/) 與 resource usage 訊號；平台要根據這些訊號調度流量。

## 【判讀】reliability pipeline 承擔失敗前驗證

reliability pipeline 的核心責任是在事故前驗證系統承受能力。[CI pipeline](/backend/knowledge-cards/ci-pipeline/)、[load test](/backend/knowledge-cards/load-test/)、[fuzz test](/backend/knowledge-cards/fuzz-test/)、[chaos test](/backend/knowledge-cards/chaos-test/) 都屬於可靠性驗證，但它們觀察的風險不同。

接近真實網路服務的例子包括：

- 發版前確認 [API Contract](/backend/knowledge-cards/api-contract/) 和 [migration](/backend/knowledge-cards/migration/) 能一起通過
- 高流量活動前用 [load test](/backend/knowledge-cards/load-test/) 驗證容量
- 對 parser、[protocol](/backend/knowledge-cards/protocol/) 或 [input validation](/backend/knowledge-cards/input-validation/) 做 fuzz campaign
- 在預備環境演練 [broker](/backend/knowledge-cards/broker/)、database、network failure

這類流程的主要風險是測試和真實系統脫節。可靠性驗證要對準實際 failure mode，並產出可行的修正或容量決策。

## 【檢查】進入實作前的概念邊界清單

當以下問題都能回答時，代表本章的概念層已完成，可以進入操作平台實作章節：

1. 每種觀測訊號的責任是否明確（log、metric、trace、alert）
2. 告警是否對應可執行動作與 runbook
3. 部署平台與服務合約是否明確（readiness、shutdown、資源限制）
4. 可靠性驗證是否有固定入口（CI、load、chaos）

下一步建議路由：

- [04-observability](/backend/04-observability/)
- [05-deployment-platform](/backend/05-deployment-platform/)
- [06-reliability](/backend/06-reliability/)

## 小結

操作平台選型要先看團隊缺的是哪種運行能力。需要事件脈絡看 log，需要趨勢看 metrics，需要跨服務路徑看 tracing，需要共同操作入口看 dashboard，需要主動通知看 alert，需要穩定交付看 deployment platform，需要事故前驗證看 reliability pipeline。分類清楚後，產品與工具比較才會有明確目標。
