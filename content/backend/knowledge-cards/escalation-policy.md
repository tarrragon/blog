---
title: "Escalation Policy"
date: 2026-04-23
description: "說明事故升級鏈與值班轉接規則"
weight: 152
---

Escalation policy 的核心概念是「在指定時間內把未解決事故交給下一層責任角色」。它確保事故在無回應或無進展時自動升級，而不是停在單一值班人員。

## 概念位置

升級策略是 [incident severity](../incident-severity/) 的執行流程，並與 [alert runbook](../alert-runbook/) 與 [incident command system](../incident-command-system/) 一起運作。

## 可觀察訊號與例子

系統需要 escalation policy 的訊號是高嚴重度告警在深夜長時間無回應。付款 API 中斷若 10 分鐘內沒有確認接手，應自動升級到下一層 on-call 與 incident commander。

## 設計責任

升級策略要定義回應時限、升級路徑、通知通道、交接內容與最終責任人。策略要定期演練，確認通訊資訊與值班名單有效。
