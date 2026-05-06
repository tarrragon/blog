---
title: "Fallback Plan"
date: 2026-04-23
description: "說明變更失敗時如何回到可接受狀態"
weight: 78
---


Fallback plan 的核心概念是「變更失敗時回到可接受狀態的計畫」。它關注 migration、發版、設定切換或服務替換失敗後的操作路徑。 可先對照 [Fallback](/backend/knowledge-cards/fallback/)。

## 概念位置

Fallback plan 是 release 與 migration 的風險控制。Rollback 是回到舊版本；fallback plan 可以包含暫停流量、切回舊路徑、凍結寫入、啟動維護模式或人工處理。 可先對照 [Fallback](/backend/knowledge-cards/fallback/)。

## 可觀察訊號與例子

系統需要 fallback plan 的訊號是變更會影響資料正確性或核心流量。新付款 provider 上線後錯誤率升高，團隊需要知道如何切回舊 provider、如何處理已送出的交易、如何對帳。

## 設計責任

Fallback plan 要在變更前完成，並明確列出觸發條件、執行者、資料影響、外部溝通與驗證方式。高風險變更應在預備環境演練。
