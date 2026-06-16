---
title: "Processing Semantics"
date: 2026-06-16
description: "說明 consumer 處理事件後業務結果是否正確，與投遞成功分屬不同責任"
weight: 376
---

Processing semantics 的核心概念是「consumer 處理事件後，業務結果是否正確」。broker 把訊息送到只代表投遞成功，consumer 的副作用是否正確是另一層責任。它回答副作用能否承受重複、亂序與部分失敗。 可先對照 [Delivery Semantics](/backend/knowledge-cards/delivery-semantics/)。

## 概念位置

Processing semantics 位在 delivery 與 [recovery semantics](/backend/knowledge-cards/recovery-semantics/) 之間。投遞語意把訊息交給 consumer，處理語意決定這次處理是否讓系統狀態正確，依賴 [idempotency](/backend/knowledge-cards/idempotency/) 把重複投遞收斂成一次結果。

## 可觀察訊號與例子

同樣是 at-least-once 投遞，寄信 consumer 重複會寄出兩封、開 invoice 重複會重複計帳、search index sync 重複則天生冪等。副作用形狀不同，能承受的處理語意就不同。

## 設計責任

設計時對每個副作用標明能否承受重複、亂序與部分失敗。承受不了的補 idempotency key 或 dedup store，把處理結果穩定在一次。
