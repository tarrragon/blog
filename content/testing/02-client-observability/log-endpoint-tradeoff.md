---
title: "自架 log endpoint vs 商業方案的取捨判斷"
date: 2026-06-19
description: "自用工具用自架 log receiver（20 行 Go + grep）、商業 app 用 Sentry/Crashlytics — 判斷依據是使用者規模和 debug 需求"
weight: 3
tags: ["testing", "observability", "logging", "infrastructure", "self-hosted"]
---

Log 收集方案的選擇取決於兩個因素：使用者在哪裡（同機 / 同網段 / 外部網路），以及 log 的消費者是誰（開發者自己 / 維運團隊 / 客服團隊）。自用工具和商業產品對這兩個因素的答案不同，適合不同的方案。

## 自架 log endpoint 的適用場景

自架 log endpoint 適合的前提是：client 和 server 在同一個網路內（同機、同 LAN、同 VPN/tailnet），log 的唯一消費者是開發者本人。

app_tunnel 就是這個場景。Server（ttyd）和 client（Flutter app）在同一台機器或同一個 Tailscale tailnet 內。開發者同時是使用者和維運者。Log 的消費方式是 grep — 不需要 dashboard、不需要告警、不需要多人共享。

在這個場景下，自架 log endpoint 的成本遠低於商業方案。一個 Go 程式開 HTTP endpoint 接收 JSON log 寫入檔案，20 行程式碼就能完成。Client 端的 `AppLogger` 在 debug mode 同時寫 console 和 POST 到 endpoint。Debug 時用 `grep` + `jq` 查詢，不需要額外工具。

```text
Client (Flutter) → HTTP POST /log → Go receiver → JSON file → grep/jq
```

這個方案沒有外部依賴、沒有帳號管理、沒有費用、沒有資料隱私顧慮（log 不離開本機網路）。

## 商業方案的適用場景

商業方案（Sentry、Crashlytics、Datadog）適合的前提是：使用者分佈在外部網路，log 的消費者包含非開發者（維運、客服、產品），且需要告警和趨勢分析。

商業方案提供的能力包括：跨網路收集（SDK 自動處理網路不穩定和批次傳輸）、多人查看 dashboard、告警規則設定、crash 報告自動分群、用戶 session 重播。這些能力在自用工具場景下不需要，在商業產品場景下是基礎需求。

商業方案的成本包括：SDK 整合和設定、帳號和權限管理、月費（依事件量計費）、資料隱私合規（log 傳到第三方伺服器）。

## 判斷流程

### 使用者在哪裡

使用者和 server 在同一個網路內（自用工具、內部工具、開發期測試）→ 自架 log endpoint 是成本最低的選擇。

使用者在外部網路（上架 app store、SaaS 產品、B2B 部署）→ 商業方案的跨網路收集能力是必要的，自架需要處理的 edge case（離線緩衝、重試、批次傳輸）太多。

### Log 消費者是誰

只有開發者自己 → grep/jq 足夠，不需要 dashboard。

包含非技術人員（客服、產品經理）→ 需要視覺化 dashboard 和搜尋介面，商業方案的 UI 是這個需求的標準答案。

### 是否需要告警

開發者自己用、即時看 log → 不需要告警。

有維運值班、需要被動發現問題 → 需要告警規則，商業方案內建。

## 混合方案

開發期用自架 log endpoint（零成本、即時可用），production 切換到商業方案 — 這個策略可行的前提是 log 層的 API 設計足夠抽象。

`AppLogger` 提供統一的 log 介面（`log(level, name, data)`），底層實作在 debug mode 寫 console + POST 到本機 endpoint，在 release mode 寫 console + 呼叫 Sentry/Crashlytics SDK。切換只改 `AppLogger` 的底層實作，不改呼叫端。

這個抽象的投資在自用工具階段就值得做 — 即使目前不需要商業方案，統一的 log 介面也讓 log 點的管理更一致。

## 下一步路由

- 三層 log 的詳細設計 → [三層 log 設計](/testing/02-client-observability/three-layer-log-design/)
- 在功能規格中定義 log 點 → [功能規格中的 log 點定義方法](/testing/02-client-observability/log-point-in-spec/)
- Log 收集後的 schema 設計 → [monitoring 模組二 Log Schema](/monitoring/02-log-schema/)
