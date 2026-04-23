---
title: "Requeue"
date: 2026-04-23
description: "說明處理失敗的訊息重新排回 queue 時的風險與控制條件"
weight: 63
---

Requeue 的核心概念是「把未完成的訊息重新放回可投遞集合」。它讓暫時失敗的工作有機會再次被處理，但也可能造成同一訊息反覆佔用 consumer。

## 概念位置

Requeue 是 nack / retry 流程的一種選擇。暫時性錯誤可以 requeue；永久性錯誤應進入 dead-letter 或人工處理流程。Requeue 需要搭配次數限制與 backoff。

## 可觀察訊號與例子

系統需要控制 requeue 的訊號是同一訊息反覆進出 queue。外部 API 權限被拒絕時，requeue 只會重複失敗；網路短暫中斷時，requeue 搭配 backoff 可能成功。

## 設計責任

Requeue 設計要包含最大次數、錯誤分類、delay、dead-letter 條件與觀測欄位。Runbook 應能查出 requeue loop 的訊息與原因。
