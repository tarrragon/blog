---
title: "8.2 PayPal：支付平台與 NoSQL / build pipelines"
date: 2026-04-23
description: "看 Go 如何處理支付平台、NoSQL proxy 與內部工程流水線"
weight: 2
---

PayPal 的案例很適合拿來理解 Go 在複雜企業系統中的角色。官方案例提到，他們的 NoSQL 與 DB proxy 原本在多執行緒模式下非常複雜，而 Go 的 channels 與 goroutines 幫助團隊把這些條件收斂成更清楚的結構。之後，PayPal 也把 build、test、release pipelines 建在 Go 上。

## 你應該看什麼

- [PayPal Taps Go to Modernize and Scale](https://go.dev/solutions/paypal)

## 這個案例告訴我們什麼

1. Go 不只適合對外服務，也適合內部工程平台。
2. 當系統條件變多時，明確並發模型比隱式 thread 管理更容易維護。
3. Go 的價值常常不是單點效能，而是讓大系統更容易演進。

## 可對照的公開原始碼

- [paypal/paypal-rest-api-specifications](https://github.com/paypal/paypal-rest-api-specifications)
- [paypal/github organization](https://github.com/paypal)

PayPal 的 Go 內部系統細節不會完整公開，但它的公開 API spec 與 SDK 生態，能幫你理解大型支付平台如何維持清楚的外部合約。
