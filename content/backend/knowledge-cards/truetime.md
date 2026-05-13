---
title: "TrueTime"
date: 2026-05-13
description: "分散式資料庫用來界定時間不確定性的時間語意機制"
weight: 245
---

TrueTime 的核心概念是「系統回傳一個帶不確定區間的時間視窗，而不是假設時間戳絕對精準」。它的責任是讓跨節點交易排序可以被驗證，而不是只靠每台機器的本地時鐘，通常和 [external-consistency](/backend/knowledge-cards/external-consistency/) 一起討論。

## 概念位置

TrueTime 常用於 [global-oltp](/backend/knowledge-cards/global-oltp/) 與 [external-consistency](/backend/knowledge-cards/external-consistency/) 的實作。它把時間誤差顯式化，讓提交順序與可見順序在工程上可檢查、可推導。

## 可觀察訊號與例子

需要 TrueTime 類機制的訊號是「交易先後順序錯誤會造成業務不可接受後果」，例如全球帳務、跨區支付對帳。若業務可接受短暫重排，通常不需要承擔此級別時鐘成本。

## 設計責任

使用 TrueTime 思路時，要同時管理時間不確定區間、提交延遲與跨區 quorum 代價。若只看一致性語意而忽略延遲成本，系統會在高峰流量下失去可用性彈性。
