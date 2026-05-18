---
title: "AWS ELB（ALB / NLB / CLB）"
date: 2026-05-01
description: "AWS managed load balancer、ALB（L7）/ NLB（L4）/ CLB（legacy）"
weight: 6
tags: ["backend", "deployment", "vendor"]
---

AWS ELB 是 AWS managed load balancer 系列、承擔三個責任：流量入口（HTTP/HTTPS for ALB、TCP/UDP for NLB）、health check + draining、跟 AWS 生態整合（ACM TLS / Target Group / WAF / Lambda）。包含 ALB（L7、HTTP/HTTPS）、NLB（L4、極低延遲）、CLB（legacy、不要選）。設計取捨偏向「managed + AWS-native + integrate with ECS/EKS/Lambda」、跨雲 / 進階 traffic management 是限制。

## 本章目標

讀完本章後、你應該能：

1. 建立 ALB / NLB、配置 listener + target group
2. 設計 health check + connection draining
3. 用 ACM 自動憑證 + SNI
4. 用 ALB Ingress Controller / AWS Load Balancer Controller for K8s
5. 評估 ALB vs NLB vs CloudFront vs API Gateway

## 最短路徑：5 分鐘把 AWS ELB 跑起來

```bash
# 1. 建 ALB（CLI）
# TODO: aws elbv2 create-load-balancer --name demo --subnets ... --security-groups ...

# 2. 建 target group + register targets
# TODO: aws elbv2 create-target-group --name demo-tg ...
# TODO: aws elbv2 register-targets --target-group-arn ... --targets Id=i-xxx

# 3. 建 listener + 驗證
# TODO: aws elbv2 create-listener --load-balancer-arn ... --protocol HTTP --port 80 ...
# TODO: curl <alb-dns>
```

## 日常操作與決策形狀

### ALB vs NLB vs CLB

子議題：

- ALB：L7、path/host routing、WebSocket、gRPC、Lambda target
- NLB：L4、static IP、preserve client IP、極低延遲、TCP/UDP
- CLB：legacy、不要新用
- 選擇判讀：HTTP/HTTPS → ALB；TCP/UDP / 高吞吐 → NLB

### Target group / listener rule

子議題：

- Target type：instance / IP / Lambda
- Listener rule：path-based / host-based / header-based routing
- Priority 排序
- 對應指令：`aws elbv2 modify-rule`

### Health check 與 draining

子議題：

- Health check：HTTP path / interval / threshold
- Connection draining（deregistration delay）：deregister 後等到 in-flight requests 完成
- 對應 [5.C9 反例 cutover without drain](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/)

## 進階主題（按需閱讀）

### TLS termination + SNI

子議題：

- ACM 自動憑證 + 續期
- SNI：單 ALB 多 domain（最多 25 certificates）
- TLS policy（min TLS version）
- Mutual TLS（ALB 2023+）

### ALB Ingress Controller / AWS Load Balancer Controller

子議題：

- 在 EKS 內配置 ALB / NLB（Ingress / Service of type LoadBalancer）
- IngressClass / annotations
- Pod readiness gate（pod 到 ALB target group healthy 才接流量）
- 對應 [Kubernetes vendor 頁](/backend/05-deployment-platform/vendors/kubernetes/)

### Cross-zone load balancing

子議題：

- ALB default enabled、NLB default disabled
- Cross-zone 跨 AZ data transfer cost
- 跟 AZ failover 對應

### WAF integration

子議題：

- AWS WAF on ALB
- Rate-based rule / managed rule group
- 對應 [07 security WAF](/backend/07-security-data-protection/)

### Idle timeout

子議題：

- ALB default 60s、可調 1-4000s
- 跟 keep-alive / WebSocket 長連線對應
- 跟 backend（K8s pod / EC2）的 timeout 對齊

### Cost 模型

子議題：

- LB-hour（per ALB / NLB）
- LCU（Load Balancer Capacity Unit）— 多維度計算
- Data processing charge
- 跨 AZ data transfer

## 排錯快速判讀

### Target unhealthy

操作原則：health check path 不對 / security group 沒開 / backend 反應慢。

```bash
# TODO: aws elbv2 describe-target-health --target-group-arn ...
```

### 504 Gateway Timeout

操作原則：backend 超 ALB idle timeout / 60s。判讀：backend log + ALB access log。

### Cross-zone imbalance

操作原則：cross-zone disabled、流量集中單 AZ。修法：enable cross-zone（注意 cost）。

### Draining 卡住

對應 [5.C9 反例](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/)。判讀：deregistration delay 太短 / connection 未結束就被斷。

### ACM cert renew 失敗

操作原則：DNS validation 失敗 / domain ownership 變動。判讀：ACM console 看 cert state。

## 何時改走其他服務

| 需求形狀                    | 改走                                                                                                              |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 跨雲 / 自管                 | [nginx](/backend/05-deployment-platform/vendors/nginx/) / [Envoy](/backend/05-deployment-platform/vendors/envoy/) |
| Service mesh                | [Envoy](/backend/05-deployment-platform/vendors/envoy/) + Istio                                                   |
| Cloud-native auto-discovery | [Traefik](/backend/05-deployment-platform/vendors/traefik/)                                                       |
| CDN / edge                  | CloudFront / Cloudflare / Fastly                                                                                  |
| API Gateway                 | AWS API Gateway / Kong                                                                                            |
| 極低成本                    | 自管 [nginx](/backend/05-deployment-platform/vendors/nginx/) on EC2                                               |

## 不在本頁內的主題

- AWS WAF rule 完整 reference
- Network Firewall 配置
- 各 AWS region 限制差異
- ELB classic（CLB）細節

## 案例回寫

### 直接相關案例

| 案例                                                                                                            | 主討論議題                                                         |
| --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| [5.C1 Tradeshift self-managed → EKS](/backend/05-deployment-platform/cases/tradeshift-self-managed-k8s-to-eks/) | 遷 EKS 時 ALB / NLB 是入口、切流批次跟 target group 權重連動       |
| [5.C2 Condé Nast EKS](/backend/05-deployment-platform/cases/conde-nast-platform-modernization-eks/)             | 多集群整併 EKS、AWS Load Balancer Controller 統一 ingress 入口     |
| [5.C4 Mobileye EKS](/backend/05-deployment-platform/cases/mobileye-workloads-to-eks/)                           | 大規模 workload 遷 EKS、ALB target group health check 是切流驗證點 |
| [5.C5 Miro EKS](/backend/05-deployment-platform/cases/miro-managed-eks-migration/)                              | Managed EKS 後 ALB / NLB 治理回到平台團隊                          |

### 跨 vendor 對照

| 案例                                                                                                        | 對 AWS ELB 的對應                                                     |
| ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| [5.C9 cutover without drain](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/) | ALB deregistration delay / NLB connection draining 是切流的關鍵回退面 |
| [5.C10 規模對照](/backend/05-deployment-platform/cases/contrast-platform-migration-by-scale/)               | AWS 生態小型 ALB + EC2 / 中型 ALB + EKS / 大型 NLB + 多 region + WAF  |

**待補 AWS ELB 案例**：大規模 AWS Load Balancer Controller 客戶案例、NLB static IP 場景、AWS WAF + ALB 安全整合。

## 下一步路由

- 上游概念：[5.3 LB Contract](/backend/05-deployment-platform/load-balancer-contract/)
- 平行 vendor：[nginx](/backend/05-deployment-platform/vendors/nginx/)、[Envoy](/backend/05-deployment-platform/vendors/envoy/)
- 下游能力：[07 security WAF](/backend/07-security-data-protection/)、[6 reliability release gate](/backend/06-reliability/)
