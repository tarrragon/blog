---
title: "Kubernetes"
date: 2026-05-01
description: "Container orchestration 主流、GKE / EKS / AKS / 自管"
weight: 1
tags: ["backend", "deployment", "vendor"]
---

Kubernetes 是 container orchestration 事實標準、承擔三個責任：workload lifecycle（pod / deployment / probe / rolling update）、cluster networking（service / ingress / DNS）、resource scheduling（resource limit / QoS / autoscaling）。設計取捨偏向「declarative + control loop + extensible」、是 cloud-native 生態的核心抽象。可自管或用 cloud managed（GKE / EKS / AKS）。

對「多服務多實例 container orchestration、需要 rolling update / blue-green / canary、跨雲 / 跨環境統一抽象」這條路徑、Kubernetes 是首選。

## 本章目標

讀完本章後、你應該能：

1. 用 kubectl 部署 Deployment + Service、配置 probe / resource limit
2. 設計 rolling update / pod disruption budget 避免服務中斷
3. 選 Ingress controller（nginx / traefik / GLBC / ALB Controller）
4. 看懂 pod stuck / probe fail / OOMKilled / drain timeout 訊號
5. 評估 managed（GKE / EKS / AKS）vs 自管 vs Operator 進階場景

## 最短路徑：5 分鐘把 Kubernetes 跑起來

```bash
# 1. 本機跑 kind / minikube
# TODO: kind create cluster / minikube start

# 2. 部署 Deployment
# TODO: kubectl create deployment nginx --image=nginx
# TODO: kubectl expose deployment nginx --port=80 --type=ClusterIP

# 3. 驗證
# TODO: kubectl get pods / svc / deploy
# TODO: kubectl port-forward / kubectl exec
```

## 日常操作與決策形狀

### kubectl 核心指令

子議題：

- 資源生命週期：apply / create / delete / get / describe / logs / exec
- Rolling update：set image / rollout status / rollout undo
- Debug：events / port-forward / cp / top
- 對應指令範例：`kubectl get pods -A`、`kubectl describe pod <name>`、`kubectl logs -f`

### Workload 設計

Pod lifecycle 是 K8s 的核心抽象。子議題：

- Deployment（stateless）/ StatefulSet（stateful）/ DaemonSet（per-node）/ Job / CronJob
- Pod 多 container（sidecar / init container）
- 對應 [5.2 K8s deployment](/backend/05-deployment-platform/kubernetes-deployment/)

### Probe / Resource limit / QoS

子議題：

- Liveness（活著嗎）/ Readiness（接流量嗎）/ Startup（啟動完了嗎）— 三 probe 各自責任
- Resource limit（requests / limits）+ QoS class（Guaranteed / Burstable / BestEffort）
- 對應 [Platform lifecycle contract](/backend/05-deployment-platform/platform-lifecycle-contract/)

## 進階主題（按需閱讀）

### Rolling update / disruption budget

對應案例 [5.C9 反例：cutover without drain](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/)。子議題：

- maxSurge / maxUnavailable 配置
- PodDisruptionBudget 限制 voluntary disruption
- Preemption / priority class

### Ingress / Service mesh integration

子議題：

- Ingress controller 選擇（[nginx](/backend/05-deployment-platform/vendors/nginx/) / [Traefik](/backend/05-deployment-platform/vendors/traefik/) / ALB Controller）
- Gateway API（next gen Ingress）
- Service mesh integration（[Envoy](/backend/05-deployment-platform/vendors/envoy/)-based Istio / Linkerd）
- 對應 [5.C7 Airbnb Istio](/backend/05-deployment-platform/cases/airbnb-istio-upgrade-governance/)

### Operator pattern / CRD

子議題：

- CRD（CustomResourceDefinition）+ Controller 模式
- Operator framework（OperatorSDK / kubebuilder）
- 常見 Operator：Prometheus / Cert-manager / Argo CD

### Managed vs self-managed

對應案例 [5.C1 Tradeshift self-managed → EKS](/backend/05-deployment-platform/cases/tradeshift-self-managed-k8s-to-eks/)、[5.C2 Condé Nast EKS](/backend/05-deployment-platform/cases/conde-nast-platform-modernization-eks/)、[5.C3 Orbitera managed K8s](/backend/05-deployment-platform/cases/orbitera-managed-kubernetes-migration/)、[5.C4 Mobileye EKS](/backend/05-deployment-platform/cases/mobileye-workloads-to-eks/)、[5.C5 Miro EKS](/backend/05-deployment-platform/cases/miro-managed-eks-migration/)。子議題：

- Self-managed（kubeadm / Cluster API）的 control plane 維運成本
- Managed（GKE / EKS / AKS）的限制（版本鎖定 / managed addon）
- 遷移路徑跟回退設計

