---
title: "Consumer Capacity"
date: 2026-04-23
description: "說明 consumer 群組每秒能穩定處理多少工作"
weight: 71
---

Consumer capacity 的核心概念是「consumer 群組在穩定條件下能處理的工作量」。它取決於 consumer 數量、handler 耗時、prefetch、下游容量、錯誤率與重試量。 可先對照 [Consumer Group](/backend/knowledge-cards/consumer-group/)。

## 跟其他概念的關係

Consumer capacity 是 queue sizing 與容量規劃的基礎。Producer rate 高於 consumer capacity 時，queue depth 與 lag 會上升；consumer capacity 高於下游容量時，壓力會轉移到資料庫或 API。 可先對照 [Consumer Group](/backend/knowledge-cards/consumer-group/)。

## 可觀察訊號與例子

系統需要估算 consumer capacity 的訊號是活動前要確認 queue 能否消化尖峰。通知服務每秒進入 5,000 筆任務，而 consumer 群組只能穩定處理 2,000 筆，lag 會持續累積。

## 判斷條件與後果

Consumer capacity 只用平均耗時估算時，會高估尖峰時的實際吞吐：p95 耗時的長尾在尖峰時佔住 consumer；重試比例高時，一部分處理能力花在重做失敗的工作上；下游限制（資料庫連線、外部 API 的 rate limit）低於 consumer 的處理能力時，加 consumer 只把等待移到下游；擴容速度慢於尖峰的爬升速度時，lag 在新 consumer 上線之前就已經累積。這幾項決定瓶頸在哪裡，處置跟著瓶頸走：瓶頸在 consumer 數或 prefetch 時，擴 consumer 或調 prefetch 有效；瓶頸在下游時，加 consumer 無效，降級 producer 或暫停低優先訊息才減得了下游的負載。Runbook 寫出這組對應時，lag 上升時才判斷得出該用哪一種處置。
