---
title: "Firebase 套件"
date: 2026-06-19
description: "Crashlytics + Analytics + Remote Config 的整合 — Firebase 把 error tracking 和行為分析拆成獨立產品的設計取捨"
weight: 3
tags: ["monitoring", "firebase", "crashlytics", "analytics", "remote-config"]
---

Firebase 把 client-side 監控拆成多個獨立產品：Crashlytics 負責 crash 報告、Analytics（GA4）負責行為分析、Remote Config 負責功能旗標和 A/B test。三個產品各自有 SDK、dashboard 和計費模型，但共享 Firebase project 的使用者識別。

## Crashlytics

Firebase Crashlytics 專注在 crash 報告 — fatal crash（app 當機）和 non-fatal exception（被捕獲但值得記錄的錯誤）。

### 自動 crash 報告

Crashlytics SDK 在 app crash 時自動收集 crash 資訊（stack trace、device info、OS version），在下次 app 啟動時上傳。不需要開發者寫程式碼 — SDK 初始化後自動運作。

### Issue 分群

和 Sentry 類似，Crashlytics 用 stack trace 自動把 crash 分群成 issue。每個 issue 有影響的使用者數、趨勢、crash-free session 比率。

### 和 Analytics 的關聯

Crashlytics 可以在 crash 報告中附加 Analytics 的使用者屬性和自訂 key。但兩者的 dashboard 獨立 — crash 資料在 Crashlytics console，行為資料在 Analytics console。要從「crash」追蹤到「crash 前使用者做了什麼」需要在兩個 console 之間切換。

## Analytics（GA4）

Firebase Analytics 是 Google Analytics 4（GA4）的 mobile SDK 版本。記錄使用者操作事件（screen view、button click、purchase）和使用者屬性。

### 自動收集事件

GA4 SDK 自動收集一組預定義事件：`first_open`、`session_start`、`screen_view`、`user_engagement`。開發者不需要手動埋點就能得到基礎的使用統計。

### 自訂事件

開發者用 `logEvent(name, parameters)` 記錄自訂事件。事件名稱和參數的命名有限制（名稱 40 字元、參數 25 個、參數值 100 字元）。

### 和四類事件的對應

GA4 主要處理 Event 類和 Lifecycle 類事件（[模組一](/monitoring/01-mental-model/four-event-types/)）。Error 類由 Crashlytics 處理。Metric 類沒有原生支援 — 需要把 metric 包裝成 event 的 parameter。

## Remote Config

Firebase Remote Config 讓開發者在不更新 app 的情況下修改 app 的行為 — 功能旗標（feature flag）、UI 文案、數值參數。

### 和 A/B test 的整合

Remote Config 和 Firebase A/B Testing 整合：定義實驗（variant A: 舊 UI / variant B: 新 UI），Remote Config 自動分配使用者到 variant，Analytics 收集兩組使用者的行為數據，A/B Testing console 顯示統計結果。

這個整合是 Firebase 生態的獨特優勢 — config 分發、使用者分群、行為收集、統計分析在同一個平台完成，不需要整合多個工具。

## Firebase 的取捨

Firebase 的設計取捨是「拆分但整合」— 每個產品獨立運作（可以只用 Crashlytics 不用 Analytics），但組合使用時有整合優勢（Crashlytics + Analytics 的 user ID 共享）。

| 優勢                        | 代價                                               |
| --------------------------- | -------------------------------------------------- |
| 自動收集、零配置啟動        | 自訂彈性受限（事件命名限制、參數數量限制）         |
| Crashlytics 免費且無量限制  | Analytics 的進階功能需要 BigQuery export（另收費） |
| A/B test 整合開箱即用       | 鎖定 Google 生態（資料 export 有限制）             |
| Mobile 優先，Flutter 支援佳 | Web 的支援較弱（GA4 web 是獨立產品線）             |

## 下一步路由

- Datadog 的全棧 APM → [Datadog RUM](/monitoring/06-commercial-comparison/datadog-rum/)
- 行為分析專用方案 → [Mixpanel / Amplitude](/monitoring/06-commercial-comparison/mixpanel-amplitude/)
- 自架 vs 商業的判斷 → [自架 vs 商業的判斷決策表](/monitoring/06-commercial-comparison/self-hosted-vs-commercial/)
