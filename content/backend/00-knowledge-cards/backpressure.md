---
title: "Backpressure"
date: 2026-04-23
description: "說明下游處理速度不足時系統如何限制上游進入速度"
weight: 27
---

Backpressure 的核心概念是「下游處理能力不足時，讓上游感知並放慢」。它讓系統在壓力下排隊、拒絕、降級或削峰，避免工作持續進入系統直到資源耗盡。

## 概念位置

Backpressure 出現在 [in-process channel](../in-process-channel/)、[queue](../queue/)、[worker pool](../worker-pool/)、[HTTP client](../http-client/)、[connection pool](../connection-pool/)、[broker](../broker/) 的 [consumer](../consumer/) 與 [stream pipeline](../stream-pipeline/)。它處理的是速度不匹配：進入速度高於處理速度。

## 可觀察訊號與例子

系統需要 backpressure 的訊號是 [queue depth](../queue-depth/) 上升、memory 上升、[timeout](../timeout/) 增加或 [consumer lag](../consumer-lag/) 擴大。通知服務突然收到大量任務時，應限制 worker 數與下游 API 呼叫量，讓任務排隊或延後。

## 設計責任

Backpressure 要定義 [buffer](../buffer/) 大小、等待期限、拒絕策略、[retry policy](../retry-policy/)、[load shedding](../load-shedding/) 與使用者回饋。觀測上要能看 [queue depth](../queue-depth/)、處理耗時、drop count、[timeout](../timeout/) 與下游 error rate，並把關鍵指標放進 [dashboard](../dashboard/)。
