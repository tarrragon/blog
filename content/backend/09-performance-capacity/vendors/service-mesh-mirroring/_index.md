---
title: "Service Mesh Mirroring"
date: 2026-05-15
description: "用 sidecar / proxy 層 mirror production traffic 到新版本或 shadow service 的 production validation 方式"
weight: 21
tags: ["backend", "performance", "capacity", "vendor", "service-mesh", "traffic-mirroring"]
---

Service mesh mirroring 的核心責任是在 proxy 層複製 production traffic 到 shadow service，讓新版本接受真實請求形狀，同時把使用者回應留在原本路徑。它適合已經落地 Istio、Linkerd 或類似 mesh 的平台，重點在用 routing policy 控制 mirror ratio、target、隔離與觀測。

跟 [GoReplay](/backend/09-performance-capacity/vendors/goreplay/) 比、Service Mesh Mirroring 在 *proxy / sidecar* 層、是 K8s mesh-native 的 L7 HTTP request mirror、不需要 application 或 host 端 capture binary；GoReplay 在 *application host* 層、適合無 mesh 的環境或要 capture artifact 離線 replay。跟 [AWS VPC Traffic Mirroring](/backend/09-performance-capacity/vendors/aws-vpc-traffic-mirroring/) 比、Service Mesh Mirroring 在 L7（HTTP route / header / subset 可控）、VPC Traffic Mirroring 在 L3-L4 packet 層、見度更底層但缺 application 語意。三者組合常見於 K8s + 多 cloud 混合環境。

## 最短判讀路徑

判斷 Service Mesh Mirroring 部署是否健康、最少看四件事：

- **Mesh implementation 對齊**：用哪套 mesh（Istio / Linkerd / Envoy gateway / Consul Connect）、control plane 版本、sidecar injection coverage、跨 namespace policy 邊界是否清楚
- **VirtualService mirror config**：mirror destination 是否限制在同 namespace / 同 cluster、mirror_percent 是否從 1% 漸進、route / header filter 是否排除 write-heavy 或 PII path
- **Target service capacity**：shadow target deployment 是否有獨立 HPA、跟 primary 同 node pool 還是隔離、DB / cache / external API 是否導 mock 或 sandbox、不會 share connection pool 造成 primary 飽和
- **Response handling**：mirrored response 是 fire-and-forget（Istio 預設）還是有 logging、shadow 端是否能辨識 mirrored request（`X-Envoy-Internal` / custom header）、side effect（payment / notification / webhook）是否走 dry-run

四件事任一缺失、就是 [9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/) shadow traffic 治理的待補項目。

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

## 進階主題

**Istio VirtualService mirror / mirror_percent**：Istio 用 `VirtualService` 的 `mirror` 欄位指定 shadow destination、`mirrorPercentage`（v1.7+；舊版 `mirror_percent`）控制比例。production 操作慣例是從 1% 起步、每 30-60min 觀察 shadow target latency / error / saturation 再放大、達到 100% 後維持一週收 evidence 才 promote。route-level config 比 mesh-wide policy 安全、blast radius 限定在指定 host / path。

**Linkerd traffic split**：Linkerd 用 SMI `TrafficSplit` CRD 或 native `HTTPRoute` 分流、走 *active-active* shadow 模式而非 fire-and-forget。Linkerd mirror 預設較輕量、proxy overhead 比 Istio 低、適合資源敏感的 K8s cluster；但 L7 policy 表達力不如 Istio EnvoyFilter。

**Envoy MirrorPolicy**：直接寫 Envoy config（不透過 Istio control plane）時、`route.RouteAction.request_mirror_policies` 是底層 primitive。多 cluster 邊緣 gateway（Contour / Emissary-Ingress / Gloo）都是這層的 abstraction、適合不想引入 full Istio 但要 mirror 能力的場景。

**跟 Argo Rollouts canary 整合 — shadow deployment**：Argo Rollouts 的 `analysis` step 可以接 mesh mirror — *shadow stage* 先用 mirror 收 evidence、*canary stage* 才放真實流量。對應 [9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/) 的「shadow 先於 canary」原則、避免把使用者當小白鼠。

**跟 [Datadog](/backend/04-observability/vendors/datadog/) APM trace correlation**：mirrored request 應該有獨立的 trace tag（`env:shadow` 或 `traffic.mirror:true`）、讓 Datadog APM / [observability stack](/backend/04-observability/) 能 filter 出 shadow path 的 p95 / error rate、不混入 primary SLO dashboard。trace propagation header 要保留、否則 distributed trace 斷在 mesh 邊界。

