---
title: "Action Item Closure"
date: 2026-06-22
description: "說明事故行動項如何被驗證完成，而不是只停留在待辦清單"
weight: 317
tags: ["backend", "observability", "incident-response"]
---

Action item closure 的核心概念是「把復盤行動項變成可驗證完成的工程責任」。它承接 [post-incident review](/backend/knowledge-cards/post-incident-review/) 的產出，關心的是每一項是否有 owner、完成標準、驗證方式與截止時間，而非列出多少待辦。

## 跟其他概念的關係

Action item closure 連接 [post-incident review](/backend/knowledge-cards/post-incident-review/)（產出行動項）、[runbook](/backend/knowledge-cards/runbook/)（行動項可能是更新 runbook）、[4.8 訊號治理閉環](/backend/04-observability/signal-governance-loop/)（行動項可能是新增 alert / metric / dashboard）。

Detection gap 類的行動項（「事故中缺少某個 alert / metric」）應指派給觀測系統的 [owner](/backend/knowledge-cards/ownership/)，帶明確的變更規格（新增哪個 metric、alert 閾值多少、連到哪個 runbook）。

## 使用情境

系統需要 action item closure 流程的訊號是事故復盤後大量 open items 超過 90 天仍未關閉，或同類事故重複發生但上次復盤的改善項還沒完成。

## 判斷條件與後果

一個 action item 缺了哪一個欄位，關閉流程就停在哪一處。沒有 owner（誰負責完成）時，這一項不在任何人的排程裡；完成標準只寫到「已開始」、沒寫到「已部署、已驗證」時，改動還沒上線也能關閉，同類事故照樣再發生；沒有驗證方式（跑一次演練、查 dashboard 確認 metric 存在）時，宣稱完成的 alert 或 metric 可能並不存在，要等下一次事故才發現；沒有截止時間（例如兩週內）時，項目一直停在 open，復盤後超過 90 天仍未關閉的那一批就是這樣累積的。截止時間本身不改變任何人的工作，逾期的 action item 自動升級到管理層才讓逾期有後果，這個升級機制是 closure 流程的背壓。
