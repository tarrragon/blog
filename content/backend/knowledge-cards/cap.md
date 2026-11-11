---
title: "CAP Theorem"
date: 2026-05-13
description: "分散式系統在網路分區時一致性與可用性的取捨框架"
weight: 249
---

CAP theorem 的核心概念是「當發生網路分區時，系統無法同時保證強一致與完全可用」。它的責任是限制設計者在故障情境下的承諾邊界，而不是提供日常延遲優化答案。可搭配 [pacelc](/backend/knowledge-cards/pacelc/) 一起判讀。

## 跟其他概念的關係

CAP 只討論 partition 發生時的取捨，不直接回答「平時要快還是要一致」。因此實作決策通常要和 [eventual-consistency](/backend/knowledge-cards/eventual-consistency/) 或 [external-consistency](/backend/knowledge-cards/external-consistency/) 一起看，才不會把框架誤用成口號。

## 可觀察訊號與例子

需要 CAP 判讀的訊號是「跨節點連線不穩時，團隊還在要求同時零錯誤與零拒絕」。例如跨區交易系統在區域斷鏈時，若仍要求所有讀寫立即一致又完全不中斷，最終會讓故障處置策略自相矛盾。

## 判斷條件與後果

Partition 發生時，系統只能在幾種降級之間選一種：拒絕寫入（保住一致、放棄可用）、接受舊資料（保住可用、放棄一致），或只保留局部能力。降級策略事前定義時，斷鏈當下系統依策略切換，事故處理只確認它是否切對；沒有事前定義時，選擇在故障當下由人臨時做，而「零錯誤又零拒絕」的要求在 partition 下無法同時滿足，處置方針自相矛盾，架構層的取捨變成事故現場的人工決策。
