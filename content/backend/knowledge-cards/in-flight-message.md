---
title: "In-Flight Message"
date: 2026-04-23
description: "說明已交給 consumer 但尚未完成確認的訊息狀態"
weight: 60
---


In-flight message 的核心概念是「已經交給 consumer，但尚未完成 ack 或 nack 的訊息」。這些訊息正在處理中，broker 通常會把它們和可投遞訊息分開管理。 可先對照 [In-Process Channel](/backend/knowledge-cards/in-process-channel/)。

## 概念位置

In-flight 狀態是 consumer lifecycle 的中間階段。它連接 prefetch、ack timeout、redelivery、consumer crash 與 graceful shutdown。In-flight 訊息越多，代表系統有越多未完成副作用。 可先對照 [In-Process Channel](/backend/knowledge-cards/in-process-channel/)。

## 可觀察訊號與例子

系統需要觀察 in-flight 訊息的訊號是部署或故障期間出現大量重複處理。Consumer 收到訂單事件後還沒 ack 就 crash，broker 可能重新投遞該事件，因此 handler 需要 idempotency。

## 設計責任

Consumer shutdown 要先停止取新訊息，再處理或交回 in-flight 訊息。Runbook 應能看到 in-flight 數量、最久處理時間、redelivery 次數與 consumer crash 紀錄。
