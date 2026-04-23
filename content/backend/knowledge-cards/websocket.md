---
title: "WebSocket"
date: 2026-04-23
description: "說明 WebSocket 如何提供長連線雙向即時通訊"
weight: 132
---

WebSocket 的核心概念是「在單一連線上維持雙向即時資料交換」。它通常從 HTTP upgrade 開始，之後以長連線承載訊息推送、狀態同步與即時互動。

## 概念位置

WebSocket 位在 application 與網路連線之間，常用於聊天、協作編輯、presence、即時通知與 dashboard 更新。它和 [socket](../socket/) 不同的是，WebSocket 是上層通訊協定與互動模式，而 socket 是底層連線抽象。

## 可觀察訊號與例子

系統需要 WebSocket 的訊號是 client 需要持續收到變化，且單純 request / response 太慢或太重。多人聊天室、即時客服、任務進度與連線狀態同步都常見 WebSocket。

## 設計責任

WebSocket 設計要定義連線生命週期、heartbeat、reconnect、訊息順序、disconnect 處理與 [offline catch-up](../offline-catchup/)。若訊息不能遺失，通常還要搭配 [pub/sub](../pub-sub/)、持久化資料或補送流程。
