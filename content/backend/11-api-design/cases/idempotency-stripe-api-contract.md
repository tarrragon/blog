---
title: "11.C39 Stripe 冪等鍵契約條款：24h 保存、500 也重放"
date: 2026-07-03
description: "可承諾的冪等契約細節：重放的是該次請求的結局而非成功結果、同 key 不同參數即錯"
weight: 39
tags: ["backend", "api-design", "case-study", "idempotency"]
---

這個案例的核心責任是提供冪等鍵「可承諾的 what」、跟 C38 的「why」互補。

## 觀察

Stripe API reference 條款：key 最長 255 字元、建議 UUIDv4；保存至少 24 小時、逾期後同 key 視為新請求；replay 回傳首次請求的 status code 加 body、包含 500 錯誤也照樣快取重放；同 key 不同參數直接報錯；只作用於 POST、GET / DELETE 無效。

## 判讀

「500 也重放」是自建實作最容易做錯的條款 — 快取的是「該次請求的結局」而非「成功結果」、否則同 key 重試會在 server 錯誤後產生第二次執行。「參數不符即錯」把 key 綁定到請求語意、防止 key 被當 session id 濫用。

## 對應大綱

11.8 API 層冪等設計（anchor）、idempotency key 標準化爭論文章。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Idempotent requests（Stripe API reference）](https://docs.stripe.com/api/idempotent_requests)
