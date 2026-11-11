---
title: "Recovery Semantics"
date: 2026-06-16
description: "說明事件處理失敗後能否透過 replay、checkpoint 與補償重建正確狀態並驗證"
weight: 378
---

Recovery semantics 的核心概念是「處理失敗或資料錯亂後，系統能否重建正確狀態並驗證」。它回答 replay、checkpoint、offset 與補償流程是否可重播、可稽核，是 queue 三層語意中最後一層。 可先對照 [Processing Semantics](/backend/knowledge-cards/processing-semantics/)。

## 跟其他概念的關係

Recovery semantics 接在 [processing semantics](/backend/knowledge-cards/processing-semantics/) 之後。處理語意保證單次結果正確，恢復語意保證出錯後能回到正確狀態，依賴 [offset](/backend/knowledge-cards/offset/)、[checkpoint](/backend/knowledge-cards/checkpoint/) 與可控的 [replay window](/backend/knowledge-cards/replay-window/)。

## 可觀察訊號與例子

consumer 處理到一半 crash，重啟後從哪個 offset 接續、會不會重做已完成的副作用，由恢復語意決定。能任意 offset replay 的事件流（Kafka）跟 ack 後即刪的工作佇列（RabbitMQ）恢復能力不同。

## 判斷條件與後果

恢復之後的狀態是否正確，取決於出錯之前 runbook 裡有沒有 replay 範圍、checkpoint 粒度與補償路徑。checkpoint 粒度粗時，consumer crash 之後從較早的 offset 接續，已完成的副作用被重做一次，要靠補償路徑抵銷；replay 範圍沒有界定時，重放的事件超出受影響的區間，正常的資料也被再處理一次。replay 前後的計數與抽樣沒有保留時，恢復只證明得了程序跑完，證明不了狀態正確。
