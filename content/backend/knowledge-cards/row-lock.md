---
title: "Row Lock（列鎖）"
date: 2026-11-12
description: "看到 SELECT … FOR UPDATE、SKIP LOCKED、NOWAIT，或兩個交易更新同一列時一個在等另一個、工作佇列的 worker 互相卡住或重複認領時"
weight: 505
tags: ["backend", "database", "transaction", "concurrency", "lock", "knowledge-card"]
---

列鎖（row lock）是資料庫在交易修改某一列時替那一列上的鎖：其他要修改同一列的交易等它提交或回滾才能繼續，讀取在 [MVCC（多版本並行控制）](/backend/knowledge-cards/mvcc/) 下不受影響。`UPDATE`、`DELETE` 會自動替改到的列上鎖；`SELECT … FOR UPDATE` 讓讀取也替讀到的列上鎖，交易結束時釋放。鎖的範圍只有那幾列，跟鎖住整個資料庫寫入的 [Single Writer Model](/backend/knowledge-cards/single-writer-model/) 不同。

## 跟其他概念的關係

`FOR UPDATE` 遇到已經被鎖住的列時有三種行為：預設等待；`NOWAIT` 立刻回錯誤；`SKIP LOCKED` 跳過那一列、挑下一列，常用在多個 worker 從同一張表認領工作。列鎖保護的是讀到的那幾列，所以擋得住 [Lost Update（遺失更新）](/backend/knowledge-cards/lost-update/)（兩個交易寫同一列），擋不住 [Write Skew（寫入偏斜）](/backend/knowledge-cards/write-skew/)（衝突的那一列在讀的時候還不存在）。[Advisory Lock（建議鎖）](/backend/knowledge-cards/advisory-lock/) 指只有數字、不綁任何列、意義由應用程式約定的鎖；列鎖指綁在資料列上、由資料庫在寫入時自動取得的鎖。[Metadata Lock](/backend/knowledge-cards/metadata-lock/) 是 schema 層的鎖，DDL 等的是它。

## 可觀察訊號與例子

PostgreSQL 的 `pg_stat_activity` 裡 `wait_event_type` 是 `Lock`、`pg_locks` 顯示 `transactionid` 等待時，是交易在等另一個交易的列鎖。工作佇列是典型的例子：worker 用 `UPDATE job SET worker = … WHERE id = (SELECT id … LIMIT 1)` 認領時，第二個 worker 等第一個的列鎖，第一個提交後 `READ COMMITTED` 只重新檢查外層條件，兩個 worker 可能認領到同一筆；子查詢加 `FOR UPDATE SKIP LOCKED` 之後，第二個 worker 不等待、直接拿下一筆。SQL 分類 [SQL.20 引擎的部署形態與 SQL 構造](/backend/01-database/sql/deployment-shape-and-sql-constructs/) 有這幾種寫法在 PostgreSQL 16 上的實測；SQLite 沒有列鎖，`FOR UPDATE` 是語法錯誤。

## 判斷條件與後果

交易要搶先拿到某一列、再依它的狀態做幾步時，`FOR UPDATE` 讓那一列在交易結束前只屬於這個交易，其他寫入者等待；多個寫入者要各拿不同的列時，`SKIP LOCKED` 把等待換成跳過，worker 之間不互相卡住，代價是被鎖住的那一列這一輪沒人處理。鎖持有的時間等於交易的長度：交易裡包含外部 API 呼叫或耗時數秒的工作時，列鎖與連線在整段時間停在 `idle in transaction`，其他等這一列的交易一起變慢，這時認領要寫成自動提交的單句、在列上記下認領者與時間，耗時的工作放在交易之外。兩個交易以相反的順序鎖兩列時會互相等待，資料庫偵測到死結後讓其中一個失敗，固定的上鎖順序避開這種情形。
