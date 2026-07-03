---
title: "11.C40 IETF Idempotency-Key draft：標準化停在 expired"
date: 2026-07-03
description: "de facto 先於 de jure 的具體例：業界事實標準先行、IETF 標準化跟進後停滯；引用必標 expired 狀態"
weight: 40
tags: ["backend", "api-design", "case-study", "idempotency"]
---

這個案例的核心責任是記錄冪等鍵標準化的現狀：業界實作先行、正式標準停滯。

## 觀察

IETF httpapi WG 的 Internet-Draft 定義 `Idempotency-Key` request header、使 POST / PATCH 可容錯重試；取代更早的個人 draft；推進到版本 07 後過期、狀態為 expired（不再 active）。

## 判讀

「de facto 先於 de jure」的具體例：Stripe / PayPal 等支付商的實作是事實標準、IETF 標準化跟進但停滯。寫 API 時該遵循的是 draft 的語意骨架加具體 vendor 的契約細節、且不能宣稱「這是 RFC」— 引用時必須標明 expired draft 狀態。

## 對應大綱

11.8 API 層冪等設計、idempotency key 標準化爭論文章。邊緣（狀態需明示）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [The Idempotency-Key HTTP Header Field（IETF draft、expired、v07）](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/)
