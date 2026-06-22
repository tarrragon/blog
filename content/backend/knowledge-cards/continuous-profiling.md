---
title: "Continuous Profiling"
date: 2026-06-22
description: "在 production 持續取得低 overhead profile 的觀察方法"
weight: 237
tags: ["backend", "observability"]
---

Continuous profiling 的核心概念是「在 production 持續以低 overhead 採集 CPU / heap / lock profile，讓 baseline 隨時可用、不需要等事故才開 profiler」。

## 概念位置

Continuous profiling 是 [metrics](/backend/knowledge-cards/metrics/)、[log](/backend/knowledge-cards/log/)、[trace](/backend/knowledge-cards/trace/) 之外的第四角觀測訊號。Metrics 告訴你「CPU usage 上升了」，trace 告訴你「某條 request 變慢」，profile 告訴你「變慢的那段程式碼是哪幾個 function call」。Profile 是唯一能精確到 callstack level 的觀測訊號。

Always-on 的核心價值是 baseline — 事故時跟 baseline 做 diff（flame graph diff），看「哪些 function 的 CPU 消耗跟平時不同」。

## 使用情境

需要 continuous profiling 的訊號是「latency 退化常找不到原因、靠事後重現很慢」或「同一段 hot path 反覆出現在事故 RCA 中但缺 baseline 資料」。版本升級後 latency 退化時，profile diff 能直接定位是哪個 function 變慢。

## 設計責任

Overhead 控制是 continuous profiling 可行性的前提 — CPU overhead < 1%、memory overhead < 10MB。eBPF-based profiler（Parca、Pyroscope eBPF）在 kernel 層採集、overhead 最低；language runtime 內建（Go pprof、Java JFR）居中。Profile 資料要帶 service / version / region label，讓跨版本 diff 跟 canary 對照可行。完整設計見 [4.9 continuous profiling](/backend/04-observability/continuous-profiling/)。
