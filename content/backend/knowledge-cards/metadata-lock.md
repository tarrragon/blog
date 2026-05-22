---
title: "Metadata Lock"
date: 2026-05-22
description: "說明 DDL 與既有交易如何在 table metadata 層互相排隊與阻塞"
weight: 324
---

Metadata Lock 的核心概念是資料庫為了保護 table 結構，在 DDL 與既有交易之間建立的相容鎖。任何讀寫某張表的交易都會持有該表的 metadata 讀鎖，DDL 需要 metadata 寫鎖；當一個長交易尚未結束，DDL 會排隊等待，而排在 DDL 後面的新查詢也會一起被擋住。它和處理 row 層並發的 [Isolation Level](/backend/knowledge-cards/isolation-level/) 是不同層的鎖；要安全執行 schema 變更時要接回 [Schema Migration](/backend/knowledge-cards/schema-migration/) 與 [Online Migration](/backend/knowledge-cards/online-migration/)。

## 概念位置

Metadata Lock 位在 DDL workflow 與 DML transaction 的交界。MySQL 的 metadata lock、PostgreSQL 的 ACCESS EXCLUSIVE lock 都是同一類機制 — 它讓一個看似輕量的 ALTER 在有長交易時放大成全表查詢停滯。它和 [Transaction Boundary](/backend/knowledge-cards/transaction-boundary/) 直接相關：交易開得越久，越容易成為 DDL 的阻塞源。

## 可觀察訊號與例子

需要注意 metadata lock 的訊號是執行一個 ALTER 後，原本正常的查詢突然大量逾時或排隊。觀察 metadata lock 類系統表會看到 DDL 在等某個長交易、後面跟著一串 waiting 查詢。常見場景是部署期間跑 migration，剛好有一個忘了 commit 的交易或一個慢報表查詢，DDL 卡住、服務讀寫一起雪崩。

## 設計責任

設計 schema 變更要先定義 DDL window、lock wait timeout 與長交易的處理策略。安全做法是在低流量窗口執行、設定 DDL 逾時讓它快速失敗而非無限等待、並先找出與終止 blocker 交易。大表結構變更應改用 [Online Migration](/backend/knowledge-cards/online-migration/) 工具，把一次性鎖換成可控的漸進搬移。runbook 要能快速定位「DDL 在等誰」與「誰被 DDL 擋住」。
