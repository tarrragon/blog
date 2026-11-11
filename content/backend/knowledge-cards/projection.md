---
title: "Projection"
date: 2026-06-22
description: "說明從事件流或資料變更推算出查詢用讀取視圖的轉換機制"
weight: 161
tags: ["backend", "architecture", "database"]
---

Projection 從事件流或資料變更中持續推算出特定用途的讀取視圖，連接寫入端（事件產生）跟讀取端（查詢消費）。Projection 的輸出是 [read model](/backend/knowledge-cards/read-model/) — 為特定查詢需求反正規化的資料形狀。

## 跟其他概念的關係

Projection 在 [event sourcing](/backend/knowledge-cards/event-sourcing/) 架構中扮演「event → current state」的推算角色。Event log 是 append-only 的事件序列，直接對 event log 做查詢效率低；projection 持續消費事件、維護可查詢的 read model，讓讀取端不需要每次 replay 整條事件流。

Projection 不限於 event sourcing。CDC（Change Data Capture）把資料庫的 row 變更推送到下游、下游建立搜尋索引或統計摘要，這也是 projection — 來源是 row change event 而非 domain event。觀測領域的 [recording rule](/backend/knowledge-cards/recording-rule/) 也是一種 projection — 從 raw time series 持續推算預聚合的 metrics。

## 判斷條件與後果

Projection 的更新策略、重建流程、正確性驗證與 schema evolution，各自決定 read model 在事件寫入、邏輯改版或損壞、程式出錯與事件 schema 改版時的狀態：

**更新策略**：同步（事件寫入時立即更新 read model）時 read model 沒有 lag，代價是 projection 的耗時算進寫入路徑；非同步（事件寫入後由背景消費者更新）時寫入路徑解耦，代價是 read model 落後於事件，讀取端可能讀到舊狀態。

**重建流程**：projection 邏輯改變或 read model 損壞時，read model 只能從 event log 重新 replay 建立。大量事件的 replay 可能需要數小時，重建無法離線執行時，這段期間的線上讀取跟著受影響；重建時間與資源沒有事先估算時，要到需要重建的那一次才知道它能不能在可接受的時間內完成。

**正確性驗證**：projection 是持續運行的計算，任何 bug 都會讓 read model 靜默偏離真實狀態，讀取端不會收到錯誤。沒有定期的 reconciliation（拿 projection 結果跟 event log 全量 replay 比較）時，這種漂移沒有被偵測的管道。

**schema evolution**：來源事件的 schema 改版之後，event log 裡同時有新舊版本的事件，projection 只處理得了新版時，replay 到舊事件就失敗或算錯。這跟 [event sourcing](/backend/knowledge-cards/event-sourcing/) 的 upcasting 問題直接相關。

## 使用情境

需要 projection 的訊號是：讀取需求跟寫入結構不同（列表頁需要反正規化 view、搜尋需要全文索引、報表需要聚合摘要），而且這些讀取視圖需要隨資料變更持續更新而非批次重建。

常見的 projection 實作包括：event handler 更新 read DB、CDC consumer 更新 Elasticsearch index、Kafka Streams 維護 KTable、觀測 collector 做 log-to-metric 轉換。
