---
title: "On-Call"
date: 2026-06-22
description: "說明值班制度如何承接告警、事故分級與升級流程"
weight: 162
tags: ["backend", "observability", "incident-response"]
---

On-call 的核心概念是「在指定時段由明確責任角色承接運行事件」。它是 [alert](/backend/knowledge-cards/alert/) 與 [escalation policy](/backend/knowledge-cards/escalation-policy/) 的執行入口，把告警回應、事故分級、升級決策與交接責任固定化，讓事故處理不依賴臨時找人。

## 跟其他概念的關係

On-call 是 [alert](/backend/knowledge-cards/alert/)、[incident severity](/backend/knowledge-cards/incident-severity/) 與 [escalation policy](/backend/knowledge-cards/escalation-policy/) 的執行入口。值班工程師是 alert 的第一個接收者，負責判斷「這個 alert 需要什麼等級的回應」。

On-call 跟 [runbook](/backend/knowledge-cards/runbook/) 搭配運作 — runbook 提供行動指南、on-call 工程師執行。制度需要跟 [dashboard](/backend/knowledge-cards/dashboard/) 跟演練一起維護，避免值班只剩 pager 通知而沒有可執行流程。

## 使用情境

系統需要 on-call 制度的訊號是事故常在非上班時間發生、或跨區團隊需要連續處理。付款 API 夜間故障時，若沒有清楚值班安排，回復時間通常被人員定位延遲拉長。

## 判斷條件與後果

一個 alert 從發出到事故處理完，中間經過幾次責任的轉手（發出到接手、交班、升級），哪一次轉手沒有定義，事故就停在那一步，直到有人發現。回應時限沒有定義時（例如 critical alert 要在幾分鐘內 ack），其他人看不出值班工程師是否已經接手，判斷不了自己該不該介入。交班沒有固定格式時，未關閉的事項只存在上一位的記憶裡，接班的人會重新排查已經排除過的原因；交班要傳的當前狀態與接班檢查的內容見 [4.29 值班的例行檢查](/backend/04-observability/on-call-routine-checks/)。升級路徑（on-call 解不了時找 tech lead 或 manager）與支援角色（secondary on-call、subject matter expert）沒有定義時，on-call 處理不了的事故留在他手上，回復時間被找人的時間拉長，付款 API 夜間故障就是這種情形。排班週期與 alert 的雜訊量一起決定每位值班工程師要處理多少 alert：雜訊多時他對 alert 的反應變慢，形成 [alert fatigue](/backend/knowledge-cards/alert-fatigue/)，回應時限與升級路徑都還寫在制度裡，執行的人已經跟不上。
