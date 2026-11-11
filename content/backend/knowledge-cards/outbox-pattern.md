---
title: "Outbox Pattern"
date: 2026-04-23
description: "說明資料庫狀態變更與事件發布如何透過 outbox 維持一致"
weight: 27
---

Outbox pattern 的核心概念是「把業務資料變更與待發布事件寫進同一個資料庫交易」。交易提交後，獨立 publisher 再從 outbox table 讀出事件並發布到 broker。 可先對照 [Ownership](/backend/knowledge-cards/ownership/)。

## 跟其他概念的關係

Outbox 解決的是資料已寫入但事件發布失敗的半成功問題。資料庫交易保護業務狀態與 outbox 紀錄；broker 發布則用後續重試與 idempotency 保證最終送出。 可先對照 [Ownership](/backend/knowledge-cards/ownership/)。

## 可觀察訊號與例子

系統需要 outbox 的訊號是「狀態改變後，其他服務必須知道」。訂單付款完成後，倉儲、通知與分析都需要收到事件；若事件發布失敗但訂單已付款，後續流程會漏執行。

## 判斷條件與後果

業務交易提交之後，事件能否送達只取決於 publisher 從 outbox table 讀出事件、發布到 broker 的那一段。缺 publisher checkpoint 時，publisher 重啟後沒有依據決定從哪一筆接著發，結果是重發或漏發；缺 retry 與 dead-letter 時，一筆發布失敗的事件不是卡住後面的事件，就是被丟掉；缺去重時，retry 產生的重複事件讓倉儲與通知各處理兩次；event schema 沒有定義時，下游讀不懂改版後的事件。這一段失效時，訂單已經付款而倉儲沒收到事件，從使用者端看不到任何錯誤，所以 runbook 要看得到 outbox backlog、發布錯誤、最舊未發布事件的時間與 replay 流程，它們是這一段延遲或漏發的訊號。
