---
title: "In-Process Channel"
date: 2026-04-23
description: "說明單一 process 內用來傳遞工作的 channel 或 queue abstraction"
weight: 125
---

In-process channel 的核心概念是「單一 process 內用來傳遞工作或訊號的通道」。它可以是語言內建 channel、blocking queue、async queue、actor mailbox 或 framework 提供的本地 queue abstraction。

## 概念位置

In-process channel 屬於 application 內部協調機制。[Broker](/backend/knowledge-cards/broker/) 跨 process 保存與投遞訊息；in-process channel 只在目前 process 存活期間承擔資料傳遞與 [backpressure](/backend/knowledge-cards/backpressure/)。

## 可觀察訊號與例子

系統需要 in-process channel 的訊號是同一個服務內部有 [producer](/backend/knowledge-cards/producer/) 與 worker 需要解耦。HTTP handler 接到工作後，可以先放進本地 queue，由 [worker pool](/backend/knowledge-cards/worker-pool/) 處理；process 重啟後，尚未處理的本地工作通常會消失。

## 設計責任

In-process channel 要定義 [buffer](/backend/knowledge-cards/buffer/) 大小、阻塞行為、關閉流程、drop policy、shutdown 與觀測欄位。需要跨 process 保存、重試或 [replay](/backend/knowledge-cards/replay-runbook/) 的工作應升級到 [broker](/backend/knowledge-cards/broker/) 或 durable queue。
