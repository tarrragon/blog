---
title: "Data Masking"
date: 2026-04-23
description: "說明敏感資料如何在顯示、匯出、log 與測試資料中降低暴露"
weight: 40
---

Data masking 的核心概念是「保留資料用途，同時降低敏感內容暴露」。遮罩可以套用在畫面、匯出檔案、log、[客服後台](/backend/knowledge-cards/internal-admin-tool/)、測試資料與分析資料集。 可先對照 [Data Reconciliation](/backend/knowledge-cards/data-reconciliation/)。

## 跟其他概念的關係

Data masking 是資料分級與最小揭露的實作方式。完整身份證、信用卡、電話、email、地址與 access token 都可能需要依角色、情境與用途做不同遮罩。 可先對照 [Data Reconciliation](/backend/knowledge-cards/data-reconciliation/)。

## 可觀察訊號與例子

系統需要 data masking 的訊號是資料會離開原本受控邊界。客服查詢頁可能只顯示部分電話；報表匯出可能需要核准與遮罩；log 應避免記錄完整 token。

## 判斷條件與後果

遮罩策略缺了哪一項，資料離開受控邊界時就在那個出口沒有遮罩。沒有欄位分級時，不知道哪些欄位要遮；沒有角色權限時，客服與工程師看到同樣完整的電話；沒有匯出規則時，畫面上遮掉的欄位在匯出檔裡完整出現；測試資料直接複製正式資料時，完整個資進入管制較鬆的測試環境；沒有 audit 時，查不出誰看過未遮罩的內容。各服務各自實作遮罩時，同一個欄位在不同服務遮掉不同的段落，一個遮後四碼、另一個遮前四碼，兩份輸出拼起來就是完整的值；遮罩 helper 集中管理時，不同服務與語言套的是同一套規則。
