---
title: "TrueTime"
date: 2026-05-13
description: "分散式資料庫用來界定時間不確定性的時間語意機制"
weight: 246
---

TrueTime 的核心概念是「系統回傳一個帶不確定區間的時間視窗，而不是假設時間戳絕對精準」。它的責任是讓跨節點交易排序可以被驗證，而不是只靠每台機器的本地時鐘，通常和 [external-consistency](/backend/knowledge-cards/external-consistency/) 一起討論。

## 跟其他概念的關係

TrueTime 常用於 [global-oltp](/backend/knowledge-cards/global-oltp/) 與 [external-consistency](/backend/knowledge-cards/external-consistency/) 的實作。它把時間誤差顯式化，讓提交順序與可見順序在工程上可檢查、可推導。

## 可觀察訊號與例子

需要 TrueTime 類機制的訊號是「交易先後順序錯誤會造成業務不可接受後果」，例如全球帳務、跨區支付對帳。若業務可接受短暫重排，通常不需要承擔此級別時鐘成本。

## 判斷條件與後果

TrueTime 類機制的寫入延遲跟著時間不確定區間的寬度變動。提交時要等不確定區間過去，才能確定這筆交易的時間戳早於之後的交易，所以區間越寬，每筆提交多等的時間越長，再加上跨區 quorum 的往返，兩項一起計入寫入延遲。業務要求交易順序不可重排時（全球帳務、跨區支付對帳），這段延遲換到的是可驗證的提交順序；業務接受短暫重排時，系統付出同樣的延遲而換到業務用不上的保證，高峰流量下吞吐被這段延遲壓低。
