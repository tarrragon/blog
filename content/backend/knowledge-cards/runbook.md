---
title: "Runbook"
date: 2026-06-22
description: "說明 runbook 如何把事故判斷與操作步驟標準化"
weight: 144
tags: ["backend", "observability", "incident-response"]
---

Runbook 的核心概念是「把事故判斷與操作步驟標準化」。它是 [alert](/backend/knowledge-cards/alert/) 的行動指南，描述 [on-call](/backend/knowledge-cards/on-call/) 工程師看到特定訊號時如何確認影響、查哪些資料、採取哪些緩解、何時升級，以及如何驗證恢復。

## 跟其他概念的關係

Runbook 是 [alert](/backend/knowledge-cards/alert/) 的行動指南。Alert 告訴 [on-call](/backend/knowledge-cards/on-call/) 工程師有問題，runbook 告訴他們「收到這個 alert 時該做什麼」。每個 critical alert 應該連到一份 runbook — 缺少 runbook link 的 alert 等於「通知了但不告訴你做什麼」，是 [alert fatigue](/backend/knowledge-cards/alert-fatigue/) 的起點。

Runbook 也服務於 [post-incident review](/backend/knowledge-cards/post-incident-review/) — 事故中實際執行的步驟跟 runbook 預設的步驟比較，差異就是 runbook 需要更新的地方。

## 使用情境

系統需要 runbook 的訊號是同一類事故每次都靠個人經驗處理。[DLQ](/backend/knowledge-cards/dead-letter-queue/) 快速增加時，runbook 應引導處理者查看錯誤分類、payload 範圍、最近部署、replay 條件與暫停 [consumer](/backend/knowledge-cards/consumer/) 的判斷。

## 判斷條件與後果

Runbook 的每一段結構對應事故處理的一個環節，缺了哪一段，處理者就在那個環節退回靠個人經驗。缺症狀描述時，處理者無法確認手上的告警是否屬於這份 runbook 處理的情形；缺影響評估時，無從決定是否升級嚴重度；缺診斷步驟（先看哪個 [dashboard](/backend/knowledge-cards/dashboard/)、查哪些 log）時，每個人從不同的地方開始查；缺修復動作（restart、scale、rollback、failover）時，處置要在現場臨時決定；缺升級路徑（15 分鐘內無法解決時通知誰）時，卡住的事故沒有人接手。runbook 與 alert 由不同的人維護時，alert rule 改了而 runbook 沒有跟著更新，處理者照舊的步驟查錯地方，所以 runbook 的 owner 跟 alert 的 owner 是同一個人。完整設計見 [4.4 dashboard 與 alert 設計](/backend/04-observability/dashboard-alert/)。
