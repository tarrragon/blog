---
title: "Escalation Policy"
date: 2026-04-23
description: "說明事故升級鏈與值班轉接規則"
weight: 153
---


Escalation policy 的核心概念是「在指定時間內把未解決事故交給下一層責任角色」。它確保事故在無回應或無進展時自動升級，而不是停在單一值班人員。 可先對照 [Incident Severity](/backend/knowledge-cards/incident-severity/)。

## 概念位置

升級策略是 [incident severity](/backend/knowledge-cards/incident-severity/) 的執行流程（使用者回報在客服各層之間怎麼往上轉是另一件事，見 [Tiered Support](/backend/knowledge-cards/tiered-support/)），並與 [alert runbook](/backend/knowledge-cards/alert-runbook/) 與 [incident command system](/backend/knowledge-cards/incident-command-system/) 一起運作。

升級策略通常同時寫了 ITIL 區分的兩種升級：沒有回應時轉給下一個值班的人或專業能力更深的團隊（functional escalation），事故沒有進展、需要調動資源或做取捨時找事故指揮與主管（hierarchical escalation）。兩個名字的界定與客服這一端的例子見 [Tiered Support（分層支援）](/backend/knowledge-cards/tiered-support/)。

## 可觀察訊號與例子

系統需要 escalation policy 的訊號是高嚴重度告警在深夜長時間無回應。付款 API 中斷若 10 分鐘內沒有確認接手，應自動升級到下一層 on-call 與 incident commander。

## 設計責任

升級策略要定義回應時限、升級路徑、通知通道、交接內容與最終責任人。策略要定期演練，確認通訊資訊與值班名單有效。
