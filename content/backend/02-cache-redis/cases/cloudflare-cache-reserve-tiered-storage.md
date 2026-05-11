---
title: "2.C7 Cloudflare：Cache Reserve 分層儲存快取"
date: 2026-05-07
description: "邊緣快取延伸到持久層以降低回源壓力的案例。"
weight: 7
tags: ["backend", "cache", "case-study"]
---

這個案例的核心責任是把快取從短期命中策略擴展到長期容量策略。

## 觀察

Cloudflare Cache Reserve 透過分層儲存延長快取可用性，降低 origin 回源成本。

## 判讀

當熱門資料長尾明顯，僅靠 edge cache 會有命中率上限，需引入分層儲存。

## 策略

1. 定義 edge 與 reserve 的資料分層規則。
2. 把回源成本納入快取策略評估。
3. 監控命中率、延遲與儲存成本三者平衡。

## 下一步路由

回 [2.3](/backend/02-cache-redis/ttl-eviction/) 與 [6.9](/backend/06-reliability/capacity-cost/)。

## 引用源

- [Cloudflare Cache Reserve](https://blog.cloudflare.com/introducing-cache-reserve/)
