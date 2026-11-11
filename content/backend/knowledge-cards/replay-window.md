---
title: "Replay Window"
date: 2026-06-16
description: "說明事件可重播的時間或 offset 範圍邊界，由 retention 與 checkpoint 決定"
weight: 379
---

Replay window 的核心概念是「事件能往回重播的範圍」。它由 broker 的 retention 與 consumer 的 checkpoint 共同界定，決定出事後能補送多久以前的事件。 可先對照 [Recovery Semantics](/backend/knowledge-cards/recovery-semantics/)。

## 跟其他概念的關係

Replay window 是 [recovery semantics](/backend/knowledge-cards/recovery-semantics/) 的具體邊界。它把「可恢復」量化成一段 [offset](/backend/knowledge-cards/offset/) 或時間區間：超出 retention 的事件已被刪除、無法重播，補償就要改走資料庫或上游來源。

## 可觀察訊號與例子

Kafka 設 7 天 retention，replay window 就是 7 天，第 8 天的錯誤要重算就找不到原始事件；SQS 最長保留 14 天、Pub/Sub 預設 7 天，managed 佇列的 replay window 由保留期上限決定。

## 判斷條件與後果

replay window 要拿來對照的是一次錯誤從發生、被偵測到、修復完成的最長時間。這段時間短於 retention 時，修好之後從錯誤發生點的 offset 重播，錯誤期間的事件都補得回來。這段時間長於 retention 時，修好的那一刻錯誤期間最早的那幾筆事件已經被 broker 刪除，重播找不到原始事件，補償只能改走資料庫或上游來源，而那些來源不一定留著重算需要的內容。所以偵測延遲可能超過 retention 的系統，在拉長保留期（代價是 broker 的儲存量）與在下游留一份可重算的來源之間選一種。
