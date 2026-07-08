---
title: "網路斷線 UX 模式"
date: 2026-06-19
description: "Offline-first / retry / degraded mode 三種網路 gate 的處理策略 — 取決於功能是否依賴即時連線"
weight: 3
tags: ["ux-design", "gate", "network", "offline", "fallback"]
---

網路 [gate](/ux-design/knowledge-cards/gate/) 和其他 gate 的差異在於狀態的連續性。生物辨識是二元結果（通過或不通過），網路狀態是連續的 — 連線中、已連線、斷線、重新連線、連線但延遲高、連線但頻繁斷開。處理策略取決於功能對即時連線的依賴程度。

## 三種處理策略

### Offline-first

功能的核心操作在本地完成，網路用於同步。斷線時使用者仍可操作，重新連線後自動同步差異。

Offline-first 適合的前提是資料可以本地存儲且衝突可以解決。筆記 app、待辦事項、表單填寫 — 使用者的操作產生本地資料，網路只負責把資料同步到 server。

Offline-first 的 UX 設計重點是讓使用者知道同步狀態：已同步、待同步、同步失敗。不需要 gate — 網路狀態不阻擋使用者操作。

### Retry with feedback

功能需要網路但可以等待。斷線時顯示狀態和重試選項，使用者決定要等還是離開。

app_tunnel 的 terminal 連線屬於這個模式。WebSocket 連線需要網路，斷線時使用者無法操作終端機。error 和 disconnected 狀態提供重連按鈕讓使用者手動重試。

Retry 策略的 UX 設計重點：

- 告知使用者發生什麼（「連線中斷」而非空白畫面）
- 提供手動重試（重連按鈕）
- 提供退出路徑（返回首頁 — app_tunnel 原本缺少這個）
- 自動重試要有上限和間隔遞增（避免無限重試消耗電量）

### Degraded mode

功能部分依賴網路。核心功能離線可用，進階功能需要網路。斷線時自動切換到降級模式，不阻擋使用者操作但功能受限。

降級模式的 UX 設計重點是清楚標示哪些功能可用、哪些不可用。「離線模式 — 搜尋功能暫時不可用」比靜默隱藏搜尋按鈕更透明。

## 網路狀態的 UI 呈現

### 全域指示器

在 app 頂部或狀態列顯示「離線」標示。適合網路狀態影響全域功能的 app。

### 功能級指示器

在需要網路的功能旁邊顯示不可用狀態。適合只有部分功能依賴網路的 app。

### 非侵入式通知

用 Snackbar 或 Toast 短暫顯示「已恢復連線」或「網路中斷」。適合網路狀態偶爾變化的場景。不適合頻繁斷開重連的場景（通知太多會干擾使用者）。

## 連線但品質差的場景

網路存在但延遲高或頻繁斷開，比完全離線更難處理。完全離線時 app 可以立即切換到離線模式；連線不穩定時，每次請求可能成功也可能逾時，使用者體驗是「有時候行有時候不行」。

處理策略：

- 設定合理的逾時時間（太短會把慢回應判定為失敗，太長讓使用者等太久）
- 逾時後顯示狀態和重試選項，不自動重試（避免在不穩定網路上累積重試）
- 在 loading 狀態提供取消選項，讓使用者可以中斷等待

## 下一步路由

- Gate 設計的通用方法論 → [Gate 分類與三問設計法](/ux-design/02-gate-fallback/gate-three-questions/)
- 權限請求的 UX 設計 → [Permission 請求時機與措辭](/ux-design/02-gate-fallback/permission-request-timing/)
- 畫面狀態矩陣中的網路狀態 → [ux-design 模組一 畫面狀態機](/ux-design/01-screen-state-machine/)
- Server 端背壓如何影響 client UX → [運行期維運 背壓機制](/operations/03-traffic-management/backpressure/)
