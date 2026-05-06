---
title: "Server-Sent Events (SSE)"
date: 2026-04-23
description: "說明 SSE 如何透過 HTTP 長連線向 client 單向推送事件"
weight: 133
---


Server-Sent Events 的核心概念是「server 用持續的 HTTP response 對 client 單向推送事件」。它比 WebSocket 更適合單向通知、直播更新與簡單即時狀態流。 可先對照 [Offline Catch-up](/backend/knowledge-cards/offline-catchup/)。

## 概念位置

SSE 位在 HTTP 之上，適合 server 主導的事件串流。它常用於通知、進度更新、系統訊號與簡化版即時 feed。 可先對照 [Offline Catch-up](/backend/knowledge-cards/offline-catchup/)。

## 可觀察訊號與例子

系統需要 SSE 的訊號是 client 只需要接收事件、不需要頻繁回傳雙向互動。活動進度條、批次作業狀態、公告 feed 與監控看板更新都可能使用 SSE。

## 設計責任

SSE 設計要定義斷線重連、事件 ID、補送起點與保留窗口。若 client 離線後仍要完整補回資料，仍要搭配 [offline catch-up](/backend/knowledge-cards/offline-catchup/) 或正式儲存路徑。
