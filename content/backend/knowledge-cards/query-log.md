---
title: "Query Log（SQL 語句記錄）"
date: 2026-10-06
description: "要確認 ORM 或資料存取函式庫實際送出了哪些 SQL、交易的 begin 與 commit 有沒有送出，或在正式環境追查慢查詢與某一筆資料被誰改過時，查應用程式端與資料庫端的語句記錄各記了什麼"
weight: 462
tags: ["backend", "database", "orm", "observability", "knowledge-card"]
---

SQL 語句記錄（query log）是把送往資料庫的每一段 SQL 記下來的紀錄。它有兩個來源，記到的內容不同：**應用程式端**由 [ORM](/backend/knowledge-cards/orm/) 或資料存取函式庫印出它送出的語句；**資料庫端**由資料庫記錄它收到的語句。用 ORM 的程式碼上看不到 SQL，這兩種記錄是確認實際行為的地方。本站文章把應用程式端那一種稱為 ORM 的 SQL 記錄（GORM 的 SQL 記錄），資料庫端那一種稱為語句記錄（PostgreSQL 的 `log_statement`）；它們和一般的應用程式記錄的關係見 [Log](/backend/knowledge-cards/log/)。

## 概念位置

| 來源       | 開啟方式                                                                                                                                                                           | 記到的內容                                                                                                                  |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| 應用程式端 | GORM 的記錄器設成 `logger.Info`；Laravel 的 `DB::listen` 或 `DB::enableQueryLog()`；Django 的 `django.db.backends` 記錄器（只在 `DEBUG = True` 時記錄）；SQLAlchemy 的 `echo=True` | 這個程式送出的語句，多半附耗時、影響列數與呼叫位置；參數常被直接代入顯示，和實際送出的「SQL 加上分開的參數」形式不同        |
| 資料庫端   | PostgreSQL 的 `log_statement`（`none`、`ddl`、`mod`、`all`）與 `log_min_duration_statement`（超過指定毫秒數才記）；MySQL 的 general query log 與 slow query log                    | 所有用戶端送來的語句，包括驅動自動送出的交易指令與預先解析查詢的名字；加上 `log_line_prefix` 的設定可以記錄資料庫名稱與連線 |

兩種記錄之外，分散式追蹤（tracing）也記得到資料庫呼叫：OpenTelemetry 這類工具在每個資料庫呼叫上記一段 span（Go 的 pgx 透過 `QueryTracer` 介面接上），同時帶著所屬的請求與耗時，適合回答「這個請求為什麼慢」。

兩種記錄各有記不到的內容。GORM 預設把每個寫入包進一個交易（`SkipDefaultTransaction` 可以關掉），那個交易的 `begin` 與 `commit` 不出現在 GORM 自己的記錄裡，只看得到資料庫端；資料庫端看不到這個語句是從程式的哪一行送出的。Go 的 pgx 預設在連線上快取 [Prepared Statement](/backend/knowledge-cards/prepared-statement/)，在 PostgreSQL 的記錄裡顯示成 `execute stmtcache_…`，參數另外記在 `DETAIL` 那一行。

## 可觀察訊號與例子

- **ORM 送出的查詢次數**：同一個形狀的查詢在應用程式端的記錄裡連續出現 N 次，是 N+1（見 [1.13 應用層查詢反模式與 Query 預算](/backend/01-database/query-anti-patterns/)）。
- **應該出現卻沒出現的語句**：GORM 用 struct 更新時跳過零值欄位，記錄裡的 `UPDATE` 少了那個欄位，要改的欄位全是零值時整句 `UPDATE` 都不會出現（model 帶 `UpdatedAt` 時只剩更新 `updated_at` 的那一句）；交易邊界不如預期時，資料庫端的 `begin` 與 `commit` 位置對不上（各 ORM 的差異見 [1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/)〈ORM 的交易邊界：GORM、Laravel、Django 與 SQLAlchemy〉）。
- **正式環境的慢查詢**：用 `log_min_duration_statement` 只記慢的語句；要看哪些查詢加總起來最耗時，PostgreSQL 的 `pg_stat_statements` 依查詢形狀彙總次數與總耗時，比逐筆記錄省空間。把慢查詢記錄定期彙整、接進審查流程的做法見 [1.14 Production Slow Log Closed Loop](/backend/01-database/production-slow-log-loop/)。

## 設計責任

開發與測試環境把兩種記錄都打開，審查 ORM 程式碼時對照的是它們，不只是方法呼叫。正式環境的 `log_statement = 'all'` 與應用程式端的逐筆記錄量都很大，而且參數裡有 email、地址這類個人資料，所以正式環境通常只記慢查詢與 DDL，記錄的保存與遮罩比照其他含個資的記錄處理（見 [7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)）。追查「這一筆資料被誰改過」用 [Audit Log](/backend/knowledge-cards/audit-log/)（PostgreSQL 端可以用 pgaudit 擴充記錄指定的語句類別）；語句記錄保存期短、正式環境不一定開著，靠不住。
