---
title: "8.10 Go 的高併發服務案例"
date: 2026-04-23
description: "從即時服務、邊緣網路與資料平台辨識 Go 的高併發使用情境"
weight: 10
---

高併發服務案例的核心判斷是「大量工作是否同時存在，且每個工作都需要清楚的生命週期」。Go 適合這類服務，因為 goroutine、channel、context、[timeout](/backend/knowledge-cards/timeout) 與標準網路庫可以共同描述工作如何開始、等待、取消與清理。

## 高併發型態

| 型態                | 主要壓力                                                          | 相關案例                        |
| ------------------- | ----------------------------------------------------------------- | ------------------------------- |
| 長連線與即時推送    | 大量 client、慢連線、斷線清理                                     | Twitch、Stream、Cloudflare      |
| 網路代理與邊緣服務  | timeout、連線管理、資源限制                                       | Cloudflare、Kubernetes 生態工具 |
| 背景處理與 pipeline | [fan-out](/backend/knowledge-cards/fan-out)、排隊、取消、錯誤回報 | PayPal、Dropbox                 |
| 分散式資料服務      | 複製、一致性、節點協調                                            | Cockroach Labs                  |

### 長連線與即時推送：先看 client 是否持續留在線上

長連線服務的核心訊號是「request 結束後，server 仍然需要替 client 保留狀態」。聊天室、直播狀態、feed 更新與即時通知，都需要管理 client 註冊、訂閱、心跳、send [buffer](/backend/knowledge-cards/buffer) 與清理流程。Go 的價值在於讓每條連線的讀取、寫入與取消責任能被拆成可讀的 goroutine 流程。

對應章節：[WebSocket 服務架構](/go-advanced/02-networking-websocket/)、[慢客戶端與 send buffer 管理](/go-advanced/02-networking-websocket/slow-client/)。

### 網路代理與邊緣服務：先看邊界是否充滿 timeout

網路代理與邊緣服務的核心訊號是「大量 I/O 邊界同時存在」。每個 request 都可能等待 DNS、[TLS](/backend/knowledge-cards/tls-mtls)、上游服務、client body 或 downstream response。Go 的 `net/http`、`context` 與 [deadline](/backend/knowledge-cards/deadline) 設計讓 timeout 和 cancellation 可以沿著 request 傳遞。

對應章節：[net/http 與 handler 設計](/go/03-stdlib/http-handler/)、[context：取消、逾時與生命週期](/go/03-stdlib/context/)。

### 背景處理與 pipeline：先看工作是否可以從 request 中拆出

背景處理的核心訊號是「使用者請求只負責提交工作，真正處理需要在後面持續執行」。例如檔案轉換、通知寄送、資料同步、報表產生與 [webhook](/backend/knowledge-cards/webhook) retry。Go 的 goroutine 和 channel 可以先建立單一 process 內的 worker 模型；當工作需要跨 process 保證時，再接到 Backend 的 message [queue](/backend/knowledge-cards/queue) 與 outbox 章節。

對應章節：[bounded worker pool](/go-advanced/01-concurrency-patterns/worker-pool/)、[Backend：訊息佇列與事件傳遞](/backend/03-message-queue/)。

### 分散式資料服務：先看狀態是否跨節點協調

分散式資料服務的核心訊號是「資料狀態需要跨節點維持一致」。這類服務會同時處理網路延遲、節點失效、複製、leader election、[transaction](/backend/knowledge-cards/transaction) 與觀測訊號。Go 提供的是可讀的並發與錯誤處理基礎；資料庫演算法、共識協定與持久化設計則需要專門章節或外部資料補足。

對應章節：[Source of Truth：狀態邊界](/go-advanced/04-architecture-boundaries/source-of-truth/)、[資料庫 transaction 與 schema migration](/go-advanced/07-distributed-operations/database-transactions/)。

## 案例閱讀檢查

閱讀高併發案例時，先找出三個問題：工作如何被限制數量、失敗如何回到 owner、資源如何被清理。若案例只談速度而沒有談生命週期，就很難轉成可維護的 Go 設計。
