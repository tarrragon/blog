---
title: "Retry Policy"
date: 2026-04-23
description: "說明重試策略如何區分暫時性錯誤、永久錯誤與副作用風險"
weight: 24
---


Retry policy 的核心概念是「定義失敗後何時再試、試幾次、用什麼間隔、何時停止」。重試可以吸收暫時性故障，但也可能放大下游壓力或重複造成副作用。 可先對照 [Retry Storm](/backend/knowledge-cards/retry-storm/)。

## 概念位置

Retry 適合網路抖動、暫時 timeout、rate limit 後恢復、broker 短暫中斷等情境。永久性錯誤，例如 payload 格式錯、權限拒絕、業務狀態不允許，應分類處理或送進 dead-letter。 可先對照 [Retry Storm](/backend/knowledge-cards/retry-storm/)。

## 可觀察訊號與例子

系統需要 retry policy 的訊號是下游偶發失敗影響成功率。付款查詢 API 短暫 timeout 可以重試；已送出的扣款請求則需要查詢結果或 idempotency key，避免重試造成重複扣款。

## 設計責任

Retry policy 要包含最大次數、backoff、jitter、timeout、錯誤分類、觀測欄位與停止條件。高流量系統還要避免 retry storm，把重試轉成全系統壓力。
