---
title: "6.2 load test"
date: 2026-04-23
description: "整理 workload model、throughput 與 latency 基準"
weight: 2
---

## 大綱

- workload model
- [throughput](/backend/knowledge-cards/throughput/) / latency
- bottleneck
- capacity planning

## 概念定位

[Load test](/backend/knowledge-cards/load-test/) 是把真實 workload model 變成可重播的壓力情境，責任是找出系統在不同負載下的吞吐、延遲與瓶頸轉折點。

這一頁關心的是實際流量長什麼樣，不是把數字推高而已。模型若不接近 production shape，壓測結果就只是在驗證假場景。

## 核心判讀

判讀 load test 時，先看模型是否貼近流量結構，再看系統在 saturation 前後的行為。真正重要的不是單點 throughput，而是曲線如何變形。

重點訊號包括：

- workload 是否包含尖峰、長尾與不同 cohort
- latency 是否在接近飽和時快速劣化
- bottleneck 是否能被定位到具體 resource
- load 結果是否能回寫到 capacity planning

## 案例對照

- [Shopify](/backend/06-reliability/cases/shopify/_index.md)：高峰型流量要求 load model 能涵蓋短時間爆量。
- [LinkedIn](/backend/06-reliability/cases/linkedin/_index.md)：大型互動流量需要把不同讀寫模式分開量測。
- [Amazon](/backend/06-reliability/cases/amazon/_index.md)：容量與成本要一起看，不能只看 peak throughput。

## 下一步路由

- 06.9 capacity / cost：load test 作為容量輸入
- 06.13 perf regression gate：把 load baseline 變成持續 gate
- 06.18 reliability metrics：把流量與可靠性指標接起來

## 判讀訊號

- workload 是合成的、跟 production traffic shape 不同
- 壓測通過但 production peak 失敗、模型未涵蓋實際模式
- 只測 throughput、不測 saturation 與 cost curve
- bottleneck 識別靠經驗、無系統定位流程
- capacity 規劃靠一次性 load test 結論、無持續對齊

## 交接路由

- 06.9 capacity / cost：load test 餵給容量規劃輸入
- 06.13 perf regression gate：load baseline 升級為持續 gate
