---
title: "Pub/Sub"
date: 2026-04-23
description: "說明 publish-subscribe 如何把事件即時分發給多個訂閱者"
weight: 140
---


Pub/Sub 的核心概念是「publisher 把事件送到主題，訂閱者依主題即時接收」。它擅長 [fan-out](/backend/knowledge-cards/fan-out/) 與低延遲通知，但通常不承諾完整歷史保存或離線補送。

## 概念位置

Pub/Sub 常用在即時通知、presence 變更、前端狀態廣播與跨節點訊號同步。它和 [durable queue](/backend/knowledge-cards/durable-queue/) 的差異在於：pub/sub 偏即時分發，durable queue 偏可靠處理。

## 可觀察訊號與例子

當需求是「在線訂閱者盡快收到訊息」時，pub/sub 是常見候選。例如聊天室 typing indicator、任務進度更新、dashboard 即時刷新。若訂閱者離線後仍要補送，通常需要搭配 [offline catch-up](/backend/knowledge-cards/offline-catchup/) 或 durable storage。

## 設計責任

設計時要明確訊息是否可遺失、是否需要持久化、是否需要重播。若需求轉向高可靠，應把關鍵事件切到 [strong reliability](/backend/knowledge-cards/strong-reliability/) 路徑。
