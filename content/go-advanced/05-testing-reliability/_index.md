---
title: "模組五：測試與可靠性"
date: 2026-04-22
description: "時間控制、WebSocket integration test、race check 與 table-driven test"
weight: 5
---

並發服務測試的核心目標是讓時間、連線、goroutine、共享狀態與錯誤路徑變得可重現。只測 happy path 不足以保護長時間運行的 Go 服務；真正需要測的是取消、[timeout](../../backend/knowledge-cards/timeout)、[queue](../../backend/knowledge-cards/queue) full、cleanup、data race 與協定邊界。

本模組承接前面的並發、[WebSocket](../../backend/knowledge-cards/websocket) 與架構邊界：時間注入讓狀態轉移可測，WebSocket integration test 驗證真實連線互動，race detector 檢查共享狀態，table-driven test 幫助案例保持清楚。

## 章節列表

| 章節                          | 主題                         | 關鍵收穫                                       |
| ----------------------------- | ---------------------------- | ---------------------------------------------- |
| [5.1](time-control/)          | 時間注入與狀態轉移測試       | 不用 sleep 也能測 timeout、[deadline](../../backend/knowledge-cards/deadline) 與狀態轉移 |
| [5.2](websocket-integration/) | WebSocket integration test   | 用真實 test server 驗證 client/server 協定     |
| [5.3](race-check/)            | race condition 檢查          | 用 `go test -race` 搭配併發測試找資料競爭      |
| [5.4](table-tests/)           | table-driven test 的設計邊界 | 讓測試表只描述單一行為維度                     |

## 本模組使用的範例主題

本模組使用虛構的即時通知服務作為範例。範例包含 job 狀態轉移、WebSocket subscribe flow、client cleanup、repository concurrent access 與 [topic](../../backend/knowledge-cards/topic) normalization。

範例只用來展示 Go 測試設計，不假設讀者正在維護任何特定專案。

## 本模組的 Go 核心概念

- 用 `now time.Time` 或 `func() time.Time` 控制時間。
- 用 `httptest.Server` 建立真實 WebSocket integration test。
- 用 read/write deadline 避免測試永久卡住。
- 用 `eventually` helper 等待非同步清理，而不是固定 sleep。
- 用 `go test -race ./...` 檢查執行到的 data race。
- 用小而清楚的 table-driven test 表達同一個行為的多組案例。

## 學習重點

學完本模組後，你應該能判斷：

1. 哪些邏輯應該用純函式測，哪些需要 integration test
2. 測試裡的時間應該如何注入，而不是等待真實時間
3. WebSocket 測試如何避免永久卡住
4. race detector 能找什麼，不能證明什麼
5. table-driven test 何時該拆成多個測試

## 本模組不處理

本模組不建立完整測試框架，也不討論大型 CI 平台、壓力測試或 chaos testing。這些主題很重要，但本模組先聚焦單一 Go 服務內最常見、最容易失控的可靠性測試；後續可接 [CI、fuzz、load test 與 chaos testing](../07-distributed-operations/reliability-pipeline/)。

## 學習時間

預計 3-4 小時