## 排錯與失敗快速判讀

- **Mirror target capacity 不足 / shadow service OOM**：shadow deployment 沒獨立 HPA、跟 primary 共用 node pool — 拆 node pool、shadow 設獨立 resource request、mirror_percent 從 1% 起步
- **Mirrored response 漏處理（fire-and-forget 副作用）**：Istio 預設丟棄 mirrored response、shadow 端的 error 沒被 collect — shadow service 自己 emit metric / log、不依賴 mirror response、加 `X-Shadow-Request` header 讓 shadow 端可辨識並走 dry-run 路徑
- **PII / sensitive data 進 staging**：mirrored request 帶真實 user token / payment info 打到 staging — header / body filter 走 EnvoyFilter 做 PII redaction、或在 mesh 邊界跑 [data masking proxy](/backend/07-security-data-protection/) 再 mirror
- **Side effect 真的發生（payment double charge / notification 真寄）**：shadow service 沒辨識 mirrored request 就走正式邏輯 — 強制 shadow 端用 sandbox credential、external API client 走 mock / dry-run mode、write 改 read-only replica
- **Mesh control plane 飽和 / mirror policy drift**：mirror rule 散落各 namespace 沒 owner、policy version 不一致 — 走 GitOps（Argo CD / Flux）+ policy as code、定期 audit `kubectl get virtualservice -A`
- **Cross-cluster mirror blast radius 失控**：mirror destination 指向其他 cluster 導致跨 cluster 流量爆增 — mirror destination 限 same-cluster、跨 cluster 要走獨立的 gateway 並設 quota
- **Shadow trace 混進 SLO dashboard**：APM 沒分 primary / shadow tag、p95 看起來變差但其實是 shadow 拖累 — trace tag `env:shadow` 強制、observability dashboard filter

## 何時改走其他服務

| 需求形狀                                      | 改走                                                                                                              |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 無 mesh 環境 / 要 capture artifact 離線重播   | [GoReplay](/backend/09-performance-capacity/vendors/goreplay/)                                                    |
| L3-L4 packet 層分析（IDS / network forensic） | [AWS VPC Traffic Mirroring](/backend/09-performance-capacity/vendors/aws-vpc-traffic-mirroring/)                  |
| 合成負載 / load test 而非 production mirror   | [k6](/backend/09-performance-capacity/vendors/k6/) / [Gatling](/backend/09-performance-capacity/vendors/gatling/) |
| Production-side 整體治理                      | [9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/)                              |

## 不在本頁內的主題

- Istio / Linkerd / Envoy 完整 install / 升級 / control plane HA 細節
- Service mesh 安全模型（mTLS / SPIFFE / authorization policy）— 屬 [7 security](/backend/07-security-data-protection/) 邊界
- Mesh-level retry / timeout / circuit breaker 等 resilience pattern
- Multi-cluster mesh federation（Istio multi-primary、Linkerd multicluster）

## 案例回寫

Service mesh mirroring 適合回寫平台遷移與新版本 shadow validation 案例。它可接 [Miro managed EKS migration](/backend/05-deployment-platform/cases/miro-managed-eks-migration/)、[Tradeshift self-managed K8s to EKS](/backend/05-deployment-platform/cases/tradeshift-self-managed-k8s-to-eks/)、[9.C28 FanDuel 雙峰 workload](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) 的逐步驗證需求、[9.C12 Riot Games 246 EKS cluster](/backend/09-performance-capacity/cases/riot-games-eks-multi-cluster/) 的 single-tenant per game 跨 cluster 流量 shadow，以及 [9.C7 Lyft 100+ 微服務](/backend/09-performance-capacity/cases/lyft-microservice-eight-x-peak/) 跨服務的 mirror 範圍治理。

這些案例的重點是 routing policy 與 blast radius。Service mesh mirroring 頁引用案例時，要把 case 轉成 route、mirror ratio、target subset、dependency isolation 與 abort condition — 例如 Riot Games 的 single-tenant 模式下、mirror policy 必須限制在 *同遊戲* cluster 內、不能跨 game 否則 blast radius 失控。

## 下一步路由

- 上游：[9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/)
- 上游：[5.6 Traffic, Config and Control Plane Boundary](/backend/05-deployment-platform/traffic-config-control-plane-boundary/)
- 平行：[GoReplay](/backend/09-performance-capacity/vendors/goreplay/)
- 平行：[AWS VPC Traffic Mirroring](/backend/09-performance-capacity/vendors/aws-vpc-traffic-mirroring/)
- 知識卡：[Shadow Traffic](/backend/knowledge-cards/shadow-traffic/)
