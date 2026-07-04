---
title: "11.C72 AWS retry 指南：retry storm 的官方定義與分層限制"
date: 2026-07-04
description: "Well-Architected 逐字定義 retry storm、建議低層服務 retry 上限 0-1 次、把 retry 委派給上層；Builders' Library 的 token bucket 路線"
weight: 72
tags: ["backend", "api-design", "case-study", "error-contract"]
---

這個案例的核心責任是提供 retry storm 的官方定義、與「retry 放哪一層」的分層量化建議。

## 觀察

AWS Well-Architected REL05-BP03（Control and limit retry calls）逐字定義：「the network can quickly become saturated with new and retried requests … This can result in a *retry storm*, which will reduce availability of the service」。分層建議逐字：「For services lower in the stack, a maximum retry limit of zero or one can limit risk yet still be effective as retries are delegated to services higher in the stack」。該文件官方引用 AWS Builders' Library 的「Timeouts, retries, and backoff with jitter」（Marc Brooker）—— 該文主張 retry 會放大依賴系統的負載、過載時 retry 讓過載更糟、偏好 token bucket 式的本地 retry 限制（意譯、見下方標注）。

## 判讀

「低層 retry 0-1 次、委派給上層」跟 C69 的跨層疊乘（64 倍）互相印證：retry 是要在架構層分配的預算、不是每層預設行為。token bucket 的本地限制把「retry 是否過量」從每次請求的局部判斷、變成程序級的資源帳 —— consumer 端對 provider 的保護寫成了自己的限流。

## 對應大綱

11.11 接收方重試決策章「retry 放哪一層」「retry budget」段（與 C69 互證）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [REL05-BP03 Control and limit retry calls（AWS Well-Architected）](https://docs.aws.amazon.com/wellarchitected/2022-03-31/framework/rel_mitigate_interaction_failure_limit_retries.html) — 一手官方文件。已 WebFetch 驗證、正文完整取回、逐字引文以此為錨。
- [Timeouts, retries, and backoff with jitter（AWS Builders' Library、Marc Brooker）](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) — 一手、但新站為 JS 渲染、WebFetch 僅取得頁殼。

## 二手來源與狀態標注

Builders' Library 的措辭（retry 放大、token bucket）為意譯 —— 逐字引文未能取得（JS 渲染）、以 REL05-BP03 的官方引用與逐字定義為錨。正文需要逐字引用時只引 REL05-BP03。
