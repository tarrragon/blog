---
title: "Write Skew（寫入偏斜）"
date: 2026-11-12
description: "兩筆寫入各自合法、合起來卻違反業務條件（班表重疊、值班時段沒人、合計超過上限），或要判斷一條跨好幾列的規則能不能靠觸發器或應用程式檢查守住時"
weight: 502
tags: ["backend", "database", "transaction", "concurrency", "knowledge-card"]
---

寫入偏斜（write skew）指兩個交易各自讀過同一個條件、判定成立之後寫入**不同的列**，每一筆寫入單獨看都合法，合起來違反那個條件的異常。典型的例子是排班：規則是同一位員工的兩段班不能重疊，兩個交易同時插入 09:00–18:00 與 13:00–22:00，各自查詢時都看不到對方還沒提交的那一段，兩筆都寫進去。它跟 [Lost Update（遺失更新）](/backend/knowledge-cards/lost-update/) 同樣出自 [Check-then-act（先讀後寫）](/backend/knowledge-cards/check-then-act/)。

## 跟其他概念的關係

遺失更新指兩個交易寫同一筆資料、後寫的覆蓋先寫的；寫入偏斜指兩個交易寫的是不同的列，沒有任何一列被覆蓋，所以只鎖住讀到的列擋不住它：衝突的那一列在讀的時候還不存在。擋得住的做法有兩種。[Serialization Failure](/backend/knowledge-cards/serialization-failure/) 那一路是 `SERIALIZABLE` 隔離等級，伺服器追蹤交易之間的讀寫相依，讓其中一個失敗；[Isolation Level](/backend/knowledge-cards/isolation-level/) 的 `REPEATABLE READ`（快照隔離）擋不住寫入偏斜，這是它跟 `SERIALIZABLE` 的主要差別。另一路是把條件寫成約束，例如 PostgreSQL 的 [Exclusion Constraint（排除約束）](/backend/01-database/sql/knowledge-cards/exclusion-constraint/)，由索引在寫入時檢查。

## 可觀察訊號與例子

訊號是資料裡出現規則不允許的組合，而每一筆的寫入紀錄都正常：同一間會議室同一時段兩筆預約、值班表某個時段一個人都沒有（兩位值班人員同時請假，各自查到「還有另一位在班」）、同一人一個月的請假合計超過上限。這類錯誤在依序執行的測試裡不會出現；規則由觸發器或應用程式「先查再插入」檢查時，SQL 分類 [SQL.20 引擎的部署形態與 SQL 構造](/backend/01-database/sql/deployment-shape-and-sql-constructs/) 實測了同一個觸發器在 PostgreSQL `READ COMMITTED` 下讓兩段重疊的班都提交。

## 判斷條件與後果

條件能寫成「某幾欄的組合不能同時成立」時（重疊、重複），排除約束或唯一鍵把檢查交給資料庫，後到的交易等前一個提交後被拒，並行的時序不影響結果。條件是幾列的合計或存在與否（合計不超過上限、至少一人在班）時寫不成約束，`SERIALIZABLE` 讓既有的檢查不必改就成立，代價是衝突時整個交易失敗、應用程式要重試，失敗可能發生在任何一句或提交時。只靠應用程式或觸發器檢查、又沒有序列化寫入時，規則只在請求依序到達時成立；寫入在資料庫層被排成一個接一個時（SQLite 的寫入鎖加上 `BEGIN IMMEDIATE`、或所有寫入都經過單一的寫入者），同一套檢查是正確的，容量上限由那個序列化點決定，見 [Single Writer Model](/backend/knowledge-cards/single-writer-model/)。
