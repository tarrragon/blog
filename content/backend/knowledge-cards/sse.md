---
title: "Server-Sent Events (SSE)"
date: 2026-04-23
description: "說明 SSE 如何透過 HTTP 長連線向 client 單向推送事件"
weight: 134
---

Server-Sent Events 的核心概念是「server 用持續的 HTTP response 對 client 單向推送事件」。它比 WebSocket 更適合單向通知、直播更新與簡單即時狀態流。 可先對照 [Offline Catch-up](/backend/knowledge-cards/offline-catchup/)。

## 跟其他概念的關係

SSE 位在 HTTP 之上，適合 server 主導的事件串流。它常用於通知、進度更新、系統訊號與簡化版即時 feed。 可先對照 [Offline Catch-up](/backend/knowledge-cards/offline-catchup/)。

## 可觀察訊號與例子

系統需要 SSE 的訊號是 client 只需要接收事件、不需要頻繁回傳雙向互動。活動進度條、批次作業狀態、公告 feed 與監控看板更新都可能使用 SSE。

## 判斷條件與後果

SSE 的連線會因網路切換、proxy 逾時或 server 重啟而中斷，斷線期間的事件是否補得回來，取決於事件 ID、補送起點與保留窗口。事件沒有 ID 時，client 重連後無法告訴 server 自己收到哪一筆，只能從最新的事件開始收，斷線期間的事件遺失；事件有 ID 而 server 沒有保留歷史事件時，client 重連時送上最後收到的 ID（`Last-Event-ID`），server 也無從補送；保留窗口比 client 的離線時間短時，窗口之前的事件同樣補不回。Client 離線很久之後仍要完整補回資料時，保留窗口涵蓋不到，補回的工作交給 [offline catch-up](/backend/knowledge-cards/offline-catchup/) 或正式儲存路徑。
