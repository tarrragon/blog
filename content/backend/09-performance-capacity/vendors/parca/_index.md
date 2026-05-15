---
title: "Parca"
date: 2026-05-15
description: "用 eBPF 與開源 continuous profiling 平台建立 infrastructure-wide profile evidence 的工具"
weight: 32
tags: ["backend", "performance", "capacity", "vendor", "parca", "profiling"]
---

Parca 的核心責任是用開源 continuous profiling 與 eBPF 路線建立 infrastructure-wide profile evidence。它適合需要低侵入、跨 process、跨 service、偏平台層的 profiling 團隊，重點在用 always-on profile 找出 CPU、memory、runtime 與 kernel / user space 的資源熱點。

## 定位

Parca 適合平台團隊建立 profiling control plane。當問題橫跨 Kubernetes cluster、node pool、multi-service path 或 shared runtime 成本，Parca 能從更接近 infrastructure 的角度收集 profile。

這個定位讓 Parca 接到 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/) 與 [4.9 Continuous Profiling](/backend/04-observability/continuous-profiling/)。它的價值在於低侵入與平台廣度；它的代價在於 eBPF 支援、symbolization、storage、權限與平台維運責任。

## 適用場景

Infrastructure-wide profiling 適合 Parca。平台團隊可以觀察 cluster、node、namespace、service 與 process 的 CPU 熱點，找出共同 library、runtime、sidecar、agent 或 kernel path 的成本。

Kubernetes 平台適合 Parca。當服務在多 namespace、多 workload、多 node pool 上運作，Parca 可以把 profile 維度接到 pod、container、node、namespace 與 label。

低侵入 profiling 適合 Parca。eBPF-based profiling 可以降低 application instrumentation 成本，讓團隊先取得廣域視角，再對特定服務加更細的 runtime profiler 或 APM 整合。

## 選型判準

| 判準                | Parca 的價值                        | 需要補的能力                             |
| ------------------- | ----------------------------------- | ---------------------------------------- |
| eBPF / low overhead | 低侵入取得廣域 profile              | kernel / runtime 支援與權限治理          |
| Platform-wide       | node、namespace、service 維度可對照 | Kubernetes label 與 ownership discipline |
| Open source         | profiling platform 可自管           | storage、retention、upgrade              |
| Compare / diff      | profile compare 支援退化定位        | deploy label、baseline 與 symbolization  |

eBPF / low overhead 價值來自平台廣度。團隊可以先觀察整個基礎設施的 CPU 熱點，再決定哪些服務需要更深入的 application-level profiling。

Platform-wide 價值來自共同成本治理。Sidecar、agent、logging library、serialization library 或 runtime upgrade 的成本可能散在多個服務中，Parca 這類工具能把分散成本聚合回平台決策。

## 跟其他工具的取捨

Parca 和 Datadog Continuous Profiler 的主要差異是平台模型。Parca 偏開源、自管、eBPF 與 infra-wide profiling；Datadog 偏 SaaS、APM drilldown、deployment marker 與產品化 workflow。

Parca 和 Pyroscope 的主要差異是視角。Pyroscope 偏 Grafana / application profiling backend；Parca 偏 eBPF、Kubernetes / infrastructure-level profiling 與平台團隊治理。

Parca 和 language runtime profiler 的主要差異是導入方式。Runtime profiler 能提供語言特定維度；Parca 能先提供低侵入廣域 profile，但 symbolization 與語言細節需要額外治理。

## 操作成本

Parca 的主要成本是平台維運。Agent / scraper、server、storage、retention、symbolization、upgrade 與 Kubernetes 權限都需要平台團隊負責。

Symbolization 成本來自可讀性。Profile 如果缺 symbol、debug info、build ID 或 source mapping，flame graph 會變成難以行動的 address / binary offset，因此 build pipeline 要保留符號資訊策略。

權限成本來自 eBPF 與 node visibility。低層 profiling 需要足夠 host / kernel 權限，受管 Kubernetes、security policy、multi-tenant cluster 與 compliance 要先評估。

## Evidence Package

Parca 結果應回寫到 evidence package。最小欄位包括 cluster、namespace、service、node pool、profile type、baseline window、candidate window、compare link、symbolization status、agent overhead、known gap 與 owner。

| 欄位         | Parca 證據來源                           |
| ------------ | ---------------------------------------- |
| Source       | Parca query、compare view、flame graph   |
| Time range   | baseline / candidate profile window      |
| Query link   | Parca UI / dashboard / metrics link      |
| Data quality | label completeness、symbolization status |
| Confidence   | cluster coverage、agent overhead         |
| Known gap    | 未覆蓋 node、symbol 缺失、kernel 限制    |

Evidence package 的核心用途是把平台層 profile 變成容量決策。Reviewer 要能看到成本來自 application code、runtime、sidecar、kernel path 還是 shared library，並把結果回寫到 owner。

## 案例回寫

Parca 適合回寫平台層與 multi-service 成本案例。它可接 [GCP 130K node GKE cluster](/backend/09-performance-capacity/cases/gcp-130k-node-gke-cluster/) 的 cluster-scale profiling 需求、[Riot Games EKS multi-cluster](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) 的平台成本治理，以及 [Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 的 shared platform noise 降低。

這些案例的重點是平台視角。Parca 頁引用案例時，要把 case 轉成 cluster / namespace / service label、compare window、symbolization、shared library cost 與 owner routing。

## 下一步路由

- 上游：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)
- 上游：[9.9 Performance Improvement Loop](/backend/09-performance-capacity/improvement-loop/)
- 跨模組：[4.9 Continuous Profiling](/backend/04-observability/continuous-profiling/)
- 平行：[Datadog Continuous Profiler](/backend/09-performance-capacity/vendors/datadog-continuous-profiler/)
- 平行：[Pyroscope](/backend/09-performance-capacity/vendors/pyroscope/)
- 官方：[Parca documentation](https://www.parca.dev/docs/)
