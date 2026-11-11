---
title: "Offline Catch-up"
date: 2026-04-23
description: "說明訂閱者離線後如何補回缺失事件或狀態"
weight: 143
---

Offline catch-up 的核心概念是「接收端離線期間漏掉的事件，如何在重新連線後補齊」。它是即時通道與正式狀態之間的補償設計。 可先對照 [Durable Queue](/backend/knowledge-cards/durable-queue/)。

## 跟其他概念的關係

Offline catch-up 常出現在 WebSocket、mobile push 與跨區域同步。即時通道只負責在線時低延遲傳遞，離線後的完整性通常由 [durable queue](/backend/knowledge-cards/durable-queue/)、event log 或資料庫狀態查詢提供。

## 可觀察訊號與例子

例如聊天訊息在使用者離線時不能遺失，重新上線後需要補拉缺失訊息；typing indicator 可以不補送。兩者差異來自事件語意，而不是傳輸通道本身。

## 判斷條件與後果

補送範圍、接續標記、補送時限與去重規則，各自決定接收端重新連線後拿到的結果。補送範圍沒有依事件語意區分時，聊天訊息與 typing indicator 一起補送，重新上線的裝置收到一批早已失效的狀態提示。沒有接續標記（cursor）或版本時，接收端無法告訴伺服器自己收到哪裡，只能全量重拉或自己選一個起點：全量重拉浪費頻寬，自選起點會漏掉事件。沒有補送時限時，離線很久的裝置要求的範圍可能超過 [durable queue](/backend/knowledge-cards/durable-queue/) 或 event log 的保存期限，補送拿不到完整資料，只能改從資料庫的狀態查詢重建。沒有去重規則時，在線期間已經收到的事件在補送時又送一次，接收端重複顯示或重複處理。流程沒有寫進 [runbook](/backend/knowledge-cards/runbook/) 時，補送失敗的當下沒有人知道該從哪個接續標記重來。
