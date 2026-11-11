---
title: "Routing Rule"
date: 2026-04-23
description: "說明訊息系統如何依規則把訊息送到不同處理路徑"
weight: 136
---

Routing rule 的核心概念是「用訊息屬性決定訊息要進入哪個處理路徑」。規則可以依 topic、routing key、header、tenant、事件類型、優先級或業務狀態分派訊息。 可先對照 [Broker](/backend/knowledge-cards/broker/)。

## 跟其他概念的關係

Routing rule 是 [broker](/backend/knowledge-cards/broker/) 內的分流邏輯。它把 [producer](/backend/knowledge-cards/producer/) 的輸出轉成不同 [queue](/backend/knowledge-cards/queue/)、[consumer group](/backend/knowledge-cards/consumer-group/) 或 stream [partition](/backend/knowledge-cards/partition/)，讓不同工作可以用不同容量、權限與 [retry policy](/backend/knowledge-cards/retry-policy/) 處理。

## 可觀察訊號與例子

系統需要 routing rule 的訊號是同一類事件有不同處理代價。一般通知可以進入低成本 queue，高價值訂單通知可以進入優先 queue；退款事件可以交給需要更完整 [audit log](/backend/knowledge-cards/audit-log/) 的 consumer。

## 判斷條件與後果

Routing rule 改動之後，每一類訊息是否仍然進到預期的 queue，broker 自己不會檢查。規則寫錯時，訊息進錯 queue、被漏處理，或集中到某一個 queue 造成局部的 [consumer lag](/backend/knowledge-cards/consumer-lag/)，而 broker 照規則投遞，不會報錯；沒有預設路徑時，不匹配任何規則的訊息可能被丟棄或滯留。規則沒有可以拿樣本訊息驗證的測試，訊息也沒有記下走了哪條路徑的觀測欄位時，這些錯誤要等下游發現少了資料才被看見。所以規則的每次變更都經過樣本驗證，並保留回到上一版規則的方式。
