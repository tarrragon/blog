---
title: "Retry Policy"
date: 2026-06-22
description: "說明重試策略如何區分暫時性錯誤、永久錯誤與副作用風險"
weight: 24
tags: ["backend", "message-queue"]
---

Retry policy 的核心概念是「定義失敗後何時再試、試幾次、用什麼間隔、何時停止」。重試可以吸收暫時性故障（網路抖動、下游短暫不可用），但也可能放大下游壓力或重複造成副作用，因此跟 [idempotency](/backend/knowledge-cards/idempotency/) 與 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 是成對設計。

## 概念位置

Retry policy 跟 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 構成錯誤處理的兩層機制 — retry 處理暫時性失敗，DLQ 承接 retry 耗盡後仍無法處理的訊息。Retry 跟 [idempotency](/backend/knowledge-cards/idempotency/) 是成對的設計 — 有 retry 就要有 idempotent consumer，否則重試可能造成重複扣款、重複發通知。

Retry 跟 [retry storm](/backend/knowledge-cards/retry-storm/) 的關係是：大量 consumer 同時 retry 失敗的訊息會形成下游的流量尖峰，把暫時性故障放大成全系統問題。Exponential backoff + jitter 是緩解 retry storm 的標準做法。

## 使用情境

系統需要 retry policy 的訊號是下游偶發失敗影響成功率。付款查詢 API 短暫 timeout 可以重試；已送出的扣款請求則需要先查詢結果或用 [idempotency](/backend/knowledge-cards/idempotency/) key，避免重試造成重複扣款。

Retry 的判斷分類：暫時性錯誤（5xx、timeout、connection refused）適合 retry；永久性錯誤（4xx、schema validation failure、business rule violation）不應該 retry，直接送 DLQ 或 reject。分類錯誤是 retry policy 最常見的 bug — 對永久性錯誤 retry 只會消耗 quota、延遲問題被發現的時間。

## 設計責任

Retry policy 要包含最大重試次數、backoff 策略（fixed / exponential / exponential + jitter）、每次 retry 的 timeout、錯誤分類規則（哪些 error code 算暫時性）、觀測欄位（retry count、最終結果）與停止條件（超過 N 次進 DLQ）。高流量系統還要設定 retry budget — 限制 retry 流量佔總流量的比例，避免 retry 自身成為負載來源。
