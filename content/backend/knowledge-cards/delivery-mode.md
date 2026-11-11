---
title: "Delivery Mode"
date: 2026-04-23
description: "說明訊息投遞模式如何影響可靠性、延遲與成本"
weight: 70
---

Delivery mode 的核心概念是「訊息系統對交付行為的可靠性選擇」。它可能包含持久化、確認、重送、順序、保留期限與 consumer 分派規則。 可先對照 [Delivery Semantics](/backend/knowledge-cards/delivery-semantics/)。

## 跟其他概念的關係

Delivery mode 把產品語意轉成 broker 設定。正式訂單事件需要較高保證；即時狀態提示可以選擇低延遲、低保留的模式。 可先對照 [Delivery Semantics](/backend/knowledge-cards/delivery-semantics/)。

## 可觀察訊號與例子

系統需要討論 delivery mode 的訊號是同一系統內有不同重要性的訊息。付款成功、庫存同步、推薦刷新、typing indicator 的失敗代價不同，應各自定義可靠性設定。

## 判斷條件與後果

Delivery mode 照 broker 預設值設定時，同一個 broker 上的付款成功事件與 typing indicator 拿到同一種可靠性，結果是重要訊息的保證不足，或低價值訊息付了不必要的持久化與確認成本。兩類訊息的失敗代價不同：付款成功遺失一筆是帳務錯誤，typing indicator 遺失一筆沒有人察覺，所以 delivery mode 依訊息語意設定。遺失、重複、延遲、順序與重放的可接受範圍沒有寫進設計文件時，broker 設定的理由只留在當初設定的人身上，之後調整設定的人判斷不出哪一類訊息可以放寬。
