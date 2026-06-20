---
title: "模組一：負載平衡與反向代理"
date: 2026-06-20
description: "流量進來怎麼分給多個服務實例 — nginx / HAProxy / DNS round-robin 的選型和健康檢查路由設計"
weight: 1
tags: ["devops", "load-balancing", "reverse-proxy", "nginx", "health-check"]
---

回答「一個入口、多個後端實例，流量怎麼分」。反向代理是 DevOps 最基礎的元件。

## 待寫章節

- [ ] 反向代理的職責（TLS 終止、路由、負載分散、健康檢查）
- [ ] 負載分散演算法（round-robin / least-connections / IP hash / consistent hash）
- [ ] nginx 實務配置（upstream + health_check + 常見 gotcha）
- [ ] 健康檢查路由設計（被動 vs 主動、check interval、unhealthy threshold）
- [ ] 和模組二（水平擴展）的銜接：LB 是水平擴展的前提

## 跨分類引用

- → [monitoring 模組四 Collector 架構](/monitoring/04-collector/)：Collector 多實例部署時的 LB 設計
- → [backend 部署平台](/backend/05-deployment-platform/)：PaaS / container 的 LB 內建 vs 自管
