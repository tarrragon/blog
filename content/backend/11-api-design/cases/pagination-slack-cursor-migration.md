---
title: "11.C37 Slack：offset 到 opaque cursor 的分頁遷移"
date: 2026-07-03
description: "深頁掃描與 page window 漂移兩個失效模式、opaque cursor 把分頁狀態表示權留在 server 端"
weight: 37
tags: ["backend", "api-design", "case-study", "pagination"]
---

這個案例的核心責任是提供 pagination 決策最乾淨的工程紀錄：明示 tradeoff 的產品決策。

## 觀察

Slack 記錄 offset 的兩個失效模式：`LIMIT / OFFSET` 深頁掃描的丟棄成本、高寫入頻率下 page window 漂移造成跳項或重複。遷移到 Base64 opaque cursor（受 Relay GraphQL spec 啟發）、介面收斂為 `cursor` 加 `limit`、回傳 `next_cursor`；opaque 編碼允許各 endpoint 底層策略不同、甚至在單一 cursor 內編多個 shard 的位置。明列 tradeoff：失去 total count 與跳頁能力。

## 判讀

opaque cursor 的核心價值是「把分頁狀態的表示權留在 server 端」— client 不能解析就不能依賴內部格式、這是介面演化自由度的直接來源。「犧牲跳頁換一致性與效能」是明示的產品決策、不是技術妥協。

## 對應大綱

11.7 集合介面設計（anchor）、分頁爭論文章。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Evolving API Pagination at Slack（Slack engineering blog）](https://slack.engineering/evolving-api-pagination-at-slack/)
