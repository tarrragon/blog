---
title: "Offset"
date: 2026-06-22
description: "說明 consumer 在事件流中的讀取位置與重放基準"
weight: 75
tags: ["backend", "message-queue"]
---

Offset 的核心概念是「consumer 在事件流中的讀取位置」。它是 [consumer group](/backend/knowledge-cards/consumer-group/) 的進度記錄，讓 consumer 知道自己已經處理到哪裡，也讓系統可以從某個位置繼續或重放。

## 跟其他概念的關係

Offset 是 [consumer group](/backend/knowledge-cards/consumer-group/) 的進度記錄、[consumer lag](/backend/knowledge-cards/consumer-lag/) 的計算基準、[replay runbook](/backend/knowledge-cards/replay-runbook/) 的起點定位。在 Kafka 中，offset 是每個 [partition](/backend/knowledge-cards/partition/) 內的遞增整數；在 Redis Streams 中是 entry ID（timestamp-sequence）；在 SQS 中沒有顯式 offset，改用 visibility timeout 控制消費進度。

Offset 提交太早（處理前就 commit）可能造成處理遺失 — consumer crash 後從已 commit 的位置繼續，跳過未完成的訊息。提交太晚（處理完成很久才 commit）可能造成重複處理 — consumer crash 後從舊 offset 重新開始，重複處理已完成的訊息。

## 使用情境

系統需要理解 offset 的訊號是 consumer 重啟後需要接續處理。報表 consumer 處理到某個 offset 後 crash，重啟時要從安全位置繼續，並用 [idempotency](/backend/knowledge-cards/idempotency/) 承受可能重複的事件。

Offset 也是 replay 操作的控制參數。「重設 offset 到三天前」意味著 consumer group 會從三天前的位置重新處理所有事件 — 下游需要有 idempotent 設計才能承受重播。

## 判斷條件與後果

Offset 提交的時間點與業務處理完成的時間點之間的落差，決定 consumer crash 之後的結果。Auto-commit（定期自動提交）依固定間隔提交，提交時訊息可能還沒處理完，crash 之後 consumer 從已提交的位置繼續，那些訊息被跳過；manual commit（處理完成後手動提交）時，crash 只讓最後一批已處理而還沒提交的訊息被重新處理，代價是提交邏輯寫進業務程式，而下游要用 [idempotency](/backend/knowledge-cards/idempotency/) 承受這批重複。runbook 沒有寫出怎麼查 current offset、committed offset 與 lag 時，事故當下分不出 consumer 是停住、變慢還是跳過了訊息；沒有寫出重設 offset 的步驟與 replay 對下游的影響時，一次重設讓下游重新處理整段事件，而下游能否承受重複沒有人事先確認。
