---
title: "Offset"
date: 2026-06-22
description: "說明 consumer 在事件流中的讀取位置與重放基準"
weight: 74
tags: ["backend", "message-queue"]
---

Offset 的核心概念是「consumer 在事件流中的讀取位置」。它讓 consumer 知道自己已經處理到哪裡，也讓系統可以從某個位置繼續或重放。

## 概念位置

Offset 是 [consumer group](/backend/knowledge-cards/consumer-group/) 的進度記錄、[consumer lag](/backend/knowledge-cards/consumer-lag/) 的計算基準、[replay runbook](/backend/knowledge-cards/replay-runbook/) 的起點定位。在 Kafka 中，offset 是每個 [partition](/backend/knowledge-cards/partition/) 內的遞增整數；在 Redis Streams 中是 entry ID（timestamp-sequence）；在 SQS 中沒有顯式 offset，改用 visibility timeout 控制消費進度。

Offset 提交太早（處理前就 commit）可能造成處理遺失 — consumer crash 後從已 commit 的位置繼續，跳過未完成的訊息。提交太晚（處理完成很久才 commit）可能造成重複處理 — consumer crash 後從舊 offset 重新開始，重複處理已完成的訊息。

## 使用情境

系統需要理解 offset 的訊號是 consumer 重啟後需要接續處理。報表 consumer 處理到某個 offset 後 crash，重啟時要從安全位置繼續，並用 [idempotency](/backend/knowledge-cards/idempotency/) 承受可能重複的事件。

Offset 也是 replay 操作的控制參數。「重設 offset 到三天前」意味著 consumer group 會從三天前的位置重新處理所有事件 — 下游需要有 idempotent 設計才能承受重播。

## 設計責任

Offset 提交策略要和業務處理完成條件對齊。Auto-commit（定期自動提交）實作簡單但在 crash 時有遺失風險；manual commit（處理完成後手動提交）更安全但程式碼更複雜。Runbook 應說明如何查 current offset、committed offset、lag、重設 offset 的操作步驟與 replay 對下游的影響。
