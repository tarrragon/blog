---
title: "Redelivery Loop"
date: 2026-04-23
description: "說明同一訊息反覆投遞失敗如何消耗 consumer 容量"
weight: 64
---

Redelivery loop 的核心概念是「同一訊息反覆被投遞、失敗、重新排回，再次被投遞」。它會消耗 consumer 容量，並讓正常訊息延遲。

## 概念位置

Redelivery loop 是 retry policy 與 dead-letter 設計不足的訊號。它通常代表錯誤分類、最大重試次數、backoff 或 DLQ 條件缺失。

## 可觀察訊號與例子

系統需要處理 redelivery loop 的訊號是同一 message id 的 redelivery count 持續上升。某筆訂單事件 payload 缺少必要欄位時，每次處理都會失敗，應進入 dead-letter 等待修復。

## 設計責任

防護要包含 redelivery 次數上限、poison message 偵測、dead-letter、告警與 replay runbook。Consumer metrics 應能分辨新訊息處理量與重送訊息處理量。
