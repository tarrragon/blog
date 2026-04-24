---
title: "Sticky Session"
tags: ["黏性會話", "Sticky Session"]
date: 2026-04-24
description: "說明同一 client 如何在一段時間內持續命中同一個後端實例"
weight: 130
---

Sticky Session 的核心概念是「讓同一個 client、session 或 connection 在一段時間內持續命中同一個服務實例」。它是一種負載平衡策略，常用來維持本機狀態、暫存資料或未外部化 session 的可用性。

## 概念位置

Sticky Session 位在 client、load balancer、application instances 與 session state 之間。它改變的是流量分派規則，不是應用邏輯本身。

## 可觀察訊號

系統需要 sticky session 的訊號是：

- 服務仍保存本機狀態，短期內不容易外部化
- 多步驟互動需要維持同一個後端實例
- session state 還沒移到共享儲存或快取

## 接近真實網路服務的例子

聊天室、即時遊戲、某些登入流程、需要本機暫存的舊系統，常會要求同一個使用者在 session 期間保持 sticky routing。

## 設計責任

設計時要定義黏著的判斷鍵、有效時間、失效後怎麼重新導向、以及單一 instance 故障時如何處理 session 遷移。Sticky Session 會讓負載分佈變得不均，因此要清楚知道它是權宜策略，不是預設最佳解。

