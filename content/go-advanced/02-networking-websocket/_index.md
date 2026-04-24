---
title: "模組二：WebSocket 服務架構"
date: 2026-04-22
description: "WebSocket client lifecycle、heartbeat、訂閱路由與慢客戶端管理"
weight: 2
---

[WebSocket](/backend/knowledge-cards/websocket/) 服務的核心難點是連線建立後的長生命週期管理。HTTP upgrade 只是入口；每個 client 都有讀取、寫入、心跳、訂閱、推送佇列與清理流程。任何一個邊界不清楚，都可能造成 goroutine leak、concurrent write、慢 client 拖垮服務或訂閱狀態不一致。

本模組承接模組一的並發主題：read pump / write pump 對應 goroutine ownership，heartbeat 對應 select loop 與 ticker，send [buffer](/backend/knowledge-cards/buffer/) 對應 [backpressure](/backend/knowledge-cards/backpressure/)，訂閱集合對應共享狀態與 copy boundary。

## 章節列表

| 章節                                                              | 主題                                                                 | 關鍵收穫                                                                                   |
| ----------------------------------------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| [2.1](/go-advanced/02-networking-websocket/read-write-pump/)      | read pump / write pump 模式                                          | 讓單一連線的讀取、寫入與清理責任可推理                                                     |
| [2.2](/go-advanced/02-networking-websocket/heartbeat-deadline/)   | heartbeat、[deadline](/backend/knowledge-cards/deadline/) 與連線清理 | 用 ping/pong、[deadline](/backend/knowledge-cards/deadline) 與統一 unregister 偵測失效連線 |
| [2.3](/go-advanced/02-networking-websocket/subscription-routing/) | 訂閱模型與訊息路由                                                   | 把 client action 轉成可測的 command 與訂閱狀態                                             |
| [2.4](/go-advanced/02-networking-websocket/slow-client/)          | 慢客戶端與 send [buffer](/backend/knowledge-cards/buffer) 管理       | 用 bounded buffer、drop policy 與 byte budget 控制容量風險                                 |

## 本模組使用的範例主題

本模組使用虛構的即時通知服務作為範例。Client 可以訂閱 [topic](/backend/knowledge-cards/topic/)，server 會依 [topic](/backend/knowledge-cards/topic) 推送 notification、status update 或 error message。

範例只用來展示 Go [WebSocket](/backend/knowledge-cards/websocket) 服務設計，不假設讀者正在維護任何特定專案。

## 本模組的 Go 核心概念

- 用一個 read pump 負責 client 輸入。
- 用一個 write pump 負責所有 WebSocket 寫入。
- 用 channel 作為 client send [queue](/backend/knowledge-cards/queue/)。
- 用 context、done channel 或 hub unregister 管理連線生命週期。
- 用 ticker 實作 heartbeat，但由 write pump 統一寫 ping。
- 用 mutex 或 hub event loop 保護訂閱狀態。
- 用 non-blocking send 保護 hub 不被慢 client 卡住。

## 學習重點

學完本模組後，你應該能判斷：

1. 哪個 goroutine 可以讀 WebSocket，哪個 goroutine 可以寫 WebSocket
2. read pump、write pump、hub unregister 之間如何協作
3. heartbeat 失敗後應該走哪一條清理路徑
4. client action 應該在 router、usecase 還是 hub 裡處理
5. send buffer 滿載時應該丟棄、斷線、回錯或改用可靠儲存

## 章節粒度說明

WebSocket 章節依照連線生命週期拆分。Read/write pump、heartbeat、subscription routing、slow client 是四個不同責任；它們常在同一個 hub 或 client type 中互相呼叫，但教學上應分開建立模型。

如果只想處理單一問題，可以這樣查：

| 問題                              | 優先閱讀                                                                                   |
| --------------------------------- | ------------------------------------------------------------------------------------------ |
| concurrent write 或讀寫責任混亂   | [read pump / write pump 模式](/go-advanced/02-networking-websocket/read-write-pump/)       |
| 連線失效沒有被清理                | [heartbeat、deadline 與連線清理](/go-advanced/02-networking-websocket/heartbeat-deadline/) |
| action、payload、訂閱狀態混在一起 | [訂閱模型與訊息路由](/go-advanced/02-networking-websocket/subscription-routing/)           |
| 慢 client 拖垮 hub                | [慢客戶端與 send buffer 管理](/go-advanced/02-networking-websocket/slow-client/)           |

## 本模組不處理

本模組不討論 WebSocket 壓縮、水平擴展、跨節點廣播或完整身份驗證。這些都是實務重要主題，但必須先建立單一 Go process 內的連線生命週期與容量邊界；後續可接 [跨節點 WebSocket、presence 與重連協定](/go-advanced/07-distributed-operations/cross-node-websocket/)。

## 先備知識

- [模組一：進階並發模式](/go-advanced/01-concurrency-patterns/)
- [Go 入門：標準庫 HTTP](/go/03-stdlib/http-handler/)
- 知道 goroutine、channel、select、context 的基本用法

## 學習時間

預計 3-4 小時
