---
title: "Metrics"
date: 2026-06-22
description: "說明指標如何描述服務趨勢、容量與健康狀態"
weight: 34
tags: ["backend", "observability"]
---

Metrics 的核心概念是「用可聚合數值描述系統行為的時間序列」。常見指標包括 request count、error rate、latency、[queue depth](/backend/knowledge-cards/queue-depth/)、[consumer lag](/backend/knowledge-cards/consumer-lag/)、CPU、memory、[connection pool](/backend/knowledge-cards/connection-pool/) 使用量與 [cache hit rate](/backend/knowledge-cards/cache-hit-rate/)。

## 跟其他概念的關係

Metrics 是趨勢觀測跟 [alert](/backend/knowledge-cards/alert/) 的基礎。跟 [log](/backend/knowledge-cards/log/)（事件明細）跟 [trace](/backend/knowledge-cards/trace/)（跨服務路徑）互補：log 適合查單一事件的細節，trace 適合看一次 request 的路徑，metrics 適合回答「服務是否在變慢、錯誤是否在增加、容量是否接近上限」。

Metrics 有三種基本型別：counter（累積計數、只增不減）、gauge（瞬間值、可增可減）、[histogram](/backend/knowledge-cards/histogram/)（分布、支援 [percentile](/backend/knowledge-cards/percentile/) 計算）。選錯型別會讓後面的 [SLI](/backend/knowledge-cards/sli-slo/)、[dashboard](/backend/knowledge-cards/dashboard/) 跟 alert 建立在錯誤訊號上。

## 使用情境

系統需要 metrics 的訊號是團隊需要在使用者回報前知道服務異常。Checkout p95 latency 上升、Redis [timeout](/backend/knowledge-cards/timeout/) 增加、[broker](/backend/knowledge-cards/broker/) lag 擴大，都應先從 metrics 看見。

## 判斷條件與後果

Metrics 的型別與 label 決定了後面的 SLI、dashboard 與 alert 算得出什麼。latency 記成 gauge 時只留下取樣那一刻的值，算不出 percentile，所以 latency 用 [histogram](/backend/knowledge-cards/histogram/)；request count 記成 gauge 時，服務重啟後歸零與流量下降分不開，counter 的變化率計算會把重啟歸零處理掉；connection pool size 是瞬間值，用 gauge。label 只放 service、method、status_code 這類值有界的維度時，時間序列數可以預估；放進 user_id、request_id 時，時間序列數隨請求成長，推高儲存與查詢成本（見 [cardinality](/backend/knowledge-cards/metric-cardinality/)）。重要指標沒有對應到 [SLI / SLO](/backend/knowledge-cards/sli-slo/) 與 [runbook](/backend/knowledge-cards/runbook/) 時，告警響了，值班的人不知道是哪個目標受損、該照哪一份程序處理。Metrics 的聚合查詢跟 [recording rule](/backend/knowledge-cards/recording-rule/) 設計見 [4.2 metrics basics](/backend/04-observability/metrics-basics/)。
