---
title: "Delivery Mode"
date: 2026-04-23
description: "說明訊息投遞模式如何影響可靠性、延遲與成本"
weight: 69
---


Delivery mode 的核心概念是「訊息系統對交付行為的可靠性選擇」。它可能包含持久化、確認、重送、順序、保留期限與 consumer 分派規則。 可先對照 [Delivery Semantics](/backend/knowledge-cards/delivery-semantics/)。

## 概念位置

Delivery mode 把產品語意轉成 broker 設定。正式訂單事件需要較高保證；即時狀態提示可以選擇低延遲、低保留的模式。 可先對照 [Delivery Semantics](/backend/knowledge-cards/delivery-semantics/)。

## 可觀察訊號與例子

系統需要討論 delivery mode 的訊號是同一系統內有不同重要性的訊息。付款成功、庫存同步、推薦刷新、typing indicator 的失敗代價不同，應各自定義可靠性設定。

## 設計責任

Delivery mode 要由訊息語意決定，而非由 broker 預設值決定。設計文件應標出遺失、重複、延遲、順序與重放的可接受範圍。
