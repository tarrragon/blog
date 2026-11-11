---
title: "Checkpoint"
date: 2026-04-23
description: "說明長時間處理流程如何記錄可恢復進度"
weight: 82
---

Checkpoint 的核心概念是「記錄處理流程已安全完成的位置」。它讓長時間工作、event consumer、migration、backfill 或資料同步在中斷後可以接續。 可先對照 [CI Pipeline](/backend/knowledge-cards/ci-pipeline/)。

## 跟其他概念的關係

Checkpoint 是恢復能力與重放安全的基礎。它可以是 offset、時間戳、primary key、batch id、file position 或業務狀態。 可先對照 [CI Pipeline](/backend/knowledge-cards/ci-pipeline/)。

## 可觀察訊號與例子

系統需要 checkpoint 的訊號是工作需要分批完成或可能中途停止。Backfill 會員資料跑到第 300 萬筆時部署中斷，checkpoint 讓下一次從安全位置繼續。

## 判斷條件與後果

Checkpoint 提交的時機相對於工作處理完成的時機，決定中斷之後的結果。工作還沒處理完就提交 checkpoint 時，重啟後從 checkpoint 之後接續，那段沒完成的工作不會再被處理，結果是遺失；工作處理完之後才提交時，處理完到提交之間發生中斷，重啟後會從較早的位置接續，同一段工作被處理第二次。重複處理的代價可以由 handler 吸收：handler 具備 idempotency 或可重入設計時，第二次處理不產生新的副作用。所以 checkpoint 放在處理完成之後提交，搭配可以重複執行的 handler。
