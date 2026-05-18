---
title: "Envoy"
date: 2026-05-01
description: "Cloud-native service proxy、xDS dynamic config、Istio / Gateway 底層"
weight: 5
tags: ["backend", "deployment", "vendor"]
---

Envoy 是 CNCF graduated 的 service proxy、承擔三個責任：cloud-native L7 + L4 proxy（HTTP/1.1 + HTTP/2 + HTTP/3 + gRPC）、xDS dynamic config（不需 reload）、observability 內建（access log / stats / tracing）。設計取捨偏向「dynamic config + advanced traffic management + filter chain extensibility」、是 Istio / Linkerd2-proxy / AWS App Mesh / Envoy Gateway 的底層實作。

對「service mesh data plane、API Gateway、advanced traffic management、gRPC / HTTP/2 / HTTP/3」這條路徑、Envoy 是首選。

## 本章目標

讀完本章後、你應該能：

1. 跑起 Envoy + 基本 reverse proxy config
2. 用 xDS API 動態更新 config（不 reload）
3. 配置 listener / route / cluster / filter chain
4. 看懂 Envoy access log + stats + admin endpoint
5. 評估 Envoy 直接用 vs 用 Istio / Envoy Gateway 抽象

## 最短路徑：5 分鐘把 Envoy 跑起來

```bash
# 1. 啟動 Envoy
# TODO: docker run -p 9901:9901 -p 10000:10000 -v ./envoy.yaml:/etc/envoy/envoy.yaml envoyproxy/envoy:v1.30-latest

# 2. Static config 範例
# TODO: listener / route / cluster YAML

# 3. 驗證 + admin endpoint
# TODO: curl http://localhost:10000
# TODO: curl http://localhost:9901/stats / /clusters / /config_dump
```

## 日常操作與決策形狀

### Envoy config 結構

子議題：

- Listener：listen address + filter chain
- Route：path matching + cluster routing
- Cluster：upstream endpoint discovery + load balancing
- Endpoint：實際 backend
- 對應 [5.3 LB Contract](/backend/05-deployment-platform/load-balancer-contract/)

### Static vs Dynamic config

子議題：

- Static：YAML 寫死、適合 dev / debug
- Dynamic（xDS）：control plane push config
- xDS protocol：LDS / RDS / CDS / EDS / SDS
- 對應 control plane：Istio / Gloo / 自寫

### Admin endpoint

子議題：

- /stats / /clusters / /config_dump / /listeners / /server_info
- runtime config（/runtime_modify）
- 對應 observability 跟 debug
- 對應指令：`curl admin:9901/clusters`

## 進階主題（按需閱讀）

### xDS API 細節

子議題：

- LDS / RDS / CDS / EDS / SDS / RTDS / ECDS
- ADS（Aggregated Discovery Service）統一通道
- Delta xDS（incremental）vs SOTW（State of the World）
- 對應案例 [5.C7 Airbnb Istio](/backend/05-deployment-platform/cases/airbnb-istio-upgrade-governance/)

### Filter chain（HTTP / network filter）

子議題：

- HTTP filters：router / cors / fault / rate_limit / ext_authz / jwt_authn
- Network filters：tcp_proxy / mongo_proxy / redis_proxy
- 自訂 filter（C++ / WebAssembly）
- 對應 [security 模組](/backend/07-security-data-protection/)（ext_authz）

### Observability 內建

子議題：

- Access log（structured / configurable format）
- Stats（envoy 內建 metrics）
- Distributed tracing（Jaeger / Zipkin / Datadog / OpenTelemetry）
- 對應 [04 observability](/backend/04-observability/)

### Envoy Gateway / Emissary / Gloo

子議題：

- Envoy Gateway：Gateway API native（CNCF project）
- Emissary（前 Ambassador）：K8s ingress + API Gateway
- Gloo：Solo.io 商業 Envoy 整合
- 選型判讀：純 K8s ingress → Envoy Gateway；商業支援 → Gloo / Emissary

### Service mesh data plane

子議題：

