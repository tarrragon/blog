---
title: "Replication Channel"
date: 2026-05-22
description: "說明多來源複製中，每個來源對應的獨立複製通道如何成為隔離單位"
weight: 344
---

Replication Channel 的核心概念是當一個資料庫同時從多個來源複製時，每個來源對應一條獨立的複製通道，各自有自己的進度、延遲、錯誤與設定。它讓多來源複製的健康狀況可以被分開判讀與分開處理，每條通道的延遲要分開接回 [Replication Lag](/backend/knowledge-cards/replication-lag/)。

## 概念位置

Replication Channel 位在多來源複製的拓撲層。單一來源的複製只有一條流；多來源複製把多條流並存在同一個目標資料庫上，每條就是一個 channel。channel 是隔離單位：一個來源的 [Replication Lag](/backend/knowledge-cards/replication-lag/) 或錯誤不必然代表其他來源也有問題，[GTID](/backend/knowledge-cards/gtid/) 之類的識別機制讓各 channel 的位置可以分開追蹤。

## 可觀察訊號與例子

需要 per-channel 視角的訊號是整體 replica 看起來健康、但某個來源的資料就是慢或對不上。只看整體 replica lag 會錯過「哪一個來源卡住」。常見場景是把多個地區或多個服務的資料庫匯總到一個分析庫，其中一條 channel 因為網路或 schema 問題落後，其他 channel 正常。

## 設計責任

設計時要為每條 channel 命名、定義各自的 owner、lag SLO 與錯誤處理策略。監控與告警要做到 per-channel，並讓單一 channel 的故障可以只停那一條、不影響其他來源。observability 要能分開看每條 channel 的位置、延遲與錯誤。
