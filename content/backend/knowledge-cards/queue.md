---
title: "Queue"
date: 2026-06-22
description: "說明 queue 如何保存等待處理的工作並形成容量邊界"
weight: 130
tags: ["backend", "message-queue"]
---

Queue 的核心概念是「把等待處理的工作依序放入一個可觀測的等待區」。它讓 [producer](/backend/knowledge-cards/producer/) 和 [consumer](/backend/knowledge-cards/consumer/) 在時間上解耦，也讓系統可以用等待長度、等待時間與處理速率評估容量壓力。

## 概念位置

Queue 可以存在於 application 內部（[in-process channel](/backend/knowledge-cards/in-process-channel/) + [worker pool](/backend/knowledge-cards/worker-pool/)），也可以由 [broker](/backend/knowledge-cards/broker/)、database table 或 stream platform 提供。Application 內部的 queue 隨 process 生命週期消失；跨 process、需要保存與重放的 queue 通常需要 [durable queue](/backend/knowledge-cards/durable-queue/) 或 broker。

Queue 跟 [topic](/backend/knowledge-cards/topic/) 的差異：queue 的語意通常是「一筆訊息被一個 consumer 處理」（competing consumers），topic 的語意是「一筆訊息可以被多個 [consumer group](/backend/knowledge-cards/consumer-group/) 各自處理」（[fan-out](/backend/knowledge-cards/fan-out/)）。但不同 broker 的術語定義不同 — RabbitMQ 的 queue 跟 Kafka 的 partition 在消費語意上有本質差異。

## 使用情境

系統需要 queue 的訊號是進入速度跟處理速度會短暫不一致。寄信、報表匯出、圖片轉檔、訂單狀態同步都適合先排入 queue，再由 consumer 依照容量處理。[Queue depth](/backend/knowledge-cards/queue-depth/) 跟 oldest item age 會反映延遲壓力 — queue depth 持續增長代表 consumer 來不及消化，需要擴展 consumer 或降低進入速率。

## 設計責任

Queue 要定義容量上限、排序語意（FIFO / priority / delay）、保存期限（[retention](/backend/knowledge-cards/retention/)）、消費模式（pull vs push）、失敗處理（[retry policy](/backend/knowledge-cards/retry-policy/) + [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/)）、[backpressure](/backend/knowledge-cards/backpressure/) 策略（滿了怎麼辦 — block / drop / reject）與觀測欄位。設計上要區分「等待可以接受」跟「等待會傷害產品結果」— 付款入帳能短暫排隊，互動式 API response 通常需要更短的等待期限與更明確的拒絕策略。
