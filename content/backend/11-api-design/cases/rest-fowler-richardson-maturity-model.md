---
title: "11.C3 Richardson 成熟度模型：分級階梯與它的自我聲明"
date: 2026-07-03
description: "RMM 四級是理解 REST 元素的思考工具、一手來源自己警告它不是 REST 分級定義；業界停在 Level 2 的參照系"
weight: 3
tags: ["backend", "api-design", "case-study", "rest"]
---

這個案例的核心責任是提供業界最通行的 REST 教學階梯、以及它「不是 REST 認證」的原始 caveat。

## 觀察

模型分四級：Level 0（HTTP 當 RPC 隧道、單一 endpoint）、Level 1（資源化、逐資源 URI）、Level 2（HTTP 動詞與狀態碼正確使用）、Level 3（hypermedia controls / HATEOAS）。Fowler 明文標注：RMM 是理解 REST 元素的思考工具、不是 REST 的分級定義；並記錄 Fielding 的立場 — 只有 Level 3 才算 REST。模型本身出自 Richardson 的 QCon 演講、此文屬權威轉述。

## 判讀

教學價值在雙重性：用 RMM 定位自己的 API 在哪一級是合法用法、拿 RMM 當 REST 認證是誤用。它也是「業界普遍停在 Level 2」這個實證現象的參照系。

## 對應大綱

[Richardson 成熟度的實用讀法](/backend/11-api-design/styles/rest/richardson-maturity-practical-reading/)（骨幹、已引用）、11.3 資源建模（定位工具段、已引用）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Richardson Maturity Model（Martin Fowler、2010）](https://martinfowler.com/articles/richardsonMaturityModel.html)
