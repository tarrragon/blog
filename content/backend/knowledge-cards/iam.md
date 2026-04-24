---
title: "IAM"
date: 2026-04-23
description: "說明 identity and access management 如何集中管理身分、角色與權限"
weight: 120
---

IAM 的核心概念是「集中管理誰是誰，以及誰能做什麼」。它通常負責使用者、服務帳號、角色、群組、policy 與權限委派，並為 application 提供登入、授權與稽核的共同基礎。

## 概念位置

IAM 位在 authentication、authorization 與組織治理之間。它常與 [authentication](/backend/knowledge-cards/authentication/)、[authorization](/backend/knowledge-cards/authorization/) 與 [least privilege](/backend/knowledge-cards/least-privilege/) 一起出現，也會影響 tenant boundary 與 service account 管理。

## 可觀察訊號與例子

系統需要 IAM 的訊號是團隊、產品或租戶數量增加，且權限規則開始無法靠單一 application hard-code 維護。企業 SaaS、內部管理後台與雲端資源操作通常都需要 IAM 來統一角色與 policy。

## 設計責任

IAM 設計要定義身分來源、角色模型、權限授予、撤銷流程與稽核記錄。實作時要避免把高風險權限散落在各個 service，否則會讓權限審查、換人與事故處置變得困難。
