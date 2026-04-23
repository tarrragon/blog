---
title: "Tenant Boundary"
date: 2026-04-23
description: "說明多租戶系統如何隔離不同客戶或組織的資料與資源"
weight: 118
---

Tenant boundary 的核心概念是「隔離不同客戶、組織或租戶的資料與資源」。多租戶系統中，使用者身份之外還要判斷他屬於哪個 tenant，以及能否跨 tenant 操作。

## 概念位置

Tenant boundary 是 authorization、data partition、rate limit、audit 與 billing 的共同邊界。它可以落在資料庫欄位、schema、database、queue、cache key、storage path 或 network policy。

## 可觀察訊號與例子

系統需要 tenant boundary 的訊號是同一服務處理多個企業或組織。A 公司管理員只能看到 A 公司訂單；A 公司的大量匯出也應使用自己的查詢配額，保留 B 公司的正常容量。

## 設計責任

Tenant boundary 要在 query、cache key、message、log、audit、rate limit 與測試中保持一致。測試要覆蓋跨 tenant IDOR、資料匯出與背景 job。
