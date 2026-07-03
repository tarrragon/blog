---
title: "11.C4 Carson Gross：REST 如何變成 REST 的反義詞"
date: 2026-07-03
description: "hypermedia 復興派的語意漂移史重建：JSON 取代 XML、業界停在 Level 2、SPA 脫鉤到 GraphQL 放棄名義"
weight: 4
tags: ["backend", "api-design", "case-study", "rest"]
---

這個案例的核心責任是把 Fielding 的抽象約束翻成工程史敘事、代表 hypermedia 復興派的論證。

## 觀察

Gross 重建語意漂移路徑：XML-RPC / SOAP 時代、JSON 取代 XML（但 JSON 是純資料、不是 hypertext）、RMM 普及但業界停在 Level 2、SPA 讓前端與 REST 原則脫鉤、GraphQL 乾脆放棄 REST 名義。結論：今日的 JSON API 是掛 REST 名的 RPC；真正 RESTful 的是 hypermedia-driven 的 HTML 回應。文中同時承認 GraphQL 對 thick-client 場景是合理選擇。

## 判讀

關鍵教學判準：「REST 的 self-describing 特性是為 uniform client（瀏覽器）設計、machine-to-machine 的 JSON client 用不上」— 這條是復興派與 pragmatic 派唯一共識的觀察、兩派從它推出相反結論、適合當章節的對照樞紐。

## 對應大綱

[Hypermedia 與 HATEOAS 復興](/backend/11-api-design/styles/rest/hypermedia-hateoas-revival/)（主案例、已引用）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [How Did REST Come To Mean The Opposite of REST?（htmx essays、Carson Gross）](https://htmx.org/essays/how-did-rest-come-to-mean-the-opposite-of-rest/)
