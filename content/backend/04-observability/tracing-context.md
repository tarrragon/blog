---
title: "4.3 tracing 與 context link"
date: 2026-04-23
description: "整理 trace id、span 與跨服務 context propagation"
weight: 3
---

## 大綱

- [trace](/backend/knowledge-cards/trace/) / [span](/backend/knowledge-cards/span/) 模型
- [trace context](/backend/knowledge-cards/trace-context/) propagation
- [sampling](/backend/knowledge-cards/sampling/)
- service graph

## 概念定位

[trace](/backend/knowledge-cards/trace/) 是把一次 request 在多個服務、queue 與背景任務中的路徑串起來的診斷訊號，責任是讓團隊從症狀追到跨服務等待點。

這一頁處理的是 context link。context 在 thread、task、process 或 queue 邊界斷掉時，trace 會從「路徑」退化成幾段需要人工拼接的局部紀錄。

## 核心判讀

判讀 tracing 時，先看 propagation 是否完整，再看 sampling 是否保留可除錯樣本。

重點訊號包括：

- [trace id](/backend/knowledge-cards/trace-id/) 是否能和 log、metric 共享 [correlation id](/backend/knowledge-cards/correlation-id/)
- async / queue / background job 是否能保留 parent-child 關係
- sampling 是否能在高流量下保留錯誤與高延遲樣本
- service graph 是否能由 trace 聚合而來，並降低 wiki 手動維護成本

## 判讀訊號

- request 跨服務後 trace 斷鏈、靠人重組
- async / queue 邊界 context 沒傳遞
- 採樣率太低、production debug 找不到對應 trace
- trace id 跟 log / metric 對不上、無共同 correlation key
- service graph 不存在或半年沒人看

## 交接路由

- 04.11 telemetry pipeline：[sampling](/backend/knowledge-cards/sampling/) 與 collector 配置
- 04.13 service topology：trace 訊號聚合成依賴圖
