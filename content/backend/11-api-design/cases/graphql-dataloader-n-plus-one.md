---
title: "11.C24 DataLoader 譜系：N+1 的官方解法變成基礎設施"
date: 2026-07-03
description: "resolver-per-field 讓 N+1 從偶發變預設、官方生態把 batching 做成基礎設施而非優化技巧"
weight: 24
tags: ["backend", "api-design", "case-study", "graphql"]
---

這個案例的核心責任是說明 N+1 在 GraphQL 執行模型下的地位轉變與解法譜系。

## 觀察

DataLoader 把單一執行 frame 內的個別 load 合併成 batch、加 per-request 快取；概念源自 Facebook 2010 年的內部 Loader API、早於 GraphQL 開源、跨語言存在（如 Haskell 的 Haxl）。Shopify 維護的 Ruby 版 graphql-batch（loader pattern + promise）被 GitHub 2016 年採用時直接引入、至 2025-09 仍在發版。

## 判讀

N+1 不是 GraphQL 發明的問題、但 resolver-per-field 執行模型讓它從偶發變成預設 — 所以官方生態把 batching 做成基礎設施、不是優化技巧。「連 GitHub day-one 都要帶 graphql-batch」是最直接的教學證據。

## 對應大綱

styles/graphql/「執行成本與安全」（N+1 / dataloader 段、anchor）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [graphql/dataloader（GraphQL 基金會、GitHub repo）](https://github.com/graphql/dataloader)
- [Shopify/graphql-batch（GitHub repo）](https://github.com/Shopify/graphql-batch)
