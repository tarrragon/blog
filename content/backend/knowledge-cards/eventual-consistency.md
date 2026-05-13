---
title: "Eventual Consistency"
date: 2026-05-13
description: "允許短暫不一致、最終收斂到同一資料狀態的一致性語意"
weight: 251
---

Eventual consistency 的核心概念是「節點可以暫時看到不同資料，但在沒有新寫入時最終會收斂一致」。它的責任是用一致性延遲換取可用性與吞吐，常和 [session-consistency](/backend/knowledge-cards/session-consistency/) 對照使用。

## 概念位置

Eventual consistency 常見於多區域 NoSQL、快取同步與讀寫分離系統。它不是「資料可以一直錯」，而是要明確定義可接受的收斂窗口，並以 [bounded-staleness](/backend/knowledge-cards/bounded-staleness/) 或告警閾值管理風險。

## 可觀察訊號與例子

適合 eventual consistency 的訊號是「短暫舊資料可接受，但系統需要高可用與跨區吞吐」。例如社群動態、商品評論、推薦內容。若是支付、庫存扣減這類路徑，通常需要更強語意。

## 設計責任

採用 eventual consistency 時，必須定義補償與對帳機制，讓「最終一致」可驗證。沒有驗證路徑時，最終一致會退化成無法證明的假設。
