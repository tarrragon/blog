---
title: "Dashboard"
date: 2026-06-22
description: "說明 dashboard 如何把關鍵訊號組成可判讀的服務狀態畫面"
weight: 141
tags: ["backend", "observability"]
---

Dashboard 的核心概念是「把多個觀測訊號組成可判讀的服務狀態畫面」。它讓團隊用同一個視角查看 [SLI / SLO](/backend/knowledge-cards/sli-slo/)、latency、error rate、traffic、saturation、[queue depth](/backend/knowledge-cards/queue-depth/)、[consumer lag](/backend/knowledge-cards/consumer-lag/) 與下游依賴狀態。

## 概念位置

Dashboard 是告警與排障之間的判讀層。[Alert](/backend/knowledge-cards/alert/) 告訴團隊需要注意，dashboard 幫團隊判斷影響範圍、變化趨勢與可能原因，[runbook](/backend/knowledge-cards/runbook/) 則把判讀結果轉成處理步驟。

Dashboard 分層服務不同使用者：service overview 給 [on-call](/backend/knowledge-cards/on-call/) 工程師、debug dashboard 給事故中的深入診斷、capacity dashboard 給容量規劃。把所有資訊擠在同一個 dashboard 會讓每個角色都找不到自己要的。

## 使用情境

系統需要 dashboard 的訊號是事故中需要快速回答「影響多大、從何時開始、哪個依賴異常」。Dashboard 也是日常巡檢的入口 — on-call 工程師每天先看 service overview 確認服務健康，再處理 alert queue。

## 設計責任

Dashboard 設計要服務具體決策。每個面板應對應一個可回答的問題（「服務現在健康嗎」「延遲瓶頸在哪」「容量還夠嗎」）。高 cardinality、缺少單位或只呈現低層資源的圖表會增加判讀成本而非降低。

Dashboard panel 的查詢效能影響使用體驗 — 長時間趨勢 panel 應讀 [recording rule](/backend/knowledge-cards/recording-rule/) 或 [rollup](/backend/knowledge-cards/rollup/) 資料，避免每次刷新都掃描 raw series。Dashboard / alert 的完整設計見 [4.4](/backend/04-observability/dashboard-alert/)。
