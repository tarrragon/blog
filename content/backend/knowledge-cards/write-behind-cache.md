---
title: "Write-Behind Cache"
date: 2026-04-23
description: "說明先寫快取再非同步寫入正式來源的風險與用途"
weight: 95
---

Write-behind cache 的核心概念是「先把變更寫入快取或緩衝層，再非同步寫入正式來源」。它可以降低使用者等待時間，但會增加資料遺失與一致性風險。 可先對照 [Data Reconciliation](/backend/knowledge-cards/data-reconciliation/)。

## 跟其他概念的關係

Write-behind 是延後持久化策略。它適合可重建、可補償或低風險資料；金流、訂單正式狀態與權限資料通常需要更強保證。 可先對照 [Data Reconciliation](/backend/knowledge-cards/data-reconciliation/)。

## 可觀察訊號與例子

系統需要評估 write-behind 的訊號是寫入流量很高、正式來源寫入成本高，且短暫延遲可接受。使用者行為計數或 analytics event 可以先進緩衝層，再批次寫入儲存。

## 判斷條件與後果

Write-behind 的風險集中在已經回應使用者、還沒寫進正式來源的那批資料。buffer 只在記憶體裡時，程序 crash 讓這批資料遺失，而使用者收到的回應是寫入成功；flush 失敗而沒有 retry 與 checkpoint 時，這批資料可能遺失，重送時也可能重複寫入，正式來源與緩衝層從此不一致，要靠 [Data Reconciliation](/backend/knowledge-cards/data-reconciliation/) 找出差異；停機前沒有 flush 時，每一次部署都帶走一批資料。尚未 flush 的資料量與最舊等待時間，就是此刻一旦 crash 會遺失的範圍，所以 runbook 查得到這兩項。
