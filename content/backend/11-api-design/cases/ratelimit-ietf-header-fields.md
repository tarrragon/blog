---
title: "11.C42 IETF RateLimit headers：政策與狀態拆兩個 header"
date: 2026-07-03
description: "限流 header 的承諾邊界：informational only、不是 SLA；active draft、引用標版本"
weight: 42
tags: ["backend", "api-design", "case-study", "rate-limit"]
---

這個案例的核心責任是提供限流語意標準化的現行進展與它明文的承諾邊界。

## 觀察

IETF httpapi WG 的 active draft（版本 11、2026-05、intended Standards Track）定義兩個 response header：`RateLimit-Policy`（靜態配額政策：quota / window / partition key、Structured Fields 語法）與 `RateLimit`（動態剩餘量）。明文「client MUST NOT assume 正配額保證下一請求會被服務」— 配額資訊僅供參考。

## 判讀

政策（policy）與即時狀態（status）拆成兩個 header 是關鍵設計：政策可快取、狀態逐請求變動。「informational only」條款界定了限流 header 的承諾邊界 — 它是禮貌性預警、不是 SLA、這直接回答「對外流量語意承諾到什麼程度」。仍是 draft、引用需標版本與狀態。

## 對應大綱

11.9 對外流量語意（anchor、draft 狀態需明示）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [RateLimit header fields for HTTP（IETF draft、active、v11）](https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/)
