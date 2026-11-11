---
title: "Transaction Boundary"
date: 2026-04-23
description: "說明哪些資料變更應在同一個交易中一起成功或一起回復"
weight: 15
---

Transaction boundary 的核心概念是「一組資料變更必須一起成功或一起回復的範圍」。交易邊界決定哪些狀態需要被 [database](/backend/knowledge-cards/database/) [transaction](/backend/knowledge-cards/transaction/) 保護，哪些外部動作應放在交易之外。

## 跟其他概念的關係

交易適合保護同一個 database 內的正式狀態變更。建立訂單與扣庫存可能需要同一個交易；寄信、呼叫外部 API 或發布 [broker](/backend/knowledge-cards/broker/) 訊息則常需要 [outbox pattern](/backend/knowledge-cards/outbox-pattern/) 或補償流程，因為它們超出 database transaction 能力。

## 可觀察訊號與例子

系統需要交易邊界的訊號是「半成功」會造成產品錯誤。若付款紀錄已建立但訂單狀態未更新，客服與帳務會看到衝突狀態；若通知寄送失敗，通常可以重試或補送。

## 判斷條件與後果

交易邊界越長，交易持有鎖的時間越長，等待同一批列的其他交易越多，deadlock 與逾時的機率跟著增加；交易裡包了外部 API 呼叫時，外部服務的延遲直接變成持鎖時間。所以邊界只包住必須一起成功或一起回復的資料變更。Deadlock 或 [timeout](/backend/knowledge-cards/timeout/) 發生時整個交易撤銷，沒有 [retry policy](/backend/knowledge-cards/retry-policy/) 與錯誤分類時，上層分不出這次失敗可以重試（deadlock、暫時的逾時）還是不該重試（資料違反約束）。跨 database 或跨服務的變更超出單一交易的能力，把它們當成被一個交易包住時，半成功的狀態（付款紀錄已建立、訂單狀態未更新）沒有任何機制收拾，這類一致性由 outbox、saga、補償或 [data reconciliation](/backend/knowledge-cards/data-reconciliation/) 處理。邊界定好之後，交易物件要傳到邊界內的每一個資料存取呼叫，傳遞方式見 [Transaction Propagation](/backend/knowledge-cards/transaction-propagation/)。
