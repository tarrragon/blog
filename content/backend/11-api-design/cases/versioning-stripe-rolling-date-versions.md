---
title: "11.C10 Stripe：日期滾動版本與 version change module"
date: 2026-07-03
description: "把相容性從路由層搬進轉換層、breaking change 成本由服務端一次吸收；date-based versioning 的原型案例"
weight: 10
tags: ["backend", "api-design", "case-study", "versioning"]
---

這個案例的核心責任是說明 date-based rolling versioning 的機制與成本結構。

## 觀察

Stripe 用日期型滾動版本（如 `2017-05-24`）、帳號首次呼叫 API 時自動 pin 住當時版本、可用 `Stripe-Version` header 覆寫。內部用 version change module 封裝每個 breaking change、response 依時間反向流過模組鏈、轉換成使用者 pin 的版本形狀。截至 2017 年累積約 100 個 backwards-incompatible 升級、維持與 2011 年以來每一版相容。

## 判讀

把「相容性」從 API 路由層（/v1、/v2）搬進轉換層、breaking change 的成本由服務端一次吸收、而非攤到所有 client。宣示性的變更定義讓 changelog 與版本感知文件可自動生成 — 版本策略是基礎設施投資、不是命名慣例。

## 對應大綱

11.5 版本策略與 deprecation（anchor、機制主展開）、11.1 成本分配段交叉、版本策略爭論文章。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [APIs as infrastructure: future-proofing Stripe with versioning（Stripe blog、Brandur Leach、2017）](https://stripe.com/blog/api-versioning)
