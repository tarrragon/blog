---
title: "Offline Catch-up"
date: 2026-04-23
description: "說明訂閱者離線後如何補回缺失事件或狀態"
weight: 142
---

Offline catch-up 的核心概念是「接收端離線期間漏掉的事件，如何在重新連線後補齊」。它是即時通道與正式狀態之間的補償設計。

## 概念位置

Offline catch-up 常出現在 WebSocket、mobile push 與跨區域同步。即時通道只負責在線時低延遲傳遞，離線後的完整性通常由 [durable queue](../durable-queue/)、event log 或資料庫狀態查詢提供。

## 可觀察訊號與例子

例如聊天訊息在使用者離線時不能遺失，重新上線後需要補拉缺失訊息；typing indicator 可以不補送。兩者差異來自事件語意，而不是傳輸通道本身。

## 設計責任

設計時要定義補送範圍、游標或版本、補送時限與去重規則，並把流程寫入 [runbook](../runbook/)。
