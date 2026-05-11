---
title: "2.C4 Meta：CacheLib / Kangaroo 分層快取"
date: 2026-05-07
description: "快取從 DRAM-only 轉向分層快取架構的實務案例。"
weight: 4
tags: ["backend", "cache", "case-study"]
---

這個案例的核心責任是說明快取容量壓力升高後，策略會從單層記憶體轉向分層管理。

## 觀察

Meta 透過 CacheLib 與 Kangaroo 把快取結構擴展到記憶體與快閃分層，改善容量與成本平衡。

## 判讀

當熱門資料集合超過 DRAM 經濟範圍時，單層快取會同時遇到成本與命中率瓶頸。

## 策略

1. 定義不同資料熱度的落層策略。
2. 把 eviction 與回補延遲納入共同指標。
3. 驗證分層後 tail latency 與成本曲線。

## 下一步路由

回 [2.3 TTL/eviction](/backend/02-cache-redis/ttl-eviction/) 與 [6.9 capacity/cost](/backend/06-reliability/capacity-cost/)。

## 引用源

- [CacheLib and Kangaroo](https://engineering.fb.com/2021/04/09/core-data/cachelib/)
