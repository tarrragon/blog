---
title: "模組六：實戰指南"
date: 2026-04-22
description: "用 Go 的核心概念完成常見服務功能：輸入、事件、狀態、背景工作、記錄與儲存邊界"
weight: 6
---

本模組把 Go 的核心概念轉成常見服務開發任務。核心順序是：先定義資料與行為語意，再處理輸入邊界，接著更新 usecase、repository、event/log 邊界，最後補測試。這裡的範例會使用中立的即時通知服務，不要求讀者知道任何特定專案。

實戰章節的重點是練習 Go 的判斷方式：何時只需要 struct，何時需要 method，何時需要 interface，何時需要 goroutine，何時應該把狀態集中管理。大型架構模板留到壓力出現後再評估；服務設計只是這些語言概念的應用場景。

## 章節列表

| 章節                          | 主題                        | 關鍵收穫                                                        |
| ----------------------------- | --------------------------- | --------------------------------------------------------------- |
| [6.1](new-websocket-action/)  | 如何新增一個即時訊息 action | 用 struct、JSON、error 與 usecase 切開輸入邊界                  |
| [6.2](new-event-type/)        | 如何新增一種 domain event   | 用明確型別定義事件語意、envelope 與驗證規則                     |
| [6.3](state-fields/)          | 如何擴展狀態投影欄位        | 判斷欄位屬於 domain state、read model 或 response view          |
| [6.4](new-background-worker/) | 如何新增背景工作流程        | 用 context、channel、ticker 與 shutdown 管理 goroutine 生命週期 |
| [6.5](structured-recording/)  | 如何新增結構化記錄欄位      | 區分 structured log、domain event log 與 state repository       |
| [6.6](repository-port/)       | 如何新增 repository port    | 用小介面建立儲存邊界，再決定 memory 或 database 實作            |
| [6.7](service-scenarios/)     | Go 常見服務場景總覽         | 看懂 Go 最常落地的即時、背景與事件處理場景                    |
| [6.8](data-access-boundaries/) | 高併發下的 Redis 與 SQL 使用原則 | 用 timeout、pool 與背壓控制下游壓力                          |

## 本模組的教學主軸

- **資料先有語意**：struct 欄位、JSON tag、zero value 與 `omitempty` 都要表達資料意義。
- **邊界先小後大**：先用函式與 struct 整理行為，只有在替換、測試或隔離需求出現時才引入 interface。
- **goroutine 要有生命週期**：背景工作必須能取消、停止與測試；只把工作丟進 `go func()` 會讓 shutdown、錯誤回報與測試邊界變模糊。
- **記錄要按用途分流**：log 用於操作診斷，event log 用於事實記錄，repository 用於目前狀態。
- **架構來自壓力**：domain package、repository port、event envelope 是服務變大後的自然拆分，不是入門程式的預設起點。

## 章節粒度說明

本模組每一章都是「完成一個常見開發任務」的完整流程，所以篇幅會比語法章長。章節會同時包含資料定義、邊界判斷、簡化實作、測試與設計檢查；這是為了讓讀者看到一次修改如何穿過 Go 服務的多個層次。

細節主題會在後續模組拆開深入：

| 本模組任務                  | 深入章節                                                                                                                                                                      |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 即時訊息 action             | [WebSocket 服務架構](../../go-advanced/02-networking-websocket/)                                                                                                              |
| domain event 與去重         | [架構邊界與事件系統](../../go-advanced/04-architecture-boundaries/)                                                                                                           |
| 狀態投影與 repository       | [Source of Truth：狀態邊界](../../go-advanced/04-architecture-boundaries/source-of-truth/)                                                                                    |
| 背景 worker 與 shutdown     | [graceful shutdown 與 signal handling](../../go-advanced/06-production-operations/graceful-shutdown/)                                                                         |
| structured log 與 event log | [結構化日誌欄位設計](../../go-advanced/06-production-operations/log-fields/) 與 [Observability pipeline](../../go-advanced/07-distributed-operations/observability-pipeline/) |
| repository 到資料庫         | [資料庫 transaction 與 schema migration](../../go-advanced/07-distributed-operations/database-transactions/)                                                                  |

## 本模組使用的範例主題

- 即時通知服務的 action route
- domain event envelope
- 任務狀態 projection 更新
- 背景 worker 啟動與停止
- structured log 欄位
- repository port 與 memory implementation

## 學習時間

預計 2-3 小時
