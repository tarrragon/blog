---
title: "Retry Policy"
date: 2026-06-22
description: "說明重試策略如何區分暫時性錯誤、永久錯誤與副作用風險"
weight: 25
tags: ["backend", "message-queue"]
---

Retry policy 的核心概念是「定義失敗後何時再試、試幾次、用什麼間隔、何時停止」。重試可以吸收暫時性故障（網路抖動、下游短暫不可用），但也可能放大下游壓力或重複造成副作用，因此跟 [idempotency](/backend/knowledge-cards/idempotency/) 與 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 是成對設計。

## 跟其他概念的關係

Retry policy 跟 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 構成錯誤處理的兩層機制 — retry 處理暫時性失敗，DLQ 承接 retry 耗盡後仍無法處理的訊息。Retry 跟 [idempotency](/backend/knowledge-cards/idempotency/) 是成對的設計 — 有 retry 就要有 idempotent consumer，否則重試可能造成重複扣款、重複發通知。

Retry 跟 [retry storm](/backend/knowledge-cards/retry-storm/) 的關係是：大量 consumer 同時 retry 失敗的訊息會形成下游的流量尖峰，把暫時性故障放大成全系統問題。Exponential backoff + jitter 是緩解 retry storm 的標準做法。

## 使用情境

系統需要 retry policy 的訊號是下游偶發失敗影響成功率。付款查詢 API 短暫 timeout 可以重試；已送出的扣款請求則需要先查詢結果或用 [idempotency](/backend/knowledge-cards/idempotency/) key，避免重試造成重複扣款。

Retry 的判斷分類：暫時性錯誤（5xx、timeout、connection refused）適合 retry；永久性錯誤（4xx、schema validation failure、business rule violation）不應該 retry，直接送 DLQ 或 reject。分類錯誤是 retry policy 最常見的 bug — 對永久性錯誤 retry 只會消耗 quota、延遲問題被發現的時間。

## 判斷條件與後果

Retry policy 的每一個成員缺席時，各有對應的失敗形態：

- **錯誤分類規則**（哪些 error code 算暫時性）缺席：永久性錯誤也被重試，每次都消耗 quota，問題被發現的時間也延後。
- **最大重試次數與停止條件**缺席：失敗的訊息一直重試，永遠不進 DLQ。
- **backoff 策略**只用 fixed 間隔、沒有 jitter：大量 consumer 在同一時刻重試，形成 retry storm。
- **每次 retry 的 timeout** 缺席：一次卡住的呼叫佔掉整段重試時間，後面的重試沒有機會發出。
- **觀測欄位**（retry count、最終結果）缺席：看不出成功是在第幾次重試才達成，重試量上升時也沒有訊號。

高流量系統沒有 retry budget 限制 retry 流量佔總流量的比例時，重試本身會成為下游的負載來源。
