---
title: "Buffer"
date: 2026-04-23
description: "說明系統如何用暫存空間吸收短暫速度差與尖峰流量"
weight: 130
---

Buffer 的核心概念是「用暫存空間吸收 [producer](/backend/knowledge-cards/producer/) 與 [consumer](/backend/knowledge-cards/consumer/) 之間的短暫速度差」。Buffer 可以存在於 [in-process channel](/backend/knowledge-cards/in-process-channel/)、[queue](/backend/knowledge-cards/queue/)、[socket](/backend/knowledge-cards/socket/)、[HTTP client](/backend/knowledge-cards/http-client/)、[broker](/backend/knowledge-cards/broker/)、[stream pipeline](/backend/knowledge-cards/stream-pipeline/) 或 [write-behind cache](/backend/knowledge-cards/write-behind-cache/)。

## 跟其他概念的關係

Buffer 是平滑尖峰的工具，也是延遲與記憶體風險來源。Buffer 太小會讓 [producer](/backend/knowledge-cards/producer/) 很快被阻塞或拒絕；buffer 太大會累積延遲、記憶體壓力與過期工作。

## 可觀察訊號與例子

系統需要 buffer 設計的訊號是流量有短暫 burst，但下游平均容量足夠。通知服務可以用小型 buffer 吸收幾秒尖峰；長時間進入速度高於處理速度時，buffer 只會把問題延後。

## 判斷條件與後果

Buffer 只在短暫 burst 下有效；進入速度長時間高於處理速度時，任何容量的 buffer 都只是把失敗延後，容量、等待期限與溢出策略決定延後的形態。沒有等待期限時，排在後面的工作出隊時已經過期，consumer 花資源處理一份沒有人要的結果；沒有溢出策略與 drop policy 時，buffer 滿了之後 producer 被阻塞還是記憶體持續增長，由實作的預設行為決定。沒有定義 shutdown 行為時，程序結束當下記憶體內 buffer 裡的工作直接遺失。fill ratio 與 oldest item age 分得開這兩種狀態：fill ratio 高而 oldest item age 短是正常的 burst，兩者一起持續上升代表處理速度長期不足；drop count 與處理耗時則顯示已經丟掉多少工作、consumer 是否變慢。
