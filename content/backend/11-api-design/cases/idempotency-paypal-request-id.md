---
title: "11.C41 PayPal-Request-Id：同語意、不同契約的冪等實作"
date: 2026-07-03
description: "跟 Stripe 的三點對照：header 命名、replay 語意（最新狀態 vs 首次結局）、契約精確度"
weight: 41
tags: ["backend", "api-design", "case-study", "idempotency"]
---

這個案例的核心責任是當 Stripe 冪等契約（C39）的對照組、展示無標準狀態下的實作分歧。

## 觀察

PayPal 的冪等 header 名為 `PayPal-Request-Id`；並非所有 API 支援、保存期只寫「a period of time」、細節要查各 API reference；replay 回傳「前次請求的最新狀態」；明示同 ID 並發請求時第二個可能失敗。

## 判讀

與 Stripe 的對照有三點：header 命名不同（無標準的直接後果、呼應 C40）；replay 語意不同 — Stripe 重放「首次結局快照」、PayPal 回「最新狀態」、後者對 async 操作友善但失去 exactly-once 回應保證；契約精確度不同 — Stripe 承諾 24h、PayPal 模糊。這組差異本身就是比較教材。

## 對應大綱

11.8 API 層冪等設計、idempotency key 標準化爭論文章。邊緣（對照組）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Idempotency（PayPal developer docs）](https://developer.paypal.com/api/rest/reference/idempotency/)
