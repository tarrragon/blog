---
title: "Parca"
date: 2026-05-15
description: "用 eBPF 與開源 continuous profiling 平台建立 infrastructure-wide profile evidence 的工具"
weight: 32
tags: ["backend", "performance", "capacity", "vendor", "parca", "profiling"]
---

Parca 的核心責任是用開源 continuous profiling 與 eBPF 路線建立 infrastructure-wide profile evidence。它適合需要低侵入、跨 process、跨 service、偏平台層的 profiling 團隊，重點在用 always-on profile 找出 CPU、memory、runtime 與 kernel / user space 的資源熱點。

## 服務定位

Parca 是 Polar Signals 主導的 OSS continuous profiling、特色是 *eBPF-based 採集 + pprof 標準格式 + Prometheus-style 拉取與 label 模型*。它跟 [Pyroscope](/backend/09-performance-capacity/vendors/pyroscope/) 是 OSS 同類、跟 [Datadog Continuous Profiler](/backend/09-performance-capacity/vendors/datadog-continuous-profiler/) 則是 OSS / 自管 vs SaaS / APM 整合的差異。eBPF agent 直接從 kernel 採 stack trace、不需要 application 改 code 或注入 runtime agent；pprof 格式讓既有 Go / Java / Python 工具鏈可以直接讀；Prometheus-style scrape 讓 Parca server 跟 metrics 用同一套 service discovery 與 label。

## 最短判讀路徑

判斷 Parca 部署是否能撐起 platform-wide profiling、最少看四件事：

- **eBPF agent deploy**：Parca Agent 走 DaemonSet 跑在每個 node、需要 kernel ≥ 4.18（CO-RE / BTF）、`SYS_ADMIN` 或 `PERF_EVENT` capability、host PID namespace。受管 Kubernetes（GKE / EKS / AKS）的 worker node 是否允許這個權限是第一個判讀點
- **Parca server scrape**：server 跟 agent 走 pull-based、Prometheus-style ServiceMonitor / scrape config、label 跟 metrics 同模型（namespace / pod / container / node）。scrape interval、retention、storage backend（FrostDB 內建 / object storage）要明確
- **pprof query**：profile 以 pprof format 存、Parca UI 提供 flame graph 與 compare view、也可 export pprof file 給 `go tool pprof` 或其他既有工具離線分析
- **Grafana integration**：Parca 提供 datasource plugin、profile 可以跟 metrics / log / trace 在 Grafana 同一頁 correlate、配 [Pyroscope](/backend/09-performance-capacity/vendors/pyroscope/) 或 Tempo 形成 observability 對齊

四件事任一缺失、就是 profiling control plane 還沒上線的待補項目。

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

## 核心取捨表

| 取捨維度       | Parca                                | Pyroscope                            | Datadog Continuous Profiler           |
| -------------- | ------------------------------------ | ------------------------------------ | ------------------------------------- |
| 採集方式       | eBPF agent（kernel-level、unwound）  | eBPF + SDK 雙路、語言 SDK 較豐富     | APM agent 內建、語言 SDK 整合         |
| Profile format | pprof（Google 標準）                 | 自家 + pprof export                  | Datadog proprietary、可 export pprof  |
| 採集模型       | Pull-based、Prometheus-style scrape  | Push or pull（Grafana Agent）        | Push to Datadog backend               |
| Label 模型     | Prometheus label（namespace / pod）  | Grafana label                        | Datadog tag                           |
| 部署模型       | Self-hosted OSS + Polar Signals SaaS | Self-hosted OSS + Grafana Cloud SaaS | SaaS only                             |
| Storage        | FrostDB 內建 / object storage        | 自家 storage / Grafana backend       | Datadog managed                       |
| APM 整合       | 弱 — 走 Grafana correlation          | 中 — Grafana stack 整合              | 強 — trace ↔ profile drilldown 內建   |
| 適合場景       | Platform team 自管、Prometheus stack | Grafana stack 已用、應用層 profiling | 已用 Datadog、APM-first、SaaS-only 可 |

## 進階主題

**Polar Signals Cloud**：Parca 上游公司 Polar Signals 提供 managed SaaS — agent 一樣走 OSS、server / storage / UI 託管。適合不想養 Parca server 又要 OSS agent 路線的團隊。差異點是 ingestion cost 跟 retention 由 SaaS 計費、license / data residency 要看合約。

**Prometheus 同 label model**：Parca 的 service discovery、scrape config 跟 label 跟 Prometheus 幾乎同形 — 既有 ServiceMonitor、relabel rule、Kubernetes SD 可以直接複用。意義是 profile 維度跟 metric 維度天然對齊、`namespace=foo, service=bar` 在兩邊都成立、cross-signal correlation 不需要再 mapping。

