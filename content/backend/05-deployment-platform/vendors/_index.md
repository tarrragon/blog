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

## 教學順序同步

部署平台服務頁的教學順序是先建立 workload runtime，再進入 orchestration、traffic entry、infra state 與 discovery。這個順序對齊 checkout E4：讀者先理解服務如何啟動、接流量、drain 與 rollback，再比較 Kubernetes、systemd、Docker、load balancer、proxy、Terraform 與 Consul 分別承擔哪一層平台責任。

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

## 內容覆蓋進度

每個 vendor 服務頁下會擴充兩類文章：deep article（vendor 自身的配置、故障、容量、走 [6-section 模板](/posts/vendor-deep-article-methodology/)）跟 migration playbook（跨 vendor 遷移流程、走 [6-type 結構](/posts/migration-playbook-methodology/)）。「→ X」代表遷移到 X 的 playbook、「← X」代表從 X 遷入。

| Vendor                    | Deep article                                       | Migration playbook                                      |
| ------------------------- | -------------------------------------------------- | ------------------------------------------------------- |
| [Kubernetes](kubernetes/) | [graceful-shutdown](kubernetes/graceful-shutdown/) | [← Docker Swarm](kubernetes/migrate-from-docker-swarm/) |
| [Terraform](terraform/)   | —                                                  | [→ OpenTofu](terraform/migrate-to-opentofu/)            |
| [Consul](consul/)         | —                                                  | [← etcd](consul/migrate-from-etcd/)                     |

其他 T1 vendor（Docker / systemd / nginx / Envoy / AWS ELB / Traefik）尚未開始。對應的 backlog 議題見上方「T1 服務頁大綱」段每個服務頁要回答的核心問題、跟各 vendor `_index.md` 的「預計實作話題」段。

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

## 跨 vendor 議題對照

本模組 9 個 vendor 跨 6 個 category（orchestrator / container / process / proxy / LB / IaC / registry）、不是同類產品的多個選項。對照表用「橫向工程議題」標明每個議題在哪些 vendor 是核心責任、哪些不適用。

| 議題              | K8s             | Docker                     | systemd            | nginx             | Envoy              | AWS ELB       | Terraform          | Traefik          | Consul          |
| ----------------- | --------------- | -------------------------- | ------------------ | ----------------- | ------------------ | ------------- | ------------------ | ---------------- | --------------- |
| 主責任            | orchestration   | container build/run        | process supervisor | reverse proxy     | service proxy      | managed LB    | IaC state          | ingress proxy    | registry / mesh |
| 服務生命週期      | pod lifecycle   | container run              | service unit       | N/A               | N/A                | target health | N/A                | N/A              | health check    |
| 流量入口          | Service/Ingress | port mapping               | listen socket      | HTTP server       | listener           | listener      | N/A                | entrypoint       | N/A             |
| 配置模式          | declarative     | imperative                 | declarative        | static config     | xDS dynamic        | API / IaC     | declarative        | dynamic provider | KV + watch      |
| Service discovery | K8s DNS         | N/A                        | N/A                | manual upstream   | xDS EDS            | target group  | provider data      | provider 自動    | registry 原生   |
| Health check      | probe           | healthcheck                | restart policy     | upstream check    | active/passive     | health check  | N/A                | health check     | health check    |
| TLS / mTLS        | cert-manager    | N/A                        | N/A                | ssl module        | filter chain       | ACM           | provider data      | ACME 自動        | Connect mTLS    |
| Multi-cluster     | federation      | N/A                        | N/A                | manual            | mesh control plane | cross-region  | provider chain     | per cluster      | DC federation   |
| 授權模式          | Apache 2        | Apache 2 / Desktop license | LGPL               | BSD-2 / Plus 商業 | Apache 2           | AWS managed   | BSL / OpenTofu MPL | MIT / Hub 商業   | BSL             |
| 主討論案例        | C1/C2/C3/C4/C8  | 待補                       | 待補               | 待補              | C5                 | C9            | 待補               | 待補             | 待補            |

對照表的用途有三：

- 寫某 vendor 頁時、檢查橫向議題該怎麼定位（不該強塞跟它無關的議題）
- 讀者理解「9 vendor 不是同類選一個、是不同 layer 各自一個」
- 評估部署 stack：選 orchestrator + container + proxy + LB + IaC + registry 各 1-2 個組合

下面 5 段把對照表的關鍵橫向議題展開（不是每行都展開 — 部分行如「主責任」「授權模式」直接看表即可）。

