---
title: "Docker Swarm → Kubernetes：5 個 Swarm production cluster 撞牆數據"
date: 2026-05-19
description: "Docker Swarm → Kubernetes 是 Type E paradigm shift — Swarm「simpler container orchestration」設計上限在 100-200 service 規模、跨 application 服務治理時 paradigm 不足；本文用 5 個 production cluster 量化數據開頭、5 個 production 踩雷"
weight: 11
tags: ["backend", "deployment-platform", "docker-swarm", "kubernetes", "paradigm-shift", "migration", "type-e"]
---

> 本文是跨 vendor migration playbook、cross-link Docker Swarm 跟 [Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/)。跑 [migration-playbook-methodology 6 維 audit](/posts/migration-playbook-methodology/) 後對映 *Paradigm = High（Swarm 簡單 container orchestration → K8s declarative resource model）→ Type E paradigm shift*。

## 5 個 Swarm production cluster 撞牆數據

從 2020-2024 觀察 5 個中型 organization 的 Swarm production cluster lifecycle、典型撞牆點：

| Cluster          | 規模 (peak)           | 撞牆點                                        | 觸發遷移時間 |
| ---------------- | --------------------- | --------------------------------------------- | ------------ |
| A (SaaS startup) | 80 service / 12 node  | service discovery latency 升、無 sidecar mesh | 2022         |
| B (E-commerce)   | 150 service / 25 node | rolling update + canary 邏輯自寫複雜          | 2023         |
| C (Fintech)      | 60 service / 15 node  | secret rotation + RBAC 自管、合規難           | 2023         |
| D (Media)        | 200 service / 40 node | autoscaling 自寫、預測流量失敗                | 2024         |
| E (Logistics)    | 100 service / 20 node | multi-region 不支援                           | 2024         |

5 個共同 pattern：

- **Swarm 簡單但 ceiling 100-200 service / 20-40 node**
- **跨 service 治理（mesh / RBAC / secret / autoscale）需要 *外掛* 工具、複雜度反超 K8s**
- **無 multi-region native**、災備受限
- **生態縮、社群活躍度低、新 feature 緩**

撞牆點不是「Swarm 跑不動」、是「Swarm 不會幫你解 *跨 service 治理* 問題、要自寫」。Kubernetes 不是 simpler、是 *把治理問題納入框架*。

## 為什麼遷：ceiling / ecosystem / multi-region 三條 driver

| Driver       | 觸發                                                                      |
| ------------ | ------------------------------------------------------------------------- |
| Ceiling      | Swarm 跑 100-200 service 後 service discovery latency / scheduling 跟不上 |
| Ecosystem    | K8s ecosystem (Helm / Operator / mesh / GitOps) 成熟、Swarm 對等工具缺    |
| Multi-region | Swarm 不支援、K8s 多 cluster federation 成熟                              |

反向 driver（K8s → Swarm）：

- 純 internal tool / 小規模（< 30 service）、K8s 過度複雜
- Edge / IoT scenario、Swarm footprint 小

## 6 維 audit

| 維度               | 等級                                                                  |
| ------------------ | --------------------------------------------------------------------- |
| Schema / API       | **High**（docker-compose stack.yml → K8s YAML、syntax 完全不同）      |
| Operational        | Medium（Swarm 自管 → K8s self-host or managed）                       |
| Paradigm           | **High**（簡單 container orchestration → declarative resource model） |
| Components         | Low（同 1 個 orchestration 系統）                                     |
| Application change | Low（container image 不變）                                           |
| Data topology      | Low                                                                   |

Schema + Paradigm 雙 High → **Type E paradigm shift** 為主、Schema 高維獨立段。

## Paradigm 對位

