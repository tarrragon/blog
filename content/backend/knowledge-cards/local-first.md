---
title: "Local-First"
date: 2026-05-22
description: "說明本機優先的資料架構如何讓離線可用，並把同步當成獨立問題"
weight: 334
---

Local-First 的核心概念是讓裝置本機持有資料、離線時功能照常運作，把和其他裝置或伺服器的同步當成次要且獨立的問題。它讓產品在弱網或離線下仍可用、互動沒有網路延遲，代價是要處理多端同步的合併語意。它依賴 [Embedded Database](/backend/knowledge-cards/embedded-database/) 作為本機儲存，依賴 [Conflict Resolution](/backend/knowledge-cards/conflict-resolution/) 處理同步衝突。

## 概念位置

Local-First 位在資料架構的一端，與「伺服器是唯一真相、客戶端只是視圖」相對。它把問題拆成兩層：本機的讀寫與持久性是一層，多端的收斂是另一層。本機層用 [Embedded Database](/backend/knowledge-cards/embedded-database/) 解決；收斂層要面對順序、權威來源與 [Conflict Resolution](/backend/knowledge-cards/conflict-resolution/)，並和 [Eventual Consistency](/backend/knowledge-cards/eventual-consistency/) 相鄰。

## 可觀察訊號與例子

適合 local-first 的訊號是行動或桌面 app 需要離線可用，或互動要求即時回饋，例如筆記、待辦、現場作業 app。需要謹慎的訊號是強一致需求：付款餘額、庫存、權限這類資料若每次都要看到最新的全域狀態，要先設計 read-after-write 路徑，而不是套用純 local-first。

## 設計責任

設計時要先界定哪些資料是 local-first、哪些必須即時和伺服器一致。同步層要決定權威來源、衝突策略，以及刪除如何傳播。observability 要能看到每個裝置的同步落後程度與待同步的本機變更量，讓「離線多久」是可量測的。
