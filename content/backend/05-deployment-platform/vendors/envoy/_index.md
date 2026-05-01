---
title: "Envoy"
date: 2026-05-01
description: "Cloud-native service proxy、xDS dynamic config、Istio / Gateway 底層"
weight: 5
---

Envoy 是 CNCF graduated 的 service proxy、Lyft 開源、xDS 動態配置 API 強大、是 Istio / Linkerd2-proxy / AWS App Mesh / Gateway API 等的底層實作。原生支援 gRPC / HTTP/2 / HTTP/3。

## 適用場景

- Service mesh data plane
- API Gateway（Envoy Gateway / Emissary / Gloo）
- 需要 dynamic config / xDS
- gRPC / HTTP/2 / HTTP/3 為主
- Advanced traffic management（retry / circuit breaker / outlier detection）

## 不適用場景

- 配置複雜度過高的小場景（用 nginx）
- 不需要 dynamic reconfig

## 跟其他 vendor 的取捨

- vs `nginx`：Envoy dynamic config 與 observability 內建；nginx 配置簡單
- vs Istio：Envoy 是 data plane；Istio 加上 control plane
- vs `traefik`：Traefik auto-discovery；Envoy xDS

## 預計實作話題

- xDS API 與 dynamic config
- Listener / Route / Cluster 模型
- Filter chain（HTTP / network filter）
- Observability（access log / stats / tracing）
- Envoy Gateway / Emissary / Gloo
- WebAssembly extension
