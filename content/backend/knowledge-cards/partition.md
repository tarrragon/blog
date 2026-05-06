---
title: "Partition"
date: 2026-04-23
description: "說明事件流如何切分成多個可並行處理的有序片段"
weight: 73
---


Partition 的核心概念是「把事件流切分成多個可並行處理的片段」。同一 partition 內通常保留順序，不同 partition 可以平行處理。 可先對照 [Percentile](/backend/knowledge-cards/percentile/)。

## 概念位置

Partition 是 throughput、ordering 與 hot key 的取捨。Partition key 決定同一類事件會落到哪裡；選錯 key 可能造成單一 partition 過熱，或讓需要順序的事件被拆散。 可先對照 [Percentile](/backend/knowledge-cards/percentile/)。

## 可觀察訊號與例子

系統需要 partition 設計的訊號是事件量很大且需要水平擴展。訂單事件可以用 order id 作為 partition key，讓同一訂單的事件保留順序；若全部熱門訂單落到同一 key，會形成 hot partition。

## 設計責任

Partition 設計要定義 key、順序需求、partition 數、擴展策略與 lag 觀測。重新分 partition 可能影響順序、重放與 consumer group 配置。
