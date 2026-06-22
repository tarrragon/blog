---
title: "欄位設計原則"
date: 2026-06-19
description: "source 標明來源、data 自由欄位、v 版本演進 — 三個設計原則讓 schema 在不同階段都能使用"
weight: 2
tags: ["monitoring", "log-schema", "design", "principles"]
---

事件 schema 的欄位設計遵循三個原則：來源可追溯、擴展不破壞、版本可辨識。這三個原則讓 schema 從自用工具的 grep 查詢一直到商業方案的資料管線都能正常運作。

## 原則一：source 標明來源

每筆事件的 source 欄位記錄「這筆事件從哪裡來」。App 名稱、版本、平台、OS 版本 — 這些資訊在事件產生時由 SDK 自動填入，不依賴使用者或開發者手動標記。

source 的設計要點是「足夠區分但不過度」。`sdk` 和 `platform` 是必填——sdk 標明事件由哪個 SDK 實作產生（`js` / `flutter` / `python` / `go`），platform 標明運行平台（`ios` / `android` / `web` / `macos`）。兩者不能互相推導：同一個 platform（iOS）上可能有不同的 SDK（Flutter SDK 或 Swift 原生 SDK），同一個 SDK（Flutter）可能跑在不同 platform（iOS / Android / Web）。App 名稱和版本能區分「這是哪個 app 的哪個版本送來的事件」。OS 版本用於分析平台特定的問題（「這個 error 只出現在 iOS 17.4」）。

不需要在 source 放裝置 ID 或使用者 ID — 這些屬於個人識別資訊，放在 source 會讓每一筆事件都攜帶 PII，增加去識別化的複雜度。Session ID 用於關聯同次使用的事件，已足夠取代裝置/使用者級別的追蹤。

## 原則二：data 自由欄位

data 欄位是事件的附加資料區域，接受任意 JSON object。核心欄位（type、name、timestamp、source）有固定的 schema 驗證，data 的內容不做 schema 驗證（或做寬鬆驗證）。

自由欄位的設計理由是「不同事件需要不同的附加資料」。`terminal.connect.done` 需要 URL 和 duration；`auth.biometric.failed` 需要 error code 和 fallback 方式。為每種事件定義固定的 data schema 會讓 schema 膨脹且頻繁變動。

自由的代價是查詢時無法保證 data 內某個欄位一定存在。處理策略：查詢時用 optional access（`data?.duration_ms`），統計時跳過缺少目標欄位的事件。

## 原則三：v 版本演進

v 欄位是整數版本號，標明「這筆事件是用哪個版本的 schema 產生的」。

版本號解決的問題是 schema 變更時的向後相容。新版本的 SDK 產生 v=2 的事件，舊版本的 SDK 仍在產生 v=1 的事件。Collector 收到事件時根據 v 決定用哪個版本的驗證和處理邏輯。

版本號的遞增規則：

- **新增選填欄位**：不需要遞增版本號。舊版事件缺少新欄位，collector 用預設值處理。
- **新增必填欄位**：遞增版本號。舊版事件沒有這個欄位，collector 需要區分版本處理。
- **刪除或改名欄位**：遞增版本號。collector 需要同時支援新舊版本的事件格式。
- **改變欄位型別**：遞增版本號。string 改成 integer 等型別變更需要不同的解析邏輯。

## 欄位命名慣例

欄位名稱使用 snake_case（`duration_ms`、`error_code`），和 JSON 的慣例一致。避免在欄位名稱中編碼單位（`duration` 不夠明確 — 是秒還是毫秒？），在名稱中加上單位後綴（`duration_ms`、`size_bytes`）。

## 下一步路由

- 完整欄位定義 → [event.schema.json 完整欄位解說](/monitoring/02-log-schema/event-schema-fields/)
- Schema 版本演進的具體策略 → [Schema 版本演進策略](/monitoring/02-log-schema/schema-versioning/)
- 和 OpenTelemetry 的比較 → [跟 OpenTelemetry 的 schema 差異對照](/monitoring/02-log-schema/otel-comparison/)
