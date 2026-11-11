---
title: "Linearizability"
date: 2026-05-13
description: "每次操作看起來都在單一全域順序中即時生效的一致性語意"
weight: 250
---

Linearizability 的核心概念是「每次讀寫都像在單一時間線上立刻生效，且順序對所有節點一致」。它的責任是提供可直覺驗證的操作語意，常作為 [external-consistency](/backend/knowledge-cards/external-consistency/) 的基礎概念。

## 跟其他概念的關係

Linearizability 比 eventual 或 session consistency 更強，通常需要跨節點協調與 [quorum](/backend/knowledge-cards/quorum/)。它常用於金融帳務、票務庫存與交易撮合這類不能接受順序錯亂的路徑。

## 可觀察訊號與例子

需要 linearizability 的訊號是「操作先後顛倒會造成不可逆後果」。例如扣款與退款順序錯亂，會讓對帳失敗或合約狀態錯誤。

## 判斷條件與後果

採用 linearizability 時，每次讀寫都要跨節點協調、取得 [quorum](/backend/knowledge-cards/quorum/)，部署跨區時每一次操作都付出跨區往返的延遲。網路抖動或部分節點失聯時 quorum 湊不齊，操作只能等待或失敗；沒有事先設定回退與降級策略時，服務的延遲與錯誤率在這段期間直接跟著網路惡化。所以採用時一併決定哪些路徑在失效時必須等待（扣款與退款這類順序錯亂會造成不可逆後果的），哪些路徑可以降到較弱的一致性繼續服務。
