---
title: "中台 Dashboard 設計"
date: 2026-06-20
description: "使用者怎麼用、在哪流失、怎麼讓他們回來 — 營運和行銷的日常指標監控與深入分析視圖，全部需要 PostgreSQL 層"
weight: 10
tags: ["monitoring", "collector", "dashboard", "business", "analytics", "funnel", "cohort"]
---

中台 dashboard 的消費者是營運單位和行銷單位，關心的是「使用者行為」和「商業指標」。這個 dashboard 和 [Developer dashboard](/monitoring/04-collector/dashboard-developer/) 的消費對象不同 — 開發者看 stack trace 和 error 分佈，營運看漏斗轉換和留存率。

中台 dashboard 的所有深入分析視圖都需要 PostgreSQL 層（[功能分層與 Backend 選擇](/monitoring/04-collector/feature-tier-boundary/)），因為它們依賴跨 session 的 JOIN 和大規模聚合查詢。SQLite 層只能提供基礎的事件計數。

## 日常監控視圖

### DAU / MAU

每日活躍使用者數（DAU）和每月活躍使用者數（MAU）的趨勢折線圖。活躍使用者的定義是「該時間段內至少有一筆 `session.start` 事件的唯一 session」。

DAU / MAU 比值（粘性指數）是產品健康的基本訊號 — 比值越高代表使用者回訪越頻繁。一般 SaaS 產品的 DAU/MAU 在 10-20% 為正常範圍，社交類產品期望 50% 以上。

```sql
-- PostgreSQL
SELECT date_trunc('day', ts) as day,
       COUNT(DISTINCT session_id) as dau
FROM events
WHERE type = 'lifecycle' AND name = 'session.start'
  AND ts >= NOW() - INTERVAL '30 days'
GROUP BY day
ORDER BY day;
```

### 核心漏斗

主要業務流程的每步轉換率。漏斗的步驟從 [動機驅動的事件設計](/monitoring/01-mental-model/motivation-to-event-mapping/) 的商業動機段定義。

日常視圖顯示最近 7 天的整體轉換率 — 營運人員每天看「昨天的漏斗有沒有異常」。轉換率突然下降是產品問題的早期訊號（UI 改版影響操作流程、第三方服務異常阻擋流程）。

### 功能使用排行

按 `event.name` 計數的排行榜。營運用它判斷「哪些功能有人用、哪些沒人用」— 功能投資的 ROI 判斷依據。

```sql
-- SQLite 層可用（基礎計數）
SELECT name, COUNT(*) as usage_count
FROM events
WHERE type = 'event'
  AND ts >= datetime('now', '-7 days')
GROUP BY name
ORDER BY usage_count DESC
LIMIT 20;
```

功能使用排行是 SQLite 層就能提供的視圖 — 單表 GROUP BY。

## 分析深入視圖

日常視圖發現異常後，營運人員進入分析視圖深入探究。所有分析視圖都需要 PostgreSQL 層。

### Funnel 漏斗圖

互動式漏斗圖：選擇步驟 → 看每步轉換率 → 點擊某步看流失使用者的行為。

Funnel 需要 session 級 JOIN — 「同一個 session 完成了步驟 1 到步驟 N 中的哪些步驟」。完整的 SQL 查詢見 [從 collector 資料做基礎 funnel 分析](/monitoring/08-business-analytics/self-hosted-funnel/)。

### Cohort 留存表

按「使用者首次出現日期」分群的留存率矩陣。行是 cohort（第 N 週註冊的使用者），列是「第 1/2/3/…週的回訪率」。

需要的事件：`user.first_seen`（cohort 分群依據）+ `session.start`（回訪判定）。

`user.first_seen` 是 collector 端計算的衍生事件 — 當某個 session_id 或 user identifier 在系統中第一次出現時記錄。和 SDK 端送來的原始事件不同，它的產生者是 collector 的計算邏輯。

### A/B 測試結果

實驗的 variant 間轉換率比較 + 統計顯著性指標（p-value、信賴區間）。

