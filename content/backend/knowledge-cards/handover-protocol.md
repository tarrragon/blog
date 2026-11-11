---
title: "Handover Protocol"
date: 2026-04-23
description: "說明事故與值班交接時要傳遞哪些資訊、責任與完成條件"
weight: 153
---

Handover protocol 的核心概念是「把事故或值班責任從一個人或一組人，完整、安全地轉到下一個接手者」。它的責任是確認目前狀態、未完成事項、風險與下一步，單純通知誰接手只完成了形式。 可先對照 [On-Call](/backend/knowledge-cards/on-call/)。

## 跟其他概念的關係

Handover protocol 位在 [on-call](/backend/knowledge-cards/on-call/)、[incident command system](/backend/knowledge-cards/incident-command-system/) 與 [escalation policy](/backend/knowledge-cards/escalation-policy/) 之間。它承接角色切換、班次結束與事故升級時的資訊交接。

## 可觀察訊號與例子

系統需要 handover protocol 的訊號是：事故已經持續一段時間、原本負責的人要下班、或指揮權需要轉給下一位。若沒有明確交接，常見問題是重複排查、遺漏已嘗試過的措施，或對下一步有不同理解。 事故以外的例行換班要交接哪些內容，見 [4.29 值班的例行檢查](/backend/04-observability/on-call-routine-checks/#交班紀錄的內容) 的〈交班紀錄的內容〉。

## 判斷條件與後果

Handover 的判斷條件是接手者拿到的資訊是否足以接著做，而不必重做前一手做過的事。當前狀態與已知事實沒有交接時，接手者從頭排查一次；已嘗試動作沒有交接時，做過的措施被重做，或接手者不知道哪些方向已經排除；阻塞點、下一個檢查時間與對外溝通狀態沒有交接時，排定的檢查與對外更新在換手的空檔中斷。接手確認是交接的結束點：確認之前由前一手負責，確認之後責任轉給接手者；兩人同時做決策時，雙方對下一步可能有不同理解，原因是兩人各自依手上不同的資訊判斷。
