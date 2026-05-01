---
title: "AWS ELB（ALB / NLB / CLB）"
date: 2026-05-01
description: "AWS managed load balancer、ALB（L7）/ NLB（L4）/ CLB（legacy）"
weight: 6
---

AWS ELB 包含 ALB（Application Load Balancer，L7）、NLB（Network Load Balancer，L4）、CLB（Classic，legacy）。是 AWS 生態下流量入口的預設選擇、跟 ECS / EKS / Lambda 深度整合。

## 適用場景

- AWS 生態流量入口
- ALB：HTTP/HTTPS、path-based routing、WebSocket、gRPC
- NLB：TCP/UDP、極低延遲、static IP
- 跟 ACM TLS 憑證自動續期整合

## 不適用場景

- 跨雲需求
- 需要 advanced traffic management（用 envoy / istio）
- 極低成本場景（ALB / NLB 都有 hourly + LCU 成本）

## 跟其他 vendor 的取捨

- vs `nginx` / `envoy` 自管：ELB managed、AWS 整合 vs 自管彈性
- vs CloudFront：ELB 是區域 LB；CloudFront 是 CDN
- vs ALB Ingress Controller / AWS Load Balancer Controller：k8s 內配置 ALB

## 預計實作話題

- ALB target group / listener rule
- NLB cross-zone / preserve client IP
- TLS termination 與 SNI
- ALB Ingress Controller for k8s
- WAF integration
- Idle timeout 與 connection draining
