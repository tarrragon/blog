---
title: "Consumer Group"
date: 2026-04-23
description: "說明一組 consumer 如何共同分攤 stream 或 topic 的處理責任"
weight: 72
---


Consumer group 的核心概念是「一組 consumer 共同承擔某個 stream 或 topic 的處理進度」。同一 group 內的 consumer 分攤工作；不同 group 可以各自獨立處理同一批事件。 可先對照 [Consumer Lag](/backend/knowledge-cards/consumer-lag/)。

## 概念位置

Consumer group 是事件流與多服務訂閱的協調模型。分析服務、搜尋索引服務、通知服務可以用不同 group 讀同一 topic；每個 group 有自己的進度與 lag。 可先對照 [Consumer Lag](/backend/knowledge-cards/consumer-lag/)。

## 可觀察訊號與例子

系統需要 consumer group 的訊號是同一事件要被多個系統各自處理。訂單事件可以同時給出貨、通知與報表，每個 group 的處理速度、錯誤與重放流程不同。

## 設計責任

Consumer group 要設計 group 名稱、ownership、offset / checkpoint、重平衡、lag 告警與 replay 權限。不同 group 的失敗應分開觀測與處理。
