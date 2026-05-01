---
title: "4.3 tracing 與 context link"
date: 2026-04-23
description: "整理 trace id、span 與跨服務 context propagation"
weight: 3
---

## 大綱

- [trace](/backend/knowledge-cards/trace/) / [span](/backend/knowledge-cards/span/) 模型
- context propagation
- [sampling](/backend/knowledge-cards/sampling/)
- service graph

## 判讀訊號

- request 跨服務後 trace 斷鏈、靠人重組
- async / queue 邊界 context 沒傳遞
- 採樣率太低、production debug 找不到對應 trace
- trace id 跟 log / metric 對不上、無共同 correlation key
- service graph 不存在或半年沒人看

## 交接路由

- 04.11 telemetry pipeline：sampling 與 collector 配置
- 04.13 service topology：trace 訊號聚合成依賴圖
