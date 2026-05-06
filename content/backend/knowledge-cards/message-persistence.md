---
title: "Message Persistence"
date: 2026-04-23
description: "說明訊息是否落盤保存，以及 broker 重啟後能否恢復"
weight: 68
---


Message persistence 的核心概念是「訊息是否被 broker 持久化保存」。持久化訊息在 broker 重啟、節點切換或暫時故障後仍有機會被恢復；非持久化訊息則偏向低延遲與低成本。 可先對照 [Message Protocol](/backend/knowledge-cards/message-protocol/)。

## 概念位置

Persistence 是投遞保證與成本的取捨。正式訊息、付款事件、資料同步工作通常需要持久化；typing indicator、presence heartbeat 或即時狀態提示可以接受遺失。 可先對照 [Message Protocol](/backend/knowledge-cards/message-protocol/)。

## 可觀察訊號與例子

系統需要 message persistence 的訊號是訊息遺失會造成產品後果。訂單付款事件遺失會造成出貨、通知或對帳漏掉；聊天室正在輸入提示遺失通常可以接受。

## 設計責任

Persistence 設計要和 queue durability、replication、retention、confirm、consumer ack 與成本一起評估。持久化降低遺失風險，也增加 IO、延遲與操作成本。
