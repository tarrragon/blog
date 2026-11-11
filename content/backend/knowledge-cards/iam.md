---
title: "IAM"
date: 2026-04-23
description: "說明 identity and access management 如何集中管理身分、角色與權限"
weight: 121
---

IAM 的核心概念是「集中管理誰是誰，以及誰能做什麼」。它通常負責使用者、服務帳號、角色、群組、policy 與權限委派，並為 application 提供登入、授權與稽核的共同基礎。 可先對照 [Authentication](/backend/knowledge-cards/authentication/)。

## 跟其他概念的關係

IAM 位在 authentication、authorization 與組織治理之間。它常與 [authentication](/backend/knowledge-cards/authentication/)、[authorization](/backend/knowledge-cards/authorization/) 與 [least privilege](/backend/knowledge-cards/least-privilege/) 一起出現，也會影響 tenant boundary 與 service account 管理。

## 可觀察訊號與例子

系統需要 IAM 的訊號是團隊、產品或租戶數量增加，且權限規則開始無法靠單一 application hard-code 維護。企業 SaaS、內部管理後台與雲端資源操作通常都需要 IAM 來統一角色與 policy。

## 判斷條件與後果

IAM 的判斷對象是權限的授予與撤銷是否集中在一處。身分來源與角色模型沒有統一時，同一個人在不同系統各有一份帳號與角色，換人時要逐一找出來；撤銷流程沒有定義時，離職或換職務的人保留舊權限；稽核記錄缺席時，事故處置時查不到誰在什麼時候拿到了哪個權限。高風險權限散落在各個 service 的 hard-code 裡時，權限審查要逐一讀各服務的程式碼，換人與事故處置都要改多處，原因是這些權限不在 IAM 的 policy 裡，集中的授予與撤銷流程管不到它們。
