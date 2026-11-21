---
title: "Lock Queue（鎖的等待佇列）"
date: 2026-11-21
description: "跑一個瞬間完成的 ALTER 之後整張表的查詢一起變慢、在 pg_stat_activity 看到一串 Lock / relation 等待時，查等鎖的請求怎麼排隊、為什麼排在 DDL 後面的普通 SELECT 也要等"
weight: 508
tags: ["backend", "database", "postgresql", "mysql", "lock", "schema migration", "knowledge-card"]
---

Lock Queue（鎖的等待佇列）是資料庫替同一個物件（一張表）上還拿不到鎖的請求排的順序：新來的請求要的鎖跟佇列裡還在等的請求衝突時，排在它後面，即使它跟目前持有鎖的交易並不衝突。PostgreSQL 的表鎖照這個順序發放，`ALTER TABLE` 預設要的 `ACCESS EXCLUSIVE` 跟所有鎖衝突，所以它在佇列裡等一筆長交易時，之後每一個要 `ACCESS SHARE` 的 `SELECT` 都排在它後面；MySQL 的 [Metadata Lock](/backend/knowledge-cards/metadata-lock/) 在 DDL 等待 exclusive metadata lock 時有同樣的行為。這個佇列讓 [Schema Migration](/backend/knowledge-cards/schema-migration/) 裡一個本身瞬間完成的 DDL，擋住整張表的讀取。

## 跟其他概念的關係

Lock Queue 描述的是等鎖的順序，跟鎖的種類是兩回事：PostgreSQL 的表鎖、MySQL 的 [Metadata Lock](/backend/knowledge-cards/metadata-lock/) 各自定義哪些鎖互相衝突，佇列決定衝突時誰先拿到。造成排隊的源頭通常是一筆還沒結束的交易，交易開多久由 [Transaction Boundary](/backend/knowledge-cards/transaction-boundary/) 決定；要限制排隊的時間，是在套用 migration 的 session 裡設等鎖的上限，或改用 [Online Migration](/backend/knowledge-cards/online-migration/) 那一類不長時間持有強鎖的做法。資料列層級的 [Row Lock](/backend/knowledge-cards/row-lock/) 也會排隊，但只擋同一列的寫入，影響範圍小得多。

## 可觀察訊號與例子

PostgreSQL 上，`pg_stat_activity` 裡 `ALTER` 與一串普通查詢的 `wait_event_type` 都是 `Lock`、`wait_event` 是 `relation`，`pg_blocking_pids()` 對那些查詢回報的是 `ALTER` 的 pid，對 `ALTER` 回報的是那筆長交易的 pid。實測一張只有兩列的表：一筆交易讀過表之後 6 秒不結束，接著送一個只改 catalog 的加欄位 `ALTER`，再送一個 `SELECT count(*)`，`ALTER` 等了約 5 秒、`SELECT` 等了約 4 秒；量測的步驟在 [goose 管理 PostgreSQL migration 的實測紀錄](/programming/go/basic/10-database-access/hands-on/goose-migration-lab/)〈長交易、排隊的 ALTER 與 lock_timeout〉。常見的情境是部署時跑 migration，剛好有一支報表查詢或一個忘了提交的交易，服務的讀寫延遲在 migration 開始的那一刻一起升高。

## 判斷條件與後果

排隊的時間取決於佇列前面的交易什麼時候結束，跟表的大小無關，所以小表的 `ALTER` 也會擋住讀取。等鎖沒有上限時（PostgreSQL 的 `lock_timeout` 預設 0，MySQL 的 `lock_wait_timeout` 預設一年），`ALTER` 一直排在佇列裡，後面的查詢跟著等到長交易結束；在套用 migration 的 session 設 `lock_timeout` 之後，`ALTER` 等滿上限就失敗退出、離開佇列，後面的查詢恢復執行，代價是那一份 migration 要重試，實測設 1 秒時 `SELECT` 只等了 678 ms。有讀取副本時，副本重做 DDL 也要取同一把鎖，副本上的查詢會再排一次隊，主庫的 `lock_timeout` 管不到那一段，見 [1.20 Schema 變更由誰寫出、何時套用](/backend/01-database/schema-change-management/)〈同一個 ALTER 在大表上的代價〉。
