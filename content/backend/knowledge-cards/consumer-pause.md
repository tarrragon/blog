---
title: "Consumer Pause"
date: 2026-06-16
description: "說明暫停消費作為事故控制手段，止住錯誤副作用擴大"
weight: 380
---

Consumer pause 的核心概念是「主動停止消費，止住錯誤副作用繼續擴大」。當下游故障、毒訊息卡關或處理邏輯有 bug 時，暫停消費讓事件留在 broker、爭取修復時間，是事故當下的控制手段。 可先對照 [Consumer Lag](/backend/knowledge-cards/consumer-lag/)。

## 跟其他概念的關係

Consumer pause 是事故處理的閥門。暫停期間 [consumer lag](/backend/knowledge-cards/consumer-lag/) 會上升，但事件多半仍在 [replay window](/backend/knowledge-cards/replay-window/) 內，前提是暫停時間短於 retention，恢復後可從原 offset 接續。

## 可觀察訊號與例子

下游資料庫過載時，繼續消費只會放大寫入壓力與重試風暴；暫停消費讓壓力停在 broker，下游恢復後再 resume。毒訊息卡住整個 partition 時，暫停加上把該訊息送 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 比硬重試更快止血。

## 判斷條件與後果

Consumer 暫停之後，事件留在 broker、lag 持續上升，事件只在 [replay window](/backend/knowledge-cards/replay-window/) 內保得住：暫停的時間超過 retention 時，最早的那批事件會被 broker 刪除，恢復後也讀不回來。pause、drain、resume 的決策與時點沒有記進 decision log 時，事故結束後沒有任何紀錄指出這個 consumer 還停著，lag 在沒有人處理的情況下累積到超過 retention。暫停與恢復需要的步驟越多，事故當下止住錯誤副作用的時間越晚，所以暫停與恢復要能用一個操作完成。
