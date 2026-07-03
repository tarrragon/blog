---
title: "11.C6 HAL spec：JSON hypermedia 標準化的過期 draft"
date: 2026-07-03
description: "在 JSON 上補 hypermedia 最接近成功的一次：有 spec 有生態、標準化止步於過期 IETF draft"
weight: 6
tags: ["backend", "api-design", "case-study", "rest"]
---

這個案例的核心責任是記錄「在 JSON 上補 hypermedia」路線的標準化現狀。

## 觀察

HAL 用 `_links` 與 `_embedded` 兩個保留屬性在 JSON 上表達 hypermedia controls、目標是讓通用函式庫可以在任何 HAL API 上重用（uniform interface）。狀態：IETF Internet-Draft（最新 v11）、已過期歸檔、無標準地位；生態面曾是 Spring HATEOAS 的預設格式。

## 判讀

教學判準：「格式碎片化（HAL / Siren / JSON-LD / Collection+JSON 並立、無一勝出）是 hypermedia JSON 未形成 uniform client 的結構性原因」— 這正是 Fielding 說要把力氣花在 media type 上、而業界沒收斂的實證。

## 對應大綱

[Hypermedia 與 HATEOAS 復興](/backend/11-api-design/styles/rest/hypermedia-hateoas-revival/)（格式現實段、與 Siren 並列、已引用）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [JSON Hypertext Application Language（IETF draft-kelly-json-hal、已過期）](https://datatracker.ietf.org/doc/html/draft-kelly-json-hal-08)
