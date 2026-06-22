---
title: "Alert"
date: 2026-06-22
description: "說明 alert 如何把需要處理的服務症狀轉成可行動通知"
weight: 142
tags: ["backend", "observability"]
---

Alert 的核心概念是「把需要人或自動流程處理的服務症狀轉成通知」。好的 alert 連到產品影響、判斷條件、[dashboard](/backend/knowledge-cards/dashboard/)、[runbook](/backend/knowledge-cards/runbook/) 與升級流程。

## 概念位置

Alert 是可觀測性進入操作流程的入口。[Symptom-based alert](/backend/knowledge-cards/symptom-based-alert/) 優先偵測使用者可感知結果（error rate、latency p99）；cause-based alert 偵測內部原因（CPU、[queue depth](/backend/knowledge-cards/queue-depth/)、[connection pool](/backend/knowledge-cards/connection-pool/)）。Symptom-based 用於 page on-call、cause-based 用於 warning 級通知。

Alert 觸發後由 [on-call](/backend/knowledge-cards/on-call/) 工程師承接，按 [runbook](/backend/knowledge-cards/runbook/) 的步驟診斷跟處理。

## 使用情境

系統需要 alert 設計的訊號是服務異常需要在使用者大量回報前被發現跟處理。付款成功率下降、API availability 低於 [SLO](/backend/knowledge-cards/sli-slo/)、[consumer lag](/backend/knowledge-cards/consumer-lag/) 持續擴大或 [DLQ](/backend/knowledge-cards/dead-letter-queue/) 快速增加，都應觸發可行動通知。

## 設計責任

Alert 設計要定義門檻、持續時間（`for` duration）、severity、通知對象、抑制規則、runbook link 與回復條件。每個 alert rule 帶 owner metadata — 沒有 owner 的 alert 會在服務演進後退化成 noise 來源，形成 [alert fatigue](/backend/knowledge-cards/alert-fatigue/)。

SLO-based alerting 用 [burn rate](/backend/knowledge-cards/burn-rate/) 取代固定閾值，自動適應流量變化。完整的 alert 設計見 [4.4](/backend/04-observability/dashboard-alert/)、SLO-based alerting 見 [4.6](/backend/04-observability/sli-slo-signal/)。
