---
title: "Incident Decision Log"
tags: ["Incident Decision Log", "Decision Log", "事故決策紀錄"]
date: 2026-05-07
description: "說明事故期間如何保留決策、證據、owner 與回退條件"
weight: 319
---

Incident decision log 的核心概念是「把事故期間的已決事項與證據鏈保存成可回放紀錄」。它連接 [incident command system](/backend/knowledge-cards/incident-command-system/)、[incident timeline](/backend/knowledge-cards/incident-timeline/) 與 [evidence package](/backend/knowledge-cards/evidence-package/)，讓事中交班與事後復盤使用同一組決策背景。

## 跟其他概念的關係

Incident decision log 位在 [on-call](/backend/knowledge-cards/on-call/)、[incident communication channel](/backend/knowledge-cards/incident-communication-channel/) 與 [post-incident review](/backend/knowledge-cards/post-incident-review/) 之間。它保存的是決策內容、時間、證據、owner、預期效果與回退條件，timeline 則保存事故事件順序。

## 可觀察訊號與例子

系統需要 incident decision log 的訊號是事故結束後很難說清楚某次 rollback、degradation 或 vendor escalation 的決策依據。常見例子是聊天頻道有大量討論，但缺少明確的「何時決定、基於哪些 evidence、誰執行、什麼條件下改路線」。

## 判斷條件與後果

Incident decision log 的欄位多寡決定事故現場是否有人持續更新它。欄位多到處置中的人來不及填時，紀錄停在事故開頭，handoff 的接班者與 post-incident review 都拿不到後半段的決策背景。欄位只剩決定本身、缺了證據、owner、預期效果與回退條件時，接班者知道做了什麼，不知道為什麼做、在什麼條件下要改路線；對 stakeholder 更新狀態的人得回頭問執行者；復盤也無法把缺口回寫到 [runbook](/backend/knowledge-cards/runbook/)、[steady state](/backend/knowledge-cards/steady-state/) 與 [action item closure](/backend/knowledge-cards/action-item-closure/)。多起事故同時進行時，每一筆決策寫明它屬於哪一起事故，負責 multi-incident coordination 的人才分得出某次 rollback 是為了哪一起做的。
