---
title: "Buffer"
date: 2026-04-23
description: "說明系統如何用暫存空間吸收短暫速度差與尖峰流量"
weight: 129
---


Buffer 的核心概念是「用暫存空間吸收 [producer](/backend/knowledge-cards/producer/) 與 [consumer](/backend/knowledge-cards/consumer/) 之間的短暫速度差」。Buffer 可以存在於 [in-process channel](/backend/knowledge-cards/in-process-channel/)、[queue](/backend/knowledge-cards/queue/)、[socket](/backend/knowledge-cards/socket/)、[HTTP client](/backend/knowledge-cards/http-client/)、[broker](/backend/knowledge-cards/broker/)、[stream pipeline](/backend/knowledge-cards/stream-pipeline/) 或 [write-behind cache](/backend/knowledge-cards/write-behind-cache/)。

## 概念位置

Buffer 是平滑尖峰的工具，也是延遲與記憶體風險來源。Buffer 太小會讓 [producer](/backend/knowledge-cards/producer/) 很快被阻塞或拒絕；buffer 太大會累積延遲、記憶體壓力與過期工作。

## 可觀察訊號與例子

系統需要 buffer 設計的訊號是流量有短暫 burst，但下游平均容量足夠。通知服務可以用小型 buffer 吸收幾秒尖峰；長時間進入速度高於處理速度時，buffer 只會把問題延後。

## 設計責任

Buffer 要定義容量、等待期限、溢出策略、drop policy、觀測欄位與 shutdown 行為。觀測上要看 fill ratio、oldest item age、drop count 與處理耗時。
