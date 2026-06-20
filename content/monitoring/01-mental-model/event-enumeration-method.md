---
title: "事件枚舉與補齊檢查"
date: 2026-06-20
description: "從操作盤點系統性地推導出完整的事件清單 — 四類補齊檢查確保沒有遺漏、粒度判準確保每個事件只記一個事實"
weight: 5
tags: ["monitoring", "mental-model", "event-enumeration", "event-design", "completeness"]
---

事件枚舉的目的是為一個服務建立完整的事件清單 — 每個事件有明確的類型、名稱、觸發時機和 data schema。枚舉的方法從操作盤點出發，經過四類補齊檢查，產出可以直接實作 SDK 埋點的事件表。

## 從操作盤點推導事件

每個使用者操作（BDD 操作盤點的產物）至少對應一個 event 類型的事件。操作的失敗路徑對應 error 類型。操作涉及的效能測量對應 metric 類型。操作觸發的系統狀態轉換對應 lifecycle 類型。

推導鏈：操作 → 四類事件候選 → 命名 → data schema。

以一個透過 WebSocket 連接遠端終端機的 app 為例，「連線到終端機」這個操作推導出的事件：

| 四類      | 事件名稱                  | 觸發時機                         | data schema                          |
| --------- | ------------------------- | -------------------------------- | ------------------------------------ |
| event     | terminal.connect.start    | 使用者點擊連線按鈕               | `{url, trigger: "manual" \| "auto"}` |
| event     | terminal.connect.done     | 連線成功、開始接收 output        | `{url, duration_ms}`                 |
| error     | terminal.connect.failed   | 連線失敗（逾時、拒絕、認證失敗） | `{url, error, step}`                 |
| metric    | terminal.connect.duration | 連線完成（成功或失敗）           | `{duration_ms, success: bool}`       |
| lifecycle | ws.connected              | WebSocket 連線狀態轉換           | `{url}`                              |
| lifecycle | ws.disconnected           | WebSocket 斷線                   | `{url, reason, code}`                |

一個操作推導出六個事件 — 因為這個操作跨越了使用者行為（event）、可能失敗（error）、有效能測量（metric）、涉及系統狀態轉換（lifecycle）四個面向。

## 四類補齊檢查

列完所有操作的事件後，對每個功能區域跑一次四類補齊檢查 — 逐列確認每一類是否都有對應的事件。

| 功能區域 | event                                | error                 | metric              | lifecycle                      |
| -------- | ------------------------------------ | --------------------- | ------------------- | ------------------------------ |
| 連線     | connect.start / connect.done         | connect.failed        | connect.duration    | ws.connected / ws.disconnected |
| 認證     | auth.biometric.attempt               | auth.biometric.failed | auth.duration       | auth.state_changed             |
| 輸入     | input.submit                         | input.parse_error     | —                   | —                              |
| 配對     | enrollment.qr.scan / enrollment.done | enrollment.failed     | enrollment.duration | —                              |

空格是候選遺漏。每個空格問一個問題：

- **event 空**：「這個功能區域有使用者操作嗎？」有 → 補事件；沒有（純系統內部）→ 合理的空格
- **error 空**：「這個功能區域能失敗嗎？」能 → 補事件；不能失敗的功能極少 → 再想一次
- **metric 空**：「這個功能區域有值得量測的效能指標嗎？」有 → 補事件；操作瞬間完成且不涉及外部依賴 → 合理的空格
- **lifecycle 空**：「這個功能區域涉及系統狀態轉換嗎？」有 → 補事件；純資料操作不改系統狀態 → 合理的空格

上表中「輸入」的 metric 和 lifecycle 空格是合理的 — 文字輸入送出不涉及效能量測和系統狀態轉換。「配對」的 lifecycle 空格也合理 — 配對完成後不改變系統的執行狀態。

## 粒度判準

事件粒度的判斷用一個 SRP 判準：**一個事件記一個事實**。

### 拆分訊號

一個事件記了兩個獨立的事實 → 拆成兩個事件。

`terminal.connect_and_auth` 同時記錄「連線建立」和「認證通過」。這兩個事實的失敗模式不同（連線失敗是網路問題、認證失敗是帳密問題）、觸發時機不同、消費者不同。拆成 `terminal.connect.done` 和 `auth.token.sent`。

### 合併訊號

兩個事件永遠同時觸發且消費者相同 → 合併成一個事件。

`terminal.input.keystroke` 和 `terminal.input.keystroke_logged` 永遠同時觸發（每個按鍵一次），data schema 相同。合併成一個 `terminal.input.keystroke`。

### 邊界案例

`connect.done` 同時記 event 和 metric（成功事件 + duration）。這是一個事實（連線完成）的兩個面向，可以合併成一個事件帶 `duration_ms` 欄位，也可以拆成 event 和 metric 兩筆。判斷依據是查詢需求 — 如果 funnel 分析和效能分析會分開查，拆開讓各自的查詢更簡單；如果都在同一個 dashboard 看，合併減少事件量。

## data schema 設計

每個事件的 data 欄位回答「發生了什麼的 context」。設計原則：

**帶足 debug context**：error 事件的 data 至少包含 error message、發生的步驟、當時的關鍵狀態值。看到這筆 error 事件時、開發者不需要再去查其他來源就能判斷問題方向。

**避免過度收集**：data 只帶回答具體問題需要的欄位。`terminal.connect.start` 帶 URL 和觸發方式就夠了；不需要帶使用者的全部設定。

**敏感欄位標記 redaction**：URL 可能含 IP、error message 可能含路徑中的使用者名稱。在事件設計階段標記需要 [redaction](/monitoring/knowledge-cards/redaction/) 的欄位，SDK 實作時自動處理。

## 事件表的產出格式

完整的事件表每列七欄：

| 事件名稱               | 類型  | 觸發時機       | data schema      | redaction 欄位 | 保留層級 | 備註          |
| ---------------------- | ----- | -------------- | ---------------- | -------------- | -------- | ------------- |
| terminal.connect.start | event | 使用者點擊連線 | `{url, trigger}` | url            | 原始 7d  | funnel 第一步 |

保留層級欄對應分層保留策略 — 哪些事件需要保留原始逐筆資料（debug 用）、哪些只需要聚合摘要（趨勢用）。

事件表是 SDK 埋點的 spec — 開發者照表實作，code review 時逐行勾選。和[功能規格中的 log 點定義](/testing/02-client-observability/log-point-in-spec/)互補 — log 點是開發期的 debug 設計，事件表是監控期的收集設計。

## 下一步路由

- 四類事件的定義 → [四類事件的完整定義](/monitoring/01-mental-model/four-event-types/)
- 事件命名規範 → [事件命名規範](/monitoring/01-mental-model/event-naming-convention/)
- 行為事件的 funnel 設計 → [行為事件設計](/monitoring/08-business-analytics/behavior-event-design/)
- 事件 schema 的欄位定義 → [event.schema.json 完整欄位解說](/monitoring/02-log-schema/event-schema-fields/)
