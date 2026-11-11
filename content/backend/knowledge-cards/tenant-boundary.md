---
title: "Tenant Boundary"
date: 2026-04-23
description: "說明多租戶系統如何隔離不同客戶或組織的資料與資源"
weight: 119
---

Tenant boundary 的核心概念是「隔離不同客戶、組織或租戶的資料與資源」。多租戶系統中，使用者身份之外還要判斷他屬於哪個 tenant，以及能否跨 tenant 操作。 可先對照 [Throughput](/backend/knowledge-cards/throughput/)。

## 跟其他概念的關係

Tenant boundary 是 authorization、data partition、rate limit、audit 與 billing 的共同邊界。它可以落在資料庫欄位、schema、database、queue、cache key、storage path 或 network policy。 可先對照 [Throughput](/backend/knowledge-cards/throughput/)。

## 可觀察訊號與例子

系統需要 tenant boundary 的訊號是同一服務處理多個企業或組織。A 公司管理員只能看到 A 公司訂單；A 公司的大量匯出也應使用自己的查詢配額，保留 B 公司的正常容量。

## 判斷條件與後果

Tenant boundary 在 query、cache key、message、log、audit 與 rate limit 之中，只要有一處沒有帶租戶識別，那一處就是跨租戶的路徑：cache key 沒有租戶時，A 公司查出的結果可能回給 B 公司；rate limit 沒有依租戶分開時，A 公司的大量匯出用掉 B 公司的容量；log 與 audit 沒有租戶時，事後查不出一次存取屬於哪個租戶。跨 tenant 的 IDOR、資料匯出與背景 job 是測試沒覆蓋時最常漏掉的三處，因為匯出與背景 job 常常不走一般請求的授權路徑，背景 job 也沒有發起的使用者可以帶出租戶。

這條邊界成立的前提是「這個請求屬於哪個租戶」判對了，而那個判斷本身怎麼建立、憑什麼可信，見 [7.40 B2B 多租戶的身分接入](/backend/07-security-data-protection/multi-tenant-identity-onboarding/)。

資料要隔到哪一層（共用表、每租戶一個 schema、每租戶一套、租戶分組），以及建置管線、營運後台與備份這類共用元件的權限如何繞過這條邊界，見 [7.44 多租戶平台的隔離層級](/backend/07-security-data-protection/multi-tenant-platform-isolation-tiers/)。
