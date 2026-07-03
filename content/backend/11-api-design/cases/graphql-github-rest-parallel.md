---
title: "11.C20 GitHub：REST 與 GraphQL 雙軌並行的十年穩態"
date: 2026-07-03
description: "2016 採用者的長期終點是共存而非取代、功能覆蓋不對等被官方明文承認"
weight: 20
tags: ["backend", "api-design", "case-study", "graphql"]
---

這個案例的核心責任是記錄大平台採用 GraphQL 後的長期穩態。

## 觀察

GitHub 官方文件明言「不需要獨佔使用其中一個 API」；GraphQL 建議用於減少請求數與精準取數（mobile、巢狀關聯）、REST 建議給熟悉傳統 HTTP 慣例者；並承認「某功能可能只在其中一個 API 支援」。

## 判讀

2016 年的採用者（C18）在多年後的穩態是雙軌並行、功能覆蓋不對等 — 這是「大平台採用 GraphQL 的長期終點是共存」的最直接證據、支撐「進退」章的結論框架。跟 Shopify 的 all-in 策略（C21）形成兩個極端。

## 對應大綱

styles/graphql/「公開 API 的 GraphQL 進退」（anchor）。GitHub cluster 之一。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Comparing GitHub's REST API and GraphQL API（GitHub docs）](https://docs.github.com/en/rest/about-the-rest-api/comparing-githubs-rest-api-and-graphql-api)
