---
title: "Webhook"
date: 2026-04-23
description: "說明外部系統回呼事件的接收、驗證與處理邊界"
weight: 155
---


Webhook 的核心概念是「外部系統主動把事件推送到你的 endpoint」。它常用於支付、物流、第三方整合通知。 可先對照 [Website Certificate Lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/)。

## 概念位置

Webhook 通常需要來源驗證、重放防護、重試處理與可追蹤事件 ID。 可先對照 [Website Certificate Lifecycle](/backend/knowledge-cards/website-certificate-lifecycle/)。

## 設計責任

設計時要定義簽章驗證、時窗限制、冪等處理與錯誤回應策略，避免假請求或重放造成狀態錯誤。
