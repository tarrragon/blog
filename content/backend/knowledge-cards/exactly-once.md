---
title: "Exactly-Once"
date: 2026-06-16
description: "說明訊息剛好被處理一次的語意承諾、它的代價，以及多數時候該用的替代路"
weight: 388
---

Exactly-once 的核心概念是「一則訊息對最終結果剛好生效一次，不漏也不重複」。它是三種投遞語意中最難實作、代價最高的一種，多數系統實際採用的是 at-least-once 投遞加上消費端 idempotency，用較低成本達到等效結果。 可先對照 [Delivery Semantics](/backend/knowledge-cards/delivery-semantics/)。

## 跟其他概念的關係

Exactly-once 是 [delivery semantics](/backend/knowledge-cards/delivery-semantics/) 的一種，與 at-most-once、at-least-once 並列。真正的 end-to-end exactly-once 需要 broker、producer 與 consumer 在同一套交易邊界內協作（如 Kafka 的 transactional producer + read-committed），成本高且邊界窄。實務上更常用 at-least-once + [idempotency](/backend/knowledge-cards/idempotency/) 處理 [duplicate delivery](/backend/knowledge-cards/duplicate-delivery/)，把「不重複」的責任放到消費端。 可先對照 [Duplicate Delivery](/backend/knowledge-cards/duplicate-delivery/)。

## 可觀察訊號與例子

把 exactly-once 當預設目標是常見的過度設計訊號。多數業務（出貨、扣款、通知）真正需要的是「重複處理不造成重複副作用」，這用 idempotency key 就能達成，不需要 broker 層的 exactly-once 承諾。誤把 at-least-once 系統當成 exactly-once 依賴、消費端不做去重，則是反向的危險假設。

## 判斷條件與後果

選哪一種投遞語意，看一則訊息重複生效的代價。事件只更新可重建的投影時，重複處理只多花一次運算，at-least-once 的代價最低。事件會扣款、出貨時，重複生效就是產品事故；這時 broker 層的 exactly-once 也擋不住重複，原因是它只涵蓋 broker、producer 與 consumer 在同一套交易邊界裡的那一段，consumer 呼叫的外部付款或出貨 API 在邊界之外，所以這類事件靠消費端的 idempotency 或唯一約束擋重複。跨系統的交易必須原子完成、而且吞吐與複雜度的代價可以接受時，end-to-end 的 exactly-once 才換得到它的保證。
