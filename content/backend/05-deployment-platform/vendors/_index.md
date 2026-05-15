---
title: "部署平台 Vendor 清單"
date: 2026-05-01
description: "規劃 workload runtime、orchestration、traffic、IaC 與 discovery 的服務頁撰寫順序與判準"
weight: 90
tags: ["backend", "deployment", "vendor"]
---

部署平台 Vendor 清單的核心責任是把平台名稱放回 runtime contract、lifecycle contract、traffic contract、control plane 與 rollout governance 的判斷。每個服務頁先回答它承擔啟動、調度、入口、設定、基礎設施狀態或 service discovery 的哪一段，再討論操作成本與案例回寫。

## 讀法

部署服務要從服務生命週期進入。讀者如果要處理 container 與 runtime，先回到 [5.1 container runtime](/backend/05-deployment-platform/container-runtime/)；如果要處理 rollout 與 probe，先回到 [5.2 Kubernetes deployment](/backend/05-deployment-platform/kubernetes-deployment/)；如果要處理入口與 drain，先回到 [5.3 Load Balancer Contract](/backend/05-deployment-platform/load-balancer-contract/)。

## T1 服務頁大綱

| 服務                                                                       | 類型               | 頁面要回答的核心問題                                                    |
| -------------------------------------------------------------------------- | ------------------ | ----------------------------------------------------------------------- |
| [Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/)          | Orchestration      | pod lifecycle、probe、rolling update 與 resource limit 如何成為平台契約 |
| [Docker](/backend/05-deployment-platform/vendors/docker/)                  | Container runtime  | image、entrypoint、runtime config 與 local / prod parity 如何管理       |
| [systemd](/backend/05-deployment-platform/vendors/systemd/)                | Process supervisor | unit、restart policy、signal 與 journal 如何支援單機服務                |
| [nginx](/backend/05-deployment-platform/vendors/nginx/)                    | Reverse proxy / LB | reverse proxy、timeout、buffering、TLS 與 ingress 如何取捨              |
| [Envoy](/backend/05-deployment-platform/vendors/envoy/)                    | Service proxy      | xDS、dynamic config、mesh data plane 與 traffic policy 如何治理         |
| [AWS ELB](/backend/05-deployment-platform/vendors/aws-elb/)                | Managed LB         | ALB / NLB、health check、draining 與 target group 如何支援 AWS 入口     |
| [Terraform / OpenTofu](/backend/05-deployment-platform/vendors/terraform/) | IaC                | state、plan、provider、drift 與 review gate 如何管理 infra 變更         |
| [Traefik](/backend/05-deployment-platform/vendors/traefik/)                | Ingress / proxy    | auto-discovery、dynamic routing 與 cloud-native ingress 如何取捨        |
| [Consul](/backend/05-deployment-platform/vendors/consul/)                  | Registry / mesh    | service registry、DNS、health check、KV 與 mesh 邊界如何取捨            |

## 服務頁撰寫欄位

| 欄位     | 部署服務頁要保留的問題                                                                          |
| -------- | ----------------------------------------------------------------------------------------------- |
| 服務責任 | 它承擔 runtime、orchestration、traffic entry、IaC、registry 還是 mesh                           |
| 適用壓力 | rollout frequency、instance count、long connection、multi-region、team ownership 哪個壓力最明顯 |
| 替代邊界 | VM、container、Kubernetes、managed platform、service mesh、simple proxy 的機會成本              |
| 操作成本 | upgrade、config drift、certificate、health check、drain、state、rollback                        |
| Evidence | deploy marker、per-version SLI、health check、drain completion、plan diff、registry freshness   |
| 案例回寫 | Tradeshift、Condé Nast、Orbitera 與平台切換案例如何提供回退判準                                 |

## 服務頁標準章節

| 章節                 | 部署服務頁要補的內容                                                         |
| -------------------- | ---------------------------------------------------------------------------- |
| 服務定位             | 它是 runtime、process supervisor、orchestrator、proxy、LB、IaC 還是 registry |
| 本章目標             | 讀者能判斷 lifecycle、traffic、config、resource 與 rollback contract         |
| 最短判讀路徑         | 用「服務如何啟動、接流量、擴容、停止、回退」快速定位平台層                   |
| 日常操作與決策形狀   | image、unit、deployment、health check、drain、TLS、plan、registry            |
| 核心取捨表           | systemd、Docker、Kubernetes、managed runtime、proxy、service mesh 的機會成本 |
| 進階主題             | multi-cluster、service mesh、dynamic config、IaC drift、managed runtime      |
| 排錯與失敗快速判讀   | readiness、liveness、drain timeout、target health、config drift、state lock  |
| 何時改走其他服務     | 單機服務回 systemd、多服務平台上 Kubernetes、簡單入口用 managed LB           |
| 不在本頁內的主題     | 完整 YAML / HCL 語法百科、雲端平台所有產品線、語言 framework deployment      |
| 案例回寫與下一步路由 | 回到 5.C migration cases、6 release gate、8 decision log                     |

## 撰寫批次

| 批次 | 服務頁                            | 撰寫目的                                                        |
| ---- | --------------------------------- | --------------------------------------------------------------- |
| D1   | Kubernetes / Docker / systemd     | 建立 workload lifecycle、runtime 與 process supervisor baseline |
| D2   | nginx / AWS ELB / Envoy / Traefik | 建立 traffic entry、drain、timeout 與 proxy policy 對照         |
| D3   | Terraform / OpenTofu / Consul     | 建立 infra state、service registry 與 control-plane boundary    |
| D4   | ECS / Fargate / Cloud Run / Nomad | 補 managed runtime、platform abstraction 與自管調度對照         |

## 後續候選

| 類型                     | 候選服務                                              | 寫作重點                                                           |
| ------------------------ | ----------------------------------------------------- | ------------------------------------------------------------------ |
| GitOps / package         | Argo CD、Flux、Helm、Kustomize                        | desired state、release review、config drift、environment promotion |
| Ingress / Gateway        | ingress-nginx、Envoy Gateway、Gateway API、HAProxy    | routing contract、TLS、cross-namespace policy、drain               |
| Service mesh             | Istio、Linkerd、Cilium Service Mesh                   | mTLS、traffic split、sidecar / ambient、control-plane cost         |
| Managed runtime          | ECS、Fargate、Cloud Run、Azure Container Apps、Fly.io | managed scaling、deployment contract、platform limit               |
| Alternative orchestrator | Nomad、OpenShift、Rancher                             | operations model、multi-cluster governance、enterprise support     |
| IaC / PaaS               | Pulumi、Heroku、Railway、Vercel                       | developer workflow、state ownership、backend suitability           |

主流覆蓋檢查的重點是分開 runtime、orchestration、ingress / gateway、GitOps、IaC 與 mesh。Kubernetes 是 orchestration baseline；Argo CD / Flux / Helm / Kustomize 解 desired state delivery；ingress-nginx / Envoy Gateway / HAProxy 解 traffic entry；Istio / Linkerd / Cilium 解 service-to-service policy；ECS / Fargate / Cloud Run 解 managed runtime。

## 下一步路由

- 上游：[5.2 Kubernetes deployment](/backend/05-deployment-platform/kubernetes-deployment/)
- 上游：[5.3 Load Balancer Contract](/backend/05-deployment-platform/load-balancer-contract/)
- 案例：[5.C 部署平台案例正文](/backend/05-deployment-platform/cases/)
- 規劃：[0.17 後端真實服務討論大綱](/backend/00-service-selection/service-entity-discussion-outline/)
