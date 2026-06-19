---
title: "Flutter 平台適配"
date: 2026-06-19
description: "Isolate 安全、Platform channel 攔截、app lifecycle 事件 — Flutter SDK 的平台特殊考量"
weight: 2
tags: ["monitoring", "platform", "flutter", "isolate", "lifecycle"]
---

Flutter 應用程式在 Dart VM 中執行，有自己的執行緒模型（Isolate）、原生平台橋接（Platform channel）和 app 生命週期管理。監控 SDK 在 Flutter 中需要處理的平台特殊問題集中在這三個面向。

## Isolate 安全

Dart 的 Isolate 是獨立的記憶體空間，Isolate 之間不共享記憶體，只能透過 message passing 溝通。SDK 的記憶體 buffer 存在於 main isolate 中，其他 isolate 產生的事件需要透過 port 傳送到 main isolate 才能進入 buffer。

SDK 端的適配：

提供 `Monitor.eventFromIsolate(SendPort port)` 方法，在子 isolate 中透過 port 把事件送回 main isolate。或者提供 isolate-aware 的 `Monitor.init()` 變體，在子 isolate 中初始化一個輕量的 event forwarder。

如果 SDK 使用 compute 或 Isolate.spawn 做背景任務（例如壓縮 buffer），需要透過 port 把結果送回 main isolate — 背景 isolate 無法直接存取 main isolate 的 HTTP client 或 buffer。

## Platform channel 攔截

Flutter 透過 Platform channel 呼叫原生平台功能（iOS 的 Swift/ObjC、Android 的 Kotlin/Java）。Platform channel 的呼叫可能失敗（原生端未實作、參數格式錯誤、原生端拋出例外），這些錯誤在 Dart 端表現為 `PlatformException`。

SDK 可以攔截 Platform channel 的呼叫記錄每次呼叫的方法名稱、參數、結果和耗時。攔截方式是替換 `ServicesBinding.defaultBinaryMessenger` 的處理器，在轉發前後記錄事件。

攔截的價值是：Platform channel 的錯誤通常難以 debug（stack trace 跨越 Dart 和原生兩層），監控記錄提供「呼叫了哪個 channel method、傳了什麼參數、在哪一層失敗」的完整 context。

注意：攔截 Platform channel 會增加每次呼叫的延遲（記錄事件的開銷）。對高頻的 Platform channel 呼叫（例如每幀都呼叫的渲染相關 channel），攔截可能影響效能。SDK 應該提供 channel 過濾機制 — 只攔截特定 channel 或只在 debug mode 攔截。

## App lifecycle 事件

Flutter 的 `WidgetsBindingObserver` 提供 app 生命週期回呼：

- `didChangeAppLifecycleState(AppLifecycleState state)` — app 在 resumed（前景）、inactive（部分可見）、paused（背景）、detached（即將關閉）之間切換。

SDK 在 init 時註冊 observer，記錄每次狀態轉換為 lifecycle 事件。

lifecycle 事件在 flush 策略中有特殊意義：

**paused（進入背景）**：觸發 flush — 把 buffer 中的事件送出，因為 app 在背景可能被系統殺掉，buffer 中的事件會遺失。iOS 在 app 進入背景後約 5 秒 suspend，flush 必須在這個時間窗口內完成。

**resumed（回到前景）**：檢查上次 flush 是否成功。如果 paused 時的 flush 失敗（網路超時），在 resumed 時重試。

**detached（即將關閉）**：呼叫 `Monitor.close()` 做最後一次 flush 和資源釋放。detached 的時間窗口更短，close flush 可能被截斷。

## 下一步路由

- Python 平台的適配 → [Python 平台適配](/monitoring/05-platform-adaptation/python-platform/)
- 跨平台 timestamp 一致性 → [跨平台 timestamp 一致性](/monitoring/05-platform-adaptation/cross-platform-timestamp/)
- 自動攔截機制 → [模組三 自動攔截](/monitoring/03-sdk-design/auto-intercept/)
