---
title: "4.9 Continuous Profiling"
date: 2026-05-01
description: "把 CPU / memory / lock profile 從一次性除錯升級為持續訊號"
weight: 9
---

## 大綱

- continuous profiling 的定位：metrics / logs / traces 之外的第四角
- 採樣方式：sampling profiler、eBPF based、language runtime 內建
- profile 維度：CPU、heap、allocations、lock contention、goroutine / async task
- flame graph 與差異比較：版本間 / canary 對照
- 跟 [4.2 metrics](/backend/04-observability/metrics-basics/) 的分工：metrics 是聚合訊號、profile 是 callstack 級別
- 跟 [4.3 tracing](/backend/04-observability/tracing-context/) 的分工：trace 是 request 維度、profile 是 process 維度
- vendor 取捨：Pyroscope / Polar Signals / Datadog Profiler / Parca
- 反模式：profiling 只在生事故時才打開、production 採樣率為 0、profile 跟 deploy version 失聯

## 判讀訊號

- 同一段熱點程式碼反覆出現在事故 RCA 中、無 baseline profile
- CPU / memory 異常時靠重現除錯、無 production profile 可對照
- 版本升級後 latency 退化、無法定位到具體 callstack
- profile 跟 commit / version label 失聯、無法跨版本 diff
- profiling overhead 過高、production 環境無法常駐

## 交接路由

- 04.7 cardinality / cost：profile 儲存量與保留策略
- 06.13 performance regression gate：profile diff 作為 gate 條件
- 08.5 postmortem：RCA 引用 profile flame graph
