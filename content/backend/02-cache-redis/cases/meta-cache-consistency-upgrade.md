---
title: "2.C1 Meta：Cache Consistency 升級"
date: 2026-05-07
description: "快取 invalidation 一致性如何從常見錯誤演進到高可信治理。"
weight: 1
---

這個案例的核心責任是說明快取轉換不只在容量與速度，還包括一致性治理能力。

## 觀察

Meta 指出快取在 promotion、shard move、故障恢復時容易引入不一致，單靠傳統 invalidation 很難在大規模系統維持穩定。

## 判讀

當快取已是核心路徑，資料新鮮度問題會直接變成服務正確性問題。這時候轉換重點不是改一個 TTL，而是把一致性追蹤與異常定位制度化。

## 策略

1. 先定義 inconsistency 來源點與觀測點。
2. 將 mutation tracing 納入治理，而不是只看命中率。
3. 把一致性指標接到告警與回退條件。

## 下一步路由

先回 [2.2 cache aside](/backend/02-cache-redis/cache-aside/) 與 [2.3 TTL/eviction](/backend/02-cache-redis/ttl-eviction/)，再接 [4.17 telemetry data quality](/backend/04-observability/telemetry-data-quality/)。

## 引用源

- [Cache made consistent](https://engineering.fb.com/2022/06/08/core-infra/cache-made-consistent/)
