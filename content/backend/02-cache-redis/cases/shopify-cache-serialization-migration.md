---
title: "2.C3 Shopify：快取序列化格式遷移"
date: 2026-05-07
description: "快取 payload 從 Marshal 轉 MessagePack 的遷移策略。"
weight: 3
tags: ["backend", "cache", "case-study"]
---

這個案例的核心責任是說明快取轉換常見的格式遷移如何安全落地。

## 觀察

Shopify 在快取編碼轉換過程使用雙軌策略，先允許新舊格式共存，再逐步收斂。

## 判讀

快取格式轉換本質上是相容性遷移。若一次切換，回退與資料可讀性風險會放大。

## 策略

1. 新格式可編碼就先寫新格式。
2. 編碼失敗回落舊格式，保留服務可用性。
3. 維持一段雙軌期，觀測命中率與錯誤率再收斂。

## 下一步路由

回 [2.2 cache aside](/backend/02-cache-redis/cache-aside/) 與 [6.11 migration safety](/backend/06-reliability/migration-safety/)。

## 引用源

- [Caching Without Marshal Part 2](https://shopify.engineering/caching-without-marshal-part-two-messagepack)