### Multi-cluster / Federation

子議題：

- Federation v2 / Cluster API multi-cluster
- Cross-cluster service mesh（Istio multi-cluster）
- 對應 [5.C6 Airbnb cluster scaling](/backend/05-deployment-platform/cases/airbnb-kubernetes-cluster-scaling-evolution/)

### Cluster autoscaling

子議題：

- Horizontal Pod Autoscaler / Vertical Pod Autoscaler
- Cluster Autoscaler / Karpenter
- 跟 [09 performance capacity](/backend/09-performance-capacity/) 對照

## 排錯快速判讀

### Pod stuck（Pending / CrashLoopBackOff）

操作原則：先 `kubectl describe pod` 看 events、再 `kubectl logs` 看 container 訊息。

```bash
# TODO: kubectl describe pod <name>（看 events 段）
# TODO: kubectl logs <name> --previous（看 crash 前 log）
```

判讀路徑：Pending → resource 不足 / nodeSelector 不匹配；CrashLoopBackOff → exit code + log 找原因。

### Probe failure 造成不停 restart

操作原則：probe path / initial delay / timeout 配置錯。判讀：`describe pod` 看 probe events。

### OOMKilled

操作原則：memory limit 太低、container 被殺。判讀：`describe pod` 看 last state reason。修法：raise limit 或優化 application memory。

### Rolling update stuck

對應 [5.C9 反例](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/)。判讀路徑：新 pod 起不來 → readiness 失敗 → 舊 pod 不下線 → 卡住。

### Drain timeout

操作原則：`kubectl drain` 失敗、PDB 限制太緊。判讀：`kubectl describe pdb`。

## 何時改走其他服務

| 需求形狀                        | 改走                                                              |
| ------------------------------- | ----------------------------------------------------------------- |
| 單機服務（VM / bare metal）     | [systemd](/backend/05-deployment-platform/vendors/systemd/)       |
| Local dev / CI                  | [Docker](/backend/05-deployment-platform/vendors/docker/) Compose |
| AWS managed runtime（不要 K8s） | ECS / Fargate                                                     |
| 極簡 PaaS                       | Cloud Run / Heroku / Fly.io                                       |
| 替代 orchestrator               | Nomad / Rancher                                                   |
| Edge / IoT 場景                 | K3s / MicroK8s                                                    |

## 不在本頁內的主題

- 完整 kubectl 指令 reference
- YAML manifest 完整 schema
- 各 Operator 細節
- 各語言 client-go API

## 案例回寫

### 直接相關案例

| 案例                                                                                                              | 主討論議題                                   |
| ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| [5.C1 Tradeshift self-managed → EKS](/backend/05-deployment-platform/cases/tradeshift-self-managed-k8s-to-eks/)   | 自管 K8s 遷 managed、零停機切流              |
| [5.C2 Condé Nast EKS](/backend/05-deployment-platform/cases/conde-nast-platform-modernization-eks/)               | 多團隊異質集群整併到單一控制面               |
| [5.C3 Orbitera managed K8s](/backend/05-deployment-platform/cases/orbitera-managed-kubernetes-migration/)         | 平台重置不中斷產品的能力遷移                 |
| [5.C4 Mobileye EKS](/backend/05-deployment-platform/cases/mobileye-workloads-to-eks/)                             | 大規模 workload 分批遷 EKS                   |
| [5.C5 Miro EKS](/backend/05-deployment-platform/cases/miro-managed-eks-migration/)                                | Managed K8s 跟團隊維運模型對齊               |
| [5.C6 Airbnb cluster scaling](/backend/05-deployment-platform/cases/airbnb-kubernetes-cluster-scaling-evolution/) | 手動擴縮 → 自動化容量治理                    |
| [5.C7 Airbnb Istio](/backend/05-deployment-platform/cases/airbnb-istio-upgrade-governance/)                       | Service mesh 升級分批治理                    |
| [5.C9 反例：cutover without drain](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/) | Rolling update / drain 沒做的傷              |
| [5.C10 規模對照](/backend/05-deployment-platform/cases/contrast-platform-migration-by-scale/)                     | 小型 systemd → 中型 K8s → 大型 multi-cluster |

## 下一步路由

- 上游概念：[5.2 K8s deployment](/backend/05-deployment-platform/kubernetes-deployment/)
- 平行 vendor：[Docker](/backend/05-deployment-platform/vendors/docker/)、[Envoy](/backend/05-deployment-platform/vendors/envoy/)
- 下游能力：[6 reliability](/backend/06-reliability/)（release gate）、[8 incident response](/backend/08-incident-response/)
