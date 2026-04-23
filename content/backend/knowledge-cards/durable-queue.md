---
title: "Durable Queue"
date: 2026-04-23
description: "說明可持久化的 queue 如何在重啟與失敗後保留待處理工作"
weight: 144
---

Durable queue 的核心概念是「待處理工作在 process 重啟或節點故障後仍可被取回」。它把 queue 從記憶體暫存提升為可恢復的工作通道。

## 概念位置

Durable queue 是 [queue](../queue/) 與 [message persistence](../message-persistence/) 的組合，常由 [broker](../broker/) 提供，並搭配 [ack/nack](../ack-nack/)、[retry policy](../retry-policy/) 與 [dead-letter queue](../dead-letter-queue/)。

## 可觀察訊號與例子

當工作可延遲但不可遺失時，durable queue 是常見候選。例如付款後通知、對帳同步、背景轉檔。若僅需在線即時廣播，通常 [pub/sub](../pub-sub/) 成本更低。

## 設計責任

設計時要定義保存期限、重試上限、去重策略、queue lag 告警與回復流程，避免把可靠性責任留給人工排障。
