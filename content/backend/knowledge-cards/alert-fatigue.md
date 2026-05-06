---
title: "Alert Fatigue"
date: 2026-04-23
description: "說明過多低品質告警如何降低 on-call 反應品質"
weight: 110
---


Alert fatigue 的核心概念是「過多低品質告警讓處理者對告警失去敏感度」。當告警常常沒有使用者影響、沒有行動步驟或頻繁自動恢復，on-call 會開始忽略訊號。 可先對照 [Alert Runbook](/backend/knowledge-cards/alert-runbook/)。

## 概念位置

Alert fatigue 是可觀測性設計的失敗模式。告警應代表需要人介入的產品風險；其他訊號可以進 dashboard、ticket、報表或自動修復流程。 可先對照 [Alert Runbook](/backend/knowledge-cards/alert-runbook/)。

## 可觀察訊號與例子

系統需要治理 alert fatigue 的訊號是告警量很高，但真正 incident 很少。每次單一 pod 重啟都叫醒 on-call，會掩蓋付款成功率下降這類高風險告警。

## 設計責任

告警治理要定期檢查觸發次數、行動率、誤報、重複告警與 runbook 品質。低行動價值告警應調整門檻、合併、降級或移到 dashboard。
