---
title: "Write-Behind Cache"
date: 2026-04-23
description: "說明先寫快取再非同步寫入正式來源的風險與用途"
weight: 94
---


Write-behind cache 的核心概念是「先把變更寫入快取或緩衝層，再非同步寫入正式來源」。它可以降低使用者等待時間，但會增加資料遺失與一致性風險。 可先對照 [Data Reconciliation](/backend/knowledge-cards/data-reconciliation/)。

## 概念位置

Write-behind 是延後持久化策略。它適合可重建、可補償或低風險資料；金流、訂單正式狀態與權限資料通常需要更強保證。 可先對照 [Data Reconciliation](/backend/knowledge-cards/data-reconciliation/)。

## 可觀察訊號與例子

系統需要評估 write-behind 的訊號是寫入流量很高、正式來源寫入成本高，且短暫延遲可接受。使用者行為計數或 analytics event 可以先進緩衝層，再批次寫入儲存。

## 設計責任

Write-behind 要處理 buffer durability、flush、retry、checkpoint、資料遺失、停機與 [Data Reconciliation](/backend/knowledge-cards/data-reconciliation/)。Runbook 應能查看尚未 flush 的資料量與最舊等待時間。
