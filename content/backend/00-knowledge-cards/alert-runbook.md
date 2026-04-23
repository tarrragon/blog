---
title: "Alert Runbook"
date: 2026-04-23
description: "說明告警如何連到可執行的排障與恢復流程"
weight: 37
---

Alert runbook 的核心概念是「每個需要人處理的告警都要附上下一步」。告警只通知異常，runbook 則說明如何判斷影響、查哪些 dashboard、執行哪些修復、何時升級。

## 概念位置

Alert runbook 是可觀測性與操作流程的交界。沒有 runbook 的告警容易變成噪音；有 runbook 的告警能把事故處理從個人經驗轉成團隊流程。

## 可觀察訊號與例子

系統需要 alert runbook 的訊號是 on-call 收到告警後仍要臨場猜原因。Consumer lag 告警應連到 queue depth、error rate、下游 latency、dead-letter 數量與擴容或暫停流程。

## 設計責任

Runbook 要包含影響判斷、查詢連結、常見原因、立即緩解、回復驗證與升級路徑。每次事故後應更新 runbook，讓下一次處理更可重現。
