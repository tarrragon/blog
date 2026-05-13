---
title: "In-Flight Work"
date: 2026-05-13
description: "目前已接收但尚未完成處理的工作量"
weight: 255
---

In-flight work 的核心概念是「系統已接收、正在處理、但尚未完成的工作集合」。它的責任是量化即時壓力，支援容量控制與回退判讀。可對照 [in-flight-message](/backend/knowledge-cards/in-flight-message/) 與 [worker-pool](/backend/knowledge-cards/worker-pool/)。

## 概念位置

In-flight 是跨語境訊號：HTTP request、queue message、batch task 都可以有 in-flight。它和 [queue-depth](/backend/knowledge-cards/queue-depth/) 一起看時，能區分「排隊壓力」與「處理壓力」的來源。

## 可觀察訊號與例子

需要 in-flight 判讀的訊號是「延遲上升但不確定是入口太快還是處理太慢」。例如 queue depth 平穩，但 in-flight 長期偏高，通常代表 worker 端處理速度下滑或下游依賴變慢。

## 設計責任

In-flight 需要可觀測上限與降載策略。沒有上限時，系統容易在壓力期把暫存資源耗盡，最後演變成全域超時或雪崩式重試。
