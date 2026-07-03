---
title: "11.C5 htmx HATEOAS essay：透支帳戶的兩種表徵對照"
date: 2026-07-03
description: "同一個 domain 狀態的 HTML 與 JSON 表徵耦合差異、HATEOAS 有無的操作型判別法"
weight: 5
tags: ["backend", "api-design", "case-study", "rest"]
---

這個案例的核心責任是提供 HATEOAS 爭論裡最小可教的具體範例。

## 觀察

essay 用銀行帳戶透支做對照：HTML 回應在透支時只回 deposit 連結 — 業務狀態直接編碼在可用操作裡、client 零業務知識；JSON 回應回 `status: "overdrawn"` 欄位、client 必須靠 out-of-band 文件理解語意與下一步 URL。結論主張 HTML 這類 natural hypermedia 是實作 RESTful 系統的 practical necessity、在 JSON 上疊 hypermedia controls 的做法已被業界廣泛拒絕。

## 判讀

教學判準：「available actions 由誰計算 — server 算完放進 response、還是 client 讀狀態欄位自己算」是 HATEOAS 有無的操作型判別法、比背定義有效。

## 對應大綱

[11.3 資源建模與操作語意](/backend/11-api-design/resource-modeling-operation-semantics/)（範例主寫、已引用）、[Hypermedia 與 HATEOAS 復興](/backend/11-api-design/styles/rest/hypermedia-hateoas-revival/)（範例層引用）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [HATEOAS（htmx essays）](https://htmx.org/essays/hateoas/)
