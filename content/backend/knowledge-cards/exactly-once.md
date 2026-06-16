---
title: "Exactly-Once"
date: 2026-06-16
description: "說明訊息剛好被處理一次的語意承諾、它的代價，以及多數時候該用的替代路"
weight: 387
---

Exactly-once 的核心概念是「一則訊息對最終結果剛好生效一次，不漏也不重複」。它是三種投遞語意中最難實作、代價最高的一種，多數系統實際採用的是 at-least-once 投遞加上消費端 idempotency，用較低成本達到等效結果。 可先對照 [Delivery Semantics](/backend/knowledge-cards/delivery-semantics/)。

## 概念位置

Exactly-once 是 [delivery semantics](/backend/knowledge-cards/delivery-semantics/) 的一種，與 at-most-once、at-least-once 並列。真正的 end-to-end exactly-once 需要 broker、producer 與 consumer 在同一套交易邊界內協作（如 Kafka 的 transactional producer + read-committed），成本高且邊界窄。實務上更常用 at-least-once + [idempotency](/backend/knowledge-cards/idempotency/) 處理 [duplicate delivery](/backend/knowledge-cards/duplicate-delivery/)，把「不重複」的責任放到消費端。 可先對照 [Duplicate Delivery](/backend/knowledge-cards/duplicate-delivery/)。

## 可觀察訊號與例子

把 exactly-once 當預設目標是常見的過度設計訊號。多數業務（出貨、扣款、通知）真正需要的是「重複處理不造成重複副作用」，這用 idempotency key 就能達成，不需要 broker 層的 exactly-once 承諾。誤把 at-least-once 系統當成 exactly-once 依賴、消費端不做去重，則是反向的危險假設。

## 設計責任

設計時先問「重複生效的代價是什麼」：可重建投影的事件重複只增加成本、用 at-least-once 即可；會扣款出貨的事件要靠消費端 idempotency 或唯一約束擋重複，而非寄望 broker 的 exactly-once。只有在跨系統交易必須原子、且願意承擔吞吐與複雜度代價時，才採真正的 exactly-once。
