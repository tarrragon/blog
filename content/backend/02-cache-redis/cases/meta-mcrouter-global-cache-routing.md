---
title: "2.C2 Meta：mcrouter 與跨區快取路由"
date: 2026-05-07
description: "快取從單點最佳化演進到分散式路由層的案例。"
weight: 2
tags: ["backend", "cache", "case-study"]
---

這個案例的核心責任是說明快取規模變大後，路由層本身會成為選型主題。

## 觀察

mcrouter 被用來統一處理大量 memcached 流量與跨叢集路由，代表快取已從局部優化變成平台層能力。

## 判讀

當快取服務跨區、跨叢集且請求量極高時，應把路由策略、故障切換與運維一致性視為主議題。

## 策略

1. 把 client 端散落邏輯收斂到路由層。
2. 把跨區路由與故障策略標準化。
3. 用可觀測訊號監控路由品質與新鮮度。

## 下一步路由

回 [2.1 高併發 Redis 邊界](/backend/02-cache-redis/high-concurrency-access/) 與 [5.4 service discovery](/backend/05-deployment-platform/service-discovery/)。

## 引用源

- [Introducing mcrouter](https://engineering.fb.com/2014/09/15/web/introducing-mcrouter-a-memcached-protocol-router-for-scaling-memcached-deployments/)
