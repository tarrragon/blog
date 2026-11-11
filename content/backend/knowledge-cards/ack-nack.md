---
title: "Ack / Nack"
date: 2026-04-23
description: "說明 consumer 如何向 broker 回報訊息處理結果"
weight: 24
---

Ack / nack 的核心概念是「[consumer](/backend/knowledge-cards/consumer/) 對 [broker](/backend/knowledge-cards/broker/) 回報訊息處理結果」。Ack 表示訊息已完成處理，可以從待處理集合移除；nack 或 reject 表示處理未完成，需要 [retry policy](/backend/knowledge-cards/retry-policy/)、[requeue](/backend/knowledge-cards/requeue/) 或送進 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/)。

## 跟其他概念的關係

Ack / nack 是投遞保證的關鍵協議。Consumer crash、網路中斷或 ack timeout 都可能讓 broker 判斷訊息尚未完成，進而 [redelivery](/backend/knowledge-cards/redelivery/)。

## 可觀察訊號與例子

系統需要理解 ack / nack 的訊號是訊息重複、[queue depth](/backend/knowledge-cards/queue-depth/) 上升或 [unacked message](/backend/knowledge-cards/unacked-message/) 累積。影片轉檔 worker 若在完成前 crash，訊息應重新投遞；若已產生外部副作用，consumer 需要 [idempotency](/backend/knowledge-cards/idempotency/) 保護。

## 判斷條件與後果

Consumer 送出 ack 的時機決定它 crash 之後訊息的去向。業務處理與必要的狀態保存完成之後才 ack 時，處理途中 crash 的訊息會被 broker 重新投遞，代價是同一則訊息可能處理兩次，所以有外部副作用的處理需要 idempotency；處理完成之前就 ack 時，crash 掉的那一則已經從待處理集合移除，訊息遺失，broker 也不會重送。nack 之後的去向看錯誤的性質：永久性錯誤（格式錯誤、資料不存在）重試幾次結果都一樣，留在佇列裡只會反覆失敗並佔住 consumer，所以分類出來送進 dead-letter queue；暫時性錯誤（下游逾時）隔一段時間會恢復，所以交給 retry policy，搭配 [exponential backoff](/backend/knowledge-cards/exponential-backoff/) 拉長間隔、[jitter](/backend/knowledge-cards/jitter/) 讓各 consumer 的重試錯開，不在同一時刻一起打回下游。
