---
title: "Dead-Letter Queue"
date: 2026-04-23
description: "說明 dead-letter queue 如何隔離多次處理失敗的訊息"
weight: 4
---

Dead-letter queue 的核心概念是「把超過處理條件的訊息移到隔離區」。訊息經過 [retry policy](/backend/knowledge-cards/retry-policy/) 仍然失敗、格式無法解析、業務狀態拒絕處理或超過存活期限時，[broker](/backend/knowledge-cards/broker/) 或 [consumer](/backend/knowledge-cards/consumer/) 會把它送進 dead-letter queue，讓主要 [queue](/backend/knowledge-cards/queue/) 保持可前進。

## 跟其他概念的關係

Dead-letter queue 是可靠性與診斷工具。它讓系統把暫時性失敗與需要人工判斷的訊息分開：暫時性失敗可以重試，需要分析的訊息則進入隔離區，等待修復資料、修復程式或建立 [replay runbook](/backend/knowledge-cards/replay-runbook/)。

## 可觀察訊號

系統需要 dead-letter queue 的訊號是某些訊息反覆阻塞處理流程。常見原因包括 payload schema 與 consumer 版本不同步、外部系統回傳永久錯誤、資料狀態已被取消、權限不足或訊息內容缺少必要欄位。

## 接近真實網路服務的例子

訂單通知 consumer 連續處理某筆事件失敗。訊息留在主要 queue 反覆重試時，後續正常訂單可能延遲；訊息進入 dead-letter queue 後，on-call 可以查看失敗原因、修復資料或部署修正後再重放該批訊息。

## 判斷條件與後果

Dead-letter queue 裡的訊息能否被處理，看它進隔離區時帶了什麼，以及之後由誰照什麼流程處理。訊息被移走時沒有保留錯誤類型、最後錯誤、重試次數、原始 [topic](/backend/knowledge-cards/topic/)、[correlation id](/backend/knowledge-cards/correlation-id/) 與建立時間的話，on-call 看得到一批失敗訊息，卻分不出是 schema 不同步、外部系統的永久錯誤還是訂單已被取消，也追不回它屬於哪一個業務流程。[runbook](/backend/knowledge-cards/runbook/) 沒有定義誰能重放、重放前檢查什麼、副作用範圍怎麼控制時，修好程式之後整批重放，已經取消的訂單可能再收到一次通知。這兩項都缺時，dead-letter queue 只是把阻塞從主要 queue 換到另一個 queue，訊息在裡面累積而沒有人處理。
