---
title: "Consul"
date: 2026-05-01
description: "Service registry / mesh / KV / DNS"
weight: 9
---

Consul 是 HashiCorp 出品的 service networking 平台、提供 service registry / discovery / health check / KV store / service mesh（Consul Connect）/ DNS interface。多用於非 k8s 環境的 service discovery、跨平台統一 registry。BSL 授權變動同 Terraform。

## 適用場景

- 非 k8s 環境的 service discovery
- 跨平台（VM + container + bare metal）統一 registry
- 需要 KV store + service registry 一體
- Service mesh（Consul Connect）作為 Istio 替代

## 不適用場景

- 純 k8s 環境（k8s 內建 service discovery）
- 不需要跨平台 registry
- 對 BSL 授權敏感（看 fork）

## 跟其他 vendor 的取捨

- vs etcd：etcd 偏 k8s control plane 後端；Consul 偏 service discovery
- vs ZooKeeper：Consul 較現代、health check 內建
- vs Istio / Linkerd：Consul Connect 多平台 mesh

## 預計實作話題

- Agent / Server 拓撲
- Service registration 與 health check
- KV store 與 watch
- Consul Connect（mTLS service mesh）
- DNS interface（Consul DNS）
- BSL 授權影響
