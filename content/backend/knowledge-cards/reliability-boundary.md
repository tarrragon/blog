---
title: "Reliability Boundary"
date: 2026-04-23
description: "說明系統在哪個邊界內承諾可靠傳遞，邊界外需要哪些補償機制"
weight: 140
---

Reliability boundary 的核心概念是「系統在哪一段路徑內承諾不遺失、可重試、可追蹤」。同一個功能中，in-process channel、[pub/sub](/backend/knowledge-cards/pub-sub/)、[durable queue](/backend/knowledge-cards/durable-queue/) 與 database transaction 的可靠性強度不同，必須先界定邊界再談工具。

## 跟其他概念的關係

可靠性邊界通常出現在 request 結束點、跨 process 傳遞點、跨服務傳遞點與外部第三方呼叫點。邊界內可依靠 transaction、持久化與 ack 機制；邊界外需要 [offline catch-up](/backend/knowledge-cards/offline-catchup/)、[replay runbook](/backend/knowledge-cards/replay-runbook/) 與 [idempotency](/backend/knowledge-cards/idempotency/) 補償。

## 可觀察訊號與例子

系統需要明確 reliability boundary 的訊號是「同一筆事件在某些路徑可追蹤，在某些路徑不可追蹤」。例如聊天推播可接受短暫遺失，但付款通知需要補送；這代表兩者的可靠性邊界不同。

## 判斷條件與後果

一類事件放在可靠性邊界之內還是之外，取決於遺失它的代價。遺失可以接受的事件（聊天推播）走低成本的即時通道，省下持久化與 ack 的成本；遺失會造成業務錯誤的事件（付款通知）走 [strong reliability](/backend/knowledge-cards/strong-reliability/) 路徑，原因是邊界外沒有 transaction、持久化與 ack 可依靠。事件類別沒有劃分時，同一筆事件在某些路徑可追蹤、某些路徑不可追蹤，出錯時查不到它在哪一段遺失。走即時通道的事件類別另外需要對應的回復與驗證流程，沒有的話遺失之後沒有補送的手段。
