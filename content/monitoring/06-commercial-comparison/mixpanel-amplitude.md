---
title: "Mixpanel / Amplitude"
date: 2026-06-19
description: "行為分析專用方案 vs 通用監控方案 — funnel、cohort、retention 的原生支援和 error tracking 的缺席"
weight: 5
tags: ["monitoring", "mixpanel", "amplitude", "analytics", "behavior"]
---

Mixpanel 和 Amplitude 是行為分析專用方案，設計重心在「使用者做了什麼」而非「系統出了什麼問題」。它們提供 funnel analysis、cohort analysis、retention curve 等分析功能的原生支援，但缺少 error tracking 和 performance monitoring。

## 和通用監控方案的定位差異

Sentry 和 Datadog 是「先解決問題（error），順便分析行為」。Mixpanel 和 Amplitude 是「先分析行為（event），需要的話整合 error tracking」。

| 能力            | Sentry / Datadog | Mixpanel / Amplitude |
| --------------- | ---------------- | -------------------- |
| Error tracking  | 核心功能         | 需整合第三方         |
| Performance     | 內建             | 不提供               |
| Funnel analysis | 基礎             | 進階（多維度分群）   |
| Cohort analysis | 有限             | 核心功能             |
| Retention curve | 不提供           | 核心功能             |
| A/B test 整合   | 不提供           | 內建或整合           |
| Session replay  | Sentry 有        | 部分方案有           |

## Funnel 的進階能力

Mixpanel 和 Amplitude 的 funnel analysis 比 Sentry 的 breadcrumb 分析和自架方案的 grep 計數提供更多維度：

**分群 funnel**：同一個 funnel 按使用者屬性分群（新使用者 vs 舊使用者、iOS vs Android），看不同群組的轉換率差異。

**時間窗口**：定義 funnel 的時間窗口（使用者必須在 7 天內完成所有步驟才算轉換），過濾掉偶然的事件序列。

**轉換趨勢**：funnel 的轉換率隨時間的變化。新版本部署後特定步驟的流失率是否增加。

## Cohort 和 Retention

Cohort analysis 把使用者按特定條件分群（註冊日期、首次使用功能、來源渠道），追蹤每個群組的長期行為。

Retention curve 顯示「首次使用後，有多少使用者在第 N 天/週/月回來使用」。這是衡量產品黏性的核心指標 — 自架方案需要手動計算，行為分析方案一鍵產出。

## 適用場景

Mixpanel / Amplitude 適合的前提：產品的核心決策依賴行為分析（「使用者在哪一步流失」「哪個功能驅動留存」），且 error tracking 由另一個方案（Sentry / Crashlytics）覆蓋。

如果同時需要 error tracking 和行為分析，有兩種策略：

**雙方案**：Sentry 做 error tracking + Mixpanel 做行為分析。兩個 SDK、兩個 dashboard、兩份費用。適合兩邊的需求都重度的場景。

**通用方案加強行為分析**：Datadog RUM 或 Firebase Analytics 提供基礎行為分析能力。功能不如 Mixpanel 深入，但一個方案覆蓋兩個需求。適合行為分析需求不重度的場景。

## 下一步路由

- 自架 vs 商業決策 → [自架 vs 商業的判斷決策表](/monitoring/06-commercial-comparison/self-hosted-vs-commercial/)
- 行為分析的工程方法論 → [模組八 行為資料商業利用](/monitoring/08-business-analytics/)
- 事件設計如何影響分析品質 → [模組八 行為事件設計](/monitoring/08-business-analytics/behavior-event-design/)
