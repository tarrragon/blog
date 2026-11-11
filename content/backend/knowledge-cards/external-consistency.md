---
title: "External Consistency"
date: 2026-05-13
description: "交易可見順序與外部真實時間順序一致的強一致性語意"
weight: 245
---

External consistency 的核心概念是「系統觀察到的交易順序，必須符合外部世界的先後順序」。它比一般 strong consistency 更強，因為要求與真實時間語意對齊，常出現在 [global-oltp](/backend/knowledge-cards/global-oltp/) 場景。

## 跟其他概念的關係

External consistency 常見於全球交易資料庫，需配合可驗證時間來源或排序機制。它可視為 linearizability 在跨節點、跨區域交易中的具體工程目標。可對照 [transaction](/backend/knowledge-cards/transaction/) 與 [global-oltp](/backend/knowledge-cards/global-oltp/)。

## 可觀察訊號與例子

需要 external consistency 的訊號是「交易先後顛倒會造成帳務、合約或稽核錯誤」。例如同一帳戶的扣款與退款、同一資產的買賣成交。若業務可接受短暫重排，多數情境不必承擔此級別成本。

## 判斷條件與後果

External consistency 要求每一筆交易的順序跟真實時間一致，跨區域的交易因此要等其他區域確認之後才提交，延遲至少包含一次跨區往返，原因是順序要在多個區域之間達成一致。所有交易都套這個語意時，連社群動態這類可以接受短暫重排的寫入也付出跨區延遲。只有交易先後顛倒會造成帳務、合約或稽核錯誤時（同一帳戶的扣款與退款），這筆延遲才換得到需要的保證，其餘交易可以用較弱的一致性。採用之後，跨區確認在網路分區或時間來源失效時無法完成，交易要等待或失敗；沒有事先定義這時的處置，使用者看到的是不定時的逾時。
