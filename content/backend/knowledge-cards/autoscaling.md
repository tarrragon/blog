---
title: "Autoscaling"
date: 2026-04-23
description: "說明系統如何依負載自動調整服務實例數量"
weight: 153
---


Autoscaling 的核心概念是「依指標自動調整容量」。它適合吸收流量波動，但不是可靠性保證本身。 可先對照 [Backfill](/backend/knowledge-cards/backfill/)。

## 概念位置

常使用 CPU、QPS、queue lag 或自訂業務指標作為擴縮容條件。 可先對照 [Backfill](/backend/knowledge-cards/backfill/)。

## 設計責任

設計時要定義擴縮容門檻、冷啟動成本、最小/最大實例與保護策略，避免擴縮容震盪。
