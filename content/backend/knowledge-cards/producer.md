---
title: "Producer"
date: 2026-04-23
description: "說明 producer 如何把工作、事件或資料送入後續處理路徑"
weight: 132
---


Producer 的核心概念是「產生工作、事件或資料並送入後續處理路徑的角色」。它可以是 API handler、排程任務、database change capture、外部 webhook 或任何把資料放進 [queue](/backend/knowledge-cards/queue/)、[broker](/backend/knowledge-cards/broker/) 與 [stream pipeline](/backend/knowledge-cards/stream-pipeline/) 的元件。

## 概念位置

Producer 位在資料流的上游。它的送入速度、資料品質與錯誤處理會直接影響 [consumer](/backend/knowledge-cards/consumer/)、[queue depth](/backend/knowledge-cards/queue-depth/)、[backpressure](/backend/knowledge-cards/backpressure/) 與下游成本。

## 可觀察訊號與例子

系統需要辨識 producer 的訊號是同一個處理路徑有多個資料來源。訂單建立 API、批次匯入工具與第三方 webhook 都可能產生訂單事件；如果每個 producer 的資料格式與重試策略不同，consumer 會承擔更多判斷成本。

## 設計責任

Producer 要定義送入條件、資料格式、唯一識別碼、[idempotency](/backend/knowledge-cards/idempotency/)、[retry policy](/backend/knowledge-cards/retry-policy/)、[rate limit](/backend/knowledge-cards/rate-limit/) 與觀測欄位。操作上要能按 producer 來源查看進入速率、錯誤率、payload 大小與被拒絕數量，才能在尖峰或資料異常時定位來源。
