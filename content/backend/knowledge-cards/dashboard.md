---
title: "Dashboard"
date: 2026-04-23
description: "說明 dashboard 如何把關鍵訊號組成可判讀的服務狀態畫面"
weight: 141
---

Dashboard 的核心概念是「把多個觀測訊號組成可判讀的服務狀態畫面」。它讓團隊用同一個視角查看 [SLI / SLO](/backend/knowledge-cards/sli-slo/)、latency、error rate、traffic、saturation、[queue depth](/backend/knowledge-cards/queue-depth/)、[consumer lag](/backend/knowledge-cards/consumer-lag/) 與下游依賴狀態。

## 概念位置

Dashboard 是告警與排障之間的判讀層。[Alert](/backend/knowledge-cards/alert/) 告訴團隊需要注意，dashboard 幫團隊判斷影響範圍、變化趨勢與可能原因，[runbook](/backend/knowledge-cards/runbook/) 則把判讀結果轉成處理步驟。

## 可觀察訊號與例子

系統需要 dashboard 的訊號是事故中需要快速回答「影響多大、從何時開始、哪個依賴異常」。Consumer lag 告警後，dashboard 應同時呈現 publish rate、process rate、queue depth、[DLQ](/backend/knowledge-cards/dead-letter-queue/)、下游 latency 與 error rate。

## 設計責任

Dashboard 設計要服務具體決策。每個面板應對應容量、可靠性、使用者影響或操作動作；高 cardinality、缺少單位或只呈現低層資源的圖表會增加判讀成本。
