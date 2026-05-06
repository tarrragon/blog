---
title: "Delivery Semantics"
date: 2026-04-23
description: "說明事件投遞語意如何定義遺失、重複、順序與補償策略"
weight: 149
---


Delivery semantics 的核心概念是「系統對事件投遞結果的承諾」。它回答訊息可否遺失、可否重複、是否要求順序，以及失敗後如何補償。 可先對照 [Retry Policy](/backend/knowledge-cards/retry-policy/)。

## 概念位置

Delivery semantics 直接影響 [retry policy](/backend/knowledge-cards/retry-policy/)、[idempotency](/backend/knowledge-cards/idempotency/)、[dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 與 [replay runbook](/backend/knowledge-cards/replay-runbook/) 設計。

## 可觀察訊號與例子

例如支付事件通常需要高可靠與去重；typing indicator 通常可接受遺失。兩者應使用不同的 delivery semantics。

## 設計責任

設計時要把語意寫入事件合約與操作流程，避免不同服務對同一事件有不同預設而造成隱性風險。
