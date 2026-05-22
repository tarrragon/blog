---
title: "Row-Level Security"
date: 2026-05-22
description: "說明資料庫如何用 policy 限制同一張表中哪些 row 對某個角色可見或可寫"
weight: 331
---

Row-Level Security（RLS）的核心概念是在資料庫層、用 policy 規則限制同一張表裡哪些 row 對某個角色可讀或可寫。它讓資料隔離多一道資料庫強制的防線，而不只依賴 application 的查詢條件。它是 [Tenant Boundary](/backend/knowledge-cards/tenant-boundary/) 的一種落地機制，和 [Authorization](/backend/knowledge-cards/authorization/)、[Least Privilege](/backend/knowledge-cards/least-privilege/) 一起構成防禦縱深。

## 概念位置

Row-Level Security 位在 application 授權的下游。application 層的 [Authorization](/backend/knowledge-cards/authorization/) 決定「誰能呼叫這個功能」，RLS 決定「即使查詢送到資料庫，引擎也只回傳這個角色該看到的 row」。它和 [Tenant Boundary](/backend/knowledge-cards/tenant-boundary/) 的差別在執行者：tenant boundary 是跨層的隔離概念，RLS 指明由資料庫引擎在 query 執行時強制過濾。

## 可觀察訊號與例子

適合 RLS 的訊號是多租戶 SaaS、需要資料庫層兜底防止跨租戶外洩，或合規要求資料存取有獨立 enforcement。RLS 通常依賴 application 在交易內設一個 session 變數（例如 tenant_id）來判斷；這個變數的生命週期要和 [Transaction Pooling](/backend/knowledge-cards/transaction-pooling/) 的綁定模式對齊，否則會漂到別的請求。table owner 與 superuser 預設會繞過 RLS，這點要納入設計。

## 設計責任

設計時要讓 policy 覆蓋 SELECT、INSERT、UPDATE、DELETE 四種操作，並為緊急例外存取留 [Audit Log](/backend/knowledge-cards/audit-log/)。RLS 要有獨立測試，證明跨租戶查詢確實被擋下。它是兜底防線，application 層授權仍要做 — 兩道防線各自承擔不同的失敗模式。
