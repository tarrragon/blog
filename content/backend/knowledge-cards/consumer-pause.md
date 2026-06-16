---
title: "Consumer Pause"
date: 2026-06-16
description: "說明暫停消費作為事故控制手段，止住錯誤副作用擴大"
weight: 379
---

Consumer pause 的核心概念是「主動停止消費，止住錯誤副作用繼續擴大」。當下游故障、毒訊息卡關或處理邏輯有 bug 時，暫停消費讓事件留在 broker、爭取修復時間，是事故當下的控制手段。 可先對照 [Consumer Lag](/backend/knowledge-cards/consumer-lag/)。

## 概念位置

Consumer pause 是事故處理的閥門。暫停期間 [consumer lag](/backend/knowledge-cards/consumer-lag/) 會上升，但事件多半仍在 [replay window](/backend/knowledge-cards/replay-window/) 內，前提是暫停時間短於 retention，恢復後可從原 offset 接續。

## 可觀察訊號與例子

下游資料庫過載時，繼續消費只會放大寫入壓力與重試風暴；暫停消費讓壓力停在 broker，下游恢復後再 resume。毒訊息卡住整個 partition 時，暫停加上把該訊息送 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 比硬重試更快止血。

## 設計責任

設計時讓消費可被快速暫停與恢復，並把 pause、drain、resume 的決策與時點記進 decision log，避免暫停後忘記恢復造成 lag 無聲累積。
