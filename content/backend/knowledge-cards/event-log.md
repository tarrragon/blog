---
title: "Event Log"
date: 2026-06-22
description: "說明事件歷史如何保存、重播與支援跨服務資料重建"
weight: 146
tags: ["backend", "architecture", "database"]
---

Event log 按時間保存已發生事件的不可變紀錄，是 [event sourcing](/backend/knowledge-cards/event-sourcing/) 的儲存層。每一筆事件記錄一次狀態變更，整條事件流構成完整的變更歷史。

## 跟其他概念的關係

Event log 是 [event sourcing](/backend/knowledge-cards/event-sourcing/) 的儲存層。在 event sourcing 架構中，event log 是 [source of truth](/backend/knowledge-cards/source-of-truth/)，current state 透過 replay 事件流推算。在非 event sourcing 架構中，event log 是輔助紀錄 — 正式狀態仍由 mutable record 承擔，event log 提供變更歷史跟 replay 能力。

Event log 的讀取面透過 [projection](/backend/knowledge-cards/projection/) 轉換成 [read model](/backend/knowledge-cards/read-model/)，讓消費者不需要每次 replay 整條事件流。在訊息傳遞面，event log 常搭配 [consumer group](/backend/knowledge-cards/consumer-group/)、[offset](/backend/knowledge-cards/offset/) 與 [replay runbook](/backend/knowledge-cards/replay-runbook/) 使用。

## 使用情境

訂單狀態變更可寫入 event log，後續由報表、通知、稽核服務各自消費。當下游落後時，可用 replay 補齊資料。金融帳務的每一筆增減、權限變更的每一次授權與撤銷、訂閱方案的每一次升降級，都是典型的 event log 應用。

## 判斷條件與後果

Event log 的事件寫入之後不再修改，所以每一筆舊事件都要在之後的每一次 replay 裡被讀得懂。新版 consumer 讀不懂舊版事件時，replay 到那一段就失敗，原因是舊事件不會被改寫成新格式。保留期限選無限保留時，event log 可以從頭重建任何時點的狀態，代價是儲存隨寫入量持續成長；選 retention-based 清理時，儲存有上限，代價是清掉的那一段再也 replay 不到，在 event sourcing 架構裡等於失去那段的 [source of truth](/backend/knowledge-cards/source-of-truth/)，所以高頻寫入的系統搭配 snapshot，從 snapshot 之後開始 replay。重播邊界沒有定義時，replay 從哪個 [offset](/backend/knowledge-cards/offset/) 開始要當場判斷，起點太早的那一段事件被處理兩次；consumer 沒有 [idempotency](/backend/knowledge-cards/idempotency/) 時，這些重複處理就變成重複的結果。
