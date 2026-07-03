---
title: "11.C8 Ben Morris：不做 hypermedia 的 pragmatic REST（反例對照）"
date: 2026-07-03
description: "反例對照：逐條拆 HATEOAS 的收益假設在 machine-to-machine 場景不成立的 pragmatic 派立場文"
weight: 8
tags: ["backend", "api-design", "case-study", "rest"]
---

這個案例的核心責任是提供 hypermedia 復興派的對照組：pragmatic 派的完整反對論證。

## 觀察

文章列四條反對論據：client 開發者實務上讀文件直打 endpoint、不會跟連結走（解耦收益落空）；格式無共識、「不會出現資料版的瀏覽器這種 generic REST client」；hypermedia 傳不了資料語意、文件仍不可免；複雜度與 response 膨脹沒有換到等比收益。主張保留 stateless 資源設計的收益、捨 HATEOAS、引 Twitter / Facebook API 為 pragmatic 成功例。

## 判讀

論證方式是逐條拆 HATEOAS 的收益假設（decoupling、discoverability、evolvability）在 machine-to-machine 場景不成立、而非攻擊名詞。教學判準：「HATEOAS 的收益前提是存在會動態跟連結走的 client — 先問你的 client 是誰、再決定投不投 hypermedia」。與 C4 / C5 形成同觀察、反結論的完整對照。

## 對應大綱

[REST 語意學之爭](/backend/11-api-design/styles/rest/rest-semantics-dispute/) 與 [Hypermedia 復興](/backend/11-api-design/styles/rest/hypermedia-hateoas-revival/)（pragmatic 派立場、皆已引用）。反例。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Pragmatic REST APIs without hypermedia and HATEOAS（Ben Morris）](https://www.ben-morris.com/pragmatic-rest-apis-without-hypermedia-and-hateoas/)
