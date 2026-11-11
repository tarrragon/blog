---
title: "Continuous Profiling"
date: 2026-06-22
description: "在 production 持續取得低 overhead profile 的觀察方法"
weight: 238
tags: ["backend", "observability"]
---

Continuous profiling 的核心概念是「在 production 持續以低 overhead 採集 CPU / heap / lock profile，讓 baseline 隨時可用、不需要等事故才開 profiler」。它是 [metrics](/backend/knowledge-cards/metrics/)、[trace](/backend/knowledge-cards/trace/) 之外能精確到 callstack level 的觀測訊號。

## 跟其他概念的關係

Continuous profiling 是 [metrics](/backend/knowledge-cards/metrics/)、[log](/backend/knowledge-cards/log/)、[trace](/backend/knowledge-cards/trace/) 之外的第四角觀測訊號。Metrics 告訴你「CPU usage 上升了」，trace 告訴你「某條 request 變慢」，profile 告訴你「變慢的那段程式碼是哪幾個 function call」。Profile 是唯一能精確到 callstack level 的觀測訊號。

Always-on 的核心價值是 baseline — 事故時跟 baseline 做 diff（flame graph diff），看「哪些 function 的 CPU 消耗跟平時不同」。

## 使用情境

需要 continuous profiling 的訊號是「latency 退化常找不到原因、靠事後重現很慢」或「同一段 hot path 反覆出現在事故 RCA 中但缺 baseline 資料」。版本升級後 latency 退化時，profile diff 能直接定位是哪個 function 變慢。

## 判斷條件與後果

Continuous profiling 能否在 production 常駐，取決於 overhead：CPU overhead 在 1% 以內、memory overhead 在 10MB 以內時，它可以一直開著累積 baseline；超過時，常駐的成本本身就影響服務，profiler 只能在事故時才開，事故時也就沒有 baseline 可以 diff。採集方式決定 overhead 的高低：eBPF-based profiler（Parca、Pyroscope eBPF）在 kernel 層採集，overhead 最低；language runtime 內建的（Go pprof、Java JFR）居中。Profile 資料沒有帶 service、version、region label 時，事故時找不到對應版本的 baseline，跨版本的 flame graph diff 與 canary 對照都做不了。完整設計見 [4.9 continuous profiling](/backend/04-observability/continuous-profiling/)。
