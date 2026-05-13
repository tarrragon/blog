---
title: "Linearizability"
date: 2026-05-13
description: "每次操作看起來都在單一全域順序中即時生效的一致性語意"
weight: 249
---

Linearizability 的核心概念是「每次讀寫都像在單一時間線上立刻生效，且順序對所有節點一致」。它的責任是提供可直覺驗證的操作語意，常作為 [external-consistency](/backend/knowledge-cards/external-consistency/) 的基礎概念。

## 概念位置

Linearizability 比 eventual 或 session consistency 更強，通常需要跨節點協調與 [quorum](/backend/knowledge-cards/quorum/)。它常用於金融帳務、票務庫存與交易撮合這類不能接受順序錯亂的路徑。

## 可觀察訊號與例子

需要 linearizability 的訊號是「操作先後顛倒會造成不可逆後果」。例如扣款與退款順序錯亂，會讓對帳失敗或合約狀態錯誤。

## 設計責任

採用 linearizability 時要同步管理兩件事：跨區延遲成本與失效時的可用性策略。只保證語意、不設回退與降級，會在網路抖動時讓服務品質急劇下降。
