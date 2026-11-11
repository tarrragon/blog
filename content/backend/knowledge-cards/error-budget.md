---
title: "Error Budget"
date: 2026-06-22
description: "說明 SLO 允許的失敗額度如何影響發版與可靠性投入"
weight: 102
tags: ["backend", "observability"]
---

Error budget 的核心概念是「[SLO](/backend/knowledge-cards/sli-slo/) 允許的失敗額度」。SLO = 99.9% 代表 30 天內允許 0.1% 的 request 失敗；這 0.1% 就是 error budget，用來平衡功能交付速度與可靠性改善投入。

## 跟其他概念的關係

Error budget 把可靠性討論轉成可量化的決策語言。Budget 消耗過快時，團隊應暫停高風險變更、優先修可靠性；budget 充足時，可以承擔更多變更風險跟 experiment。

Error budget 是 [burn rate](/backend/knowledge-cards/burn-rate/) alerting 的基礎 — burn rate 量化的是 error budget 被消耗的速度。Error budget 接近耗盡時，進入 [release gate](/backend/knowledge-cards/release-gate/) 的 freeze 條件。

## 使用情境

系統需要 error budget 的訊號是發版速度與事故風險需要共同管理。Checkout 服務本月多次 timeout，若 error budget 已接近耗盡，團隊應暫停高風險變更直到 budget 恢復。

## 判斷條件與後果

Budget remaining 是 rolling window 內 failed requests 對 total requests 的比例跟 SLO 允許額度相減的結果，兩項計數少了任一項就算不出來（指標結構見 [4.6 SLI/SLO 訊號設計](/backend/04-observability/sli-slo-signal/)）。它同時是 [dashboard](/backend/knowledge-cards/dashboard/) panel 與 release gate 的輸入時，每一次 panel 重新整理與每一次 gate 檢查都要算一次 30 天的 rolling window；直接從 raw data 算，每次查詢都掃過 30 天的原始資料，查詢成本隨流量增加，gate 檢查也跟著變慢。所以 rolling window 的計算由 [recording rule](/backend/knowledge-cards/recording-rule/) 預先算好，dashboard 與 gate 讀算好的結果。
