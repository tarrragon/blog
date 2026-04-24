---
title: "Communication Protocol"
date: 2026-04-23
description: "說明不同系統如何對齊資料交換與錯誤語意"
weight: 127
---

Communication Protocol 的核心概念是「雙方對資料格式、順序、錯誤與互動方式達成一致的規則」。它描述的是通訊雙方如何交換資料，以及在失敗時如何解讀結果。

## 概念位置

Communication Protocol 位在 application、client、broker、[API Gateway](/backend/knowledge-cards/api-gateway/) 或 service 之間，決定兩端如何交換資料與解讀狀態。

## 可觀察訊號

系統需要 communication protocol 明確化的訊號是多個元件開始共用同一種資料交換方式。若格式不穩定，錯誤就會出現在解析、版本相容、重試語意或欄位命名上。

## 接近真實網路服務的例子

請求/回應型通訊、queue message schema、webhook payload 與簽章驗證，都屬於 communication protocol 問題。這類約定需要被拆到更具體的子卡，才能維持原子性。

## 設計責任

設計時要定義版本相容、錯誤處理、欄位演進與測試方式。Communication Protocol 的目標不是把格式做得很複雜，而是讓雙方知道哪些行為是約定的一部分。
