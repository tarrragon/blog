---
title: "Projection"
date: 2026-06-22
description: "說明從事件流或資料變更推算出查詢用讀取視圖的轉換機制"
weight: 160
tags: ["backend", "architecture", "database"]
---

Projection 從事件流或資料變更中持續推算出特定用途的讀取視圖，連接寫入端（事件產生）跟讀取端（查詢消費）。Projection 的輸出是 [read model](/backend/knowledge-cards/read-model/) — 為特定查詢需求反正規化的資料形狀。

## 概念位置

Projection 在 [event sourcing](/backend/knowledge-cards/event-sourcing/) 架構中扮演「event → current state」的推算角色。Event log 是 append-only 的事件序列，直接對 event log 做查詢效率低；projection 持續消費事件、維護可查詢的 read model，讓讀取端不需要每次 replay 整條事件流。

Projection 不限於 event sourcing。CDC（Change Data Capture）把資料庫的 row 變更推送到下游、下游建立搜尋索引或統計摘要，這也是 projection — 來源是 row change event 而非 domain event。觀測領域的 [recording rule](/backend/knowledge-cards/recording-rule/) 也是一種 projection — 從 raw time series 持續推算預聚合的 metrics。

## 設計責任

設計 projection 時要定義四個面向：

**更新策略**：同步（事件寫入時立即更新 read model）或非同步（事件寫入後由背景消費者更新）。同步更新延遲低但耦合寫入路徑的效能；非同步更新解耦但 read model 有 lag。

**重建流程**：當 projection 邏輯改變或 read model 損壞時，需要從 event log 重新 replay 建立 read model。重建流程要能離線執行、不影響線上讀取。大量事件的 replay 可能需要數小時，設計時要估算重建時間跟資源需求。

**正確性驗證**：projection 是持續運行的計算，任何 bug 都會讓 read model 靜默偏離真實狀態。需要定期的 reconciliation（拿 projection 結果跟 event log 全量 replay 比較）來偵測漂移。

**schema evolution**：當來源事件的 schema 改版，projection 邏輯要能同時處理新舊版本的事件。這跟 [event sourcing](/backend/knowledge-cards/event-sourcing/) 的 upcasting 問題直接相關。

## 使用情境

需要 projection 的訊號是：讀取需求跟寫入結構不同（列表頁需要反正規化 view、搜尋需要全文索引、報表需要聚合摘要），而且這些讀取視圖需要隨資料變更持續更新而非批次重建。

常見的 projection 實作包括：event handler 更新 read DB、CDC consumer 更新 Elasticsearch index、Kafka Streams 維護 KTable、觀測 collector 做 log-to-metric 轉換。
