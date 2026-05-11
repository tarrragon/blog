---
title: "2.C5 Shopify：Write-through Cache 在高讀流量的實作"
date: 2026-05-07
description: "read-heavy 服務如何轉向 write-through 快取模型。"
weight: 5
tags: ["backend", "cache", "case-study"]
---

這個案例的核心責任是把快取從被動補貨模式，轉成資料寫入時即同步更新的模式。

## 觀察

Shopify 在高讀取路徑以 write-through 策略降低 miss 風險，改善熱門資料讀取穩定性。

## 判讀

當 cache miss 成本過高且資料更新可控時，write-through 能降低讀路徑抖動。

## 策略

1. 把寫入流程與快取更新綁定。
2. 對失敗寫入設計補償與重試。
3. 用 hit rate 與 stale rate 檢驗策略收益。

## 下一步路由

回 [2.2 cache aside](/backend/02-cache-redis/cache-aside/) 與 [6.8 release gate](/backend/06-reliability/release-gate/)。

## 引用源

- [How Shop App uses write-through caching](https://shopify.engineering/horizontally-scaling-the-rails-backend-of-shop-app-with-vitess)
