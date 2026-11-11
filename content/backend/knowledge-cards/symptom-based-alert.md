---
title: "Symptom-Based Alert"
date: 2026-06-22
description: "說明告警應優先偵測使用者可感知症狀"
weight: 109
tags: ["backend", "observability"]
---

Symptom-based alert 的核心概念是「[alert](/backend/knowledge-cards/alert/) 優先偵測使用者或產品可感知的症狀」。症狀包括錯誤率、延遲、可用性、資料延遲、付款失敗與訊息未送達。

## 跟其他概念的關係

Symptom-based alert 跟 cause-based alert 分工不同。CPU 高、[queue depth](/backend/knowledge-cards/queue-depth/) 高、GC 頻繁是可能的原因；checkout 失敗率升高才是直接的產品症狀。Symptom-based 適合 critical severity（page [on-call](/backend/knowledge-cards/on-call/)），cause-based 適合 warning severity（工作時間排入 task）。

Symptom-based alert 是 [4.4 dashboard-alert](/backend/04-observability/dashboard-alert/) 建議的 alert 設計起點 — 先確認使用者是否受影響、再看系統原因。

## 使用情境

系統需要 symptom-based alert 的訊號是 on-call 被大量低層訊號吵醒，但無法判斷使用者是否受影響。付款成功率下降應立即告警；單台 instance CPU 高則可先進 [dashboard](/backend/knowledge-cards/dashboard/) 觀察或走自動修復流程。

## 判斷條件與後果

Symptom-based alert 觸發時，on-call 從它判斷使用者受了多大影響、接著從哪裡查。Alert 沒有連到 [SLI / SLO](/backend/knowledge-cards/sli-slo/) 時，門檻是憑經驗訂的數字，觸發不代表對使用者的承諾被違反；沒有連到 [runbook](/backend/knowledge-cards/runbook/) 時，on-call 知道使用者受影響，卻不知道先查哪個原因。用 [burn rate](/backend/knowledge-cards/burn-rate/) 量化症狀嚴重度時，同一個錯誤率放在不同的 SLO 下有不同的份量：「error budget 消耗速度是允許值的 14 倍」說出照這個速度預算多快會用完，「error rate > 1%」只說出錯誤率越過一個固定門檻，不說它對承諾的影響有多大。完整設計見 [4.6 SLI/SLO 訊號設計](/backend/04-observability/sli-slo-signal/)。
