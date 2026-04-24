---
title: "Strong Reliability"
date: 2026-04-23
description: "說明高可靠事件路徑需要的保存、重試、去重與回復責任"
weight: 143
---

Strong reliability 的核心概念是「關鍵事件在失敗條件下仍可被恢復到可接受狀態」。它不代表絕對零失敗，而是要求可追蹤、可補償、可驗證。

## 概念位置

高可靠路徑常用在金流、庫存、權限與稽核事件。這些路徑通常需要 [message persistence](/backend/knowledge-cards/message-persistence/)、[retry policy](/backend/knowledge-cards/retry-policy/)、[idempotency](/backend/knowledge-cards/idempotency/)、[dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 與回復流程。

## 可觀察訊號與例子

例如付款成功事件若遺失，可能造成對帳錯誤；這類事件需要保存與補送。相對地，typing indicator 遺失通常不影響核心產品承諾。

## 設計責任

設計時要定義失敗代價、保證等級、觀測指標與驗證流程，並界定 [reliability boundary](/backend/knowledge-cards/reliability-boundary/)。
