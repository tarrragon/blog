---
title: "WebSocket"
date: 2026-04-23
description: "說明 WebSocket 如何提供長連線雙向即時通訊"
weight: 133
---

WebSocket 的核心概念是「在單一連線上維持雙向即時資料交換」。它通常從 HTTP upgrade 開始，之後以長連線承載訊息推送、狀態同步與即時互動。 可先對照 [Socket](/backend/knowledge-cards/socket/)。

## 跟其他概念的關係

WebSocket 位在 application 與網路連線之間，常用於聊天、協作編輯、presence、即時通知與 dashboard 更新。它和 [socket](/backend/knowledge-cards/socket/) 不同的是，WebSocket 是上層通訊協定與互動模式，而 socket 是底層連線抽象。

## 可觀察訊號與例子

系統需要 WebSocket 的訊號是 client 需要持續收到變化，且單純 request / response 太慢或太重。多人聊天室、即時客服、任務進度與連線狀態同步都常見 WebSocket。

## 判斷條件與後果

WebSocket 的訊息只存在於連線上，連線斷掉時，傳到一半的訊息與斷線期間產生的訊息都不在任何一端，所以連線生命週期的每個環節決定斷線時會失去什麼。沒有 heartbeat 時，中間的 proxy 或 NAT 已經切斷閒置連線而兩端都不知道，server 繼續往斷掉的連線推送；沒有 reconnect 時，client 斷線後停在舊狀態；重連之後沒有 [offline catch-up](/backend/knowledge-cards/offline-catchup/) 時，斷線期間的訊息再也收不到；沒有約定訊息順序時，補送的舊訊息與新訊息交錯，client 顯示的狀態倒退。訊息不能遺失的場景，連線本身不保存訊息，所以搭配 [pub/sub](/backend/knowledge-cards/pub-sub/)、持久化資料或補送流程。
