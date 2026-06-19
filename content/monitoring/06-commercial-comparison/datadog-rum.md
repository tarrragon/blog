---
title: "Datadog RUM"
date: 2026-06-19
description: "全棧 APM 的 client-side 觀點 — client action 到 server trace 的完整鏈路追蹤"
weight: 4
tags: ["monitoring", "datadog", "rum", "apm", "full-stack"]
---

Datadog Real User Monitoring（RUM）從全棧 APM 的角度設計 client-side 監控。核心特徵是 client 端的使用者操作可以關聯到 server 端的 trace，形成從按鈕點擊到 database query 的完整請求鏈路。

## 全棧追蹤

Datadog RUM 的 SDK 在 HTTP 請求中自動注入 trace context header。Server 端的 Datadog APM agent 讀取 header，把 server 端的 trace 和 client 端的 action 關聯。

這個能力在 debug「API 慢」的問題時特別有用 — 從 client 端看到「這個按鈕的回應時間 3 秒」，點進去看到 server 端的 trace 顯示「database query 佔了 2.8 秒」。自架方案和 Sentry 都做不到這個深度的跨層關聯。

前提是 server 端也使用 Datadog APM。如果 server 端用其他 APM（New Relic、Elastic APM），client-server 的關聯需要自行實作或用 OpenTelemetry 橋接。

## 四種 RUM 事件

Datadog RUM 收集四種事件，和自架方案的四類事件有對應關係（[模組一 商業方案對應](/monitoring/01-mental-model/commercial-event-mapping/)）：

**View**：頁面或畫面的載入和離開。自動偵測 SPA 的 route 變換，對應 lifecycle 事件。

**Action**：使用者操作。自動捕獲 click、tap、scroll，可手動記錄自訂 action，對應 event 事件。

**Error**：JS exception、network error、自訂 error，對應 error 事件。

**Long Task**：執行時間超過 50ms 的任務（阻塞主執行緒），對應 metric 事件。

## 定價

Datadog RUM 按 session 數計費（每個 session 是一次使用者訪問）。和 Sentry 按事件數計費不同 — session 計費讓成本更可預測（不會因為單次訪問觸發大量事件而費用暴增）。

Datadog 的完整方案（RUM + APM + Logs + Infrastructure）費用較高，適合已經用 Datadog 做 server-side 監控的團隊。單獨用 RUM 而 server 端用其他方案，失去全棧追蹤的優勢。

## 下一步路由

- 行為分析專用方案 → [Mixpanel / Amplitude](/monitoring/06-commercial-comparison/mixpanel-amplitude/)
- Sentry 對比 → [Sentry 深入](/monitoring/06-commercial-comparison/sentry-deep-dive/)
- 自架 vs 商業決策 → [自架 vs 商業的判斷決策表](/monitoring/06-commercial-comparison/self-hosted-vs-commercial/)
