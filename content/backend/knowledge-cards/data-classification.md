---
title: "Data Classification"
tags: ["資料分級", "Data Classification"]
date: 2026-04-23
description: "說明資料分級如何決定保護、存取、保留與匯出規則"
weight: 124
---

Data classification 的核心概念是「依敏感度與風險把資料分級」。常見分級包括公開資料、內部資料、敏感資料、個資、金流資料、機密資料與合規資料。

## 概念位置

資料分級是資安設計的上游。Authorization、data masking、TLS、secret management、audit log、retention 與 backup policy 都需要依資料等級調整。

## 可觀察訊號與例子

系統需要 data classification 的訊號是同一服務處理多種風險資料。商品名稱可能是公開資料，使用者地址是 PII，付款 token 是高敏感資料，管理員操作紀錄是 audit 資料。

## 設計責任

資料分級要落到欄位、表、事件、log、匯出與測試資料。每個等級應定義存取條件、遮罩、加密、保留期限、audit 與事故處理要求。
