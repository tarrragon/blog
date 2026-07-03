---
title: "11.C18 GitHub：採用 GraphQL 的可量化動機"
date: 2026-07-03
description: "REST 佔資料庫層 60% 請求、over/under-fetching 並存的重構動機；什麼規模的痛才值得換風格的錨點"
weight: 18
tags: ["backend", "api-design", "case-study", "graphql"]
---

這個案例的核心責任是記錄大平台採用 GraphQL 的可量化動機。

## 觀察

GitHub 2016 年公開 GraphQL API 時明言：既有 REST API 負責超過 60% 的資料庫層請求、且同時「送太多資料、又缺消費者需要的資料」（over-fetching 與 under-fetching 並存）。技術棧為 graphql-ruby 加 Shopify 的 graphql-batch、公告前已在 production 運行、前後端用 Relay 協作。

## 判讀

採用動機是可量化的基礎設施成本（DB 層負載）、不只是 DX 敘事 — 這讓它成為「什麼規模的 over-fetching 痛才值得換風格」的錨點案例。graphql-batch 出現在 day-one 技術棧、顯示 N+1 是第一天就要面對的問題、不是後期優化。

## 對應大綱

[公開 API 的 GraphQL 進退](/backend/11-api-design/styles/graphql/graphql-public-api-tradeoffs/)（anchor、已引用）、11.2 風格選型交叉。GitHub cluster 之一（C18-C20）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [The GitHub GraphQL API（GitHub engineering blog、2016）](https://github.blog/engineering/the-github-graphql-api/)
