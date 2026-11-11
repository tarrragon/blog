---
title: "Exponential Backoff"
date: 2026-04-23
description: "說明重試間隔如何逐步拉長以降低下游壓力"
weight: 46
---

Exponential backoff 的核心概念是「每次重試後把下一次等待時間按倍數拉長」。它讓系統在暫時性故障期間降低呼叫頻率，給下游恢復時間。 可先對照 [Facet Query](/backend/knowledge-cards/facet-query/)。

## 跟其他概念的關係

Backoff 是 retry policy 的節奏控制。固定間隔重試容易在下游尚未恢復時持續施壓；指數退避能讓重試從快速恢復逐漸轉成保守等待。 可先對照 [Facet Query](/backend/knowledge-cards/facet-query/)。

## 可觀察訊號與例子

系統需要 backoff 的訊號是下游服務短暫 timeout、rate limit 或重啟。通知服務呼叫第三方簡訊 API 失敗時，可以先快速重試一次，再逐步拉長間隔，避免所有 worker 持續打向同一個故障 API。

## 判斷條件與後果

錯誤是暫時性還是永久性，決定 backoff 是否有效。下游短暫 timeout、rate limit 或重啟這類暫時性錯誤，等一段時間之後重試可能成功，backoff 拉長間隔讓下游有時間恢復；參數錯誤、權限不足這類永久性錯誤，重試幾次結果都一樣，退避只是延後失敗、佔住 worker，所以永久性錯誤交給分類處理或 dead-letter。只用倍數拉長間隔時，等待時間沒有上限，幾次之後間隔長到超過業務能接受的延遲；重試次數沒有上限時，一個始終不恢復的下游讓同一個請求永遠重試。沒有 jitter 時，同一時間失敗的 worker 照同一組倍數計算等待時間，在同一個時間點一起重試，剛恢復的下游又同時收到一批請求。
