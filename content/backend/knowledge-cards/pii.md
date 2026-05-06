---
title: "PII"
date: 2026-04-23
description: "說明可識別個人的資料如何影響權限、遮罩、保留與稽核"
weight: 123
---


PII 的核心概念是「可識別特定個人的資料」。姓名、電話、email、地址、身份證號、裝置 ID、付款資訊與某些組合資料都可能成為 PII。 可先對照 [Data Classification](/backend/knowledge-cards/data-classification/)。

## 概念位置

PII 是 [data classification](/backend/knowledge-cards/data-classification/)、[data masking](/backend/knowledge-cards/data-masking/)、權限、[retention](/backend/knowledge-cards/retention/)、[audit log](/backend/knowledge-cards/audit-log/) 與資料匯出的核心分類。資料是否為 PII 會直接改變系統的存取控制與操作成本。

## 可觀察訊號與例子

系統需要 PII 分級的訊號是服務保存會員、訂單、付款、客服或行為資料。客服查詢電話需要遮罩；資料匯出需要核准與 audit log；[log](/backend/knowledge-cards/log/) 應控制 PII 欄位。

## 設計責任

PII 設計要標出欄位分類、存取角色、遮罩規則、保留期限、匯出流程與刪除流程。測試資料也需要匿名化或合成資料策略，並和 [secret management](/backend/knowledge-cards/secret-management/) 分開管理。
