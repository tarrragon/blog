---
title: "Runbook"
tags: ["執行手冊", "Runbook"]
date: 2026-04-23
description: "說明 runbook 如何把事故判斷與操作步驟標準化"
weight: 143
---

Runbook 的核心概念是「把事故判斷與操作步驟標準化」。它描述看到特定訊號時如何確認影響、查哪些資料、採取哪些緩解、何時升級，以及如何驗證恢復。

## 概念位置

Runbook 是 domain knowhow 的操作化文件。[Alert](../alert/)、[dashboard](../dashboard/)、[log](../log/) query、[trace](../trace/)、擴容、rollback、[replay runbook](../replay-runbook/) 與 [failover](../failover/) 都需要 runbook 把零散知識整理成可執行流程。

## 可觀察訊號與例子

系統需要 runbook 的訊號是同一類事故每次都靠個人經驗處理。[DLQ](../dead-letter-queue/) 快速增加時，runbook 應引導處理者查看錯誤分類、payload 範圍、最近部署、replay 條件與暫停 [consumer](../consumer/) 的判斷。

## 設計責任

Runbook 要包含觸發條件、影響判斷、查詢連結、立即緩解、權限需求、停止條件、回復驗證與事後更新責任。每次事故後應把實際學到的判斷規則補回 runbook。

