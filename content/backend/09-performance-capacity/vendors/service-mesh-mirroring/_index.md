---
title: "Service Mesh Mirroring"
date: 2026-05-15
description: "用 sidecar / proxy 層 mirror production traffic 到新版本或 shadow service 的 production validation 方式"
weight: 21
tags: ["backend", "performance", "capacity", "vendor", "service-mesh", "traffic-mirroring"]
---

Service mesh mirroring 的核心責任是在 proxy 層複製 production traffic 到 shadow service，讓新版本接受真實請求形狀，同時把使用者回應留在原本路徑。它適合已經落地 Istio、Linkerd 或類似 mesh 的平台，重點在用 routing policy 控制 mirror ratio、target、隔離與觀測。

## 定位

Service mesh mirroring 適合平台已經有 proxy control plane 的團隊。當 service-to-service traffic 都經過 sidecar 或 gateway，mirror policy 可以把部分 production request 複製到新版本，不需要在 application code 中加 capture / replay 邏輯。

這個定位讓 service mesh mirroring 接到 [9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/) 的 shadow traffic 與 canary perf check。它比 host capture 更貼近 service routing，但也依賴 mesh 的觀測、policy、資源隔離與治理能力。

## 適用場景

新版本 shadow validation 適合 service mesh mirroring。平台可以把 1%、5% 或特定 route 的流量 mirror 到 shadow deployment，觀察新版本 CPU、memory、latency、DB read 與 error。

Service-to-service migration 適合 service mesh mirroring。當下游服務準備換 runtime、framework、DB client 或 cache client，mirror 可以讓新路徑吃到 production upstream pattern。

多 region / 多 version 對照適合 service mesh mirroring。Mesh policy 能按 namespace、host、route、header 或 subset 控制 mirror target，讓平台在小 blast radius 下收集 production-shaped evidence。

## 選型判準

| 判準               | Service mesh mirroring 的價值               | 需要補的能力                        |
| ------------------ | ------------------------------------------- | ----------------------------------- |
| Proxy 層控制       | mirror policy 不侵入 application code       | mesh control plane 治理與變更審核   |
| Service routing    | 可按 host、route、subset 控制 target        | route 命名、ownership、policy drift |
| Mesh observability | request metric、trace、service graph 可對照 | shadow target 的獨立 dashboard      |
| 漸進比例           | mirror ratio 可逐步放大                     | 下游容量與 stop condition           |

Proxy 層控制價值來自一致性。當所有 service 都走 mesh，mirror policy 可以用同一套控制面管理，避免每個 application 自行實作 replay。

Mesh observability 價值來自對照能力。Shadow service 的 latency、error、resource saturation 與 dependency call 可以直接跟 primary path 對比，但 dashboard 要清楚標記 mirrored traffic，避免混入正式 SLO。

## 跟其他方式的取捨

Service mesh mirroring 和 GoReplay 的主要差異是控制面。Service mesh mirroring 依賴既有 proxy / mesh，適合服務間流量；GoReplay 適合 HTTP capture artifact、離線 replay 與沒有 mesh 的環境。

Service mesh mirroring 和 AWS VPC Traffic Mirroring 的主要差異是語意層級。Mesh 在 L7 routing 層，能按 route、host、header 與 subset 控制；VPC mirroring 在網路層，能見度更底層但應用語意控制較少。

Service mesh mirroring 和 canary 的主要差異是使用者影響。Mirrored request 的回應不回給使用者，適合 capacity / correctness observation；canary 會讓真實使用者走新版本，適合最終放量。

## 操作成本

Service mesh mirroring 的主要成本是下游容量。Shadow traffic 雖然不回應使用者，但仍會消耗 shadow service、DB、cache、third-party mock、queue 與 observability pipeline 的資源。

Policy 成本來自控制面治理。Mirror rule、route、subset、namespace、owner 與 rollout window 都要可審查；錯誤的 mirror policy 可能把過大比例流量導到未準備好的 target。

Side effect 成本來自 application 行為。Shadow service 要能辨識 mirrored request，並把 write、external API call、notification、payment 與 queue publish 導到 sandbox、mock 或 dry-run。

## Evidence Package

Service mesh mirroring 結果應回寫到 evidence package。最小欄位包括 mesh policy version、source service、route、mirror ratio、target subset、time range、shadow target resource、data / side effect isolation、p95 / p99、error rate、dependency saturation、known gap 與 owner。

| 欄位         | Service mesh mirroring 證據來源                  |
| ------------ | ------------------------------------------------ |
| Source       | mesh policy、route config、deployment version    |
| Time range   | mirror start / end                               |
| Query link   | service graph、metrics、trace、logs              |
| Data quality | mirror ratio、route coverage、header filter      |
| Confidence   | target parity、dependency isolation              |
| Known gap    | 未 mirror route、side effect mock、mesh overhead |

Evidence package 的核心用途是讓 mirror 實驗可關閉。Reviewer 要能看到 mirror policy 何時啟動、何時停止、覆蓋哪些 route、消耗哪些下游資源，以及 shadow target 是否接近 production。

## 案例回寫

Service mesh mirroring 適合回寫平台遷移與新版本 shadow validation 案例。它可接 [Miro managed EKS migration](/backend/05-deployment-platform/cases/miro-managed-eks-migration/)、[Tradeshift self-managed K8s to EKS](/backend/05-deployment-platform/cases/tradeshift-self-managed-k8s-to-eks/) 與 [FanDuel dual peak](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) 的逐步驗證需求。

這些案例的重點是 routing policy 與 blast radius。Service mesh mirroring 頁引用案例時，要把 case 轉成 route、mirror ratio、target subset、dependency isolation 與 abort condition。

## 下一步路由

- 上游：[9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/)
- 上游：[5.6 Traffic, Config and Control Plane Boundary](/backend/05-deployment-platform/traffic-config-control-plane-boundary/)
- 平行：[GoReplay](/backend/09-performance-capacity/vendors/goreplay/)
- 平行：[AWS VPC Traffic Mirroring](/backend/09-performance-capacity/vendors/aws-vpc-traffic-mirroring/)
- 知識卡：[Shadow Traffic](/backend/knowledge-cards/shadow-traffic/)
