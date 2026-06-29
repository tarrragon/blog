---
title: "Google：Error Budget 政策如何決定發布節奏"
date: 2026-05-07
description: "把 SLO 消耗量轉成 release gate，讓可靠性與交付速度共用同一套決策語言。"
weight: 11
tags: ["backend", "reliability", "case-study"]
---

Error budget policy 的核心責任是把「可靠性目標」轉成「發布節奏控制」。團隊不需要在每次風險升高時重新爭論要不要繼續推版，而是用同一套 SLO 消耗判準決定放行、限流或凍結。

## 問題場景

高變更頻率服務最常見的失效是小幅回歸連續累積，單點故障反而少見。每次回歸都不夠大，不會立刻觸發全停；但連續幾週後，使用者體感持續惡化，團隊才發現可靠性債已經超標。

這種情境需要的是「連續消耗判讀」，不是單次事故判讀。error budget policy 就是把連續消耗變成可操作的放行規則。

## 決策機制

政策設計先做三個對齊，再做門檻定義。

| 對齊項目       | 核心問題                       | 產出        |
| -------------- | ------------------------------ | ----------- |
| 使用者行為對齊 | 哪些 journey 直接反映服務價值  | SLI 範圍    |
| 可靠性承諾對齊 | 什麼水準算服務仍可接受         | SLO 目標    |
| 交付節奏對齊   | 可靠性消耗到哪裡要改變發布策略 | Budget gate |

有了這三個對齊後，release gate 可以從「主觀風險判斷」轉成「政策驅動」：

1. budget 健康：正常發版。
2. budget 快速消耗：啟用變更限速、提高驗證門檻。
3. budget 透支：凍結非必要變更，先修復與回補訊號。

## 可觀測訊號

政策有效與否要靠訊號判讀，不靠會議共識。

| 訊號                  | 判讀重點               | 對應章節                                                            |
| --------------------- | ---------------------- | ------------------------------------------------------------------- |
| burn rate             | 是否進入短期高消耗區   | [6.6](/backend/06-reliability/slo-error-budget/)                    |
| release failure ratio | 發版後回歸是否集中     | [6.8](/backend/06-reliability/release-gate/)                        |
| alert noise           | 告警是否支持 gate 判讀 | [4.6](/backend/04-observability/sli-slo-signal/)                    |
| recovery latency      | 凍結後修復是否收斂     | [8.3](/backend/08-incident-response/containment-recovery-strategy/) |

## 常見陷阱

把 error budget 當 KPI 會讓政策失真。這個機制的責任是「保護可靠性與交付節奏的平衡」，不是讓團隊追求某個固定分數。當 KPI 化開始主導行為，常見結果是 SLI 縮小、告警延後或例外條件過度擴張，最終反而降低判讀可信度。

## 下一步路由

要把這個案例落到制度層，先回到 [6.6](/backend/06-reliability/slo-error-budget/) 定義政策欄位，再到 [6.8](/backend/06-reliability/release-gate/) 實作 gate。若你發現訊號不足，先補 [4.16](/backend/04-observability/observability-readiness-review/) 與 [4.20](/backend/04-observability/observability-evidence-package/)。
