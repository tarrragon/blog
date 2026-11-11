---
title: "Runbook Link"
date: 2026-04-23
description: "說明告警與 dashboard 如何直接連到處理流程"
weight: 110
---

Runbook link 的核心概念是「[alert](/backend/knowledge-cards/alert/) 或 [dashboard](/backend/knowledge-cards/dashboard/) 直接連到對應處理流程」。它讓 on-call 從訊號直接進入可執行步驟，並降低對搜尋文件或個人記憶的依賴。

## 跟其他概念的關係

Runbook link 是 observability UX 的一部分。它把 alert、dashboard、[log](/backend/knowledge-cards/log/) query、rollback、擴容、停用 feature 與升級聯絡方式串起來。

## 可觀察訊號與例子

系統需要 runbook link 的訊號是告警發出後，處理者仍要在聊天紀錄或文件庫中找下一步。[Consumer lag](/backend/knowledge-cards/consumer-lag/) 告警應直接連到 lag dashboard、[DLQ](/backend/knowledge-cards/dead-letter-queue/) 查詢、擴容指令與 [replay runbook](/backend/knowledge-cards/replay-runbook/) 注意事項。

## 判斷條件與後果

Runbook link 的判斷對象是處理者點開連結之後，是否直接拿到這次處理要用的查詢與步驟。連結指向的文件被搬移或改名而告警沒有更新時，連結失效，處理者退回聊天紀錄與文件庫裡找下一步；文件沒有版本化時，處理者看到的步驟可能已經不符合目前的架構；文件無法被搜尋時，連結失效之後也找不到它的新位置。事故中實際用到、而連結的內容沒有的查詢與判斷條件，就是這份連結落後於系統的地方，所以每次事故後拿實際處理過程對照連結內容，把缺的部分補進去。
