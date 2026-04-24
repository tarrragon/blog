---
title: "Alert"
date: 2026-04-23
description: "說明 alert 如何把需要處理的服務症狀轉成可行動通知"
weight: 142
---

Alert 的核心概念是「把需要人或自動流程處理的服務症狀轉成通知」。好的 alert 連到產品影響、判斷條件、[dashboard](/backend/knowledge-cards/dashboard/)、[runbook](/backend/knowledge-cards/runbook/) 與升級流程。

## 概念位置

Alert 是可觀測性進入操作流程的入口。[Symptom-based alert](/backend/knowledge-cards/symptom-based-alert/) 優先偵測使用者可感知結果；原因型訊號則協助診斷，例如 CPU、[queue depth](/backend/knowledge-cards/queue-depth/)、[connection pool](/backend/knowledge-cards/connection-pool/)、error [log](/backend/knowledge-cards/log/) 或 downstream [timeout](/backend/knowledge-cards/timeout/)。

## 可觀察訊號與例子

系統需要 alert 設計的訊號是服務異常需要在使用者大量回報前處理。付款成功率下降、API availability 低於 [SLO](/backend/knowledge-cards/sli-slo/)、consumer lag 持續擴大或 [DLQ](/backend/knowledge-cards/dead-letter-queue/) 快速增加，都應觸發可行動通知。

## 設計責任

Alert 設計要定義門檻、持續時間、嚴重度、通知對象、抑制規則、[runbook link](/backend/knowledge-cards/runbook-link/) 與回復條件。低品質 alert 會造成 [alert fatigue](/backend/knowledge-cards/alert-fatigue/)，因此每個 alert 都要能支援明確處理動作。
