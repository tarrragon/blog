---
title: "4.2 metrics 與 SLI/SLO"
date: 2026-04-23
description: "整理 counter、gauge、histogram 與服務健康指標"
weight: 2
---

## 大綱

- [metrics](/backend/knowledge-cards/metrics/) 基本型別
- latency [histogram](/backend/knowledge-cards/histogram/)
- error rate / [throughput](/backend/knowledge-cards/throughput/)
- [SLI / SLO](/backend/knowledge-cards/sli-slo/) / [error budget](/backend/knowledge-cards/error-budget/)

## 概念定位

[metrics](/backend/knowledge-cards/metrics/) 是把服務狀態壓縮成可聚合、可比較、可告警的時間序列，責任是讓團隊看見趨勢、容量與服務健康。

這一頁處理的是 metric 型別與計算語意。counter、gauge 與 [histogram](/backend/knowledge-cards/histogram/) 各自回答不同問題；選錯型別會讓後面的 SLI、dashboard 與 alert 都建立在錯誤訊號上。

## 核心判讀

判讀 metrics 時，先看指標型別是否對應問題，再看分母、bucket 與 label 是否穩定。

重點訊號包括：

- latency 是否用 [percentile](/backend/knowledge-cards/percentile/) / [histogram](/backend/knowledge-cards/histogram/) 補足 average 的盲點
- error rate 的分母是否能代表真實請求量
- bucket 是否覆蓋實際尾端延遲
- label 是否能切出必要維度，同時不讓 [metric cardinality](/backend/knowledge-cards/metric-cardinality/) 失控

## 判讀訊號

- 用 average 而非 percentile 追 latency、p99 失真
- counter / gauge 混用、計算公式錯
- histogram bucket 沒對齊實際分佈、tail latency 被截斷
- error rate 分母不穩（流量低時誤觸發、高時稀釋）
- 商業 SLI 跟 metric 對不上、靠人解釋

## 交接路由

- 04.6 SLI/SLO 訊號設計：把 metric 升級為 user-journey SLI
- 04.7 [metric cardinality](/backend/knowledge-cards/metric-cardinality/) / cost：label 治理與成本邊界
- 04.9 continuous profiling：metrics 之外的第四角觀測訊號
