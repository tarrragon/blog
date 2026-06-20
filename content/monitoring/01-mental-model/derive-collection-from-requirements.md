---
title: "從需求推導「該收集哪些事件」"
date: 2026-06-19
description: "從 debug 需求、行為分析需求、效能需求、合規需求四個方向推導事件收集策略 — 避免「什麼都收」和「什麼都不收」"
weight: 4
tags: ["monitoring", "mental-model", "requirements", "collection-strategy"]
---

事件收集策略的起點是需求，而非技術能力。「能收集什麼」取決於 SDK 和 collector 的實作；「該收集什麼」取決於誰需要這些資料、用來做什麼決策。從需求推導收集策略，避免兩個極端：什麼都收（儲存成本高、隱私風險大、真正重要的事件淹沒在噪音中）和什麼都不收（問題發生時沒有資料可查）。

## 四個需求方向

### Debug 需求：問題發生時能定位根因

Debug 需求驅動的事件收集目標是「問題發生時，開發者能從事件記錄中重建問題的 context」。

需要的事件類型：

- **Error**：例外、非預期狀態、API 錯誤回應。包含 stack trace、error code、觸發條件。
- **Lifecycle**：問題發生時的系統狀態 — app 版本、OS 版本、網路狀態、前景/背景。
- **Event（最近操作）**：問題發生前使用者做了哪些操作。不需要完整的操作歷史，最近 10-20 個操作通常足夠。

推導方法：列出最近三個月遇到的 debug 困難場景，問「如果當時有哪些事件記錄，debug 時間能從 30 分鐘降到 5 分鐘？」。答案就是 debug 需求驅動的事件清單。

app_tunnel（透過 WebSocket 連接遠端終端機的 Flutter app）的 T.C4 案例是典型的 debug 需求缺口 — 六個元件中四個零 log，debug 只能靠實機反覆測試。如果在企劃階段就設計了連線生命週期的五步 log，auth token 問題在第一次連線就能從 log 定位（[testing 模組二](/testing/02-client-observability/)）。

具體的事件表和查詢場景見 [動機驅動的事件設計](/monitoring/01-mental-model/motivation-to-event-mapping/)。

### 行為分析需求：使用者如何使用產品

行為分析需求驅動的事件收集目標是「回答產品決策的問題」。

需要的事件類型：

- **Event**：使用者操作的完整記錄。需要足夠的粒度來回答「使用者在哪一步流失」（[funnel](/monitoring/knowledge-cards/funnel-analysis/)）和「不同使用者群體的行為差異」（[cohort](/monitoring/knowledge-cards/cohort-analysis/)）。
- **Lifecycle**：session 的開始和結束，用於計算使用時長和 session 頻率。

推導方法：列出產品團隊最常問的 3-5 個問題（「新功能有多少人用」「註冊流程在哪一步流失最多」「付費使用者和免費使用者的行為差異」），為每個問題列出需要的事件。

自用工具通常沒有行為分析需求 — 使用者就是開發者本人。這個方向的事件可以跳過。

具體的事件表和查詢場景見 [動機驅動的事件設計](/monitoring/01-mental-model/motivation-to-event-mapping/)。

### 效能需求：系統是否在可接受的範圍內運作

效能需求驅動的事件收集目標是「發現效能退化和容量瓶頸」。

需要的事件類型：

- **Metric**：回應時間、frame rate、記憶體使用量、佇列長度。定期取樣或事件觸發。

推導方法：列出使用者會感知到的效能指標（頁面載入時間、動畫流暢度、操作回應延遲），為每個指標定義可接受的範圍和取樣頻率。

具體的事件表和查詢場景見 [動機驅動的事件設計](/monitoring/01-mental-model/motivation-to-event-mapping/)。

### 合規需求：法規要求收集或禁止收集什麼

合規需求同時驅動「必須收集」和「禁止收集」。

必須收集：access log（誰在什麼時間存取了什麼資料）、audit trail（誰修改了什麼設定）。

禁止收集：未經同意的個人識別資訊、兒童資料（COPPA）、健康資料（HIPAA）。

推導方法：確認適用的法規（GDPR、CCPA、個資法），列出法規要求的最小收集項目和禁止項目。

具體的事件表和查詢場景見 [動機驅動的事件設計](/monitoring/01-mental-model/motivation-to-event-mapping/)。

## 從需求到事件清單的步驟

1. **列出需求方向**：Debug / 行為分析 / 效能 / 合規，每個方向的消費者是誰（開發者 / 產品團隊 / 維運 / 法務）。
2. **每個方向列出問題**：消費者最常需要回答的 3-5 個問題。
3. **每個問題列出需要的事件**：回答這個問題需要哪些事件類型和哪些屬性。
4. **去重和分類**：不同方向可能需要同一個事件（error 事件同時服務 debug 和效能監控）。去重後按四類事件分類。
5. **排優先順序**：按「缺少這個事件的損失」排序。Debug 需求的 error 事件通常是最高優先。

## 下一步路由

- 四類事件的定義 → [四類事件的完整定義](/monitoring/01-mental-model/four-event-types/)
- 事件的命名和結構化 → [事件命名規範](/monitoring/01-mental-model/event-naming-convention/)
- 收集到的事件怎麼處理 → [模組四 Collector 設計](/monitoring/04-collector/)
- 四個方向展開到具體事件名稱級 → [動機驅動的事件設計](/monitoring/01-mental-model/motivation-to-event-mapping/)
