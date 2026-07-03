---
title: "11.C27 WunderGraph：GraphQL 不該直接暴露在公網"
date: 2026-07-03
description: "介於全開與撤退之間的第三條路：GraphQL 當 server-side 查詢語言、對外只開 persisted operations；vendor 立場需標明"
weight: 27
tags: ["backend", "api-design", "case-study", "graphql"]
---

這個案例的核心責任是提供公開 API 進退光譜的中間選項：persisted queries 家族做法。vendor 創辦人立場、引用時標明利益相關。

## 觀察

兩篇文章的論點：單一 query 可觸發數千次 resolver、middleware 式安全模型失效；introspection 洩漏內部架構；schema traversal 可越權。解法是把 named operations 存在後端、對外轉成 JSON-RPC 式端點、完全不暴露 GraphQL endpoint。後篇補充：versioning 的組織問題 GraphQL 沒解、self-documenting 是迷思、type safety OpenAPI 也有。

## 判讀

「GraphQL 當 server-side 查詢語言、對外只開 persisted operations」是介於全開與撤退之間的第三條路、公開 API 進退章需要這個中間選項。來源是賣此方案的 vendor、立場要標明；但攻擊面描述與 Bessey（C22）、HackerOne（C25）獨立互證。

## 對應大綱

[執行成本與攻擊面](/backend/11-api-design/styles/graphql/graphql-execution-cost-security/)（persisted queries 段、已引用）與 [公開 API 的 GraphQL 進退](/backend/11-api-design/styles/graphql/graphql-public-api-tradeoffs/)（中間路線段、已引用）。邊緣偏反例。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [GraphQL is not meant to be exposed over the internet（WunderGraph blog、Jens Neuse）](https://wundergraph.com/blog/graphql_is_not_meant_to_be_exposed_over_the_internet)
- [Why not use GraphQL?（WunderGraph blog）](https://wundergraph.com/blog/why_not_use_graphql)
