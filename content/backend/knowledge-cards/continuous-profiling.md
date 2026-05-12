---
title: "Continuous Profiling"
date: 2026-05-12
description: "在 production 持續取得低 overhead profile 的觀察方法"
weight: 237
---

Continuous profiling 的核心概念是「production 持續取 profile（通常 1% 取樣 CPU / heap / lock）、不是事件型才開」。讓 [profile diff](/backend/knowledge-cards/profile-diff/) 隨時可做、不必等下次 incident 才補資料。可先對照 [Profile Diff](/backend/knowledge-cards/profile-diff/)。

## 概念位置

Continuous profiling 工具：Datadog Continuous Profiler、Pyroscope（開源 + Grafana 整合）、Parca（CNCF）、GCP Cloud Profiler、Azure Application Insights Profiler、AWS CodeGuru Profiler。Overhead 通常 < 1% CPU、放心開在 production。要跟 distributed tracing 整合（trace → span → profile）。可先對照 [Profile Diff](/backend/knowledge-cards/profile-diff/)。

## 可觀察訊號與例子

需要 continuous profiling 的訊號是「latency 退化常找不到原因、靠事後重現很慢」。對應案例：[Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) production-level profiling 釋放 DBA 工程資源；[Tubi](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) ML feature store latency 改善靠 profile 定位 hot path。

## 設計責任

Continuous profiling 的關鍵是 *資料分段儲存* — 按 service / version / region 切、不要混在一個 timeline。flame graph 要可以「跳到任意時間點」對比。跟 [profile diff](/backend/knowledge-cards/profile-diff/) 流程整合：每次 deploy 後自動對比 baseline、退化幅度過門檻 trigger alert。
