---
title: "Alert Fatigue"
date: 2026-06-22
description: "說明過多低品質告警如何降低 on-call 反應品質"
weight: 110
tags: ["backend", "observability"]
---

Alert fatigue 的核心概念是「過多低品質告警讓處理者對告警失去敏感度」。當告警常常沒有使用者影響、沒有行動步驟或頻繁自動恢復，[on-call](/backend/knowledge-cards/on-call/) 會開始忽略訊號 — 包括真正需要處理的那些。

## 概念位置

Alert fatigue 是可觀測性設計的失敗模式，跟 [alert](/backend/knowledge-cards/alert/) 的品質治理直接相關。告警應代表需要人介入的產品風險；其他訊號可以進 [dashboard](/backend/knowledge-cards/dashboard/)、ticket、報表或自動修復流程。

常見的 fatigue 來源：false positive（條件觸發但實際沒問題）、redundant alert（同一問題觸發多個 alert）、stale alert（條件已不適用但 rule 沒更新）。

## 使用情境

系統需要治理 alert fatigue 的訊號是 noise rate > 30%（超過三成的 alert 不需要行動），或 on-call 工程師反應「收到 alert 先 ack 再看、有時直接 resolve 不看」。

## 設計責任

Alert fatigue 的治理包括：追蹤 noise rate（on-call ack 時標記 actionable / noise）、定期審視高 noise 的 alert rule（調整閾值、改 [symptom-based](/backend/knowledge-cards/symptom-based-alert/)、加 inhibition、或刪除）、用 grouping 跟 inhibition 減少同一問題的重複通知。治理節奏跟 [4.8 訊號治理閉環](/backend/04-observability/signal-governance-loop/) 整合。
