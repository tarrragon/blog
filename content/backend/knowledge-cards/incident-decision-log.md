---
title: "Incident Decision Log"
tags: ["Incident Decision Log", "Decision Log", "事故決策紀錄"]
date: 2026-05-07
description: "說明事故期間如何保留決策、證據、owner 與回退條件"
weight: 318
---

Incident decision log 的核心概念是「把事故期間的已決事項與證據鏈保存成可回放紀錄」。它連接 [incident command system](/backend/knowledge-cards/incident-command-system/)、[incident timeline](/backend/knowledge-cards/incident-timeline/) 與 [evidence package](/backend/knowledge-cards/evidence-package/)，讓事中交班與事後復盤使用同一組決策背景。

## 概念位置

Incident decision log 位在 [on-call](/backend/knowledge-cards/on-call/)、[incident communication channel](/backend/knowledge-cards/incident-communication-channel/) 與 [post-incident review](/backend/knowledge-cards/post-incident-review/) 之間。它保存的是決策內容、時間、證據、owner、預期效果與回退條件，timeline 則保存事故事件順序。

## 可觀察訊號與例子

系統需要 incident decision log 的訊號是事故結束後很難說清楚某次 rollback、degradation 或 vendor escalation 的決策依據。常見例子是聊天頻道有大量討論，但缺少明確的「何時決定、基於哪些 evidence、誰執行、什麼條件下改路線」。

## 設計責任

Incident decision log 要支援 handoff、multi-incident coordination、stakeholder update 與 post-incident review。它的欄位應足夠輕量，讓事故現場能持續更新，同時足夠完整，能把缺口回寫到 [runbook](/backend/knowledge-cards/runbook/)、[steady state](/backend/knowledge-cards/steady-state/) 與 [action item closure](/backend/knowledge-cards/action-item-closure/)。
