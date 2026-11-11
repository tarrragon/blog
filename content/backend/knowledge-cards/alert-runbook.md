---
title: "Alert Runbook"
tags: ["告警處置手冊", "Alert Runbook"]
date: 2026-04-23
description: "說明告警如何連到可執行的排障與恢復流程"
weight: 38
---

Alert runbook 的核心概念是「每個需要人處理的 [alert](/backend/knowledge-cards/alert/) 都要附上下一步」。Alert 通知異常，runbook 則說明如何判斷影響、查哪些 [dashboard](/backend/knowledge-cards/dashboard/)、執行哪些修復、何時升級。

## 跟其他概念的關係

Alert runbook 是可觀測性與操作流程的交界。告警搭配 [runbook](/backend/knowledge-cards/runbook/) 後，事故處理可以從個人經驗轉成團隊流程。

## 可觀察訊號與例子

系統需要 alert runbook 的訊號是 on-call 收到告警後仍要臨場猜原因。[Consumer lag](/backend/knowledge-cards/consumer-lag/) 告警應連到 [queue depth](/backend/knowledge-cards/queue-depth/)、error rate、下游 latency、[dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 數量與擴容或暫停流程。

## 判斷條件與後果

Runbook 少了哪一項，on-call 就在那一步回到臨場猜測。沒有影響判斷時，收到告警的人分不出這則要立刻處理還是可以等到上班；沒有查詢連結時，他要自己找該看哪個 dashboard；沒有原因分類時，同一個症狀的幾種成因要從頭逐一排除；沒有立即緩解的步驟時，止血要等找到根因之後；沒有回復驗證時，處理完不知道服務是否已經恢復；沒有升級路徑時，處理不了的人不知道該找誰。處理事故時發現的缺口沒有寫回 runbook 時，下一次收到同一則告警的人會在同一處卡住，所以每次事故後更新 runbook。
