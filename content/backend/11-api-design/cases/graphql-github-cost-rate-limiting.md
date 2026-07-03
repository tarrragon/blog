---
title: "11.C19 GitHub：GraphQL point system 成本計點限流"
date: 2026-07-03
description: "GraphQL 打破 per-request 限流假設、平台被迫發明查詢成本模型、加 node 上限雙層防線"
weight: 19
tags: ["backend", "api-design", "case-study", "graphql"]
---

這個案例的核心責任是說明 GraphQL 對傳統限流模型的衝擊與平台的應對設計。

## 觀察

GitHub GraphQL API 依 connection 展開的請求數對每個 query 計 point（總請求數除以 100、最低 1 點）、user 每小時 5,000 點、Enterprise 10,000 點；另有 500,000 node 上限與 `first` / `last` 參數 1-100 的限制；client 可事後查 `rateLimit.cost`、也可事前預估。

## 判讀

一個 request 的成本在 GraphQL 下不再是常數 — per-request rate limiting 的假設被打破、平台被迫發明成本模型。node 上限與分頁參數上限是防執行爆炸的靜態防線、動靜兩層並存本身就是教學重點。

## 對應大綱

[執行成本與攻擊面](/backend/11-api-design/styles/graphql/graphql-execution-cost-security/)（機制主寫、已引用）、[11.9 對外流量語意](/backend/11-api-design/external-traffic-semantics/)（現象層、已引用）。GitHub cluster 之一。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Rate limits and node limits for the GraphQL API（GitHub docs）](https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits-for-the-graphql-api)
