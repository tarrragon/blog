---
title: "11.C12 GitHub：REST API calendar versioning 與 24 個月支援承諾"
date: 2026-07-03
description: "date-based versioning 成為大平台收斂方向的證據點、最低支援窗口把 deprecation 成本變成明文契約"
weight: 12
tags: ["backend", "api-design", "case-study", "versioning"]
---

這個案例的核心責任是記錄 date-based versioning 在 Stripe 之後被第二個大平台採納的決策與承諾結構。

## 觀察

GitHub 2022 年為 REST API 引入日期命名版本（如 `2022-11-28`）、client 逐請求用 `X-GitHub-Api-Version` header 選版、承諾新版釋出後舊版至少支援 24 個月。範圍只涵蓋 REST API、GraphQL 與 webhooks 除外。公告明講理由：「不能也不期待 integrator 隨我們調整 API 而不斷更新整合」。

## 判讀

「最低支援窗口」把 deprecation 成本從隱性承諾變成 SLA 式的明文契約。header 選版（而非 URL 路徑）代表版本被視為內容協商、不是資源身分 — 直接對接版本策略爭論文章的 URI vs header 流派分界。

## 對應大綱

11.5 版本策略與 deprecation（anchor）、版本策略爭論文章。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [To infinity and beyond: enabling the future of GitHub's REST API with API versioning（GitHub blog、2022）](https://github.blog/2022-11-28-to-infinity-and-beyond-enabling-the-future-of-githubs-rest-api-with-api-versioning/)
