---
title: "Redelivery Loop"
date: 2026-04-23
description: "說明同一訊息反覆投遞失敗如何消耗 consumer 容量"
weight: 65
---

Redelivery loop 的核心概念是「同一訊息反覆被投遞、失敗、重新排回，再次被投遞」。它會消耗 consumer 容量，並讓正常訊息延遲。 可先對照 [Redelivery](/backend/knowledge-cards/redelivery/)。

## 跟其他概念的關係

Redelivery loop 是 retry policy 與 dead-letter 設計不足的訊號。它通常代表錯誤分類、最大重試次數、backoff 或 DLQ 條件缺失。 可先對照 [Redelivery](/backend/knowledge-cards/redelivery/)。

## 可觀察訊號與例子

系統需要處理 redelivery loop 的訊號是同一 message id 的 redelivery count 持續上升。某筆訂單事件 payload 缺少必要欄位時，每次處理都會失敗，應進入 dead-letter 等待修復。

## 判斷條件與後果

一筆每次處理都會失敗的訊息（例如 payload 缺少必要欄位）能重送幾次，由 redelivery 次數上限與 poison message 偵測決定。兩者都沒有時，這筆訊息被無限重送，持續佔用 consumer 容量，正常訊息跟著延遲；沒有 dead-letter 時，偵測到了也沒有地方把它移出去等修復。Consumer metrics 不分新訊息與重送訊息時，總處理量看起來正常，loop 消耗掉的容量看不出來。修好之後要把 dead-letter 裡的訊息送回處理，靠的是告警讓人知道它們存在，以及 replay runbook 讓重送可控。
