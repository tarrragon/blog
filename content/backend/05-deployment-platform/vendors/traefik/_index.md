---
title: "Traefik"
date: 2026-05-01
description: "Cloud-native ingress / reverse proxy、auto-discovery"
weight: 8
---

Traefik 是 cloud-native reverse proxy / ingress、強項是 auto-discovery（Docker / Kubernetes / Consul / etc）、dynamic config、ACME 自動 TLS 憑證、配置簡潔。在 Docker / k8s 生態廣泛使用。

## 適用場景

- Docker / Kubernetes 環境的 ingress
- 需要 auto-discovery（labels / annotations / CRD）
- ACME / Let's Encrypt 自動 TLS
- 中小規模、配置簡潔需求

## 不適用場景

- 大規模 / 複雜 traffic management（用 envoy）
- 需要極致效能調校
- 不在 cloud-native 環境

## 跟其他 vendor 的取捨

- vs `nginx`：Traefik auto-discovery；nginx 配置控制力
- vs `envoy`：Traefik 簡潔；Envoy xDS / 高級
- vs ingress-nginx：Traefik CRD-native 配置；ingress-nginx 透過 annotation

## 預計實作話題

- Provider auto-discovery
- Dynamic config（CRD / labels / file）
- ACME 自動憑證
- Traefik Hub（managed）
- Middlewares chain
