---
title: "Sentry 深入"
date: 2026-06-19
description: "Error tracking + performance monitoring + session replay 的架構 — Sentry 從 error-first 出發如何擴展到全面可觀測性"
weight: 2
tags: ["monitoring", "sentry", "error-tracking", "performance", "session-replay"]
---

Sentry 的核心是 error tracking — 自動捕獲未處理的例外、提供 stack trace、自動分群（grouping）相同 root cause 的 error。在 error tracking 的基礎上，Sentry 擴展了 performance monitoring（transaction / span）和 session replay（重播使用者操作）。

## Error tracking

Sentry 的 error tracking 架構有三個層次：SDK 端的自動捕獲、server 端的 issue grouping 和 UI 端的 issue management。

### 自動捕獲

Sentry SDK 在各平台註冊全域錯誤處理器（和[模組三 自動攔截](/monitoring/03-sdk-design/auto-intercept/)的機制相同）。捕獲到例外後，SDK 收集 stack trace、breadcrumbs（最近的使用者操作）、device context（OS / browser / device model）和自訂 tags，打包成 event 送到 Sentry server。

### Issue grouping

Sentry server 收到 error event 後，用 fingerprinting 演算法判斷這個 error 是否和已有的 issue 相同。預設的 fingerprinting 基於 stack trace 的 frame — 如果兩個 error 的 stack trace 指向同一個位置，歸入同一個 issue。

自訂 fingerprint 讓開發者控制 grouping 邏輯。例如：不同使用者觸發的同一個 API error 可能有不同的 stack trace（因為 call site 不同），但 root cause 相同 — 自訂 fingerprint 把它們歸入同一個 issue。

### Issue management

每個 issue 有狀態（unresolved / resolved / ignored）、指派（誰負責修復）、趨勢（這個 issue 的發生頻率是上升還是下降）。Sentry 的 UI 提供 issue 列表、趨勢圖、影響範圍（影響多少使用者）。

## Performance monitoring

Sentry 的 performance monitoring 用 transaction 和 span 模型（和 OpenTelemetry 的 trace / span 概念相同）。

Transaction 代表一個完整的操作（頁面載入、API 請求處理）。Span 是 transaction 內的子操作（database query、外部 API 呼叫）。Transaction 和 span 的 duration 構成操作的時間分佈。

Performance monitoring 的價值是發現「慢」的問題 — P95 回應時間超過閾值、特定 span 佔了 transaction 80% 的時間。和 error tracking 互補：error 告訴你「什麼壞了」，performance 告訴你「什麼慢了」。

## Session replay

Session replay 錄製使用者的操作過程 — DOM 變化、滑鼠移動、點擊事件 — 在 Sentry UI 中重播。開發者可以看到「使用者在觸發 error 之前做了什麼操作」。

Session replay 的實作是 DOM snapshot + mutation recording。記錄的是 DOM 結構的變化（非螢幕錄影），在重播時重建 DOM。資料量比錄影小很多，但仍然是所有 Sentry 功能中資料量最大的。

隱私考量：session replay 會看到使用者輸入的內容（除非做 masking）。Sentry 提供 privacy configuration 控制哪些元素被 mask（輸入框、敏感資料區域）。

## 自架方案和 Sentry 的差距

| 功能           | 自架方案               | Sentry                         |
| -------------- | ---------------------- | ------------------------------ |
| Error 捕獲     | SDK 自動攔截           | SDK 自動攔截（相同）           |
| Issue grouping | 手動 grep 分群         | 自動 fingerprinting + 自訂規則 |
| 趨勢分析       | 手動計數               | 自動趨勢圖 + 告警              |
| Performance    | metric 事件 + 手動分析 | Transaction / span + 自動 P95  |
| Session replay | 無                     | DOM recording + 重播 UI        |

Sentry 的核心價值在 issue grouping 和趨勢分析 — 把大量 error event 歸類成可管理的 issue 列表，自動追蹤每個 issue 的趨勢。自架方案用 grep 做不到自動 grouping。

## 下一步路由

- Firebase 的整合方案 → [Firebase 套件](/monitoring/06-commercial-comparison/firebase-suite/)
- Datadog 的全棧 APM → [Datadog RUM](/monitoring/06-commercial-comparison/datadog-rum/)
- 自架 vs 商業的判斷 → [自架 vs 商業的判斷決策表](/monitoring/06-commercial-comparison/self-hosted-vs-commercial/)
