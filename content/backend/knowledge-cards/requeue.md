---
title: "Requeue"
date: 2026-04-23
description: "說明處理失敗的訊息重新排回 queue 時的風險與控制條件"
weight: 64
---

Requeue 的核心概念是「把未完成的訊息重新放回可投遞集合」。它讓暫時失敗的工作有機會再次被處理，但也可能造成同一訊息反覆佔用 consumer。 可先對照 [Resource Limit](/backend/knowledge-cards/resource-limit/)。

## 跟其他概念的關係

Requeue 是 nack / retry 流程的一種選擇。暫時性錯誤可以 requeue；永久性錯誤應進入 dead-letter 或人工處理流程。Requeue 需要搭配次數限制與 backoff。 可先對照 [Resource Limit](/backend/knowledge-cards/resource-limit/)。

## 可觀察訊號與例子

系統需要控制 requeue 的訊號是同一訊息反覆進出 queue。外部 API 權限被拒絕時，requeue 只會重複失敗；網路短暫中斷時，requeue 搭配 backoff 可能成功。

## 判斷條件與後果

Requeue 是否有效，取決於讓訊息失敗的條件在下一次投遞之前是否已經消失。網路短暫中斷這類暫時性錯誤，requeue 加上 delay 讓下一次投遞發生在故障恢復之後，有機會成功；外部 API 權限被拒這類永久性錯誤，requeue 只讓同一則訊息反覆進出 queue，每一輪都佔用 consumer，原因是讓它失敗的條件沒有改變。錯誤分類失準時，永久性錯誤也被當成暫時性而反覆投遞，所以超過最大次數的訊息轉進 dead-letter。訊息沒有記下 requeue 次數與失敗原因的觀測欄位時，runbook 查不出是哪幾則訊息在 loop、為什麼失敗。
