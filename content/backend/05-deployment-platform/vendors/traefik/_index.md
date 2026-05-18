---
title: "Traefik"
date: 2026-05-01
description: "Cloud-native ingress / reverse proxy、auto-discovery"
weight: 8
tags: ["backend", "deployment", "vendor"]
---

Traefik 是 cloud-native reverse proxy / ingress、承擔三個責任：auto-discovery（從 Docker / K8s / Consul / file 自動發現 backend）、dynamic config（不 reload、即時更新）、ACME 自動 TLS（Let's Encrypt 整合）。設計取捨偏向「cloud-native 簡潔 + auto-discovery 為核心 + middleware chain extensibility」、適合 Docker / K8s 中小規模、大規模 / 複雜 traffic management 跟 nginx / envoy 比相對弱。

對「Docker / K8s ingress、需要 auto-discovery、ACME 自動 TLS、配置簡潔」這條路徑、Traefik 是 cloud-native first 選擇。

## 本章目標

讀完本章後、你應該能：

1. 部署 Traefik 到 Docker / K8s
2. 配置 dynamic provider（labels / annotations / CRD / file）
3. 配置 ACME 自動 TLS
4. 設計 middleware chain（auth / rate limit / circuit breaker）
5. 評估 Traefik vs nginx vs Envoy 的選用

## 最短路徑：5 分鐘把 Traefik 跑起來

```bash
# 1. Docker 跑 Traefik + dashboard
# TODO: docker run -d -p 80:80 -p 8080:8080 -v /var/run/docker.sock:/var/run/docker.sock traefik:v3

# 2. 用 docker label 配置 routing
# TODO: docker run -d --label "traefik.http.routers.demo.rule=Host(`demo.local`)" nginx

# 3. 訪 dashboard 驗證
# TODO: curl http://localhost:8080/api/http/routers
```

## 日常操作與決策形狀

### Provider auto-discovery

子議題：

- Docker provider：從 container labels 讀 config
- Kubernetes Ingress provider：從 Ingress resource
- Kubernetes CRD provider：Traefik IngressRoute CRD
- Consul / Etcd provider：從 KV store
- File provider：YAML / TOML 靜態 file

### IngressRoute（K8s CRD）

子議題：

- Traefik CRD：IngressRoute / Middleware / TLSOption / ServersTransport
- 比 Ingress 表達力強（middleware chain / TLS option / multi-protocol）
- 跟 Gateway API 對比

### Middleware chain

子議題：

- 內建 middleware：headers / rate limit / basic auth / forward auth / retry / circuit breaker / compress / IP whitelist
- 自訂 middleware：plugin（Yaegi-based）
- 順序：定義 middleware → 在 router 引用

## 進階主題（按需閱讀）

### ACME 自動 TLS

子議題：

- Let's Encrypt 整合（自動憑證 + 續期）
- DNS challenge（適合 wildcard）vs HTTP challenge（適合單 domain）
- 多 resolver 配置（staging / production / 不同 CA）
- 對應 ACME storage（local / KV / Traefik Hub）

### Provider weight / priority

子議題：

- 多 provider 同時跑、config 來源衝突處理
- Provider 優先順序
- 對應 dynamic config debug

### Traefik Hub（managed）

子議題：

- Traefik Hub：商業 managed control plane
- 適合：跨 cluster 統一管理 / API Gateway portal
- 跟 self-host Traefik 對比

### 跟 nginx / Envoy 對比

子議題：

- Traefik 強：cloud-native auto-discovery、配置簡潔
- nginx 強：穩定 + 配置控制力 + 大量 community recipe
- Envoy 強：xDS dynamic config、advanced traffic management
- 選型判讀：Docker / K8s 小中規模 → Traefik；複雜 traffic → Envoy；標準 HTTP → nginx

### Plugin 機制（Yaegi）

子議題：

- Traefik plugins 用 Yaegi（Go interpreter）跑、不需 recompile
- Plugin catalog（社群 + 官方）
- 適合：客戶 auth / metric / transformation 小邏輯
- 對應 Envoy WASM extension 對比

### Multi-protocol

子議題：

- HTTP / HTTPS / TCP / UDP
- gRPC（HTTP/2）原生支援
- WebSocket sticky session

## 排錯快速判讀

### Service 沒被發現

操作原則：先看 provider 是否啟用、再看 label / annotation / CRD 配置。

```bash
# TODO: curl http://localhost:8080/api/http/services 看 discovered services
```

### Route 衝突

操作原則：兩個 router 同 rule，看 priority 排序。判讀：dashboard 看 router list。

### ACME rate limit

操作原則：Let's Encrypt 有 rate limit、staging environment 先測再切 production。

### Middleware chain 順序錯

操作原則：middleware 順序影響行為（auth before rate limit vs after）。判讀：dashboard 看 middleware order。

### Dashboard 連不上

操作原則：dashboard 預設 8080、需要 entrypoint 配置。判讀：traefik.yml + entrypoints 設定。

## 何時改走其他服務

| 需求形狀                         | 改走                                                        |
| -------------------------------- | ----------------------------------------------------------- |
| 配置控制力 / 大量 community 模板 | [nginx](/backend/05-deployment-platform/vendors/nginx/)     |
| Advanced traffic / xDS           | [Envoy](/backend/05-deployment-platform/vendors/envoy/)     |
| AWS managed                      | [AWS ELB](/backend/05-deployment-platform/vendors/aws-elb/) |
| Service mesh                     | Istio / Linkerd / Consul Connect                            |
| Gateway API standard             | Envoy Gateway / Contour                                     |
| 純 dev / local                   | Docker Compose + direct port mapping                        |

## 不在本頁內的主題

- Traefik plugin 開發
- Yaegi Go interpreter 細節
- Traefik Hub 商業細節
- 各 cloud provider 整合差異

## 案例回寫

### 跨 vendor 對照

| 案例                                                                                                        | 對 Traefik 的對應                                                                     |
| ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| [5.C9 cutover without drain](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/) | Traefik auto-discovery 在 service 下線時、要靠 health check + grace period 等價 drain |
| [5.C10 規模對照](/backend/05-deployment-platform/cases/contrast-platform-migration-by-scale/)               | Docker / K8s 中小規模選 Traefik 簡潔、大規模通常升階到 Envoy / ingress-nginx 或 mesh  |

**待補 Traefik 案例**：Traefik Labs customer story、IngressRoute CRD 大規模採用、Traefik Hub 早期 adopter。

## 下一步路由

- 上游概念：[5.3 LB Contract](/backend/05-deployment-platform/load-balancer-contract/)
- 平行 vendor：[nginx](/backend/05-deployment-platform/vendors/nginx/)、[Envoy](/backend/05-deployment-platform/vendors/envoy/)
- 下游能力：[Kubernetes vendor 頁](/backend/05-deployment-platform/vendors/kubernetes/)
