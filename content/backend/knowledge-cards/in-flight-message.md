---
title: "In-Flight Message"
date: 2026-04-23
description: "說明已交給 consumer 但尚未完成確認的訊息狀態"
weight: 61
---

In-flight message 的核心概念是「已經交給 consumer，但尚未完成 ack 或 nack 的訊息」。這些訊息正在處理中，broker 通常會把它們和可投遞訊息分開管理。 可先對照 [In-Process Channel](/backend/knowledge-cards/in-process-channel/)。

## 跟其他概念的關係

In-flight 狀態是 consumer lifecycle 的中間階段。它連接 prefetch、ack timeout、redelivery、consumer crash 與 graceful shutdown。In-flight 訊息越多，代表系統有越多未完成副作用。 可先對照 [In-Process Channel](/backend/knowledge-cards/in-process-channel/)。

## 可觀察訊號與例子

系統需要觀察 in-flight 訊息的訊號是部署或故障期間出現大量重複處理。Consumer 收到訂單事件後還沒 ack 就 crash，broker 可能重新投遞該事件，因此 handler 需要 idempotency。

## 判斷條件與後果

Consumer 關閉時若還在取新訊息，新取到的訊息與手上的訊息一起停在未 ack 的狀態，broker 在連線中斷或 ack timeout 之後重新投遞它們，部署期間就出現大量重複處理，原因是 broker 只靠 ack 判斷一則訊息是否完成。先停止取新訊息，再把手上的訊息處理完或 nack 交回，in-flight 數量在 consumer 結束前歸零，重新投遞的只剩確實沒處理完的那幾則。Runbook 看不到 in-flight 數量、最久處理時間、redelivery 次數與 consumer crash 紀錄時，重複處理發生後分不出是哪一批訊息、卡在哪一個 consumer，因為這幾個數字是 in-flight 狀態在 broker 外面僅有的痕跡。
