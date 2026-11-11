---
title: "Message Persistence"
date: 2026-04-23
description: "說明訊息是否落盤保存，以及 broker 重啟後能否恢復"
weight: 69
---

Message persistence 的核心概念是「訊息是否被 broker 持久化保存」。持久化訊息在 broker 重啟、節點切換或暫時故障後仍有機會被恢復；非持久化訊息則偏向低延遲與低成本。 可先對照 [Message Protocol](/backend/knowledge-cards/message-protocol/)。

## 跟其他概念的關係

Persistence 是投遞保證與成本的取捨。正式訊息、付款事件、資料同步工作通常需要持久化；typing indicator、presence heartbeat 或即時狀態提示可以接受遺失。 可先對照 [Message Protocol](/backend/knowledge-cards/message-protocol/)。

## 可觀察訊號與例子

系統需要 message persistence 的訊號是訊息遺失會造成產品後果。訂單付款事件遺失會造成出貨、通知或對帳漏掉；聊天室正在輸入提示遺失通常可以接受。

## 判斷條件與後果

訊息是否持久化，看它遺失時的產品後果。付款事件、正式訊息、資料同步工作遺失時，出貨、通知或對帳會漏掉，持久化讓這類訊息在 broker 重啟或節點切換後仍能恢復；typing indicator、presence heartbeat 遺失時，下一次更新就會補上，持久化只多付 IO、延遲與操作成本。持久化只保護 broker 已經寫下的訊息：queue 本身不是 durable 時，broker 重啟後 queue 不在，裡面的訊息跟著消失；producer 沒有等 confirm 時，訊息在寫入之前遺失，producer 不會知道；consumer 在處理完成前就 ack 時，訊息在 consumer 端遺失；沒有 replication 時，承載訊息的那個節點磁碟損壞就一起遺失。所以持久化的效果要和 queue durability、replication、retention、confirm 與 consumer ack 一起看，只開其中一項時，遺失改由其他環節發生。
