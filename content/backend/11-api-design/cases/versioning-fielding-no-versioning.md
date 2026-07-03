---
title: "11.C14 Fielding：對 API 版本化的建議是「別做」"
date: 2026-07-03
description: "no-versioning 流派的理論錨點：hypermedia 演化取代版本號、與運營現實路線分歧的根源"
weight: 14
tags: ["backend", "api-design", "case-study", "versioning"]
---

這個案例的核心責任是提供 no-versioning 流派的理論錨點。刊載平台是 InfoQ（第三方媒體）、內容為 Fielding 本人一手陳述。

## 觀察

Fielding 在 2014 年訪談明言對 `/v1/` 式介面版本化的建議是「DON'T」：版本化逼 client 要嘛跟著重佈署、要嘛讓舊版成為「permanent lead weight」。他主張 hypermedia as the engine of application state 是 REST 的約束而非選配、控制項應在執行期動態習得、並稱「Versioning interface names only manages change for the API owner's sake」。

## 判讀

no-versioning 立場的前提是 client 動態習得控制項 — 這個前提在大多數 JSON-over-HTTP API 不成立、正是 Stripe / GitHub 實務路線與學院立場分歧的根源。爭論文章用此案例呈現張力、而非判定對錯。

## 對應大綱

版本策略爭論文章（no-versioning 派錨點）、styles/rest/ 交叉。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Roy Fielding on Versioning, Hypermedia, and REST（InfoQ 訪談、Mike Amundsen 採訪、2014）](https://www.infoq.com/articles/roy-fielding-on-versioning/)
