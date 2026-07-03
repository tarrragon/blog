---
title: "11.C21 Shopify：宣告 GraphQL 為唯一 API、REST 轉 legacy"
date: 2026-07-03
description: "跟共存路線相反的策略極端：用新功能只上 GraphQL 製造遷移壓力、配套降成本加倍配額"
weight: 21
tags: ["backend", "api-design", "case-study", "graphql"]
---

這個案例的核心責任是記錄 GraphQL 採用光譜的另一個極端：平台強制遷移。

## 觀察

Shopify 2024-10 宣告 REST Admin API 標為 legacy、不再開發新功能；2025-04-01 起新上架 app 必須只用 GraphQL；配套措施包含 rate limit 加倍、connection query 成本降 75%；部分新能力（2,000 product variants、Metaobjects）只在 GraphQL 提供。

## 判讀

跟 GitHub 的共存路線（C20）相反 — 用「新功能只上 GraphQL」製造遷移壓力。判準案例：「平台對生態系有強制力時才可能 all-in」。成本降 75% 的配套也反向印證 cost-based limiting 是 GraphQL 採用的隱含稅。

## 對應大綱

styles/graphql/「公開 API 的 GraphQL 進退」（anchor）、11.2 風格選型（共存段、已引用）。Shopify cluster（與 C24 graphql-batch 相關）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [All in on GraphQL（Shopify partners blog、2024）](https://www.shopify.com/partners/blog/all-in-on-graphql)
