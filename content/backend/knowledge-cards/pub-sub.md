---
title: "Pub/Sub"
date: 2026-04-23
description: "說明 publish-subscribe 如何把事件即時分發給多個訂閱者"
weight: 141
---

Pub/Sub 的核心概念是「publisher 把事件送到主題，訂閱者依主題即時接收」。它擅長 [fan-out](/backend/knowledge-cards/fan-out/) 與低延遲通知，但通常不承諾完整歷史保存或離線補送。

## 跟其他概念的關係

Pub/Sub 常用在即時通知、presence 變更、前端狀態廣播與跨節點訊號同步。它和 [durable queue](/backend/knowledge-cards/durable-queue/) 的差異在於：pub/sub 偏即時分發，durable queue 偏可靠處理。

## 可觀察訊號與例子

當需求是「在線訂閱者盡快收到訊息」時，pub/sub 是常見候選。例如聊天室 typing indicator、任務進度更新、dashboard 即時刷新。若訂閱者離線後仍要補送，通常需要搭配 [offline catch-up](/backend/knowledge-cards/offline-catchup/) 或 durable storage。

## 判斷條件與後果

Pub/Sub 適不適用，看訊息遺失的代價。訊息可以遺失時（typing indicator、dashboard 即時刷新），離線的訂閱者錯過的訊息不需要補，pub/sub 的低延遲 fan-out 就滿足需求。訊息需要持久化或重播時，訂閱者離線期間的訊息在它重新連上時已經取不回來，原因是 pub/sub 把事件送給當下在線的訂閱者，通常不保存完整歷史。所以需求轉向高可靠時，關鍵事件改走 [strong reliability](/backend/knowledge-cards/strong-reliability/) 路徑。
