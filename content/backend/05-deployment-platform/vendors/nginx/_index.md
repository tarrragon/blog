---
title: "nginx"
date: 2026-05-01
description: "HTTP server / reverse proxy / LB / ingress"
weight: 4
---

nginx 是 HTTP server / reverse proxy / load balancer 的事實標準之一、配置簡單、效能穩定。在 Kubernetes 生態作為 ingress controller（ingress-nginx）。OpenResty 提供 Lua 擴展、F5 收購後 nginx Plus 商業版本。

## 適用場景

- HTTP reverse proxy / LB
- Static content serving
- TLS termination
- Kubernetes ingress controller
- API gateway 入門

## 不適用場景

- 需要 advanced traffic management（用 envoy / istio）
- 需要 dynamic config 大量更新（reload 成本）
- gRPC / WebSocket 為主場景（envoy 更原生）

## 跟其他 vendor 的取捨

- vs `envoy`：nginx 配置簡單；envoy dynamic config 與 xDS 強大
- vs `traefik`：traefik cloud-native、auto-discovery
- vs `haproxy`：haproxy L4 強；nginx L7 強
- vs `aws-elb`：nginx 自管；ELB managed

## 預計實作話題

- Reverse proxy 配置
- TLS / mTLS
- Rate limiting / connection limit
- ingress-nginx controller
- OpenResty / Lua 擴展
- nginx vs nginx Plus / OSS fork（Freenginx / angie）
