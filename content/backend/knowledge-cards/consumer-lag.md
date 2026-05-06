---
title: "Consumer Lag"
date: 2026-04-23
description: "說明 consumer lag 如何反映訊息堆積、處理能力與容量風險"
weight: 2
---


Consumer lag 的核心概念是「consumer 已處理位置落後於 broker 最新訊息位置的距離」。這個距離可以用訊息數量、offset 差距或預估處理時間表示，它反映事件進入系統的速度是否高於處理速度。 可先對照 [Consumer](/backend/knowledge-cards/consumer/)。

## 概念位置

Consumer lag 是訊息系統的容量與健康訊號。Lag 上升代表某個 consumer group 正在累積未處理工作；lag 下降代表處理速度追上進入速度。不同 broker 的名稱不同，例如 Kafka 常看 offset lag，Redis Streams 可看 pending 與未讀項目，RabbitMQ 常看 queue depth 與 unacked messages。 可先對照 [Consumer](/backend/knowledge-cards/consumer/)。

## 可觀察訊號

系統需要關注 consumer lag 的訊號是「工作延遲開始影響產品結果」。例如通知延遲、報表延遲、搜尋索引更新延遲、訂單狀態同步延遲。Lag 也常伴隨 CPU 飽和、下游 API 變慢、資料庫鎖競爭或 consumer 反覆重試。

## 接近真實網路服務的例子

外送平台在尖峰時段大量產生訂單事件。若地圖更新 consumer 的 lag 持續上升，使用者看到的騎手位置會落後；若付款入帳 consumer 的 lag 上升，客服與帳務對帳會延後。兩者都叫 lag，但產品代價不同，因此告警門檻也應分開設計。

## 設計責任

Consumer lag 要搭配 runbook 使用。Runbook 應說明 lag 上升時先看進入量、處理耗時、錯誤率、下游延遲、重試數與 instance 數量；再決定擴容、暫停低優先工作、修復 poison message 或調整下游保護。
