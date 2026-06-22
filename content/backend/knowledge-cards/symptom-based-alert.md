---
title: "Symptom-Based Alert"
date: 2026-06-22
description: "說明告警應優先偵測使用者可感知症狀"
weight: 108
tags: ["backend", "observability"]
---

Symptom-based alert 的核心概念是「[alert](/backend/knowledge-cards/alert/) 優先偵測使用者或產品可感知的症狀」。症狀包括錯誤率、延遲、可用性、資料延遲、付款失敗與訊息未送達。

## 概念位置

Symptom-based alert 跟 cause-based alert 分工不同。CPU 高、[queue depth](/backend/knowledge-cards/queue-depth/) 高、GC 頻繁是可能的原因；checkout 失敗率升高才是直接的產品症狀。Symptom-based 適合 critical severity（page [on-call](/backend/knowledge-cards/on-call/)），cause-based 適合 warning severity（工作時間排入 task）。

Symptom-based alert 是 [4.4 dashboard-alert](/backend/04-observability/dashboard-alert/) 建議的 alert 設計起點 — 先確認使用者是否受影響、再看系統原因。

## 使用情境

系統需要 symptom-based alert 的訊號是 on-call 被大量低層訊號吵醒，但無法判斷使用者是否受影響。付款成功率下降應立即告警；單台 instance CPU 高則可先進 [dashboard](/backend/knowledge-cards/dashboard/) 觀察或走自動修復流程。

## 設計責任

Symptom-based alert 要連到 [SLI / SLO](/backend/knowledge-cards/sli-slo/)、[runbook](/backend/knowledge-cards/runbook/) 與影響判斷。SLO-based alerting 用 [burn rate](/backend/knowledge-cards/burn-rate/) 量化症狀嚴重度 — 「error budget 消耗速度是允許值的 14 倍」比「error rate > 1%」更能反映使用者影響規模。完整設計見 [4.6 SLI/SLO 訊號設計](/backend/04-observability/sli-slo-signal/)。
