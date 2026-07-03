---
title: "11.C11 Stripe 現行方案：具名 major release 與相容變更清單"
date: 2026-07-03
description: "同一家公司版本策略隨規模演進的第二個時間切片、附「什麼算 backwards-compatible」的明文清單"
weight: 11
tags: ["backend", "api-design", "case-study", "versioning"]
---

這個案例的核心責任是記錄 Stripe 版本策略的現行切片、跟 2017 blog 構成演進對照。

## 觀察

現行 Stripe docs 描述的方案已從純日期版演進：major release 具名（如 Acacia）、含 backward-incompatible 變更；月度 release 只含相容變更、沿用上一個 major 名。docs 明列「什麼算 backwards-compatible」：新增資源、新增 optional 參數、新增 response property、property 順序改變、opaque string（object ID、可到 255 字元）長度格式改變、新增 event type。

## 判讀

同一家公司的版本策略會隨規模演進 — 2017 blog（C10）與現行 docs 是兩個時間切片、引用時要標時點。「相容變更清單」是變更紀律章的直接教材：把 client 不可依賴的介面性質（ID 長度、欄位順序）明文化、等於劃出契約邊界。

## 對應大綱

11.6 向後相容的變更紀律（清單主展開）、11.5 版本策略、11.1 契約劃界段交叉。與 C10 同 cluster。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Stripe API upgrades（Stripe docs）](https://docs.stripe.com/upgrades)
