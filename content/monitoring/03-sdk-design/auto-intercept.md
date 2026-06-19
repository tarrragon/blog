---
title: "自動攔截機制"
date: 2026-06-19
description: "JS window.onerror / Flutter FlutterError.onError / Python sys.excepthook — 各平台攔截未捕獲例外的機制和限制"
weight: 2
tags: ["monitoring", "sdk", "error-handling", "auto-intercept", "platform"]
---

自動攔截機制讓 SDK 在開發者不寫任何 error 上報程式碼的情況下，自動捕獲未處理的例外並記錄為 error 事件。每個平台有各自的全域錯誤處理器，SDK 在 init 時註冊攔截器，捕獲後轉換為統一的 error 事件格式送出。

## 各平台的攔截點

### JavaScript / TypeScript

JS 環境有兩個全域錯誤攔截點：

`window.onerror` 捕獲同步程式碼中未處理的例外。回呼函式收到 error message、來源 URL、行號、列號和 Error 物件。

`window.onunhandledrejection` 捕獲未處理的 Promise rejection。回呼函式收到 PromiseRejectionEvent，包含 rejection reason。

SDK 在 init 時註冊這兩個處理器。註冊前先保存原有的處理器（如果有），攔截後先呼叫原有處理器再執行 SDK 的記錄邏輯 — 避免覆蓋應用程式已有的錯誤處理。

限制：`onerror` 對跨域腳本的錯誤只收到 `Script error.` 訊息，沒有 stack trace。需要在 `<script>` 標籤加 `crossorigin` 屬性，server 端的 CORS header 加 `Access-Control-Allow-Origin`。

### Flutter

Flutter 有兩個攔截層：

`FlutterError.onError` 捕獲 widget build / layout / paint 過程中的例外。預設行為是在 console 印出錯誤，SDK 替換為記錄 error 事件後再呼叫預設處理器。

`PlatformDispatcher.instance.onError` 捕獲其他非同步區域的未處理例外（Dart 2.15+）。包含 Isolate 內的未捕獲例外。

`runZonedGuarded` 是另一個選項 — 在指定的 Zone 內捕獲所有未處理例外。SDK 可以用 `runZonedGuarded` 包住整個 `runApp()`，但這和 `PlatformDispatcher.onError` 有重疊，需要避免同一個例外被記錄兩次。

限制：Flutter 的 release mode 會移除 stack trace 的符號資訊（obfuscation）。需要保留 debug symbols 檔案（`.dSYM` / `mapping.txt`），在 collector 端做 symbolication。

### Python

`sys.excepthook` 處理主執行緒的未捕獲例外。回呼函式收到 exception type、value 和 traceback。

`threading.excepthook`（Python 3.8+）處理子執行緒的未捕獲例外。

`atexit.register` 用於在 Python 程序退出時 flush 剩餘的 buffer。但 `atexit` 在 `os._exit()` 或 SIGKILL 時不會執行。

限制：Python 的 GIL 讓 SDK 的網路操作可能阻塞主執行緒。SDK 的 flush 應該在獨立的 daemon thread 中執行，主執行緒只負責把事件放入 buffer。

## 攔截後的統一處理

不同平台的錯誤物件格式不同（JS 的 Error、Flutter 的 FlutterErrorDetails、Python 的 sys.exc_info tuple）。SDK 在攔截後把平台特定的錯誤物件轉換為統一的 error 事件格式：

- type: `"error"`
- name: 從 error class name 推導（`TypeError` → `error.TypeError`）
- data: 包含 message、stack trace（字串化）、觸發位置

轉換層是每個平台 SDK 唯一的平台特定程式碼。轉換完成後，事件進入和手動上報相同的 buffer → flush 管線。

## 和手動上報的分工

自動攔截處理「開發者沒有預期到的錯誤」— 未捕獲的例外、未處理的 rejection。手動上報（`Monitor.error()`）處理「開發者知道可能發生但想記錄的錯誤」— 已捕獲的例外、業務邏輯的異常狀態。

兩者進入同一個 buffer 和 flush 管線，在 collector 端可以用 data 中的 `source: "auto"` / `source: "manual"` 欄位區分。

## 下一步路由

- SDK 公開 API → [SDK 公開 API 設計](/monitoring/03-sdk-design/public-api/)
- 各平台的深入適配問題 → [模組五 平台適配](/monitoring/05-platform-adaptation/)
- Buffer 和 flush → [攢批送出策略](/monitoring/03-sdk-design/batch-flush/)