需要的事件：`experiment.{name}.assigned`（分組）+ `experiment.{name}.converted`（轉換）。這些事件在 [動機驅動的事件設計](/monitoring/01-mental-model/motivation-to-event-mapping/) 的 A/B 測試段定義。統計分析的方法見 [A/B test 的統計基礎](/monitoring/08-business-analytics/ab-test-statistics/)。

### RFM 分群散佈圖

三維度（Recency / Frequency / Monetary）的使用者分群。每個使用者計算 R/F/M 分數，按分數分群後在散佈圖上顯示。

需要的事件：event 類的購買/使用事件 + lifecycle 的 session 事件。計算方法見 [RFM 分群](/monitoring/08-business-analytics/rfm-segmentation/)。

### 通路歸因

使用者從哪裡來（哪個廣告、哪個推薦連結、自然流量），每個通路帶來多少轉換。

需要的事件：`attribution.install_source`（SDK 首次啟動時從 referrer / UTM 參數 / deep link 取得安裝來源）+ `conversion.{type}`（轉換事件）。

`attribution.install_source` 只在 SDK 首次啟動時送一次。來源資訊的取得方式依平台不同 — Web 從 URL 的 UTM 參數取、mobile app 從 deferred deep link 或 install referrer API 取。

## 需要的缺口事件

中台 dashboard 暴露了三個目前事件表未覆蓋的事件：

| 事件名稱                   | 類型      | 產生者         | 用途            | 為什麼缺                                          |
| -------------------------- | --------- | -------------- | --------------- | ------------------------------------------------- |
| user.first_seen            | lifecycle | Collector 計算 | Cohort 分群依據 | 原始事件設計聚焦 SDK 端，衍生計算事件不在設計範圍 |
| attribution.install_source | event     | SDK 首次啟動   | 通路歸因        | 只在首次啟動送一次的事件沒有被操作盤點覆蓋        |
| session.active.count       | metric    | Collector 計算 | 即時在線大屏    | 即時統計是 collector 端的衍生 metric              |

這三個事件的共同特徵：前兩個是「只發生一次」的事件（首次出現、首次安裝），第三個是 collector 端的即時計算結果。操作盤點和四類補齊檢查聚焦在「反覆發生的使用者操作」，容易遺漏「只發生一次」的生命週期轉折點和 collector 端的衍生計算。

## 中台的權限隔離

營運和行銷人員看行為資料，但不需要也不應該看到 stack trace、raw error message、session 級別的原始事件明細。權限隔離在 collector 的查詢 API 層實作 — 不同的 API scope 回傳不同粒度的資料。

| Scope     | 可見                                      | 不可見                                        |
| --------- | ----------------------------------------- | --------------------------------------------- |
| devops    | collector 健康 metric、SDK 狀態           | 業務事件明細                                  |
| developer | 全部事件、stack trace、session 回放       | 無限制                                        |
| business  | 聚合統計（funnel/cohort/count）、匿名行為 | stack trace、error raw data、session 原始事件 |

Scope 的實作可以是 API key 分級（不同 key 有不同 scope）、或 HTTP header 帶 role。Day-one 可以跳過（自用場景只有 developer 一個角色），tripwire 是「第一個非開發者要看 dashboard 時加入 scope 機制」。

## 下一步路由

- DevOps dashboard 設計 → [DevOps Dashboard 設計](/monitoring/04-collector/dashboard-devops/)
- Developer dashboard 設計 → [Developer Dashboard 設計](/monitoring/04-collector/dashboard-developer/)
- Funnel 分析的完整方法 → [Funnel analysis](/monitoring/08-business-analytics/funnel-analysis/)
- 功能分層與 Backend 選擇 → [功能分層與 Backend 選擇](/monitoring/04-collector/feature-tier-boundary/)
- 去識別化是中台 dashboard 的入場條件 → [模組七 資安與隱私](/monitoring/07-security-privacy/)
- 畫面狀態矩陣定義了 funnel 步驟的操作來源 → [畫面狀態矩陣](/ux-design/01-screen-state-machine/state-matrix-definition/)