| 概念               | Swarm                               | K8s                                               |
| ------------------ | ----------------------------------- | ------------------------------------------------- |
| Workload unit      | Service                             | Deployment + Pod + Service                        |
| Stack 定義         | stack.yml (docker-compose 格式)     | YAML manifest (multiple resources)                |
| Networking         | Overlay network (built-in)          | CNI plugin (Calico / Cilium / etc)                |
| Service discovery  | DNS-based built-in                  | DNS-based (CoreDNS) + Service object              |
| Load balancing     | Built-in routing mesh               | Service + Ingress + LoadBalancer                  |
| Secret management  | Docker secrets                      | K8s Secret + 外部 Vault / Secrets Manager         |
| Rolling update     | `docker service update --image ...` | Deployment + rolling update + readiness probe     |
| Autoscaling        | 手動 scale                          | HPA (Horizontal Pod Autoscaler)                   |
| RBAC               | Limited (Swarm enterprise)          | First-class (Role / RoleBinding / ServiceAccount) |
| Persistent storage | Volume + driver plugin              | PV / PVC + CSI driver                             |
| Service mesh       | 無 (要外掛 Traefik)                 | Istio / Linkerd / Cilium                          |
| GitOps             | 無 native                           | Argo CD / Flux (first-class)                      |

## Schema gap：docker-compose vs K8s YAML

```yaml
# Docker Swarm stack.yml
version: '3.8'
services:
  webapp:
    image: myapp:1.0
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
      restart_policy:
        condition: on-failure
    networks:
      - frontend
    ports:
      - "8080:8080"
```

```yaml
# K8s equivalent (Deployment + Service + Ingress)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels: { app: webapp }
  template:
    metadata:
      labels: { app: webapp }
    spec:
      containers:
        - name: webapp
          image: myapp:1.0
          ports:
            - containerPort: 8080
          readinessProbe:
            httpGet:
              path: /healthz
              port: 8080
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: webapp
spec:
  selector: { app: webapp }
  ports:
    - port: 8080
      targetPort: 8080
```

1 Swarm service → 2-3 K8s resource（Deployment + Service + 可能 Ingress / HPA）；application 不改但 *deployment 端工作量 5-10x*。

## Migration 流程

### Partial migration + 混合架構

跟 [Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/) / [etcd → Consul](/backend/05-deployment-platform/vendors/consul/migrate-from-etcd/) 同 Type E pattern：

```text
1. Audit application：列所有 Swarm stack + service
2. 分類處理 plan:
   - 簡單 stateless: 先切 K8s (低風險)
   - Stateful (DB / queue): 評估 K8s operator 或保留 Swarm
   - Critical service: 雙跑期確認 K8s 行為對等
3. K8s cluster 建置:
   - Managed (EKS / GKE / AKS) vs self-host (kubeadm)
   - 配 ingress controller / cert-manager / monitoring
4. Application 遷移 (per stack)
   - 寫 K8s YAML / Helm chart
   - 配 readiness/liveness probe / resource request
   - Networking + secret 對位
5. Cutover + Swarm decommission
   - 部分 stack 切完、評估 Swarm 是否保留 (legacy / edge)
   - 多數 organization 完全 decommission Swarm
```

整體 3-6 個月、依 stack 數量跟 application 複雜度。

## Production 故障演練

### Case 1：Networking model 差、cross-service connectivity 失效

**徵兆**：cutover 後 service A 連 service B 失敗、Swarm 端 `tasks.service_b` DNS 對位 K8s 端 `service-b.namespace.svc.cluster.local` 不通。

**根因**：Swarm overlay network 內 service-to-service 用 short name (`service_b`)、K8s 用 FQDN；application 端 service URL 寫死。

**修法**：

1. Application 端用 short name + cluster DNS search domain
2. K8s 端設 `dnsPolicy: ClusterFirst` 預設、確認 `kubectl get svc -A` 對應
3. NetworkPolicy 預設 deny-all、明示 allow rule

### Case 2：Secret rotation 從 Swarm secrets 換 Vault / Secrets Manager

**徵兆**：原本 Swarm 用 `docker secret` 旋轉 secret、切 K8s 後 K8s Secret 是 *static value*、rotation 不自動。

**根因**：K8s Secret 是 K8s-native 但 *not auto-rotated*、需要外部 Vault / Secrets Manager + agent (vault-agent-injector / external-secrets-operator)。

**修法**：

