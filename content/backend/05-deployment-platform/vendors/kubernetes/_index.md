---
title: "Kubernetes"
date: 2026-05-01
description: "Container orchestration 主流、GKE / EKS / AKS / 自管"
weight: 1
---

Kubernetes 是 container orchestration 事實標準、提供 deployment / pod lifecycle / service / ingress / probe / resource limit / rolling update。可自管或用 cloud managed（GKE / EKS / AKS）。是 cloud-native 生態核心。

## 適用場景

- 多服務、多實例的 container orchestration
- 需要 rolling update / blue-green / canary deploy
- 需要 service discovery 與內部 networking
- 跨雲 / 跨環境統一抽象

## 不適用場景

- 單服務、流量適中（過度複雜、用 systemd 或 PaaS）
- 小團隊運維能力不足（k8s 學習曲線陡）
- 極端低延遲需求（網路抽象有 overhead）

## 跟其他 vendor 的取捨

- vs `systemd`：k8s 是 cluster orchestration；systemd 是單機
- vs `docker` 單獨：k8s 用 container runtime（containerd），不是 Docker 替代
- vs ECS / Cloud Run / Nomad：選型路徑見 05 主章

## 預計實作話題

- Pod / Deployment / StatefulSet 設計
- Probe（liveness / readiness / startup）
- Resource limit 與 QoS class
- Rolling update / pod disruption budget
- Ingress controller（nginx / traefik / GLBC / ALB Controller）
- Operator pattern
- Managed（GKE / EKS / AKS）vs 自管
