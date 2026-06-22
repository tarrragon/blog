---
title: "Action Item Closure"
date: 2026-06-22
description: "說明事故行動項如何被驗證完成，而不是只停留在待辦清單"
weight: 316
tags: ["backend", "observability", "incident-response"]
---

Action item closure 的核心概念是「把復盤行動項變成可驗證完成的工程責任」。它關心的是每一項是否有 owner、完成標準、驗證方式與截止時間，而非列出多少待辦。

## 概念位置

Action item closure 連接 [post-incident review](/backend/knowledge-cards/post-incident-review/)（產出行動項）、[runbook](/backend/knowledge-cards/runbook/)（行動項可能是更新 runbook）、[4.8 訊號治理閉環](/backend/04-observability/signal-governance-loop/)（行動項可能是新增 alert / metric / dashboard）。

Detection gap 類的行動項（「事故中缺少某個 alert / metric」）應指派給觀測系統的 [owner](/backend/knowledge-cards/ownership/)，帶明確的變更規格（新增哪個 metric、alert 閾值多少、連到哪個 runbook）。

## 使用情境

系統需要 action item closure 流程的訊號是事故復盤後大量 open items 超過 90 天仍未關閉，或同類事故重複發生但上次復盤的改善項還沒完成。

## 設計責任

每個 action item 定義：owner（誰負責完成）、完成標準（什麼狀態算 done — 不是「已開始」而是「已部署、已驗證」）、驗證方式（怎麼確認完成 — 跑一次演練、查 dashboard 確認 metric 存在）、截止時間（兩週內 close）。逾期的 action item 自動升級到管理層 — 這個升級機制是 closure 流程的背壓。
