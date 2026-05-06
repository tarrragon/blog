---
title: "Queue Contract"
date: 2026-04-23
description: "說明佇列工作在重試、確認與重複投遞上的約定"
weight: 0
---


Queue Contract 的核心概念是「producer、queue 與 consumer 對工作如何被確認與重送達成一致」。它描述的是交付語意，而不是單純的格式。 可先對照 [Queue Depth](/backend/knowledge-cards/queue-depth/)。

## 概念位置

Queue Contract 位在 producer、broker 與 consumer 之間。當工作要可靠排隊與重試時，就需要清楚的 contract。 可先對照 [Queue Depth](/backend/knowledge-cards/queue-depth/)。

## 可觀察訊號

系統需要 queue contract 的訊號是工作可能重試、可能重複投遞，且 consumer 需要知道確認失敗後會發生什麼。

## 接近真實網路服務的例子

ack / nack、retry、dead-letter、duplicate delivery 與 redelivery 都屬於 queue contract 的範圍。

## 設計責任

Queue Contract 要定義確認語意、重試策略、重送條件、隔離方式與去重責任，避免 broker 與 consumer 對失敗結果理解不同。
