---
title: "Partition"
date: 2026-06-22
description: "說明事件流如何切分成多個可並行處理的有序片段"
weight: 73
tags: ["backend", "message-queue"]
---

Partition 的核心概念是「把事件流切分成多個可並行處理的片段」。同一 partition 內保留順序，不同 partition 可以平行處理。Partition 數量決定 consumer 的最大並行度 — 一個 [consumer group](/backend/knowledge-cards/consumer-group/) 中 consumer 數量不能超過 partition 數量。

## 概念位置

Partition 是 throughput、ordering 與 hot key 之間的取捨核心。它跟 [topic](/backend/knowledge-cards/topic/) 的關係是：topic 是邏輯分類（order events、payment events），partition 是 topic 內的物理分片。Partition key 決定同一類事件會落到哪個 partition；選錯 key 會造成 hot partition（單一 partition 過載）或讓需要順序的事件被拆散。

在 Kafka 中 partition 是一級概念；RabbitMQ 沒有原生 partition（用多個 queue + consistent hash exchange 模擬）；SQS 沒有顯式 partition（內部自動分片）。

## 使用情境

系統需要 partition 設計的訊號是事件量大且需要水平擴展處理能力。訂單事件可以用 order_id 作為 partition key，讓同一訂單的事件保留順序；若所有高流量商家的訂單都 hash 到同一個 partition，會形成 hot partition。

Partition 數量也影響 [offset](/backend/knowledge-cards/offset/) 管理的複雜度 — 每個 partition 有獨立的 offset，consumer group 的 rebalance 要重新分配 partition ownership。

## 設計責任

Partition 設計要定義 partition key（通常是業務實體 ID）、partition 數量（建議初期設多一點，Kafka partition 數量只能增加不能減少）、順序需求（同 key 保序 vs 全域保序）與 lag 觀測（per-partition lag 能定位 hot partition）。重新分 partition 可能影響順序、consumer group 配置與 replay 範圍。