**Compare profiles（diff before/after deploy）**：Parca UI 支援選 baseline window 跟 candidate window 做 flame graph diff、顏色標示哪個 stack frame 變胖變瘦。配 [9.9 Performance Improvement Loop](/backend/09-performance-capacity/improvement-loop/) 的 deploy marker、可以把「這次發版讓 CPU +15%」直接歸因到具體 frame。

**Continuous profiling vs sampling-only**：傳統 profiler 是「出問題時手動跑 30 秒」、Parca 是「always-on、低頻率持續採」。差異是 *事後回溯能力* — incident 發生時直接拉時間區間的 profile、不用重現問題；sampling-only 工具在偶發 spike 時抓不到現場。代價是 storage 跟 agent overhead 要長期治理。

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

## 排錯與失敗快速判讀

- **eBPF agent 起不來 / kernel 不支援**：舊 kernel（< 4.18）或缺 BTF / CO-RE 支援、受管 Kubernetes 不開 `SYS_ADMIN` — 先確認 node OS image、必要時換 distribution 或升級 worker node pool
- **Profile storage 暴增**：scrape interval 太密 + retention 沒設 + label cardinality 爆炸（把 request-id 放進 label）— 降頻、限 retention window、把高 cardinality 維度移出 profile label
- **Symbol resolution 失敗 / flame graph 全是 address**：build pipeline 沒保留 debug info、stripped binary、容器 image 不含符號 — 在 build 階段保留 debug symbol、用 separate debuginfo 上傳 Parca debuginfod、或在 image 保留 unstripped binary
- **JIT 語言（Java / Node.js）stack 不完整**：eBPF 看到的是 native frame、JIT-compiled frame 需要額外 perf map / JVMTI agent — 補語言層 profiler 或開 JIT symbol dump
- **Agent overhead 影響 production**：sample rate 預設 19 Hz、特定 workload 可能仍敏感 — 在 noisy neighbor 敏感的 node pool 降頻或排除特定 namespace
- **多 cluster scrape 中心化太重**：單一 Parca server 拉 N 個 cluster 變瓶頸 — 改 federation 模型、每 cluster 一個 Parca server、上層做 query aggregation

## 案例回寫

Parca 適合回寫平台層與 multi-service 成本案例。它可接 [9.C34 GCP 130K node GKE cluster](/backend/09-performance-capacity/cases/gcp-130k-node-gke-cluster/) 的 cluster-scale profiling 需求、[9.C12 Riot Games EKS multi-cluster](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) 的 246 cluster 平台成本治理、[9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 的 shared platform noise 降低、[9.C33 Maersk + Bosch Azure AKS](/backend/09-performance-capacity/cases/maersk-bosch-azure-aks/) 的傳統產業多 BU 平台層歸因，以及 [9.C19 Capcom DynamoDB + EKS](/backend/09-performance-capacity/cases/capcom-gaming-dynamodb-eks/) 跨遊戲共用後端的 profile 切分。

這些案例的重點是平台視角。Parca 頁引用案例時，要把 case 轉成 cluster / namespace / service label、compare window、symbolization、shared library cost 與 owner routing — 例如 GCP 130K-node 規模下，Parca 自身的 storage / scrape capacity 也成為 profile target、不只是觀測 application。

兩個典型用途值得單獨點名：

- **Performance regression detection**：發版前後拉 compare profile、把「這次 release 讓 P99 CPU +18%」歸因到具體 stack frame。配 [9.C12 Riot Games EKS multi-cluster](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) 的 246 cluster 規模、單一 service rollout 在 always-on profile 下可秒級看出 hot path 變化、不需要等 SRE 跑手動 pprof
- **Cost engineering**：把 CPU profile 折算成 node 成本、找出 shared library / runtime / sidecar 的 hidden cost。配 [9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 的 platform consolidation 思路、profile 證據可以決定要不要重寫熱點、換 library、還是接受成本

## 下一步路由

- 上游：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)
- 上游：[9.9 Performance Improvement Loop](/backend/09-performance-capacity/improvement-loop/)
- 跨模組：[4.9 Continuous Profiling](/backend/04-observability/continuous-profiling/)
- 平行：[Datadog Continuous Profiler](/backend/09-performance-capacity/vendors/datadog-continuous-profiler/)
- 平行：[Pyroscope](/backend/09-performance-capacity/vendors/pyroscope/)
- 官方：[Parca documentation](https://www.parca.dev/docs/)
