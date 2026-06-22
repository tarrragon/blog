---
title: "Runbook"
date: 2026-06-22
description: "說明 runbook 如何把事故判斷與操作步驟標準化"
weight: 143
tags: ["backend", "observability", "incident-response"]
---

Runbook 的核心概念是「把事故判斷與操作步驟標準化」。它描述看到特定訊號時如何確認影響、查哪些資料、採取哪些緩解、何時升級，以及如何驗證恢復。

## 概念位置

Runbook 是 [alert](/backend/knowledge-cards/alert/) 的行動指南。Alert 告訴 [on-call](/backend/knowledge-cards/on-call/) 工程師有問題，runbook 告訴他們「收到這個 alert 時該做什麼」。每個 critical alert 應該連到一份 runbook — 缺少 runbook link 的 alert 等於「通知了但不告訴你做什麼」，是 [alert fatigue](/backend/knowledge-cards/alert-fatigue/) 的起點。

Runbook 也服務於 [post-incident review](/backend/knowledge-cards/post-incident-review/) — 事故中實際執行的步驟跟 runbook 預設的步驟比較，差異就是 runbook 需要更新的地方。

## 使用情境

系統需要 runbook 的訊號是同一類事故每次都靠個人經驗處理。[DLQ](/backend/knowledge-cards/dead-letter-queue/) 快速增加時，runbook 應引導處理者查看錯誤分類、payload 範圍、最近部署、replay 條件與暫停 [consumer](/backend/knowledge-cards/consumer/) 的判斷。

## 設計責任

Runbook 的有效結構：症狀描述、影響評估、診斷步驟（先看哪個 [dashboard](/backend/knowledge-cards/dashboard/)、查哪些 log）、可能的修復動作（restart / scale / rollback / failover）、升級路徑（15 分鐘內無法解決時通知誰）。維護責任跟 alert 的 owner 一致 — alert rule 改了但 runbook 沒更新是常見的退化。完整設計見 [4.4](/backend/04-observability/dashboard-alert/)。
