---
title: "Strong Reliability"
date: 2026-04-23
description: "說明高可靠事件路徑需要的保存、重試、去重與回復責任"
weight: 144
---

Strong reliability 的核心概念是「關鍵事件在失敗條件下仍可被恢復到可接受狀態」。它不代表絕對零失敗，而是要求可追蹤、可補償、可驗證。 可先對照 [Message Persistence](/backend/knowledge-cards/message-persistence/)。

## 跟其他概念的關係

高可靠路徑常用在金流、庫存、權限與稽核事件。這些路徑通常需要 [message persistence](/backend/knowledge-cards/message-persistence/)、[retry policy](/backend/knowledge-cards/retry-policy/)、[idempotency](/backend/knowledge-cards/idempotency/)、[dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 與回復流程。

## 可觀察訊號與例子

例如付款成功事件若遺失，可能造成對帳錯誤；這類事件需要保存與補送。相對地，typing indicator 遺失通常不影響核心產品承諾。

## 判斷條件與後果

一個事件是否需要 strong reliability，看它遺失時的失敗代價：付款成功事件遺失會造成對帳錯誤，typing indicator 遺失不影響核心產品承諾，兩者套同一套保證時，不是付款事件保護不足，就是 typing indicator 付出不必要的保存與補送成本。失敗代價決定保證等級（可補送、可去重、可稽核），保證等級沒有寫出來時，[message persistence](/backend/knowledge-cards/message-persistence/)、[retry policy](/backend/knowledge-cards/retry-policy/) 與 [idempotency](/backend/knowledge-cards/idempotency/) 要做到什麼程度沒有依據。保證等級沒有對應的觀測指標與驗證流程時，「可恢復」停在設計時的宣稱，補送路徑走不通要到事故發生才看得出來。[reliability boundary](/backend/knowledge-cards/reliability-boundary/) 劃出哪些路徑屬於高可靠路徑，沒有劃時，同一條流程裡的高可靠事件與一般事件混用同一套處理，保證等級不一致。
