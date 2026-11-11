---
title: "Load Shedding"
tags: ["負載削峰", "Load Shedding"]
date: 2026-04-23
description: "說明服務過載時如何主動拒絕低優先工作以保護核心能力"
weight: 53
---

Load shedding 的核心概念是「在過載時主動丟棄或拒絕部分工作」。它用有限失敗保護核心能力，避免所有工作一起排隊到超時：被拒的請求立刻得到錯誤，其餘請求維持原本的延遲，等於主動選擇請求失敗、避開無回應（各種結果見 [9.16 負載超過容量時服務的表現](/backend/09-performance-capacity/overload-outcomes/)）。 可先對照 [Load Test](/backend/knowledge-cards/load-test/)。

## 跟其他概念的關係

Load shedding 是過載保護工具。它和 rate limit、backpressure、degradation、priority queue 與 [Admission Control](/backend/knowledge-cards/admission-control/) 相關；重點是先定義哪些工作可以被拒絕，哪些工作需要保留。 可先對照 [Load Test](/backend/knowledge-cards/load-test/)。

## 可觀察訊號與例子

系統需要 load shedding 的訊號是流量尖峰超過服務容量。活動期間可以拒絕低優先的推薦刷新、延後報表產生，保留下單、付款與資料保存。

## 判斷條件與後果

過載時哪些工作被拒，由事先定義的優先級決定；沒有優先級時，被拒的是剛好在那一刻到達的請求，下單與付款可能和推薦刷新一起被丟掉。被拒的請求收到的回應沒有明確的錯誤與重試建議（多久之後再試）時，client 立刻重試，被拒的流量回到入口，抵消了 shedding 釋出的容量。Shedding 啟動時沒有告警，容量不足的狀態被它遮住，團隊不知道需要擴容；使用者端沒有對應的畫面時，被拒的使用者看到的是不明的錯誤。觀測上記下 shed count、原因、受影響的 endpoint 與核心路徑是否恢復，才判斷得出 shedding 是否保住了它要保護的那些工作。
