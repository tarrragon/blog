---
title: "Fallback"
date: 2026-04-23
description: "說明主要路徑失敗時使用替代結果或替代流程的設計責任"
weight: 57
---

Fallback 的核心概念是「主要路徑失敗時使用替代結果或替代流程」。Fallback 可以是 cached data、預設值、簡化頁面、備援服務、延後處理或人工流程。 可先對照 [Partial Failure](/backend/knowledge-cards/partial-failure/)。

## 跟其他概念的關係

Fallback 是 [partial failure](/backend/knowledge-cards/partial-failure/) 與 [degradation](/backend/knowledge-cards/degradation/) 設計的一部分。它能保留使用者流程，但也可能帶來 [stale data](/backend/knowledge-cards/stale-data/)、成本增加、結果品質下降或邏輯分歧。

## 可觀察訊號與例子

系統需要 fallback 的訊號是輔助依賴失敗時仍可提供核心價值。推薦服務失敗時，商品頁可以顯示熱門商品；付款服務失敗時，fallback 可能只允許保留訂單而暫停付款。

## 判斷條件與後果

Fallback 路徑只在主要路徑失敗時啟用，所以它的設定平時沒有被流量驗證過。使用條件沒有標明時，哪一種失敗會切到 fallback 由各處程式碼各自決定；資料新鮮度與使用者文案沒有標明時，使用者看到快取裡的舊資料（[stale data](/backend/knowledge-cards/stale-data/)）而以為是即時的。沒有 [alert](/backend/knowledge-cards/alert/) 與恢復條件時，主要路徑恢復之後系統仍停在 fallback，降級狀態沒有人察覺。容量是另一個條件：事故時原本走主要路徑的流量一次轉到 fallback，fallback 路徑沒有做過測試與容量評估時，會在事故當下跟著失敗，原因是它平時只收到很少的流量。
