---
title: "Row-Level Security"
date: 2026-05-22
description: "說明資料庫如何用 policy 限制同一張表中哪些 row 對某個角色可見或可寫"
weight: 332
---

Row-Level Security（RLS）的核心概念是在資料庫層、用 policy 規則限制同一張表裡哪些 row 對某個角色可讀或可寫。它讓資料隔離多一道資料庫強制的防線，而不只依賴 application 的查詢條件。它是 [Tenant Boundary](/backend/knowledge-cards/tenant-boundary/) 的一種落地機制，和 [Authorization](/backend/knowledge-cards/authorization/)、[Least Privilege](/backend/knowledge-cards/least-privilege/) 一起構成防禦縱深。

## 跟其他概念的關係

Row-Level Security 位在 application 授權的下游。application 層的 [Authorization](/backend/knowledge-cards/authorization/) 決定「誰能呼叫這個功能」，RLS 決定「即使查詢送到資料庫，引擎也只回傳這個角色該看到的 row」。它和 [Tenant Boundary](/backend/knowledge-cards/tenant-boundary/) 的差別在執行者：tenant boundary 是跨層的隔離概念，RLS 指明由資料庫引擎在 query 執行時強制過濾。

## 可觀察訊號與例子

適合 RLS 的訊號是多租戶 SaaS、需要資料庫層兜底防止跨租戶外洩，或合規要求資料存取有獨立 enforcement。RLS 通常依賴 application 在交易內設一個 session 變數（例如 tenant_id）來判斷；這個變數的生命週期要和 [Transaction Pooling](/backend/knowledge-cards/transaction-pooling/) 的綁定模式對齊，否則會漂到別的請求。table owner 與 superuser 預設會繞過 RLS，這點要納入設計。

## 判斷條件與後果

RLS 的判斷對象是資料庫這道防線實際涵蓋了哪些操作與哪些連線角色。SELECT、INSERT、UPDATE、DELETE 的 policy 各自獨立，只寫了其中幾種時，沒涵蓋的那幾種操作的行為取決於引擎的預設，可能全部被拒絕，也可能不受租戶限制；應用程式用 table owner 或 superuser 連線時，policy 預設不套用在這些角色上。這兩種缺口在正常流量下都不會出錯，沒有獨立測試證明跨租戶查詢被擋下時，要到外洩才看得到。application 層的授權與 RLS 承擔不同的失敗模式：前者管誰能呼叫哪個功能，後者管查詢送到資料庫之後回傳哪些 row，拿掉任一層，另一層的漏洞就直接成為外洩路徑。緊急例外存取需要繞過 RLS 時，沒有 [Audit Log](/backend/knowledge-cards/audit-log/) 就查不到誰在什麼時候看了哪些 row，所以例外存取一律留下紀錄。
