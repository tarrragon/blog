---
title: "Break-Glass Access"
date: 2026-05-22
description: "說明緊急情況下臨時授予的高權限存取，如何用工單、時限與事後審查治理"
weight: 341
---

Break-Glass Access 的核心概念是在正常權限模型之外，為緊急事故臨時授予的高權限存取，並要求它伴隨工單、時限與事後審查。它讓事故處理在需要時拿得到必要權限，同時讓這個例外可被追溯。它是 [Least Privilege](/backend/knowledge-cards/least-privilege/) 的受控例外，和 [Security Exception](/backend/knowledge-cards/security-exception/) 相鄰。

## 跟其他概念的關係

Break-Glass Access 位在日常權限與緊急需求之間。[Least Privilege](/backend/knowledge-cards/least-privilege/) 讓角色平時只拿必要權限；事故有時需要超出平時的存取，break-glass 讓這個提權是有流程、有時限、可回收的。它和 [Security Exception](/backend/knowledge-cards/security-exception/) 的差別在形態：security exception 是對已知風險的書面豁免決策，break-glass 是執行中的緊急存取流程。

## 可觀察訊號與例子

需要 break-glass 機制的訊號是事故處理偶爾需要 production 高權限，但平時不該有人持有。沒有 break-glass 流程時，團隊常落入兩種有問題的做法：長期保留 admin 後門，或事故當下臨時亂開權限而沒有紀錄。健康的 break-glass 會在每次啟用時留下工單、申請人、時間窗與事後審查結果。

## 判斷條件與後果

Break-glass 流程的每一個元素各自擋住一種失控。沒有限定誰能啟用、沒有綁工單時，提權對不回一次具體的事故，事後分不出哪一次啟用是必要的；沒有自動回收時限時，事故結束後權限留在帳號上，break-glass 退化成長期保留的 admin 後門；沒有指定事後審查的人時，啟用紀錄存在，卻沒有人比對它是否合理。啟用沒有寫進 [Audit Log](/backend/knowledge-cards/audit-log/) 時，這個例外無法追溯。流程沒有演練過時，帳號失效或審批人聯絡不到要到事故當下才暴露，所以 break-glass 流程定期演練，確認事故當下拿得到、事後收得回。
