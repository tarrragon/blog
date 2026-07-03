---
title: "模組一：負載平衡與反向代理"
date: 2026-06-20
description: "流量進來怎麼分給多個服務實例 — 反向代理職責、負載分散演算法、nginx 實務配置與健康檢查路由設計"
weight: 1
tags: ["devops", "load-balancing", "reverse-proxy", "nginx", "health-check"]
---

反向代理是擋在使用者與後端之間的單一入口，流量進來由它決定分給哪個實例——這是 DevOps 最基礎的元件。這個模組是「單服務營運」路線的第三站：服務探活（模組四）解決了單一實例的死活，接下來是把流量分給多個實例。

## 章節

| 章節                                                                        | 回答什麼問題                                        |
| --------------------------------------------------------------------------- | --------------------------------------------------- |
| [反向代理的職責](/devops/01-load-balancing/reverse-proxy-responsibilities/) | TLS 終止、路由、負載分散、健康檢查、timeout 層級    |
| [負載分散演算法](/devops/01-load-balancing/load-balancing-algorithms/)      | round-robin、least-connections、雜湊、sticky 怎麼選 |
| [nginx 實務配置](/devops/01-load-balancing/nginx-configuration/)            | upstream、被動健康檢查、主動探測的商業版限制        |
| [健康檢查路由設計](/devops/01-load-balancing/health-check-routing/)         | 被動 vs 主動、interval 與 threshold、flapping       |
| [LB 是水平擴展的前提](/devops/01-load-balancing/scaling-prerequisite/)      | 流量分得進、任何實例接任何請求兩個前提              |

## 跨分類引用

- → [monitoring 模組四 Collector 架構](/monitoring/04-collector/)：Collector 多實例部署時的 LB 設計
- → [backend 部署平台](/backend/05-deployment-platform/)：PaaS / container 的 LB 內建 vs 自管
- → [infra 模組三：網路地基](/infra/03-network-foundation/)：ALB 掛在 public subnet、後端在 private subnet 的網路分層設計
- → [infra 模組五：入口上 IaC](/infra/05-core-services/loadbalancer-alb/)：ALB 的 listener、target group、TLS 與健康檢查在 IaC 裡怎麼描述
