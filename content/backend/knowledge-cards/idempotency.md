---
title: "Idempotency"
date: 2026-04-23
description: "說明同一操作執行多次時如何保持結果一致"
weight: 26
---

Idempotency 的核心概念是「同一操作執行一次或多次，最終業務結果相同」。後端系統用 idempotency 保護重試、重複投遞、使用者重送 request 與外部 API timeout。同一則訊息被送達不只一次的情形見 [Duplicate Delivery](/backend/knowledge-cards/duplicate-delivery/)。

## 跟其他概念的關係

Idempotency 是副作用邊界的穩定性設計。查詢通常天然接近 idempotent；建立訂單、扣款、出貨、寄送通知與發放點數都需要額外設計 idempotency key 或狀態檢查——key 作為對外契約的語意（誰生成、存多久、衝突怎麼回）獨立成 [Idempotency Key](/backend/knowledge-cards/idempotency-key/) 卡。重試由誰發起、重試幾次，見 [Retry Policy](/backend/knowledge-cards/retry-policy/)。

## 可觀察訊號與例子

系統需要 idempotency 的訊號是同一 intent 可能重送。使用者按兩次付款、broker 重複投遞付款成功事件、HTTP client timeout 後重試，都可能讓同一業務意圖進入系統多次。

## 判斷條件與後果

Idempotency 的每一個成分各自對應一種重送情形。沒有穩定 key 時，同一個業務意圖的兩次送出無法被認成同一件事；只在應用程式裡檢查，資料庫沒有唯一約束時，兩個同時到達的重送可能都通過檢查並各自寫入；沒有處理紀錄時，處理到一半 crash 之後重送進來，系統分不出上一次做到哪一步；沒有結果查詢時，HTTP client timeout 之後重試的那一方拿不到第一次的結果；過期策略決定 key 保存多久，保存太短時，超過保存期的重送被當成新的操作。這幾種情形各自只在對應的情境下出現，所以測試分別覆蓋連續重送、處理中 crash、外部 API timeout 與 replay。事件批次寫入資料庫時，識別碼由程式在事件產生時產生、寫入用 `ON CONFLICT DO NOTHING` 的做法與實測見 [1.18 高頻計數的寫入與彙總：熱點列的鎖、只新增的事件、可以重跑的彙總與重送的事件](/backend/01-database/high-frequency-counting/)〈重送的事件：識別碼的產生位置與 ON CONFLICT 的寫法〉。
