---
title: "2.C8 Meta：TAO 社交圖快取演進"
date: 2026-05-07
description: "社交圖查詢在規模化下如何把快取做成資料層能力。"
weight: 8
tags: ["backend", "cache", "case-study"]
---

這個案例的核心責任是說明快取在高關聯查詢場景會接近資料庫層角色。

## 觀察

Meta TAO 用於社交圖讀取，演進重點在一致性、可擴展性與資料關聯查詢效率。

## 判讀

當查詢負載是高度關聯圖資料，快取策略需從 key-value 轉向資料模型治理。

## 策略

1. 把資料關聯模型納入快取鍵設計。
2. 以一致性窗口設計更新策略。
3. 定期驗證讀取正確性與延遲目標。

## 下一步路由

回 [2.2](/backend/02-cache-redis/cache-aside/) 與 [1.2](/backend/01-database/schema-design/)。

## 引用源

- [TAO: Facebook's Distributed Data Store](https://engineering.fb.com/2013/06/25/core-infra/tao-the-power-of-the-graph/)
