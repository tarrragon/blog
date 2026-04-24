---
title: "1.7 從入口程式看應用啟動流程"
date: 2026-04-22
description: "用入口程式建立 Go 程式的啟動與資料流模型"
weight: 7
---

入口程式是 Go 應用的系統地圖。它不一定包含最多細節，但應該讓你知道 process 如何初始化、哪些 goroutine 會啟動、HTTP endpoint 如何註冊，以及程式如何關閉。

## 本章目標

學完本章後，你將能夠：

1. 用啟動流程理解 Go 應用結構
2. 看懂 channel 與元件之間的資料流
3. 理解 `context.WithCancel` 在關閉流程中的角色
4. 判斷新增功能應該接在哪個生命週期位置

---

## 【觀察】入口流程分成五段

入口程式的核心責任是揭露應用如何啟動，而不是承載所有實作細節。一個稍具規模的 `main()` 可以切成五個區塊：

| 區塊               | 責任                                                                                                                            |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| Runtime 與日誌設定 | 設定記憶體限制、初始化 `slog`                                                                                                   |
| 環境設定           | 讀取設定檔、環境變數與 port                                                                                                     |
| 元件組裝           | 建立 repository、worker、service 或 server                                                                                      |
| 背景工作           | 啟動 worker、[queue](../../../backend/knowledge-cards/queue/) [consumer](../../../backend/knowledge-cards/consumer/) 或定時任務 |
| 對外介面           | 註冊 CLI command、HTTP endpoint 或 [WebSocket](../../../backend/knowledge-cards/websocket/) route                               |

這種切法讓入口同時保留完整脈絡，又不把所有實作細節塞進 `main()`。

## 【判讀】`main()` 的價值是揭露依賴關係

`main()` 的核心價值是讓依賴關係可見。Go 專案常把依賴直接組裝在 `main()`，好處是維護者能直接看到應用骨架：

```go
events := make(chan Event, 128)
notifications := make(chan Notification, 128)

repo := NewNotificationRepository()
worker := NewWorker(repo, events, notifications)
server := NewHTTPServer(repo, notifications)
```

這段程式揭露一個重要事實：`repo` 負責保存共享狀態，`worker` 負責處理背景事件，`server` 負責提供 HTTP 入口。資料如何流動，不需要先查框架設定就能看懂。

## 【策略】用生命週期判斷功能應該放哪裡

新增功能的核心判斷是：先確認它屬於哪一種生命週期，再決定接入位置。新增功能時，先判斷它屬於哪一種生命週期：

| 新功能類型        | 接入位置                               |
| ----------------- | -------------------------------------- |
| 新 HTTP endpoint  | 入口程式註冊 route，實作獨立 handler   |
| 新背景事件來源    | 新增 channel、worker 或 queue consumer |
| 新即時訊息 action | message router 或連線管理元件          |
| 新狀態欄位        | repository 更新與 model 擴展           |
| 新診斷能力        | 條件註冊 endpoint 或 `slog` 欄位       |

這個判斷可以避免把功能塞進錯誤元件，造成後續難測與難改。

## 【執行】完整啟動路徑

啟動路徑的核心用途是提供除錯地圖。一個有背景工作與 HTTP 介面的 Go 應用，啟動後的主要路徑可能如下：

```text
main()
  ├─ setup logger / runtime
  ├─ create channels
  ├─ create repository / worker / server
  ├─ context.WithCancel()
  ├─ go worker.Run(ctx)
  ├─ go startPeriodicSync(ctx)
  ├─ go server.Run(ctx)
  ├─ register /health
  ├─ register /ws
  ├─ register /events
  ├─ go waitForShutdown(cancel, ...)
  └─ http.Server.ListenAndServe()
```

這份路徑也是除錯清單。當應用沒有產生預期輸出時，可以依序確認：輸入來源是否產生資料、worker 是否處理資料、對外介面是否有 client 或呼叫者、狀態資料是否被正確更新。

## 小結

讀 Go 應用時，入口程式不是細節檔，而是系統索引。先用它建立元件與生命週期模型，再進入各元件實作，會比直接從單一 handler 或函式開始讀更穩定。
