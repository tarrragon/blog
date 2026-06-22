---
title: "Event Log"
date: 2026-06-22
description: "說明事件歷史如何保存、重播與支援跨服務資料重建"
weight: 145
tags: ["backend", "architecture", "database"]
---

Event log 按時間保存已發生事件的不可變紀錄。每一筆事件記錄一次狀態變更，整條事件流構成完整的變更歷史。

## 概念位置

Event log 是 [event sourcing](/backend/knowledge-cards/event-sourcing/) 的儲存層。在 event sourcing 架構中，event log 是 [source of truth](/backend/knowledge-cards/source-of-truth/)，current state 透過 replay 事件流推算。在非 event sourcing 架構中，event log 是輔助紀錄 — 正式狀態仍由 mutable record 承擔，event log 提供變更歷史跟 replay 能力。

Event log 的讀取面透過 [projection](/backend/knowledge-cards/projection/) 轉換成 [read model](/backend/knowledge-cards/read-model/)，讓消費者不需要每次 replay 整條事件流。在訊息傳遞面，event log 常搭配 [consumer group](/backend/knowledge-cards/consumer-group/)、[offset](/backend/knowledge-cards/offset/) 與 [replay runbook](/backend/knowledge-cards/replay-runbook/) 使用。

## 使用情境

訂單狀態變更可寫入 event log，後續由報表、通知、稽核服務各自消費。當下游落後時，可用 replay 補齊資料。金融帳務的每一筆增減、權限變更的每一次授權與撤銷、訂閱方案的每一次升降級，都是典型的 event log 應用。

## 設計責任

設計時要定義事件 schema 演進（新版 consumer 要能消費舊版事件）、保留期限（無限保留 vs retention-based 清理）、重播邊界（從哪個 offset 開始 replay）與去重策略（[idempotency](/backend/knowledge-cards/idempotency/) 保證）。Event log 的儲存成長是長期成本 — 高頻寫入的系統需要 snapshot 機制或 retention 策略來控制。
