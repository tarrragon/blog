---
title: "Visibility Timeout"
date: 2026-06-16
description: "說明訊息被取走後對其他 consumer 暫時不可見的時間窗，timeout 後重新投遞"
weight: 387
---

Visibility timeout 的核心概念是「訊息被一個 consumer 取走後，在一段時間內對其他 consumer 不可見；consumer 在這段時間內處理完並刪除訊息，否則 timeout 後訊息重新變可見、被重新投遞」。它是任務佇列模型（如 SQS）實作 at-least-once 的核心機制。 可先對照 [ack / nack](/backend/knowledge-cards/ack-nack/)。

## 跟其他概念的關係

Visibility timeout 是 [ack / nack](/backend/knowledge-cards/ack-nack/) 在「拉取式佇列」上的一種實作：consumer 沒有顯式長連線，而是靠「取走訊息 + 限時處理 + 刪除確認」三步完成 ack。處理超時等同 nack，訊息回到可見狀態觸發 [redelivery](/backend/knowledge-cards/redelivery/)，多次後進 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/)。 可先對照 [Redelivery](/backend/knowledge-cards/redelivery/)。

## 可觀察訊號與例子

需要調整 visibility timeout 的訊號是「同一訊息被處理多次、或處理完的訊息仍被重投」。timeout 設太短，慢任務還沒處理完就被重新投遞給別的 consumer 造成重複處理；設太長，crash 的 consumer 持有的訊息要等很久才被接手。SQS 的 visibility timeout 預設 30 秒、可依任務耗時調整，長任務用 ChangeMessageVisibility 動態延長。

## 判斷條件與後果

Visibility timeout 與任務耗時分布的相對位置，決定會出現哪一種失誤。timeout 短於部分任務的處理時間時，那些任務還在處理就重新變可見，被另一個 consumer 拿走，同一筆工作做兩次；timeout 遠長於處理時間時，crash 的 consumer 握著的訊息要等整段 timeout 結束才被接手，這段等待直接加進訊息的延遲。耗時長尾很長的任務找不到一個同時避開兩者的固定值，所以用 heartbeat 式續期動態延長。timeout 設成任何值，consumer 仍可能在處理完、刪除訊息之前 crash，at-least-once 下的重複投遞因此無法完全避免，處理要是 idempotent。
