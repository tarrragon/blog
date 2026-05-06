---
title: "Competing Consumers"
date: 2026-04-23
description: "說明多個 consumer 共同處理同一個 queue 如何提高吞吐與影響順序"
weight: 71
---


Competing consumers 的核心概念是「多個 consumer 從同一個 queue 競爭取得工作」。這個模式可以提高吞吐與可用性，但會讓單一 queue 中的處理順序更難保證。 可先對照 [Config Rollout](/backend/knowledge-cards/config-rollout/)。

## 概念位置

Competing consumers 是水平擴展 worker 的常見模式。它適合彼此獨立的工作，例如寄信、轉檔、縮圖、資料同步；對需要嚴格順序的工作，要額外設計 partition、key 或 single consumer。 可先對照 [Config Rollout](/backend/knowledge-cards/config-rollout/)。

## 可觀察訊號與例子

系統需要 competing consumers 的訊號是單一 worker 處理速度追不上進入速度。報表產生任務彼此獨立時，可以增加 consumer 數；同一訂單的狀態事件則可能需要按 order id 保持順序。

## 設計責任

設計要定義工作是否可並行、是否需要順序、是否具備 idempotency，以及下游容量是否足夠。擴 consumer 前要確認 bottleneck 不在資料庫、外部 API 或全域 lock。
