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

## 判讀訊號

- workload 是合成的、跟 production traffic shape 不同
- 壓測通過但 production peak 失敗、模型未涵蓋實際模式
- 只測 throughput、不測 saturation 與 cost curve
- bottleneck 識別靠經驗、無系統定位流程
- capacity 規劃靠一次性 load test 結論、無持續對齊

## 交接路由

- 06.9 capacity / cost：load test 餵給容量規劃輸入
- 06.13 perf regression gate：load baseline 升級為持續 gate
