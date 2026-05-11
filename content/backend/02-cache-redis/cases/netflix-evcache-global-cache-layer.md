---
title: "2.C6 Netflix：EVCache 全域快取層"
date: 2026-05-07
description: "快取從本地層演進為跨區分散式能力的案例。"
weight: 6
tags: ["backend", "cache", "case-study"]
---

這個案例的核心責任是說明快取在全球服務下會變成平台能力。

## 觀察

Netflix 用 EVCache 支撐大規模低延遲讀取，把快取從單服務實作提升為共用基礎設施。

## 判讀

當讀取延遲目標很嚴格且區域分布廣，快取需要跨區一致性與故障容忍設計。

## 策略

1. 平台化快取客戶端與治理規則。
2. 把失效策略與區域容錯納入同一模型。
3. 以可觀測指標評估命中率與恢復能力。

## 下一步路由

回 [2.1](/backend/02-cache-redis/high-concurrency-access/) 與 [0.7](/backend/00-service-selection/failure-observability-design/)。

## 引用源

- [EVCache](https://netflixtechblog.com/caching-for-a-global-netflix-7bcc457012f1)