### 配置模式

配置模式跨 vendor 差異大、影響 dev workflow 跟 GitOps 整合度。**K8s** declarative（kubectl apply / YAML）；**Terraform** declarative（HCL）；**systemd** declarative（unit file）；**Docker** imperative（CLI）+ Compose declarative；**nginx** static config + reload；**Envoy** xDS dynamic（control plane push）；**Traefik** dynamic（provider 自動 sync）；**AWS ELB** API + IaC；**Consul** KV + watch。

選型判讀：要 GitOps → declarative（K8s + Terraform + systemd unit）；要 zero-reload → dynamic config（Envoy / Traefik）；要 manual control → imperative（Docker / 純 CLI）。

### Service discovery + Health check

Service discovery 是 5 模組多個 vendor 共同關心的議題、但實作差異大。**K8s** 內建（Service + DNS + kube-proxy）；**Consul** registry first + DNS interface + health check 內建；**Envoy** EDS（xDS endpoint discovery）；**Traefik** provider 自動發現；**nginx / AWS ELB** 配置 upstream target；**Docker / systemd** N/A（單機 / 不負責 discovery）。

選型判讀：K8s-only → 內建；非 K8s 多平台 → Consul；K8s + service mesh → Istio + Envoy；單機 → nginx + manual config。

### Multi-cluster / 跨 DC

跨多 cluster / DC 拓樸差異大。**K8s** federation（v2 / Cluster API multi-cluster）；**Consul** 一級公民跨 DC（WAN federation）；**Envoy + Istio** multi-cluster mesh；**Terraform** 用 provider chain 管多 cloud / 多 cluster；**AWS ELB** cross-region replication；**nginx / Traefik** 一般 per cluster；**systemd / Docker** N/A。

選型判讀：跨 DC 為核心需求 → Consul / Istio；單一 cluster + cross-region LB → ELB / Global LB；多 cluster K8s → Cluster API + federation。

### TLS / mTLS

TLS / mTLS 在不同 vendor 由不同 layer 負責。**K8s** cert-manager（Let's Encrypt / 內部 CA）；**AWS ELB** ACM 自動憑證；**Traefik** ACME 自動 TLS；**nginx** ssl module + manual cert / cert-manager；**Envoy** filter chain（SDS 動態 cert）；**Consul Connect** mTLS 自動 sidecar；**Terraform** 不負責 TLS、提供 provider；**Docker / systemd** 不負責（交給 application 或上游 proxy）。

選型判讀：cluster 內 mTLS → cert-manager / Consul Connect；外部 TLS → ACME（Traefik / 自管 cert-manager）；managed → AWS ELB / Cloudflare。

### 授權模式（2023-2024 BSL 變動）

2023-2024 多個 HashiCorp 產品改 BSL（Terraform / Vault / Consul / Boundary / Vagrant）— 影響採用決策。**Terraform** → OpenTofu fork（Linux Foundation、MPL 2.0）；**Consul** → 暫無大型 fork；**Docker Desktop** → 商業 license（員工 > 250 / 收入 > $10M）→ Podman Desktop 替代；**nginx** → F5 後 OSS 不滿 → Freenginx / angie fork；**K8s / Envoy / Traefik** → 仍 OSI 開源。

選型判讀：商業 SaaS 提供類似服務 → 避 BSL（用 OpenTofu / 自評）；企業內部使用 → BSL 多數無影響；公部門 / 嚴格合規 → 仍要 OSI 認可 license。

## 撰寫批次

| 批次 | 服務頁                            | 撰寫目的                                                          |
| ---- | --------------------------------- | ----------------------------------------------------------------- |
| D1   | Docker / systemd                  | 建立 runtime、entrypoint、process supervisor 與單機服務 baseline  |
| D2   | Kubernetes                        | 建立 workload lifecycle、orchestration、probe 與 rollout contract |
| D3   | nginx / AWS ELB / Envoy / Traefik | 建立 traffic entry、drain、timeout 與 proxy policy 對照           |
| D4   | Terraform / OpenTofu / Consul     | 建立 infra state、service registry 與 control-plane boundary      |
| D5   | ECS / Fargate / Cloud Run / Nomad | 補 managed runtime、platform abstraction 與自管調度對照           |

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
- 服務路徑：[5.8 Deployment Rollout with Drain and Rollback](/backend/05-deployment-platform/deployment-rollout-drain-rollback/)