- Istio：control plane + Envoy sidecar
- Linkerd2：自家 Rust proxy（不是 Envoy）— Linkerd2-proxy
- Cilium Service Mesh：eBPF + Envoy
- 對應 [5.C7 Airbnb Istio governance](/backend/05-deployment-platform/cases/airbnb-istio-upgrade-governance/)

### WebAssembly extension

子議題：

- WASM filter：跨語言寫 Envoy extension（Rust / AssemblyScript / Go）
- 跟 Lua（OpenResty 模式）對比
- 適合：custom auth / rate limit / metric collection

### Advanced traffic management

子議題：

- Retry / Circuit breaker / Outlier detection
- Timeout（connect / request / idle）
- Traffic split（canary / blue-green / mirror）
- Rate limit（local + global）

## 排錯快速判讀

### Config sync 失敗

操作原則：xDS control plane 連不上 / config 格式錯。判讀：admin /stats 看 update_failure、/config_dump 看當前 config。

### Listener config error

操作原則：YAML 格式錯、port 衝突、bind address 錯。判讀：startup log + admin /listeners。

### Cluster endpoint 全 unhealthy

操作原則：health check 失敗、SDS 沒提供 cert、network 不通。判讀：admin /clusters 看 endpoint state。

### Circuit breaker trip

操作原則：upstream 失敗率 > threshold、Envoy 主動切。判讀：admin /stats 看 cb 相關 metric。

### Tracing missing spans

操作原則：tracer config + sampler rate 設錯、context propagation 不對。對應 [04 observability OTel](/backend/04-observability/vendors/opentelemetry/)。

## 何時改走其他服務

| 需求形狀                    | 改走                                                        |
| --------------------------- | ----------------------------------------------------------- |
| 配置簡單 / 小場景           | [nginx](/backend/05-deployment-platform/vendors/nginx/)     |
| Cloud-native auto-discovery | [Traefik](/backend/05-deployment-platform/vendors/traefik/) |
| AWS managed                 | [AWS ELB](/backend/05-deployment-platform/vendors/aws-elb/) |
| K8s ingress only            | Ingress-nginx / Envoy Gateway / Gateway API                 |
| Service mesh control plane  | Istio / Linkerd / Consul Connect                            |
| Edge proxy / CDN            | Cloudflare / Fastly / CloudFront                            |

## 不在本頁內的主題

- 完整 Envoy YAML schema reference
- xDS protocol binary format
- 各 Istio / Gloo / Emissary 細節（見各自 docs）
- Envoy C++ filter 開發

## 案例回寫

### 直接相關案例

| 案例                                                                                                   | 主討論議題                                                  |
| ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------- |
| [5.C7 Airbnb Istio governance](/backend/05-deployment-platform/cases/airbnb-istio-upgrade-governance/) | Envoy-based service mesh 在大規模叢集的分批升級與可重播流程 |

### 跨 vendor 對照

| 案例                                                                                                            | 對 Envoy 的對應                                                        |
| --------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| [5.C1 Tradeshift self-managed → EKS](/backend/05-deployment-platform/cases/tradeshift-self-managed-k8s-to-eks/) | Tradeshift 選 Linkerd（非 Envoy）做切流、對照 Envoy/Istio 的取捨       |
| [5.C9 cutover without drain](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/)     | Envoy outlier detection / circuit breaker / draining listener 是回退面 |
| [5.C10 規模對照](/backend/05-deployment-platform/cases/contrast-platform-migration-by-scale/)                   | 大規模 / 複雜 traffic / 多 DC → Envoy mesh 才能撐住協同節奏            |

**待補 Envoy 案例**：Lyft 自家 Envoy production 案例、Stripe / Reddit 用 Envoy 邊緣案例、Envoy Gateway 早期 adopter。

## 下一步路由

- 上游概念：[5.3 LB Contract](/backend/05-deployment-platform/load-balancer-contract/)
- 平行 vendor：[nginx](/backend/05-deployment-platform/vendors/nginx/)、[Traefik](/backend/05-deployment-platform/vendors/traefik/)
- 下游能力：[04 observability OTel](/backend/04-observability/vendors/opentelemetry/)、[07 security](/backend/07-security-data-protection/)
