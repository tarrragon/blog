---
title: "SDK 公開 API 設計"
date: 2026-06-19
description: "init / event / error / metric / flush / close 六個方法構成 SDK 的完整生命週期 — 跨平台共用相同 API 介面"
weight: 1
tags: ["monitoring", "sdk", "api-design", "lifecycle"]
---

SDK 的公開 API 是應用程式和監控系統之間的契約。六個方法涵蓋 SDK 的完整生命週期：初始化、四類事件上報、資料送出控制和資源釋放。跨平台的 SDK（JS / Flutter / Python）共用相同的方法簽名，讓開發者在不同平台上使用一致的 API。

## 六個方法

### init

SDK 初始化。設定 collector endpoint、app 識別資訊、flush 間隔、buffer 大小。在 app 啟動時呼叫一次。

```text
Monitor.init({
  endpoint: 'https://collector.example.com/v1/events',
  app: 'my_app',
  version: '1.2.0',
  flushInterval: 30000,   // 毫秒
  bufferSize: 100,
})
```

init 負責建立 session、記錄 lifecycle.session.start 事件、啟動 flush 計時器。init 之前呼叫其他方法應該拋出明確錯誤（SDK 未初始化），而非靜默忽略。

### event

記錄使用者操作事件（[四類事件中的 Event 類](/monitoring/01-mental-model/four-event-types/)）。接受事件名稱和可選的 data 物件。

```text
Monitor.event('terminal.connect.start', { url: 'wss://...' })
Monitor.event('enrollment.qr.scan')
```

event 方法是非阻塞的 — 事件進入內部 buffer 立即返回，不等待網路送出。應用程式的操作流程不應該被監控 SDK 的網路延遲阻塞。

### error

記錄錯誤事件。接受 Error/Exception 物件或自訂的錯誤描述。自動附加 stack trace、錯誤類型、觸發位置。

```text
Monitor.error(exception, { step: 'ws_connect' })
Monitor.error('Auth token missing', { context: 'handshake' })
```

error 方法和自動攔截機制（[自動攔截](/monitoring/03-sdk-design/auto-intercept/)）互補 — 自動攔截處理未捕獲的例外，error 方法處理開發者主動上報的已知錯誤。

### metric

記錄數值指標。接受指標名稱和數值。

```text
Monitor.metric('connect.duration_ms', 320)
Monitor.metric('terminal.fps', 58.5)
```

metric 方法記錄的是離散的數值快照。聚合計算（平均、百分位、趨勢）在 collector 端完成，SDK 端只負責記錄原始值。

### flush

強制送出 buffer 中所有待發事件。正常情況下 SDK 按 flushInterval 定期自動 flush（[攢批送出](/monitoring/03-sdk-design/batch-flush/)）。flush 方法用於需要確保事件已送出的場景 — 例如 app 即將進入背景或使用者手動觸發 log 上傳。

```text
await Monitor.flush()
```

flush 是非同步方法 — 需要等待網路請求完成。呼叫端可以 await 確認送出成功，也可以 fire-and-forget。

### close

SDK 資源釋放。停止 flush 計時器、送出 buffer 中剩餘事件、關閉網路連線、記錄 lifecycle.session.end 事件。

```text
await Monitor.close()
```

close 在 app 關閉時呼叫。呼叫後 SDK 進入已關閉狀態，後續的 event/error/metric 呼叫應該被靜默忽略（不拋錯，因為 app 正在關閉）。

## API 設計原則

**方法名稱和四類事件對齊**。event / error / metric 三個方法直接對應三類事件，lifecycle 事件由 init 和 close 自動產生。開發者看到方法名稱就知道對應哪類事件。

**所有上報方法非阻塞**。event、error、metric 進 buffer 立即返回。監控 SDK 阻塞應用程式的操作流程是反模式。

**init 和 close 成對出現**。init 開始 session，close 結束 session。兩者界定 SDK 的活躍期間。

各平台的 SDK 整合範例（Flutter 的 pubspec.yaml + main.dart init、Python 的 pip install + init code、JS 的 script tag + init）見 monitor repo 各 SDK 的 README。

## 下一步路由

- 自動攔截未捕獲的錯誤 → [自動攔截機制](/monitoring/03-sdk-design/auto-intercept/)
- Buffer 和 flush 的策略 → [攢批送出策略](/monitoring/03-sdk-design/batch-flush/)
- SDK 端的資料脫敏 → [SDK redaction helper](/monitoring/03-sdk-design/redaction-helper/)
- SDK 的 HTTP POST 行為需要 protocol test → [testing 模組三 協議整合測試](/testing/03-protocol-integration-test/)
