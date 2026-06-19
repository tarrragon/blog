---
title: "Mixpanel / Amplitude"
date: 2026-06-19
description: "行為分析專用方案 vs 通用監控的差異 — Mixpanel 和 Amplitude 的 funnel / cohort / retention 分析能力"
weight: 5
tags: ["monitoring", "mixpanel", "amplitude", "analytics", "funnel", "cohort"]
---

Mixpanel 和 Amplitude 是行為分析（product analytics）專用方案。核心功能是 funnel analysis、cohort analysis、retention analysis — 回答「使用者怎麼使用產品」。和 Sentry（error-first）、Datadog（APM-first）的定位有本質差異：行為分析的消費者是產品團隊，通用監控的消費者是工程團隊。

## 行為分析 vs 通用監控

通用監控方案（Sentry、Crashlytics、Datadog）的主要產出是 error 報告和 performance 數據 — 工程團隊用來修復 bug 和優化效能。

行為分析方案的主要產出是 funnel 和 cohort 數據 — 產品團隊用來決定功能優先順序、評估改版效果、優化使用者體驗。

兩類需求可以共存。工程團隊需要 error tracking，產品團隊需要行為分析。一些團隊同時使用 Sentry + Mixpanel，各自服務不同的消費者。

## 核心功能

### Funnel analysis

定義使用者操作的步驟序列，計算每步的轉換率和流失率。Mixpanel 和 Amplitude 的 funnel 分析支援：步驟之間的時間窗口限制（步驟 1 到步驟 2 在 24 小時內完成才算轉換）、按使用者屬性分群（新使用者 vs 老使用者的轉換率差異）、步驟之間的路徑分析（流失的使用者去了哪裡）。

自架方案能做基礎的 funnel 計數（[模組八 自架 funnel](/monitoring/08-business-analytics/)），但不支援時間窗口、分群和路徑分析。

### Cohort analysis

按使用者屬性或行為把使用者分成群組，比較不同群組的行為差異。例：「從 Google 廣告來的使用者」vs「從社群分享來的使用者」，兩組的留存率和付費率差異。

### Retention analysis

追蹤使用者在初次使用後的回訪率。Day 1 / Day 7 / Day 30 retention — 多少使用者在首次使用後 1 天 / 7 天 / 30 天內回來。

Retention 是產品健康度的核心指標。行為分析方案提供 retention curve（留存曲線）和 retention by cohort（不同群組的留存差異），這些在自架方案中需要大量的 SQL 查詢和手動計算。

## Mixpanel vs Amplitude 的差異

兩者的功能高度重疊，差異主要在定價和資料模型：

| 維度     | Mixpanel                    | Amplitude                       |
| -------- | --------------------------- | ------------------------------- |
| 定價模型 | 按事件量計費                | 按 MTU（月活使用者）計費        |
| 資料模型 | event-centric（事件為中心） | event + user profile            |
| SQL 查詢 | JQL（自訂查詢語言）         | 原生 SQL 支援（Amplitude SQL）  |
| 免費額度 | 每月 2000 萬事件            | 每月 1000 萬事件                |
| 整合     | 豐富的第三方整合            | CDP（Customer Data Platform）強 |

選擇依據通常是團隊的既有工具鏈和定價模型偏好。

## 什麼時候需要行為分析方案

行為分析方案的投資在以下條件下有回報：

**有產品團隊消費數據**：如果只有工程團隊，error tracking + 自架 log 通常足夠。行為分析方案的 dashboard 需要產品團隊定期查看和基於數據做決策。

**使用者數量足夠產生統計意義**：Funnel 和 cohort 分析需要足夠的樣本量。DAU < 100 的產品，分析結果的統計信度低。

**有明確的優化目標**：「提高註冊轉換率」「降低 Day 7 流失率」— 有具體的 metric 目標，行為分析方案能提供追蹤和歸因。

自用工具場景下不需要行為分析方案 — 使用者就是開發者本人，行為數據沒有分析價值。

## 下一步路由

- 自架 vs 商業的判斷 → [自架 vs 商業的判斷決策表](/monitoring/06-commercial-comparison/self-hosted-vs-commercial/)
- 行為分析的方法論 → [模組八 行為資料的商業利用](/monitoring/08-business-analytics/)
- 四類事件在商業方案中的對應 → [模組一 商業方案事件類型對應](/monitoring/01-mental-model/commercial-event-mapping/)
