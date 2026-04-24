---
title: "7.R3 資料暴露與外洩路徑"
date: 2026-04-24
description: "說明敏感資料會從哪些回應、紀錄或工具中流出"
weight: 713
---

紅隊看資料不是只看 API response，而是看資料會不會從更多路徑被帶走。Excessive data exposure、log、search index、support tool、backup、export、cache 與錯誤訊息都可能是外洩路徑。

## 概念位置

這一類問題會與 [Excessive Data Exposure](../../knowledge-cards/excessive-data-exposure/)、[Data Classification](../../knowledge-cards/data-classification/)、[Data Masking](../../knowledge-cards/data-masking/)、[Audit Log](../../knowledge-cards/audit-log/) 與 [Secret Management](../../knowledge-cards/secret-management/) 交疊。紅隊的工作是找出哪個資料流最容易被忘記，哪個中介層最容易被誤當成安全邊界。

## 可觀察訊號與例子

當系統有客服介面、管理後台、批次匯出、搜尋索引或觀測工具時，資料外洩風險會不只存在於前台 API。紅隊會特別注意 response 裡多出來的欄位、log 裡的敏感資訊、支援工具是否能查到未遮罩資料，以及索引或備份是否保留過多原始內容。

## 設計責任

資料暴露的防護責任要從資料分級開始，延伸到回應、紀錄、搜尋、分析與備份。只要某個資料流會離開主要存取路徑，就要重新定義遮罩、權限與保存策略，不能只靠單一 API 的回傳格式保護整個系統。
