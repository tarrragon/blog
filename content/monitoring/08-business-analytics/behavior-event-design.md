---
title: "行為事件設計"
date: 2026-06-19
description: "事件命名規範、屬性設計、funnel 定義 — 行為分析的品質取決於事件設計的品質"
weight: 1
tags: ["monitoring", "analytics", "event-design", "funnel", "naming"]
---

行為事件是使用者操作的結構化記錄，每一筆事件回答「誰、在什麼時候、做了什麼、結果如何」。行為分析的品質上限由事件設計決定 — 事件粒度太粗無法回答細節問題，事件粒度太細讓儲存和查詢成本失控。

## 事件命名

行為事件的命名遵循 `namespace.action` 格式（[模組一 事件命名規範](/monitoring/01-mental-model/event-naming-convention/)）。行為分析場景對命名的額外要求是：同一個 funnel 內的事件要能用 namespace 前綴篩選。

例：註冊流程的事件用共同前綴 `signup`：

```text
signup.page.view          使用者看到註冊頁
signup.form.submit        使用者送出表單
signup.email.verify       使用者點擊驗證信連結
signup.complete           註冊完成
```

用 `signup.*` 就能篩選出整個註冊流程的事件，不需要事先知道每一步的完整名稱。

## 屬性設計

每個事件除了名稱，還帶有屬性（properties / parameters）描述事件的 context。屬性分成三層：

### 通用屬性（每個事件都有）

- `timestamp`：事件發生的時間（UTC，毫秒精度）
- `session_id`：當次使用的 session 識別碼
- `user_id`：使用者識別碼（去識別化後，見 [模組七](/monitoring/07-security-privacy/)）
- `platform`：iOS / Android / Web
- `app_version`：app 版本號

### 事件類型屬性（同類事件共有）

- 頁面瀏覽事件：`page_name`、`referrer`
- 按鈕點擊事件：`button_id`、`button_text`
- 搜尋事件：`query`、`result_count`

### 事件專屬屬性（特定事件才有）

- `signup.form.submit`：`form_method`（email / Google / Apple）
- `purchase.complete`：`amount`、`currency`、`product_id`

屬性設計的判斷標準是：這個屬性是否用於回答一個分析問題。「註冊方式的轉換率差異」需要 `form_method` 屬性；如果沒有這個分析問題，就不需要這個屬性。

## Funnel 定義

Funnel 是一連串有順序的事件，代表使用者完成一個目標的步驟。Funnel 定義在事件設計階段完成 — 決定哪些事件構成一個 funnel、順序是什麼、每步之間的最大時間間隔。

定義一個 funnel 需要：

**步驟清單**：funnel 包含哪些事件，順序是什麼。

**時間窗口**：步驟之間的最大間隔。使用者在步驟 A 之後 30 天才做步驟 B，是否算在同一個 funnel 內？時間窗口的設定取決於業務場景 — 電商結帳 funnel 通常是 30 分鐘，SaaS onboarding funnel 可能是 7 天。

**完成條件**：什麼算「完成」funnel。到達最後一步即完成，還是需要特定屬性值（`purchase.complete` 且 `status = success`）。

## 過度收集的成本

行為事件收集的邊界是「能回答已知的分析問題」。收集超出分析需求的事件有三個成本：

**儲存成本**：每個事件佔一行 JSONL。高頻事件（每次滾動、每次 hover）的資料量遠大於低頻事件（按鈕點擊、頁面瀏覽）。

**隱私風險**：收集的事件越多，包含可識別個人行為模式的風險越高（[模組七 資安與隱私](/monitoring/07-security-privacy/)）。

**噪音**：分析時需要從大量事件中篩選出有意義的模式。事件越多，訊噪比越低。

## 下一步路由

- 用行為事件做 funnel 分析 → [Funnel analysis](/monitoring/08-business-analytics/funnel-analysis/)
- 事件的四類分類 → [模組一 四類事件定義](/monitoring/01-mental-model/four-event-types/)
- 去識別化是行為分析的入場條件 → [模組七 資安與隱私](/monitoring/07-security-privacy/)
