---
title: "Bucket"
date: 2026-04-23
description: "說明 histogram 分桶如何決定觀測解析度與成本"
weight: 99
---


Bucket 的核心概念是「histogram 中用來統計觀測值範圍的界線」。每個 bucket 代表小於等於某個上限的觀測值累積數。 可先對照 [Buffer](/backend/knowledge-cards/buffer/)。

## 概念位置

Bucket 是 histogram 可用性的關鍵。Bucket 應圍繞 SLO 門檻與常見延遲分布設計；錯誤 bucket 會讓 dashboard 看起來有資料，卻回答不了服務是否達標。 可先對照 [Buffer](/backend/knowledge-cards/buffer/)。

## 可觀察訊號與例子

系統需要調整 bucket 的訊號是 p95 / p99 查詢不穩，或 SLO 門檻附近缺乏解析度。若 checkout SLO 是 300ms，bucket 應在 100ms、200ms、300ms、500ms 附近提供足夠區分。

## 設計責任

Bucket 設計要平衡解析度與 cardinality。不同 endpoint 或任務類型可能需要不同 bucket，但過多自訂 bucket 會增加儲存與查詢成本。
