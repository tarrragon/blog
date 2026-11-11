---
title: "Local-First"
date: 2026-05-22
description: "說明本機優先的資料架構如何讓離線可用，並把同步當成獨立問題"
weight: 335
---

Local-First 的核心概念是讓裝置本機持有資料、離線時功能照常運作，把和其他裝置或伺服器的同步當成次要且獨立的問題。它讓產品在弱網或離線下仍可用、互動沒有網路延遲，代價是要處理多端同步的合併語意。它依賴 [Embedded Database](/backend/knowledge-cards/embedded-database/) 作為本機儲存，依賴 [Conflict Resolution](/backend/knowledge-cards/conflict-resolution/) 處理同步衝突。

## 跟其他概念的關係

Local-First 位在資料架構的一端，與「伺服器是唯一真相、客戶端只是視圖」相對。它把問題拆成兩層：本機的讀寫與持久性是一層，多端的收斂是另一層。本機層用 [Embedded Database](/backend/knowledge-cards/embedded-database/) 解決；收斂層要面對順序、權威來源與 [Conflict Resolution](/backend/knowledge-cards/conflict-resolution/)，並和 [Eventual Consistency](/backend/knowledge-cards/eventual-consistency/) 相鄰。

## 可觀察訊號與例子

適合 local-first 的訊號是行動或桌面 app 需要離線可用，或互動要求即時回饋，例如筆記、待辦、現場作業 app。需要謹慎的訊號是強一致需求：付款餘額、庫存、權限這類資料若每次都要看到最新的全域狀態，要先設計 read-after-write 路徑，而不是套用純 local-first。

## 判斷條件與後果

哪些資料採 local-first、哪些必須即時和伺服器一致，決定了同步層要處理的範圍。付款餘額、庫存、權限這類要看到最新全域狀態的資料若也走本機優先的路徑，離線期間裝置會依過期的值做決定，原因是本機副本在重新連線之前收不到其他裝置的變更。同步層沒有定出權威來源與衝突策略時，兩台裝置離線期間改了同一筆資料，重新連線後留下哪一份沒有規則可循；刪除沒有傳播規則時，被刪掉的資料會由還留著舊副本的裝置同步回來。每個裝置的同步落後程度與待同步的本機變更量沒有量測時，「離線多久」只能靠使用者回報，同步停住時監控上看不到。
