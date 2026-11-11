---
title: "Input Validation"
date: 2026-04-23
description: "說明進入系統的資料如何先被檢查格式、範圍與語意"
weight: 122
---

Input validation 的核心概念是「資料進入系統時先檢查格式、範圍與語意」。它保護後續 business logic、database、queue、parser 與外部 API。 可先對照 [Internal Endpoint](/backend/knowledge-cards/internal-endpoint/)。

## 跟其他概念的關係

Input validation 是 API 邊界與安全邊界的第一層。它不取代 authorization、business rule 或 database constraint，但能提早拒絕無效資料並產生清楚錯誤。 可先對照 [Internal Endpoint](/backend/knowledge-cards/internal-endpoint/)。

## 可觀察訊號與例子

系統需要 input validation 的訊號是 API 接收 JSON、檔案、URL、查詢條件或 webhook payload。日期範圍、email 格式、檔案大小、enum 值與 ID 格式都應在入口被驗證。

## 判斷條件與後果

一條 validation 規則放在哪一層，看它需要哪些資訊。格式檢查（email 格式、日期範圍、enum 值、檔案大小）只需要請求本身，放在入口時，無效資料在進入 business logic、queue 與 parser 之前就被拒絕，錯誤也指得出是哪個欄位。業務規則要讀系統目前的狀態（庫存、帳號狀態），入口拿不到這些資訊，所以放在 usecase。資料完整性由 database constraint 保底，原因是兩個並發請求可能都通過了應用層的檢查，只有資料庫在寫入的那一刻看得到兩者的衝突。錯誤回應附上內部細節（SQL 錯誤原文、stack trace、內部欄位名）時，呼叫者拿到了探測系統結構的線索，所以回應寫出哪個欄位不合格與原因，不附內部錯誤原文。
