---
title: "Break-Glass Access"
date: 2026-05-22
description: "說明緊急情況下臨時授予的高權限存取，如何用工單、時限與事後審查治理"
weight: 340
---

Break-Glass Access 的核心概念是在正常權限模型之外，為緊急事故臨時授予的高權限存取，並要求它伴隨工單、時限與事後審查。它讓事故處理在需要時拿得到必要權限，同時讓這個例外可被追溯。它是 [Least Privilege](/backend/knowledge-cards/least-privilege/) 的受控例外，和 [Security Exception](/backend/knowledge-cards/security-exception/) 相鄰。

## 概念位置

Break-Glass Access 位在日常權限與緊急需求之間。[Least Privilege](/backend/knowledge-cards/least-privilege/) 讓角色平時只拿必要權限；事故有時需要超出平時的存取，break-glass 讓這個提權是有流程、有時限、可回收的。它和 [Security Exception](/backend/knowledge-cards/security-exception/) 的差別在形態：security exception 是對已知風險的書面豁免決策，break-glass 是執行中的緊急存取流程。

## 可觀察訊號與例子

需要 break-glass 機制的訊號是事故處理偶爾需要 production 高權限，但平時不該有人持有。沒有 break-glass 流程時，團隊常落入兩種有問題的做法：長期保留 admin 後門，或事故當下臨時亂開權限而沒有紀錄。健康的 break-glass 會在每次啟用時留下工單、申請人、時間窗與事後審查結果。

## 設計責任

設計時要定義誰能啟用、啟用要綁哪種工單、權限的自動回收時限，以及事後審查由誰做。每次 break-glass 啟用都要進 [Audit Log](/backend/knowledge-cards/audit-log/)。break-glass 流程本身要定期演練，確認事故當下真的拿得到、事後真的收得回。
