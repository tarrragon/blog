---
title: "External Consistency"
date: 2026-05-13
description: "交易可見順序與外部真實時間順序一致的強一致性語意"
weight: 244
---

External consistency 的核心概念是「系統觀察到的交易順序，必須符合外部世界的先後順序」。它比一般 strong consistency 更強，因為要求與真實時間語意對齊，常出現在 [global-oltp](/backend/knowledge-cards/global-oltp/) 場景。

## 概念位置

External consistency 常見於全球交易資料庫，需配合可驗證時間來源或排序機制。它可視為 linearizability 在跨節點、跨區域交易中的具體工程目標。可對照 [transaction](/backend/knowledge-cards/transaction/) 與 [global-oltp](/backend/knowledge-cards/global-oltp/)。

## 可觀察訊號與例子

需要 external consistency 的訊號是「交易先後顛倒會造成帳務、合約或稽核錯誤」。例如同一帳戶的扣款與退款、同一資產的買賣成交。若業務可接受短暫重排，多數情境不必承擔此級別成本。

## 設計責任

採用 external consistency 要同時設計延遲預算與失效處置。跨區確認必然增加延遲，因此要先界定哪些交易必須此語意、哪些可降級為較弱一致性。
