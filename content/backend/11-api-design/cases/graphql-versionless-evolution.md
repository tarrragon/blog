---
title: "11.C26 GraphQL 官方：versionless API 與 nullable-by-default"
date: 2026-07-03
description: "no-versioning 的成本轉嫁鏈：只加不改、deprecation、nullable 預設三個紀律換掉版本號"
weight: 26
tags: ["backend", "api-design", "case-study", "graphql"]
---

這個案例的核心責任是記錄 GraphQL 官方的 versionless 設計哲學與其依賴的紀律。

## 觀察

官方教學明文：GraphQL 只回傳明確請求的資料、所以新能力可以透過新 type 或既有 type 的新 field 加入而不造成 breaking change；「永遠避免 breaking change、提供 versionless API」被稱為 common practice。同時「type system 中每個 field 預設 nullable」、理由包含後端局部故障與細粒度授權。驗證備註：官方站主頁對 fetcher 回 403、內容以官方 GitHub repo 的 source 檔驗證、對外引用用官方教學頁 URL。

## 判讀

no-versioning 的實質是把演進成本轉嫁到三個紀律：只加不改、deprecation 標注、nullable 預設 — 版本管理的工作換了位置、沒有消失。nullable-by-default 正是為了讓局部失敗與授權拒絕不炸掉整個 response — 這條因果鏈是 schema 演進篇的骨幹。可與 WunderGraph 批評（C27）對照：versionless 解 schema 相容、解不了組織層的舊 client 支援。

## 對應大綱

[Schema 演進](/backend/11-api-design/styles/graphql/graphql-schema-evolution/)（anchor、已引用）、11.6 格式層紀律（主引用）、11.2 / 11.5 交叉、版本策略爭論文章。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Schema design（GraphQL 官方教學）](https://graphql.org/learn/schema-design/)