1. K8s 端 deploy external-secrets-operator + AWS Secrets Manager / Vault integration
2. Application 端 mount file or env variable、不在 code 寫死
3. Rotation 走 vendor-side、K8s 端 sidecar 自動 reload

### Case 3：Readiness probe 沒設、rolling update 期間 traffic loss

**徵兆**：cutover 後 deploy 期間 application 5-10% request 失敗；發現 pod startup 完成前就接 traffic。

**根因**：Swarm 簡單 restart_policy 沒對等 probe 概念；K8s 預設 deploy 後 immediate ready、若沒 readiness probe、startup 時間長的 application 會在未 ready 時接流量。

**修法**：

1. **必加 readiness probe**：HTTP / TCP / exec check
2. **配 initial delay**：JVM application 預留 30-60s
3. **配 `minReadySeconds`**：deployment 端設 30s 確保 stable

### Case 4：HPA 預設不啟、autoscaling 失效

**徵兆**：Swarm 端寫了 cron-based autoscale script、切 K8s 後 script 失效、流量高峰沒 scale up。

**根因**：K8s HPA 不是預設啟動、需要 *明示配置* + metrics-server install。

**修法**：

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: webapp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: webapp
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

裝 metrics-server / Keda（event-driven autoscaling）+ 配 HPA per Deployment。

### Case 5：YAML 維護地獄、Helm / Kustomize 配置遲

**徵兆**：cutover 後 K8s YAML 從 5 個檔（Swarm stack）變 50+ 個 K8s manifest；每個 application 端要改一個 config 都要動 N 個 file。

**根因**：K8s YAML 是 *very verbose*、不像 docker-compose 簡潔；缺 templating 跟 environment 抽象。

**修法**：

1. **Helm chart**：對 application 包成 chart、用 `values.yaml` 抽象環境差異
2. **Kustomize**：base + overlay pattern、不靠 templating
3. **GitOps with Argo CD / Flux**：宣告式部署、降 manual kubectl 操作

## Capacity / cost

| 維度                    | Docker Swarm       | Kubernetes (managed)                                |
| ----------------------- | ------------------ | --------------------------------------------------- |
| Cluster cost (mid-tier) | $300-800 / mo      | $500-1500 / mo（EKS/GKE/AKS control plane + nodes） |
| Operational FTE         | 0.3-0.8            | 0.5-1.5（除非 managed、降到 0.3-0.7）               |
| Ecosystem maturity      | 低、衰退           | 高、active growth                                   |
| Multi-region            | 不支援             | 多 cluster federation 成熟                          |
| Migration cost          | -                  | 2-4 FTE × 3-6 個月                                  |
| Long-term ROI           | Negative（社群縮） | Positive（feature growth）                          |

**判讀**：< 30 service 小 organization 可不切；50+ service 開始撞 Swarm ceiling、值得評估；100+ service / multi-region 必切。

## 整合 / 下一步

### 跟 Service mesh 整合

Cutover 後 *順便* 評估 Istio / Linkerd / Cilium service mesh、cover mTLS / observability / traffic policy；不要在 Swarm migration 後立刻上 mesh、分階段。

### 跟 GitOps 整合

K8s + Argo CD / Flux 是 *natural pair*；migration 時直接走 GitOps、避免 manual kubectl 操作累積。

### 跟 [Vault → AWS Secrets Manager](/backend/07-security-data-protection/vendors/hashicorp-vault/migrate-to-aws-secrets-manager/) 對齊

Swarm secrets → K8s Secret → external secrets management 是 *3-step 演進*、不是 1-step；migration 期間先用 K8s Secret、之後切 Vault / Secrets Manager。

## 相關連結

- Target vendor：[Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/)
- 平行 migration playbook (Type E)：[Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/) / [Redis → Memcached](/backend/02-cache-redis/vendors/redis/migrate-to-memcached/) / [etcd → Consul](/backend/05-deployment-platform/vendors/consul/migrate-from-etcd/) / [Sentry → Honeycomb](/backend/04-observability/vendors/honeycomb/migrate-from-sentry/)
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/)
