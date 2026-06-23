---
title: "nginx"
date: 2026-05-01
description: "HTTP server / reverse proxy / LB / ingress"
weight: 4
tags: ["backend", "deployment", "vendor"]
---

nginx 是 HTTP server / reverse proxy / load balancer 的事實標準之一、承擔三個責任：HTTP 7 層處理（reverse proxy / TLS termination / static content）、L4 / L7 load balancing、Kubernetes ingress controller（ingress-nginx）。設計取捨偏向「配置簡單 + 效能穩定 + reload 機制成熟」、跟 envoy 比是靜態 config-driven（無 dynamic xDS）。F5 收購後 nginx Plus 是商業版、社群 fork 有 Freenginx / angie。

對「HTTP reverse proxy / LB、TLS termination、K8s ingress、API gateway 入門」這條路徑、nginx 是穩定首選。

## 本章目標

讀完本章後、你應該能：

1. 寫 nginx config（server / location / upstream）
2. 配置 TLS / mTLS + SNI
3. 設計 rate limiting + connection limit
4. 部署 ingress-nginx 到 Kubernetes
5. 評估 nginx vs nginx Plus / OSS fork（Freenginx / angie）

## 最短路徑：5 分鐘把 nginx 跑起來

```bash
# 1. 啟動 nginx（docker）
docker run -d --name nginx-demo -p 80:80 \
  -v "$(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro" nginx:stable-alpine

# 2. 寫 reverse proxy config（nginx.conf 範例）
cat <<'CONF' > nginx.conf
events { worker_connections 1024; }
http {
  upstream backend {
    server app:8080;
  }
  server {
    listen 80;
    location / {
      proxy_pass http://backend;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
    }
  }
}
CONF

# 3. reload + 驗證
nginx -t            # test config syntax
nginx -s reload     # reload without restart（zero-downtime config update）
```

## 日常操作與決策形狀

### nginx config 設計

子議題：

- 階層：events / http / server / location / upstream
- 變數：$host / $remote_addr / $http_<name>
- Include 拆分大 config
- 對應指令：`nginx -T`（dump full config）、`nginx -t`（test）、`nginx -s reload`

### Reverse proxy 配置

子議題：

- proxy_pass / proxy_set_header / proxy_http_version
- proxy_buffering / proxy_request_buffering
- upstream load balancing（round_robin / least_conn / ip_hash）
- 對應 [5.3 LB contract](/backend/05-deployment-platform/load-balancer-contract/)

### TLS termination

子議題：

- ssl_certificate / ssl_certificate_key / ssl_protocols
- SNI（server_name + listen 443 ssl）
- mTLS：ssl_client_certificate + ssl_verify_client
- 對應 [07 security](/backend/07-security-data-protection/) TLS 章

## 進階主題（按需閱讀）

### Rate limiting / connection limit

子議題：

- limit_req_zone + limit_req（leaky bucket）
- limit_conn_zone + limit_conn
- 跟 [knowledge cards rate-limit](/backend/knowledge-cards/rate-limit/) 對照
- 對應威脅建模: [2.6 快取威脅建模](/backend/02-cache-redis/attacker-view-cache-risks/)

### ingress-nginx for Kubernetes

子議題：

- Helm chart 部署
- Ingress resource + Annotations 配置
- ConfigMap + Snippets（power users）
- 跟 [Traefik](/backend/05-deployment-platform/vendors/traefik/) / Gateway API 對比

### OpenResty / Lua extension

子議題：

- OpenResty：nginx + LuaJIT、可寫 Lua handler
- ngx_lua: access / content / log phase handler
- 適合：自訂 auth / dynamic routing
- 對應 envoy WASM extension 對比

### nginx vs nginx Plus / Freenginx / angie

子議題：

- nginx OSS（F5 維護）：basic feature
- nginx Plus（商業）：active health check / dynamic config API / DNS upstream
- Freenginx：2024 社群 fork（不滿 F5 治理）
- angie：另一個 fork、多 commercial extension
- 選擇判讀：dynamic config 重要 → 看 Envoy / Plus；OSS 純社群 → Freenginx / angie

### Performance tuning

子議題：

- worker_processes / worker_connections
- keepalive_timeout / keepalive_requests
- sendfile / tcp_nopush / tcp_nodelay
- 跟 [09 performance capacity](/backend/09-performance-capacity/) 對照

## 排錯快速判讀

### 502 Bad Gateway

操作原則：upstream 不可達 / 回應錯。判讀：`error.log` + upstream health。

### 504 Gateway Timeout

操作原則：proxy_read_timeout / proxy_send_timeout 超過。判讀：upstream 處理時間 vs timeout 配置。

### Connection limit / 502 under load

操作原則：worker_connections 不夠、ephemeral port 耗盡、upstream keepalive 不對。判讀：`netstat` + nginx stub_status。

### SSL handshake failure

操作原則：cipher / protocol mismatch、cert chain incomplete、SNI 不對。判讀：`openssl s_client -connect host:443 -servername host`。

### Reload 不生效

操作原則：`nginx -t` 先 test、新 worker 起來舊 worker drain。若行為怪、檢查是否拿到舊 listening socket。

## 何時改走其他服務

| 需求形狀                    | 改走                                                                     |
| --------------------------- | ------------------------------------------------------------------------ |
| Dynamic config / xDS        | [Envoy](/backend/05-deployment-platform/vendors/envoy/)                  |
| Cloud-native auto-discovery | [Traefik](/backend/05-deployment-platform/vendors/traefik/)              |
| AWS managed                 | [AWS ELB](/backend/05-deployment-platform/vendors/aws-elb/)（ALB / NLB） |
| L4 為主 / 高吞吐            | HAProxy / NLB                                                            |
| Service mesh                | Istio / Linkerd / Consul Connect                                         |
| API Gateway 進階            | Kong / Tyk / Apigee                                                      |

## 不在本頁內的主題

- 完整 nginx directive reference
- ngx_lua / OpenResty 完整教學
- 各 distro nginx 版本差異
- nginx internal architecture

## 案例回寫

### 跨 vendor 對照

| 案例                                                                                                        | 對 nginx 的對應                                                                      |
| ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| [5.C9 cutover without drain](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/) | 切流時 nginx upstream / ingress-nginx 沒做 graceful drain、長連線跟 5xx 一起放大     |
| [5.C10 規模對照](/backend/05-deployment-platform/cases/contrast-platform-migration-by-scale/)               | 小型直接 nginx reverse proxy、中型走 ingress-nginx、大型才考慮 envoy 或 service mesh |

**待補 nginx 案例**：Cloudflare 為何 fork（freenginx）、大規模 ingress-nginx 客戶案例、OpenResty 在 production 的擴展案例。

## 下一步路由

- 上游概念：[5.3 LB Contract](/backend/05-deployment-platform/load-balancer-contract/)
- 平行 vendor：[Envoy](/backend/05-deployment-platform/vendors/envoy/)、[Traefik](/backend/05-deployment-platform/vendors/traefik/)、[AWS ELB](/backend/05-deployment-platform/vendors/aws-elb/)
- 下游能力：[07 security](/backend/07-security-data-protection/)（TLS / WAF）、[09 performance](/backend/09-performance-capacity/)
