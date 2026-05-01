---
title: "4.2 metrics 與 SLI/SLO"
date: 2026-04-23
description: "整理 counter、gauge、histogram 與服務健康指標"
weight: 2
---

## 大綱

- [metrics](/backend/knowledge-cards/metrics/) 基本型別
- latency [histogram](/backend/knowledge-cards/histogram/)
- error rate
- [SLI / SLO](/backend/knowledge-cards/sli-slo/) / [error budget](/backend/knowledge-cards/error-budget/)

## 判讀訊號

- 用 average 而非 percentile 追 latency、p99 失真
- counter / gauge 混用、計算公式錯
- histogram bucket 沒對齊實際分佈、tail latency 被截斷
- error rate 分母不穩（流量低時誤觸發、高時稀釋）
- 商業 SLI 跟 metric 對不上、靠人解釋

## 交接路由

- 04.6 SLI/SLO 訊號設計：把 metric 升級為 user-journey SLI
- 04.7 cardinality / cost：label 治理與成本邊界
- 04.9 continuous profiling：metrics 之外的第四角觀測訊號
