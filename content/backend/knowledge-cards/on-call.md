---
title: "On-Call"
date: 2026-06-22
description: "說明值班制度如何承接告警、事故分級與升級流程"
weight: 161
tags: ["backend", "observability", "incident-response"]
---

On-call 的核心概念是「在指定時段由明確責任角色承接運行事件」。它把告警回應、事故分級、升級決策與交接責任固定化，讓事故處理不依賴臨時找人。

## 概念位置

On-call 是 [alert](/backend/knowledge-cards/alert/)、[incident severity](/backend/knowledge-cards/incident-severity/) 與 [escalation policy](/backend/knowledge-cards/escalation-policy/) 的執行入口。值班工程師是 alert 的第一個接收者，負責判斷「這個 alert 需要什麼等級的回應」。

On-call 跟 [runbook](/backend/knowledge-cards/runbook/) 搭配運作 — runbook 提供行動指南、on-call 工程師執行。制度需要跟 [dashboard](/backend/knowledge-cards/dashboard/) 跟演練一起維護，避免值班只剩 pager 通知而沒有可執行流程。

## 使用情境

系統需要 on-call 制度的訊號是事故常在非上班時間發生、或跨區團隊需要連續處理。付款 API 夜間故障時，若沒有清楚值班安排，回復時間通常被人員定位延遲拉長。

## 設計責任

On-call 設計要定義排班週期、回應時限（critical alert 需要 N 分鐘內 ack）、交接格式（交班時把當前狀態跟未關閉事項傳給下一位）、升級路徑（on-call 解不了時升級到 tech lead / manager）與支援角色（secondary on-call 或 subject matter expert）。Alert noise 治理跟 on-call 品質直接相關 — [alert fatigue](/backend/knowledge-cards/alert-fatigue/) 會讓值班品質退化。
