---
title: "In-Flight Work"
date: 2026-05-13
description: "目前已接收但尚未完成處理的工作量"
weight: 256
---

In-flight work 的核心概念是「系統已接收、正在處理、但尚未完成的工作集合」。它的責任是量化即時壓力，支援容量控制與回退判讀。可對照 [in-flight-message](/backend/knowledge-cards/in-flight-message/) 與 [worker-pool](/backend/knowledge-cards/worker-pool/)。

## 跟其他概念的關係

In-flight 是跨語境訊號：HTTP request、queue message、batch task 都可以有 in-flight。它和 [queue-depth](/backend/knowledge-cards/queue-depth/) 一起看時，能區分「排隊壓力」與「處理壓力」的來源。

## 可觀察訊號與例子

需要 in-flight 判讀的訊號是「延遲上升但不確定是入口太快還是處理太慢」。例如 queue depth 平穩，但 in-flight 長期偏高，通常代表 worker 端處理速度下滑或下游依賴變慢。

## 判斷條件與後果

In-flight 沒有上限時，入口接收的速度超過處理速度的那段期間，每一件未完成的工作持續佔用記憶體、連線與 worker 這類暫存資源；資源耗盡之後所有請求一起超時，client 的重試又把 in-flight 推得更高，演變成雪崩式重試。有上限時，超過上限的工作由降載策略決定拒絕、延後或排隊；沒有降載策略時，超過上限的請求依框架的預設行為處理。上限與目前的 in-flight 數量沒有被觀測時，壓力期的延遲上升分不出是 in-flight 在逼近上限，還是 [queue depth](/backend/knowledge-cards/queue-depth/) 代表的排隊在變長，原因是兩者要放在一起看才分得出處理壓力與排隊壓力。
