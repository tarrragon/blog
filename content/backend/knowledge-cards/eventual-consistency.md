---
title: "Eventual Consistency"
date: 2026-05-13
description: "允許短暫不一致、最終收斂到同一資料狀態的一致性語意"
weight: 252
---

Eventual consistency 的核心概念是「節點可以暫時看到不同資料，但在沒有新寫入時最終會收斂一致」。它的責任是用一致性延遲換取可用性與吞吐，常和 [session-consistency](/backend/knowledge-cards/session-consistency/) 對照使用。

## 跟其他概念的關係

Eventual consistency 常見於多區域 NoSQL、快取同步與讀寫分離系統。它不是「資料可以一直錯」，而是要明確定義可接受的收斂窗口，並以 [bounded-staleness](/backend/knowledge-cards/bounded-staleness/) 或告警閾值管理風險。

## 可觀察訊號與例子

適合 eventual consistency 的訊號是「短暫舊資料可接受，但系統需要高可用與跨區吞吐」。例如社群動態、商品評論、推薦內容。若是支付、庫存扣減這類路徑，通常需要更強語意。

## 判斷條件與後果

採用 eventual consistency 而沒有對帳機制時，「最終會收斂」是一個沒有人驗證過的假設：某個節點漏掉一次寫入、收斂永遠不會發生，系統也不會報錯，原因是收斂只在每一次同步都成功的前提下成立。對帳定期比對各節點的資料，把沒有收斂的差異找出來；補償機制把找到的差異修回一致。兩者都有時，收斂窗口可以量測，超出 [bounded-staleness](/backend/knowledge-cards/bounded-staleness/) 或告警閾值時看得到；缺任一項，差異不是找不到就是找到了修不回來。
