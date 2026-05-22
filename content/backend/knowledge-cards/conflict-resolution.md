---
title: "Conflict Resolution"
date: 2026-05-22
description: "說明並發或離線寫入產生衝突時，如何偵測、呈現與合併成可接受狀態"
weight: 330
---

Conflict Resolution 的核心概念是當兩筆都合法的寫入落在同一份資料上時，用一個明確策略把它們合併成可接受的最終狀態。它讓多裝置同步、離線編輯與多區寫入有確定的結果，代價是要先選定策略並承擔它的取捨。它和事後比對修復的 [Data Reconciliation](/backend/knowledge-cards/data-reconciliation/) 是不同時機 — conflict resolution 是寫入或合併當下的策略，是 [Local-First](/backend/knowledge-cards/local-first/) 系統的核心決策。

## 概念位置

Conflict Resolution 位在多寫入來源收斂成一致狀態的關鍵環節。常見策略有 last-write-wins、欄位層合併、CRDT，以及交給人工或伺服器裁決；每種策略對「哪一筆寫入會被保留」給出不同答案。它和 [Eventual Consistency](/backend/knowledge-cards/eventual-consistency/) 相鄰：最終一致描述系統會收斂，conflict resolution 描述它收斂到什麼結果。

## 可觀察訊號與例子

需要明確 conflict resolution 的訊號是同一份資料會被多個裝置或多個區域並發修改。last-write-wins 實作簡單，但會在兩個使用者同時編輯時靜默覆蓋其中一份 — 對筆記、購物車、協作文件這類場景等於資料遺失。欄位層合併能保留兩邊改的不同欄位，CRDT 能讓特定資料型別自動收斂。

## 設計責任

設計時要先依資料型別與業務後果選策略，再決定衝突要不要讓使用者看見。刪除要當成可傳播的事件處理（tombstone），讓離線裝置上的刪除能正確同步出去。observability 要能看到衝突發生率與被覆蓋的寫入量，讓 last-write-wins 的代價是可量測的，而不是隱形的。
