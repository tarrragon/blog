---
title: "Event Log"
date: 2026-04-23
description: "說明事件歷史如何保存、重播與支援跨服務資料重建"
weight: 145
---

Event log 的核心概念是「按時間保存已發生事件的紀錄」。它適合承擔歷史追蹤、重播補送與衍生資料重建，而不是直接取代業務主資料。

## 概念位置

Event log 常搭配 [consumer group](/backend/knowledge-cards/consumer-group/)、[offset](/backend/knowledge-cards/offset/) 與 [replay runbook](/backend/knowledge-cards/replay-runbook/) 使用。正式狀態通常仍由 [source of truth](/backend/knowledge-cards/source-of-truth/) 承擔。

## 可觀察訊號與例子

例如訂單狀態變更可寫入 event log，後續由報表、通知、稽核服務各自消費。當下游落後時，可用 replay 補齊資料。

## 設計責任

設計時要定義事件 schema 演進、保留期限、重播邊界與去重策略，避免把 event log 當成無限制的萬用儲存。
