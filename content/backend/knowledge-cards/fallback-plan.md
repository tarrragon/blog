---
title: "Fallback Plan"
date: 2026-04-23
description: "說明變更失敗時如何回到可接受狀態"
weight: 79
---

Fallback plan 的核心概念是「變更失敗時回到可接受狀態的計畫」。它關注 migration、發版、設定切換或服務替換失敗後的操作路徑。 可先對照 [Fallback](/backend/knowledge-cards/fallback/)。

## 跟其他概念的關係

Fallback plan 是 release 與 migration 的風險控制。Rollback 是回到舊版本；fallback plan 可以包含暫停流量、切回舊路徑、凍結寫入、啟動維護模式或人工處理。 可先對照 [Fallback](/backend/knowledge-cards/fallback/)。

## 可觀察訊號與例子

系統需要 fallback plan 的訊號是變更會影響資料正確性或核心流量。新付款 provider 上線後錯誤率升高，團隊需要知道如何切回舊 provider、如何處理已送出的交易、如何對帳。

## 判斷條件與後果

Fallback plan 在變更之前完成，原因是變更失敗之後的那段時間，錯誤率在升高、已送出的交易在累積，臨時擬計畫的每一分鐘都在擴大影響。計畫沒有觸發條件時，錯誤率升到多少才切回沒有共識，切回的時點取決於當下的判斷；沒有執行者時，切回的動作沒有人負責；沒有寫出資料影響時，切回之後才發現新 provider 已經送出的交易要另外對帳；沒有外部溝通時，使用者在切換期間看到的狀態沒有說明；沒有驗證方式時，判斷不了切回之後是否已經回到可接受狀態。高風險變更的 fallback plan 沒有在預備環境演練過時，計畫裡的步驟是否執行得通，要到失敗當下才第一次知道。
