---
title: "11.C7 Siren spec：表達力更完整、採用曲線停滯"
date: 2026-07-03
description: "帶 first-class actions 的 hypermedia 格式、表達力勝 HAL 而採用更少；client 生態決定格式命運的證據"
weight: 7
tags: ["backend", "api-design", "case-study", "rest"]
---

這個案例的核心責任是跟 HAL 對照、揭露 hypermedia 格式勝出的變數。

## 觀察

Siren 用 entities / actions / links 三元件表達資源、特點是 first-class 的 `actions`（含 method 與欄位、比 HAL 的純連結更接近 HTML form）。採用現狀：約 1.3k stars、最後 release v0.6.2 停在 2017-04、media type `application/vnd.siren+json`。

## 判讀

教學判準：「表達力不是 hypermedia 格式勝出的變數、client 生態才是」— Siren 表達力上更完整（actions 近似 HTML form 的 JSON 化）、採用反而更少。同時支撐 htmx 派「JSON 不是 natural hypermedia」與 pragmatic 派「別等標準收斂」兩邊的決策。

## 對應大綱

[Hypermedia 與 HATEOAS 復興](/backend/11-api-design/styles/rest/hypermedia-hateoas-revival/)（格式現實段、與 HAL 並列、已引用）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Siren: a hypermedia specification（Kevin Swiber、GitHub repo）](https://github.com/kevinswiber/siren)
