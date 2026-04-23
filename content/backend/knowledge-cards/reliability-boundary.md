---
title: "Reliability Boundary"
date: 2026-04-23
description: "說明系統在哪個邊界內承諾可靠傳遞，邊界外需要哪些補償機制"
weight: 139
---

Reliability boundary 的核心概念是「系統在哪一段路徑內承諾不遺失、可重試、可追蹤」。同一個功能中，in-process channel、[pub/sub](../pub-sub/)、[durable queue](../durable-queue/) 與 database transaction 的可靠性強度不同，必須先界定邊界再談工具。

## 概念位置

可靠性邊界通常出現在 request 結束點、跨 process 傳遞點、跨服務傳遞點與外部第三方呼叫點。邊界內可依靠 transaction、持久化與 ack 機制；邊界外需要 [offline catch-up](../offline-catchup/)、[replay runbook](../replay-runbook/) 與 [idempotency](../idempotency/) 補償。

## 可觀察訊號與例子

系統需要明確 reliability boundary 的訊號是「同一筆事件在某些路徑可追蹤，在某些路徑不可追蹤」。例如聊天推播可接受短暫遺失，但付款通知需要補送；這代表兩者的可靠性邊界不同。

## 設計責任

設計時要定義哪類事件屬於 [strong reliability](../strong-reliability/)、哪類事件可用低成本即時通道，並對每類事件提供對應的回復與驗證流程。
