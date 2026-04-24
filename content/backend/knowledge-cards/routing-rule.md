---
title: "Routing Rule"
date: 2026-04-23
description: "說明訊息系統如何依規則把訊息送到不同處理路徑"
weight: 135
---

Routing rule 的核心概念是「用訊息屬性決定訊息要進入哪個處理路徑」。規則可以依 topic、routing key、header、tenant、事件類型、優先級或業務狀態分派訊息。

## 概念位置

Routing rule 是 [broker](/backend/knowledge-cards/broker/) 內的分流邏輯。它把 [producer](/backend/knowledge-cards/producer/) 的輸出轉成不同 [queue](/backend/knowledge-cards/queue/)、[consumer group](/backend/knowledge-cards/consumer-group/) 或 stream [partition](/backend/knowledge-cards/partition/)，讓不同工作可以用不同容量、權限與 [retry policy](/backend/knowledge-cards/retry-policy/) 處理。

## 可觀察訊號與例子

系統需要 routing rule 的訊號是同一類事件有不同處理代價。一般通知可以進入低成本 queue，高價值訂單通知可以進入優先 queue；退款事件可以交給需要更完整 [audit log](/backend/knowledge-cards/audit-log/) 的 consumer。

## 設計責任

Routing rule 要有可測試規則、預設路徑、觀測欄位與變更流程。規則錯誤會讓訊息進錯 queue、漏處理或造成局部 [consumer lag](/backend/knowledge-cards/consumer-lag/)，因此每次調整都要搭配樣本驗證與回復方式。
