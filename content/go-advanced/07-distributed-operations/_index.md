---
title: "模組七：跨節點與平台整合"
date: 2026-04-22
description: "把單一 Go 服務延伸到資料庫、queue、跨節點 WebSocket、可觀測性與部署平台"
weight: 7
---

跨節點與平台整合的核心目標是把「單一 Go process 內的正確邊界」延伸到外部基礎設施。前六個模組先建立 goroutine lifecycle、[WebSocket](../../backend/knowledge-cards/websocket/) 連線、runtime 診斷、事件邊界、測試與操作語意；本模組處理服務進入多節點、多資料來源、多觀測工具與部署平台後會出現的新責任。

本模組已開始補成正文。章節先定義問題邊界與前置脈絡，再逐步補上 [transaction](../../backend/knowledge-cards/transaction/)、outbox、跨節點 [WebSocket](../../backend/knowledge-cards/websocket)、observability、部署與可靠性驗證的實作語意；後續仍可依實戰需求繼續擴寫。

## 與 Backend 教材的分工

本模組保留在 Go 進階篇，因為它要回答的是「Go 服務跨出單一 process 前，程式內部需要準備哪些 port、訊號、錯誤語意與測試合約」。具體資料庫、Redis、RabbitMQ、observability、Kubernetes 或 CI 平台操作，會放在跨語言的 [Backend 服務實務指南](../../backend/)。

## 章節列表

| 章節                           | 主題                                                                                                                               | 承接問題                                                                                                                  | Backend 實作                                                                               |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| [7.1](database-transactions/)  | 資料庫 [transaction](../../backend/knowledge-cards/transaction) 與 schema [migration](../../backend/knowledge-cards/migration/)    | 狀態邊界進入持久化層後如何維持一致                                                                                        | [資料庫與持久化](../../backend/01-database/)                                               |
| [7.2](outbox-idempotency/)     | [Durable queue](../../backend/knowledge-cards/durable-queue/)、outbox 與 [idempotency](../../backend/knowledge-cards/idempotency/) | 事件跨 process 後如何避免遺失、重複與半成功                                                                               | [訊息佇列與事件傳遞](../../backend/03-message-queue/)                                      |
| [7.3](cross-node-websocket/)   | 跨節點 WebSocket、presence 與重連協定                                                                                              | 多台 server 如何管理訂閱、推送與連線狀態                                                                                  | [快取與 Redis](../../backend/02-cache-redis/)、[訊息佇列](../../backend/03-message-queue/) |
| [7.4](observability-pipeline/) | Observability pipeline、[metrics](../../backend/knowledge-cards/metrics/) 與 tracing                                               | [log](../../backend/knowledge-cards/log/)、metric、[trace](../../backend/knowledge-cards/trace/) 如何組成可操作的診斷系統 | [可觀測性平台](../../backend/04-observability/)                                            |
| [7.5](deployment-contracts/)   | Kubernetes、systemd 與 load balancer 合約                                                                                          | 部署平台如何影響 shutdown、health 與資源限制                                                                              | [部署平台與網路入口](../../backend/05-deployment-platform/)                                |
| [7.6](reliability-pipeline/)   | CI、fuzz、[load test](../../backend/knowledge-cards/load-test/) 與 chaos testing                                                   | 測試如何從單一行為擴展到系統可靠性                                                                                        | [可靠性驗證流程](../../backend/06-reliability/)                                            |

## 本模組和前面章節的關係

本模組適合在你已經理解單一 Go 服務的內部邊界後閱讀，用來補足生產環境常見的外部系統責任。

- 事件與狀態邊界先讀 [模組四：架構邊界與事件系統](../04-architecture-boundaries/)。
- WebSocket lifecycle 先讀 [模組二：WebSocket 服務架構](../02-networking-websocket/)。
- 測試可靠性先讀 [模組五：測試與可靠性](../05-testing-reliability/)。
- 操作語意先讀 [模組六：生產操作](../06-production-operations/)。

## 學習時間

目前已可作為第一輪正文閱讀，完整學習時間可隨後續擴寫再調整。
