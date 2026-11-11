---
title: "Alert"
date: 2026-06-22
description: "說明 alert 如何把需要處理的服務症狀轉成可行動通知"
weight: 143
tags: ["backend", "observability"]
---

Alert 的核心概念是「把需要人或自動流程處理的服務症狀轉成通知」。好的 alert 連到產品影響、判斷條件、[dashboard](/backend/knowledge-cards/dashboard/)、[runbook](/backend/knowledge-cards/runbook/) 與升級流程。

## 跟其他概念的關係

Alert 是可觀測性進入操作流程的入口；它要被監看的系統自己發出，系統整台停掉時發不出來，反過來在訊號消失時通知的形式見 [Dead Man's Switch](/backend/knowledge-cards/dead-mans-switch/)。[Symptom-based alert](/backend/knowledge-cards/symptom-based-alert/) 優先偵測使用者可感知結果（error rate、latency p99）；cause-based alert 偵測內部原因（CPU、[queue depth](/backend/knowledge-cards/queue-depth/)、[connection pool](/backend/knowledge-cards/connection-pool/)）。Symptom-based 用於 page on-call、cause-based 用於 warning 級通知。

Alert 觸發後由 [on-call](/backend/knowledge-cards/on-call/) 工程師承接，按 [runbook](/backend/knowledge-cards/runbook/) 的步驟診斷跟處理。

## 使用情境

系統需要 alert 設計的訊號是服務異常需要在使用者大量回報前被發現跟處理。付款成功率下降、API availability 低於 [SLO](/backend/knowledge-cards/sli-slo/)、[consumer lag](/backend/knowledge-cards/consumer-lag/) 持續擴大或 [DLQ](/backend/knowledge-cards/dead-letter-queue/) 快速增加，都應觸發可行動通知。

## 判斷條件與後果

一條 alert rule 的每個欄位各對應一種失效。門檻與持續時間（`for` duration）決定誤報與延遲之間的取捨：持續時間太短，短暫的尖峰也發通知；太長，真正的異常要等更久才通知。沒有 severity 時，不需要立刻處理的訊號也 page on-call；沒有通知對象時，告警成立而沒有人收到；沒有抑制規則時，同一個原因引出的一串症狀各發一則；沒有 runbook link 時，收到的人要臨場猜下一步；沒有回復條件時，告警何時算結束沒有定義。通知也可能被人手動設定的靜音壓下，見 [Alert Silence（告警靜音）](/backend/knowledge-cards/alert-silence/)。alert rule 沒有 owner metadata 時，服務演進之後沒有人負責調整它，它退化成 noise 來源，形成 [alert fatigue](/backend/knowledge-cards/alert-fatigue/)，所以每條 rule 帶 owner。

SLO-based alerting 用 [burn rate](/backend/knowledge-cards/burn-rate/) 取代固定閾值，自動適應流量變化。完整的 alert 設計見 [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)、SLO-based alerting 見 [4.6 SLI 量測與 SLO 訊號設計](/backend/04-observability/sli-slo-signal/)。
