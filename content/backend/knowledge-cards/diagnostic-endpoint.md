---
title: "Diagnostic Endpoint"
date: 2026-04-23
description: "說明健康檢查、診斷與調試入口如何控制暴露面"
weight: 0
---

Diagnostic Endpoint 的核心概念是「讓平台或工程師查詢服務狀態，但不暴露業務資料」。它包含 [health check](health-check/)、readiness、metrics snapshot、debug info 等入口。

## 概念位置

Diagnostic Endpoint 位在運維系統、負載平衡器、監控工具與 application 之間。它通常不承擔產品功能，而是承擔操作判斷。

## 可觀察訊號

系統需要 diagnostic endpoint 的訊號是平台要判斷服務是否可接流量，或工程師需要快速確認特定狀態，但不想翻 log。

## 接近真實網路服務的例子

[health check](health-check/)、readiness 檢查、liveness 檢查、debug status、版本資訊與依賴健康狀態，都可能透過 diagnostic endpoint 暴露。

## 設計責任

設計時要限制可見資訊、避免透露敏感設定，並把用途與 public API 明確分開。Diagnostic Endpoint 應優先服務平台決策，而不是人手排障的便利性。
