---
title: "Symptom-Based Alert"
tags: ["症狀式告警", "Symptom-Based Alert"]
date: 2026-04-23
description: "說明告警應優先偵測使用者可感知症狀"
weight: 108
---

Symptom-based alert 的核心概念是「[alert](/backend/knowledge-cards/alert/) 優先偵測使用者或產品可感知的症狀」。症狀包括錯誤率、延遲、可用性、資料延遲、付款失敗與訊息未送達。

## 概念位置

症狀型告警和原因型告警分工不同。CPU 高、[queue depth](/backend/knowledge-cards/queue-depth/) 高、GC 頻繁是可能原因；checkout 失敗率升高才是直接產品症狀。

## 可觀察訊號與例子

系統需要 symptom-based alert 的訊號是 on-call 被大量低層訊號吵醒，但使用者影響不清楚。付款成功率下降應立即告警；單台 instance CPU 高則可先進 dashboard 或自動修復流程。

## 設計責任

告警要連到 [SLI / SLO](/backend/knowledge-cards/sli-slo/)、[runbook](/backend/knowledge-cards/runbook/) 與影響判斷。原因型指標仍然重要，但應用來診斷症狀，而非全部升級成醒人的告警。
