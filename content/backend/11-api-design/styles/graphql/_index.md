---
title: "GraphQL 流派：schema 演進、執行成本與公開 API 進退"
date: 2026-07-03
description: "versionless 演進的紀律代價、resolver 執行模型的成本與攻擊面、大平台採用與撤退的情境差異"
weight: 2
tags: ["backend", "api-design", "graphql"]
---

GraphQL 的爭論結構跟 REST 不同：定義沒有歧義（spec 明確、基金會治理）、爭的是代價 — client 聲明取數的彈性、由誰在哪一層付出成本。本目錄三篇各追一條代價線：schema 層（versionless 的紀律轉嫁）、執行層（resolver 模型的成本與攻擊面）、組織層（公開 API 的採用與撤退）。中性選型判準見 [11.2 風格選型總覽](/backend/11-api-design/api-style-selection/)。

| 文章                                                                                                   | 主題                                            | 案例支撐                |
| ------------------------------------------------------------------------------------------------------ | ----------------------------------------------- | ----------------------- |
| [Schema 演進：versionless 的紀律代價](/backend/11-api-design/styles/graphql/graphql-schema-evolution/) | 只加不改、deprecation、nullable 預設的因果鏈    | C26                     |
| [執行成本與攻擊面](/backend/11-api-design/styles/graphql/graphql-execution-cost-security/)             | N+1、成本計點、introspection、persisted queries | C19、C22、C24、C25、C27 |
| [公開 API 的 GraphQL 進退](/backend/11-api-design/styles/graphql/graphql-public-api-tradeoffs/)        | 同一技術的多種結局與適用邊界                    | C18、C20-C23、C27       |
