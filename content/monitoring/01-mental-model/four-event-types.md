---
title: "四類事件的完整定義"
date: 2026-06-19
description: "Event / Error / Metric / Lifecycle 四類事件各自的語意、觸發時機和典型用途 — 分類是監控體系的統一語言"
weight: 1
tags: ["monitoring", "mental-model", "event", "error", "metric", "lifecycle"]
---

監控資料由四類事件構成。每類事件回答不同的問題，觸發時機不同，消費方式不同。分類的目的是讓「我要收集什麼」有結構化的答案，而非在每個功能上各自決定要不要加 log。

## Event：使用者做了什麼

Event 記錄使用者主動發起的操作。按鈕點擊、頁面瀏覽、表單提交、搜尋查詢 — 每個 event 代表使用者的一個意圖表達。

Event 的觸發時機是使用者操作發生時。程式碼中的位置通常是 UI 事件處理器（onClick、onSubmit、onNavigate）。

Event 的消費方式：

- **Debug context**：問題發生前使用者做了哪些操作。和 error 事件搭配使用，還原問題的操作路徑。
- **行為分析**：使用者做了哪些操作、操作順序是什麼、在哪一步停止。Funnel analysis 的原料（[模組八](/monitoring/08-business-analytics/)）。
- **功能使用率**：哪些功能被頻繁使用、哪些很少被觸發。功能優先順序的決策依據。

## Error：什麼出了問題

Error 記錄程式碼執行中的非預期狀態。例外拋出、assertion 失敗、非預期的 API 回應、資源存取失敗。

Error 的觸發時機是非預期狀態被偵測到時。來源包括：語言層級的 try/catch 捕獲、框架的全域錯誤處理器（Flutter 的 `FlutterError.onError`、JavaScript 的 `window.onerror`）、自訂的錯誤檢查邏輯。

Error 的消費方式：

- **即時告警**：特定類型的 error 或 error 數量超過閾值時通知開發者。
- **趨勢分析**：error 數量隨時間的變化。新版本部署後 error 是否增加。
- **根因分析**：error 的 stack trace、觸發條件、影響範圍。和 event 搭配還原「使用者做了什麼導致 error」。

## Metric：系統狀態的數值快照

Metric 記錄系統狀態的可量化指標。回應時間、記憶體使用量、佇列長度、連線數、frame rate。

Metric 的觸發時機是定期取樣或特定事件發生時。定期取樣適合持續變化的指標（記憶體使用量每 30 秒取一次），事件觸發適合離散的測量（每次 API 回應記錄回應時間）。

Metric 的消費方式：

- **效能監控**：回應時間的 P50 / P95 / P99 分佈。記憶體使用量的趨勢。
- **容量規劃**：佇列長度接近上限、連線數接近 pool 上限 — 需要擴容的訊號。
- **SLA 追蹤**：服務可用性、回應時間是否在承諾範圍內。

## Lifecycle：系統經歷了什麼階段

Lifecycle 記錄系統本身的狀態轉換。App 啟動、前景/背景切換、連線建立/斷開、版本更新、設定變更。

Lifecycle 的觸發時機是系統狀態轉換發生時。來源包括：app 生命週期回呼（onCreate、onResume、onPause）、連線狀態變化事件、部署和設定變更鉤子。

Lifecycle 的消費方式：

- **Session 分析**：使用者一次使用多久、啟動頻率、前後景切換頻率。
- **環境資訊**：Error 發生時的系統狀態（app 版本、OS 版本、網路狀態）。
- **連線品質**：連線建立成功率、斷線頻率、重連次數（[testing 模組二 三層 log](/testing/02-client-observability/three-layer-log-design/)）。

## 四類事件的區別

| 維度   | Event            | Error          | Metric             | Lifecycle          |
| ------ | ---------------- | -------------- | ------------------ | ------------------ |
| 觸發者 | 使用者操作       | 系統非預期狀態 | 定期取樣或事件觸發 | 系統狀態轉換       |
| 回答   | 使用者做了什麼   | 什麼出了問題   | 系統現在怎麼樣     | 系統經歷了什麼     |
| 頻率   | 依使用者行為     | 低（理想狀態） | 固定間隔或事件驅動 | 低（狀態轉換才有） |
| 消費   | 行為分析、funnel | 告警、根因分析 | 效能監控、容量規劃 | session、環境資訊  |

## 下一步路由

- 事件命名規範 → [事件命名規範](/monitoring/01-mental-model/event-naming-convention/)
- 從需求推導收集策略 → [從需求推導「該收集哪些事件」](/monitoring/01-mental-model/derive-collection-from-requirements/)
- Event 類事件在商業分析中的用途 → [模組八 行為資料的商業利用](/monitoring/08-business-analytics/)
- Log 點的設計方法 → [testing 模組二 客戶端可觀測性](/testing/02-client-observability/)
