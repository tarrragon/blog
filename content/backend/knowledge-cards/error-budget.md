---
title: "Error Budget"
date: 2026-06-22
description: "說明 SLO 允許的失敗額度如何影響發版與可靠性投入"
weight: 101
tags: ["backend", "observability"]
---

Error budget 的核心概念是「[SLO](/backend/knowledge-cards/sli-slo/) 允許的失敗額度」。SLO = 99.9% 代表 30 天內允許 0.1% 的 request 失敗；這 0.1% 就是 error budget，用來平衡功能交付速度與可靠性改善投入。

## 概念位置

Error budget 把可靠性討論轉成可量化的決策語言。Budget 消耗過快時，團隊應暫停高風險變更、優先修可靠性；budget 充足時，可以承擔更多變更風險跟 experiment。

Error budget 是 [burn rate](/backend/knowledge-cards/burn-rate/) alerting 的基礎 — burn rate 量化的是 error budget 被消耗的速度。Error budget 接近耗盡時，進入 [release gate](/backend/knowledge-cards/release-gate/) 的 freeze 條件。

## 使用情境

系統需要 error budget 的訊號是發版速度與事故風險需要共同管理。Checkout 服務本月多次 timeout，若 error budget 已接近耗盡，團隊應暫停高風險變更直到 budget 恢復。

## 設計責任

Error budget 的 metric 結構需要 rolling window 的 total requests 跟 failed requests（見 [4.6 SLI/SLO 訊號設計](/backend/04-observability/sli-slo-signal/)）。Budget remaining 作為 [dashboard](/backend/knowledge-cards/dashboard/) panel 跟 release gate 的輸入 — 用 [recording rule](/backend/knowledge-cards/recording-rule/) 維護 rolling window 計算，避免每次查詢掃描 30 天的 raw data。
