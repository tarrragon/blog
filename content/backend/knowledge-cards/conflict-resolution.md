---
title: "Conflict Resolution"
date: 2026-05-22
description: "說明並發或離線寫入產生衝突時，如何偵測、呈現與合併成可接受狀態"
weight: 331
---

Conflict Resolution 的核心概念是當兩筆都合法的寫入落在同一份資料上時，用一個明確策略把它們合併成可接受的最終狀態。它讓多裝置同步、離線編輯與多區寫入有確定的結果，代價是要先選定策略並承擔它的取捨。它和事後比對修復的 [Data Reconciliation](/backend/knowledge-cards/data-reconciliation/) 是不同時機 — conflict resolution 是寫入或合併當下的策略，是 [Local-First](/backend/knowledge-cards/local-first/) 系統的核心決策。

## 跟其他概念的關係

Conflict Resolution 位在多寫入來源收斂成一致狀態的關鍵環節。常見策略有 last-write-wins、欄位層合併、CRDT，以及交給人工或伺服器裁決；每種策略對「哪一筆寫入會被保留」給出不同答案。它和 [Eventual Consistency](/backend/knowledge-cards/eventual-consistency/) 相鄰：最終一致描述系統會收斂，conflict resolution 描述它收斂到什麼結果。

## 可觀察訊號與例子

需要明確 conflict resolution 的訊號是同一份資料會被多個裝置或多個區域並發修改。last-write-wins 實作簡單，但會在兩個使用者同時編輯時靜默覆蓋其中一份 — 對筆記、購物車、協作文件這類場景等於資料遺失。欄位層合併能保留兩邊改的不同欄位，CRDT 能讓特定資料型別自動收斂。

## 判斷條件與後果

策略的取捨依資料型別與業務後果而定。last-write-wins 用在兩邊會同時編輯同一份資料的場景（筆記、購物車、協作文件）時，較早的那一份被靜默覆蓋，等於資料遺失；欄位層合併保留兩邊改的不同欄位，CRDT 讓特定資料型別自動收斂，換到的是不遺失寫入，付出的是實作複雜度。策略決定的是保留哪一筆，衝突是否顯示給使用者是策略選定之後的另一個決定。刪除若只是把資料移除，離線裝置同步時看不到這次刪除，它手上的舊資料不會被移除；把刪除記成一筆可傳播的事件（tombstone）時，刪除才同步得到其他裝置。observability 看不到衝突發生率與被覆蓋的寫入量時，last-write-wins 遺失了多少寫入無從得知；量得到時，這個代價可以拿來比較是否換策略。
