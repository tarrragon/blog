---
title: "Queue"
date: 2026-04-23
description: "說明 queue 如何保存等待處理的工作並形成容量邊界"
weight: 130
---

Queue 的核心概念是「把等待處理的工作依序放入一個可觀測的等待區」。它讓 [producer](/backend/knowledge-cards/producer/) 和 [consumer](/backend/knowledge-cards/consumer/) 在時間上解耦，也讓系統可以用等待長度、等待時間與處理速率評估容量壓力。

## 概念位置

Queue 可以存在於 application 內部，也可以由 [broker](/backend/knowledge-cards/broker/)、database、cache 或 stream platform 提供。Application 內部的 queue 常和 [in-process channel](/backend/knowledge-cards/in-process-channel/) 與 [worker pool](/backend/knowledge-cards/worker-pool/) 一起使用；跨 process、需要保存與重放的 queue 通常需要 broker 或 durable storage。

## 可觀察訊號與例子

系統需要 queue 的訊號是進入速度與處理速度會短暫不一致。寄信、報表匯出、圖片轉檔、訂單狀態同步都適合先排入 queue，再由 [consumer](/backend/knowledge-cards/consumer/) 依照容量處理；此時 [queue depth](/backend/knowledge-cards/queue-depth/) 與 oldest item age 會反映延遲壓力。

## 設計責任

Queue 要定義容量、排序語意、保存期限、消費模式、失敗處理、[backpressure](/backend/knowledge-cards/backpressure/) 與觀測欄位。設計上要區分「等待可以接受」與「等待會傷害產品結果」：付款入帳與通知補送能短暫排隊，互動式 API response 通常需要更短的等待期限與更明確的拒絕策略。
