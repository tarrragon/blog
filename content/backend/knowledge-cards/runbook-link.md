---
title: "Runbook Link"
date: 2026-04-23
description: "說明告警與 dashboard 如何直接連到處理流程"
weight: 109
---

Runbook link 的核心概念是「[alert](/backend/knowledge-cards/alert/) 或 [dashboard](/backend/knowledge-cards/dashboard/) 直接連到對應處理流程」。它讓 on-call 從訊號直接進入可執行步驟，並降低對搜尋文件或個人記憶的依賴。

## 概念位置

Runbook link 是 observability UX 的一部分。它把 alert、dashboard、[log](/backend/knowledge-cards/log/) query、rollback、擴容、停用 feature 與升級聯絡方式串起來。

## 可觀察訊號與例子

系統需要 runbook link 的訊號是告警發出後，處理者仍要在聊天紀錄或文件庫中找下一步。[Consumer lag](/backend/knowledge-cards/consumer-lag/) 告警應直接連到 lag dashboard、[DLQ](/backend/knowledge-cards/dead-letter-queue/) 查詢、擴容指令與 [replay runbook](/backend/knowledge-cards/replay-runbook/) 注意事項。

## 設計責任

Runbook link 要保持有效、可搜尋、版本化。每次事故後應確認連結是否真的支援當次處理，並補上缺少的查詢與判斷條件。
