---
title: "商業方案的事件類型對應"
date: 2026-06-19
description: "Sentry / Crashlytics / GA4 / Datadog RUM 各自如何對應四類事件 — 理解商業方案的分類邏輯才能正確接入"
weight: 3
tags: ["monitoring", "mental-model", "sentry", "crashlytics", "ga4", "datadog"]
---

商業監控方案各自有不同的事件分類體系。理解它們的分類邏輯和四類事件（event / error / metric / lifecycle）的對應關係，才能在接入時正確映射自架方案的事件，避免資料遺漏或分類錯誤。

## Sentry

Sentry 的核心概念是 error tracking，但已擴展到 performance monitoring 和 session replay。

| 四類事件  | Sentry 對應              | 說明                                               |
| --------- | ------------------------ | -------------------------------------------------- |
| Event     | Breadcrumb               | 使用者操作記錄在 breadcrumb trail，附加在 error 上 |
| Error     | Event（Exception type）  | Sentry 的核心。自動捕獲 + 手動 captureException    |
| Metric    | Transaction + Span       | Performance monitoring 的度量單位                  |
| Lifecycle | Breadcrumb（navigation） | app 生命週期記錄為 navigation/system breadcrumb    |

Sentry 的設計假設是「error 是主角，其他事件是 error 的 context」。Event 和 lifecycle 都以 breadcrumb 形式附加在 error 報告上，獨立查看的能力有限。如果主要需求是行為分析而非 error tracking，Sentry 的 breadcrumb 模型可能不夠用。

## Firebase Crashlytics + Analytics

Firebase 把 error tracking 和行為分析拆成兩個獨立產品。

| 四類事件  | Firebase 對應                | 說明                                             |
| --------- | ---------------------------- | ------------------------------------------------ |
| Event     | Analytics custom event       | GA4 的 event，有 parameters 附加屬性             |
| Error     | Crashlytics exception        | fatal + non-fatal exception 分開處理             |
| Metric    | Analytics event + parameters | 用 event 的 parameters 記錄數值（無原生 metric） |
| Lifecycle | Analytics auto events        | screen_view、app_open 等自動收集                 |

Firebase 的特點是 Crashlytics 和 Analytics 各自獨立運作 — error 資料在 Crashlytics console，行為資料在 Analytics console。兩者的關聯需要手動（在 Crashlytics 的 custom key 中設定 user ID，再到 Analytics 用同一個 ID 查行為）。

## Datadog RUM

Datadog Real User Monitoring 從全棧 APM 的角度設計 client-side 監控。

| 四類事件  | Datadog RUM 對應 | 說明                                           |
| --------- | ---------------- | ---------------------------------------------- |
| Event     | Action           | 使用者操作（click、tap、scroll）自動或手動捕獲 |
| Error     | Error            | JS exception、network error、custom error      |
| Metric    | Long Task + 自訂 | 長任務自動捕獲，自訂 metric 用 global context  |
| Lifecycle | View             | 頁面/畫面的進入和離開，自動偵測 SPA route 變換 |

Datadog RUM 的特點是和 backend APM 的深度整合。Client-side 的 action 可以關聯到 server-side 的 trace，形成從按鈕點擊到 database query 的完整鏈路。自架方案通常做不到這個深度的跨層關聯。

## 接入策略

接入商業方案時的映射原則：

**自架事件名稱是 source of truth**。商業方案的事件名稱是自架名稱的映射，不是取代。映射邏輯集中在一個 adapter 層，商業方案更換時只改 adapter。

**不要為了配合商業方案改變自架的分類**。Sentry 把 event 記錄為 breadcrumb 不代表自架方案也要把 event 降級成 error 的附屬品。自架的四類分類是語意正確的，商業方案的分類是它自己的產品設計。

**同時接入多個方案時做去重**。Error 同時發到 Sentry 和 Crashlytics 會產生重複。在 adapter 層控制「哪類事件發到哪個方案」，避免同一個事件在多個 dashboard 出現。

## 下一步路由

- 四類事件的定義 → [四類事件的完整定義](/monitoring/01-mental-model/four-event-types/)
- 商業方案的深入比較 → [模組六 商業方案比較](/monitoring/06-commercial-comparison/)
- 事件命名規範 → [事件命名規範](/monitoring/01-mental-model/event-naming-convention/)
