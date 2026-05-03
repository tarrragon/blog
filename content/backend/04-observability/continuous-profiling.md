---
title: "4.9 Continuous Profiling"
date: 2026-05-01
description: "把 CPU / memory / lock profile 從一次性除錯升級為持續訊號"
weight: 9
---

## 大綱

- continuous profiling 的定位：metrics / logs / traces 之外的第四角
- 採樣方式：[sampling](/backend/knowledge-cards/sampling/) profiler、eBPF based、language runtime 內建
- profile 維度：CPU、heap、allocations、lock contention、goroutine / async task
- flame graph 與差異比較：版本間 / canary 對照
- 跟 [4.2 metrics](/backend/04-observability/metrics-basics/) 的分工：metrics 是聚合訊號、profile 是 callstack 級別
- 跟 [4.3 tracing](/backend/04-observability/tracing-context/) 的分工：trace 是 request 維度、profile 是 process 維度
- vendor 取捨：Pyroscope / Polar Signals / Datadog Profiler / Parca
- 反模式：profiling 只在生事故時才打開、production 採樣率為 0、profile 跟 deploy version 失聯

## 概念定位

Continuous profiling 是把 CPU、memory、allocation 與 lock contention 變成長期可比較的 production 訊號，責任是補上 metrics、logs、traces 看不到的 callstack 成本。

這一頁處理的是 process 層的持續觀測。metrics 會告訴你變慢，trace 會告訴你哪條 request 變慢，profile 會告訴你哪段程式碼正在消耗資源。

## 核心判讀

判讀 profiling 時，先看 profile 是否能按版本比較，再看 overhead 是否能常駐承受。

重點訊號包括：

- profile 是否帶有 service、version、environment 與 deploy label
- flame graph diff 是否能對照 canary / baseline
- CPU、heap、lock、allocation 是否覆蓋主要退化模式
- production sampling 是否足夠低成本且足夠穩定

## 判讀訊號

- 同一段熱點程式碼反覆出現在事故 [RCA](/backend/knowledge-cards/rca/) 中、無 baseline profile
- CPU / memory 異常時靠重現除錯、無 production profile 可對照
- 版本升級後 latency 退化、定位具體 callstack 需要重現環境
- profile 跟 commit / version label 失聯、跨版本 diff 需要人工對照
- profiling overhead 過高、production 環境常駐成本過高

## 交接路由

- 04.7 cardinality / cost：profile 儲存量與保留策略
- 06.13 performance regression gate：profile diff 作為 gate 條件
- 08.5 [post-incident review](/backend/knowledge-cards/post-incident-review/)：[RCA](/backend/knowledge-cards/rca/) 引用 profile flame graph
