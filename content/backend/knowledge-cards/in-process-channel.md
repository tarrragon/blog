---
title: "In-Process Channel"
date: 2026-04-23
description: "說明單一 process 內用來傳遞工作的 channel 或 queue abstraction"
weight: 126
---

In-process channel 的核心概念是「單一 process 內用來傳遞工作或訊號的通道」。它可以是語言內建 channel、blocking queue、async queue、actor mailbox 或 framework 提供的本地 queue abstraction。 可先對照 [Broker](/backend/knowledge-cards/broker/)。

## 跟其他概念的關係

In-process channel 屬於 application 內部協調機制。[Broker](/backend/knowledge-cards/broker/) 跨 process 保存與投遞訊息；in-process channel 只在目前 process 存活期間承擔資料傳遞與 [backpressure](/backend/knowledge-cards/backpressure/)。

## 可觀察訊號與例子

系統需要 in-process channel 的訊號是同一個服務內部有 [producer](/backend/knowledge-cards/producer/) 與 worker 需要解耦。HTTP handler 接到工作後，可以先放進本地 queue，由 [worker pool](/backend/knowledge-cards/worker-pool/) 處理；process 重啟後，尚未處理的本地工作通常會消失。

## 判斷條件與後果

In-process channel 的幾項設定各自決定 producer 比 worker 快時發生什麼。[buffer](/backend/knowledge-cards/buffer/) 沒有上限時，積壓的工作持續佔用記憶體，直到 process 因記憶體不足被終止；buffer 滿了而阻塞行為沒有定義時，producer（例如 HTTP handler）被卡住的時間直接加進 client 的延遲；drop policy 沒有定義時，滿載時丟掉哪些工作由 channel 的實作決定。關閉流程與 shutdown 沒有定義時，process 結束時 buffer 裡的工作直接消失；缺觀測欄位（buffer 長度、阻塞時間、丟棄數）時，以上幾種情形從外面看都只是延遲或遺失。工作需要跨 process 保存、重試或 [replay](/backend/knowledge-cards/replay-runbook/) 時，in-process channel 只在 process 存活期間保存資料的性質正好排除了這些需求，所以這類工作放進 [broker](/backend/knowledge-cards/broker/) 或 durable queue。
