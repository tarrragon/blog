---
title: "Chaos Mesh"
date: 2026-05-01
description: "Kubernetes-native chaos engineering（CNCF incubating）"
weight: 7
tags: ["backend", "reliability", "vendor"]
---

Chaos Mesh 是 PingCAP 開源、CNCF incubating 的 Kubernetes-native chaos engineering 平台、承擔三個責任：CRD-driven fault injection（PodChaos / NetworkChaos / IOChaos / StressChaos）、Chaos Workflow（多步驟編排）、Chaos Dashboard 視覺化 + experiment scope 控制。設計取捨偏向「K8s-native + GitOps-friendly + multi-fault types」、適合 K8s 為主的 chaos engineering。

## 本章目標

讀完本章後、你應該能：

1. 部署 Chaos Mesh 到 K8s cluster
2. 設計 PodChaos / NetworkChaos / IOChaos experiment
3. 用 Chaos Workflow 編排多步驟實驗 + steady state probe
4. 控制 blast radius（namespace / labelSelector / mode）
5. 跟 [6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/) 對齊 chaos 實驗審批

## 最短路徑：5 分鐘把 Chaos Mesh 跑起來

```bash
# 1. 安裝
# TODO: curl -sSL https://mirrors.chaos-mesh.org/v2.7.0/install.sh | bash

# 2. 跑第一個 PodChaos
# TODO: 寫 podchaos.yaml、kubectl apply
# TODO: action: pod-kill / selector / mode

# 3. Dashboard
# TODO: kubectl port-forward svc/chaos-dashboard 2333:2333
```

## 日常操作與決策形狀

### CRD 設計

子議題：

- PodChaos：pod-kill / pod-failure / container-kill
- NetworkChaos：delay / loss / duplicate / corrupt / partition
- IOChaos：delay / errno / mistake / attrOverride
- StressChaos：CPU / memory pressure
- 對應 GitOps：Helm / Kustomize 管 experiment

### Chaos Workflow

子議題：

- 多步驟 chaos 編排（serial / parallel）
- Suspend / resume 控制
- Probe（steady state validation）
- 對應 [6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)

### Chaos Dashboard

子議題：

- 視覺化 experiment timeline
- Experiment archive
- Event log
- RBAC

## 進階主題（按需閱讀）

### Blast radius 控制

子議題：

- namespace 限制
- labelSelector / value mode（one / all / fixed / fixed-percent / random-max-percent）
- annotationSelector
- Pause / resume 緊急中止

### Schedule 與 GitOps

子議題：

- Schedule CRD 定期 chaos
- ArgoCD / Flux 整合
- Experiment as code review

### 跟 LitmusChaos / Gremlin 對比

子議題：

- Chaos Mesh：CRD-driven、PingCAP 主導
- LitmusChaos：ChaosHub experiment / CNCF graduated
- Gremlin：商業 SaaS、跨平台
- 選擇判讀：K8s OSS first → Chaos Mesh / Litmus；商業跨平台 → Gremlin

### Steady state 驗證

子議題：

- HTTP / TCP / Pod / podHTTPChaos
- Probe success threshold
- 跟 [9.13 SLO](/backend/09-performance-capacity/) 對應 burn rate

## 排錯快速判讀

### Experiment 沒生效

操作原則：先 `kubectl describe podchaos` 看 status、再看 webhook + RBAC。

### Blast radius 過大

操作原則：mode 設 all 或 percent 設太高、影響超出預期。預防：先 dry-run / staging 測試。

### Pause 不及時

操作原則：experiment running 中要 pause、不是 delete（delete 不會 cleanup state）。

### Dashboard 連不上

操作原則：service 沒暴露、RBAC 不對。

## 何時改走其他服務

| 需求形狀                  | 改走                                                                                                          |
| ------------------------- | ------------------------------------------------------------------------------------------------------------- |
| 非 K8s 環境               | [Gremlin](/backend/06-reliability/vendors/gremlin/) / [Toxiproxy](/backend/06-reliability/vendors/toxiproxy/) |
| AWS-native chaos          | AWS Fault Injection Service                                                                                   |
| K8s + ChaosHub experiment | [LitmusChaos](/backend/06-reliability/vendors/litmuschaos/)                                                   |
| Integration test 模擬故障 | [Toxiproxy](/backend/06-reliability/vendors/toxiproxy/)                                                       |
| 商業 + GameDay 設計       | [Gremlin](/backend/06-reliability/vendors/gremlin/)                                                           |

## 不在本頁內的主題

- 完整 CRD spec
- Chaos Mesh internal architecture
- 各 fault type 詳細 parameter

## 案例回寫

| 案例方向                                                                                                               | 對應主題                                                 |
| ---------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| [Netflix：Steady State、Chaos 與 FIT](/backend/06-reliability/cases/netflix/steady-state-chaos-and-fit/)               | steady state hypothesis 對應 Chaos Workflow Probe        |
| [Netflix：Business-Hours Guardrails](/backend/06-reliability/cases/netflix/chaos-monkey-business-hours-guardrails/)    | blast radius / pause / mode 控制對應時段策略             |
| [Pinterest：快取可靠性與容量驚奇](/backend/06-reliability/cases/pinterest/cache-reliability-and-capacity-surprises/)   | NetworkChaos / StressChaos 模擬熱點與 cache failure mode |
| [Google：Error Budget 與 Release Gating](/backend/06-reliability/cases/google/error-budget-policy-and-release-gating/) | chaos finding 對應 SLO burn rate 的回寫                  |

**待補 Chaos Mesh customer case**：PingCAP / TiDB 客戶 Chaos Mesh 案例、CNCF Chaos Mesh adopters。

## 下一步路由

- 上游概念：[6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)
- 平行 vendor：[LitmusChaos](/backend/06-reliability/vendors/litmuschaos/)、[Gremlin](/backend/06-reliability/vendors/gremlin/)
- 下游能力：[8 incident response](/backend/08-incident-response/)（chaos finding 進 IR 流程）
