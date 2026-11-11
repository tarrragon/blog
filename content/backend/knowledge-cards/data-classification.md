---
title: "Data Classification"
tags: ["資料分級", "Data Classification"]
date: 2026-04-23
description: "說明資料分級如何決定保護、存取、保留與匯出規則"
weight: 125
---

Data classification 的核心概念是「依敏感度與風險把資料分級」。常見分級包括公開資料、內部資料、敏感資料、個資、金流資料、機密資料與合規資料。 可先對照 [Data Completeness](/backend/knowledge-cards/data-completeness/)。

## 跟其他概念的關係

資料分級是資安設計的上游。Authorization、data masking、TLS、secret management、audit log、retention 與 backup policy 都需要依資料等級調整。 可先對照 [Data Completeness](/backend/knowledge-cards/data-completeness/)。

## 可觀察訊號與例子

系統需要 data classification 的訊號是同一服務處理多種風險資料。商品名稱可能是公開資料，使用者地址是 PII，付款 token 是高敏感資料，管理員操作紀錄是 audit 資料。

## 判斷條件與後果

資料分級只標到系統或資料庫這一層時，同一張表裡的商品名稱與使用者地址拿到同一個等級，結果是公開欄位被過度管制，或敏感欄位被放鬆。分級落到欄位、表、事件、log、匯出與測試資料時，資料離開主資料庫之後（寫進 log、匯出成檔、複製成測試資料）仍然帶著等級。一個等級沒有對應的存取條件、遮罩、加密、保留期限、audit 與事故處理要求時，標了等級也不改變任何處理方式。

外洩當下，通報門檻是否判得出來取決於這份分級：外洩了哪些欄位、多少筆、哪一類資料，要在事發那一刻答得出來，見 [7.37 密碼外洩之後](/backend/07-security-data-protection/credential-breach-response/)。
