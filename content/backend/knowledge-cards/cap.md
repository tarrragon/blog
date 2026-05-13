---
title: "CAP Theorem"
date: 2026-05-13
description: "分散式系統在網路分區時一致性與可用性的取捨框架"
weight: 248
---

CAP theorem 的核心概念是「當發生網路分區時，系統無法同時保證強一致與完全可用」。它的責任是限制設計者在故障情境下的承諾邊界，而不是提供日常延遲優化答案。可搭配 [pacelc](/backend/knowledge-cards/pacelc/) 一起判讀。

## 概念位置

CAP 只討論 partition 發生時的取捨，不直接回答「平時要快還是要一致」。因此實作決策通常要和 [eventual-consistency](/backend/knowledge-cards/eventual-consistency/) 或 [external-consistency](/backend/knowledge-cards/external-consistency/) 一起看，才不會把框架誤用成口號。

## 可觀察訊號與例子

需要 CAP 判讀的訊號是「跨節點連線不穩時，團隊還在要求同時零錯誤與零拒絕」。例如跨區交易系統在區域斷鏈時，若仍要求所有讀寫立即一致又完全不中斷，最終會讓故障處置策略自相矛盾。

## 設計責任

使用 CAP 時要先定義 partition 下的降級策略：拒絕寫入、接受舊資料、或只保留局部能力。沒有預先定義，事件當下就會把架構問題轉成人工決策壓力。
