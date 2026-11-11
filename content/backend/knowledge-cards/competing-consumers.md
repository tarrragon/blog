---
title: "Competing Consumers"
date: 2026-04-23
description: "說明多個 consumer 共同處理同一個 queue 如何提高吞吐與影響順序"
weight: 72
---

Competing consumers 的核心概念是「多個 consumer 從同一個 queue 競爭取得工作」。這個模式可以提高吞吐與可用性，但會讓單一 queue 中的處理順序更難保證。 可先對照 [Config Rollout](/backend/knowledge-cards/config-rollout/)。

## 跟其他概念的關係

Competing consumers 是水平擴展 worker 的常見模式。它適合彼此獨立的工作，例如寄信、轉檔、縮圖、資料同步；對需要嚴格順序的工作，要額外設計 partition、key 或 single consumer。 可先對照 [Config Rollout](/backend/knowledge-cards/config-rollout/)。

## 可觀察訊號與例子

系統需要 competing consumers 的訊號是單一 worker 處理速度追不上進入速度。報表產生任務彼此獨立時，可以增加 consumer 數；同一訂單的狀態事件則可能需要按 order id 保持順序。

## 判斷條件與後果

增加 consumer 能否提高吞吐，取決於工作本身與下游的條件。工作彼此獨立（寄信、轉檔）時，多個 consumer 可以並行處理；同一個 key 的工作需要順序（同一訂單的狀態事件）時，多個 consumer 同時取用會讓後送進來的事件先處理完，狀態被較舊的事件覆蓋，這類工作要依 key 分 partition 或交給單一 consumer。broker 重新投遞或 consumer 失敗重試時，同一筆工作會被處理兩次，handler 沒有 idempotency 時產生重複的副作用（同一封信寄兩次）。bottleneck 在資料庫、外部 API 或全域 lock 時，增加 consumer 只增加等在同一個資源前的工作數，吞吐不變，下游的負載反而上升。
