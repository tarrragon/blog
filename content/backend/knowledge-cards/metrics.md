---
title: "Metrics"
date: 2026-04-23
description: "說明指標如何描述服務趨勢、容量與健康狀態"
weight: 33
---

Metrics 的核心概念是「用可聚合數值描述系統行為」。常見指標包括 request count、error rate、latency、[queue depth](/backend/knowledge-cards/queue-depth/)、[consumer lag](/backend/knowledge-cards/consumer-lag/)、CPU、memory、[connection pool](/backend/knowledge-cards/connection-pool/) 使用量與 [cache hit rate](/backend/knowledge-cards/cache-hit-rate/)。

## 概念位置

Metrics 是趨勢與 [alert](/backend/knowledge-cards/alert/) 的基礎。[Log](/backend/knowledge-cards/log/) 適合查單一事件，metrics 適合回答服務是否變慢、錯誤是否變多、容量是否接近上限。

## 可觀察訊號與例子

系統需要 metrics 的訊號是團隊需要在使用者回報前知道服務異常。Checkout p95 latency 上升、Redis [timeout](/backend/knowledge-cards/timeout/) 增加、[broker](/backend/knowledge-cards/broker/) lag 擴大，都應先從 metrics 看見。

## 設計責任

Metrics 設計要選擇 counter、gauge、[histogram](/backend/knowledge-cards/histogram/) 與 label。重要指標要能對應 [SLI / SLO](/backend/knowledge-cards/sli-slo/) 與 [runbook](/backend/knowledge-cards/runbook/)；高 [metric cardinality](/backend/knowledge-cards/metric-cardinality/) label 會增加成本與查詢壓力。
