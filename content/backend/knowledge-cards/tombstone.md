---
title: "Tombstone"
date: 2026-05-22
description: "說明刪除如何用一筆標記記錄下來，讓刪除事件能跨副本與裝置傳播"
weight: 342
---

Tombstone 的核心概念是用一筆「已刪除」標記來記錄刪除，而不是直接讓資料消失，讓刪除這個事件能跨副本、裝置或下游系統傳播。它讓最終一致系統裡的刪除不會被遺漏。它是 [Conflict Resolution](/backend/knowledge-cards/conflict-resolution/) 與資料同步處理刪除的基礎機制。

## 概念位置

Tombstone 位在「刪除如何被當成事件」的環節。在單一資料庫內，刪除就是移除一列；但在有副本、有離線裝置或有 CDC 下游的系統裡，直接移除會讓其他端不知道「這筆被刪了」。tombstone 把刪除變成一筆可傳播的標記，和 [Eventual Consistency](/backend/knowledge-cards/eventual-consistency/) 一起讓刪除能收斂。它的保留期限要接回 [資料生命週期](/backend/knowledge-cards/data-lifecycle/)。

## 可觀察訊號與例子

需要 tombstone 的訊號是資料會被多端複製或同步，而刪除必須確實傳到每一端。常見失敗是離線裝置重新上線後，把本地還在的「已被刪除資料」同步回伺服器 — 對隱私與合規是實質失效。tombstone 也要設保留期：留太短會讓久未上線的端漏接刪除，留太長會讓墓碑本身累積。

## 設計責任

設計時要決定哪些資料的刪除需要 tombstone、墓碑保留多久、以及何時可以真正清除。保留期要長過預期的最長離線或失聯窗口。observability 要能看到 tombstone 數量與最舊未被所有端確認的刪除。
