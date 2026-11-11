---
title: "PII"
date: 2026-04-23
description: "說明可識別個人的資料如何影響權限、遮罩、保留與稽核"
weight: 124
---

PII 的核心概念是「可識別特定個人的資料」。姓名、電話、email、地址、身份證號、裝置 ID、付款資訊與某些組合資料都可能成為 PII。 可先對照 [Data Classification](/backend/knowledge-cards/data-classification/)。

## 跟其他概念的關係

PII 是 [data classification](/backend/knowledge-cards/data-classification/)、[data masking](/backend/knowledge-cards/data-masking/)、權限、[retention](/backend/knowledge-cards/retention/)、[audit log](/backend/knowledge-cards/audit-log/) 與資料匯出的核心分類。資料是否為 PII 會直接改變系統的存取控制與操作成本。

## 可觀察訊號與例子

系統需要 PII 分級的訊號是服務保存會員、訂單、付款、客服或行為資料。客服查詢電話需要遮罩；資料匯出需要核准與 audit log；[log](/backend/knowledge-cards/log/) 應控制 PII 欄位。

## 判斷條件與後果

PII 的處理從欄位分類開始，因為分類決定其餘各項套不套得到某個欄位：沒有標成 PII 的欄位，存取角色、遮罩規則、保留期限、匯出與刪除流程都管不到它，它照一般資料被查詢、寫進 [log](/backend/knowledge-cards/log/)、被匯出。遮罩規則缺席時，客服查詢看得到完整的電話；匯出流程沒有核准與 [audit log](/backend/knowledge-cards/audit-log/) 時，大量個資離開系統而沒有紀錄；保留期限與刪除流程缺席時，資料留存超過用途所需，收到刪除要求時沒有可以執行的路徑。測試資料直接複製 production 時，PII 隨著複本進入權限較鬆的環境，所以測試資料用匿名化或合成資料，並和 [secret management](/backend/knowledge-cards/secret-management/) 分開管理。
