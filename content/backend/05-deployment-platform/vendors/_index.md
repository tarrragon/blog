---
title: "部署平台 Vendor 清單"
date: 2026-05-01
description: "後端部署、編排、網路入口實作時的常用選擇"
weight: 90
---

本清單列出 backend 服務實作會選用的 deployment / orchestration / network entrypoint vendor / platform。每個 vendor 一個資料夾，先建定位與取捨骨架。

## T1 vendor

- [kubernetes](/backend/05-deployment-platform/vendors/kubernetes/) — container orchestration 主流（含 GKE/EKS/AKS）
- [docker](/backend/05-deployment-platform/vendors/docker/) — container runtime / image 標準
- [systemd](/backend/05-deployment-platform/vendors/systemd/) — VM / 單機 service lifecycle
- [nginx](/backend/05-deployment-platform/vendors/nginx/) — LB / reverse proxy / ingress
- [envoy](/backend/05-deployment-platform/vendors/envoy/) — service proxy、Istio / Gateway 底層
- [aws-elb](/backend/05-deployment-platform/vendors/aws-elb/) — ALB / NLB
- [terraform](/backend/05-deployment-platform/vendors/terraform/) — IaC 主流
- [traefik](/backend/05-deployment-platform/vendors/traefik/) — cloud-native ingress / proxy
- [consul](/backend/05-deployment-platform/vendors/consul/) — service registry / mesh / KV

## 後續擴充

- T2 候選：istio / linkerd（service mesh）、haproxy、nomad、ecs / fargate、cloud-run、fly-io、pulumi
- T3 候選：rancher、openshift、heroku（PaaS）、vercel / railway（PaaS for app）
