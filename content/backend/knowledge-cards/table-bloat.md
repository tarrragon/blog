---
title: "Table Bloat（表膨脹與 VACUUM）"
date: 2026-10-06
description: "大量更新或刪除之後表的檔案沒有變小、autovacuum 越跑越久、或查詢讀的頁數比資料量該有的多時，查舊版本的列怎麼累積、VACUUM 與 VACUUM FULL 各拿回什麼，以及大表要量的清理指標"
weight: 466
tags: ["backend", "database", "postgresql", "vacuum", "knowledge-card"]
---

Table bloat 是表的檔案比實際資料大的狀態，多出來的是不再被任何交易需要的舊版本列，以及這些舊版本清掉之後留在檔案裡、還沒還給作業系統的空間。PostgreSQL 的 `UPDATE` 不在原位修改，而是寫入一份新版本、舊版本留在原處，`DELETE` 也只是把列標成已刪除；舊版本由 `VACUUM`（平常由 autovacuum 自動執行）清理。一般的 `VACUUM` 讓那些空間可以被之後的寫入重用，檔案通常不會變小（只有檔案尾端整頁都空出來時才截掉）；`VACUUM FULL` 重寫整張表才把空間還給作業系統，執行期間整張表被鎖住。它是 PostgreSQL 多版本並行控制（MVCC，讓讀取不必等寫入的機制）的成本；每個新版本另外也會寫進 [Write-Ahead Log](/backend/knowledge-cards/write-ahead-log/)。表變大之後清理成本怎麼影響擴充的判斷，見 [1.19 資料表長期成長的成本](/backend/01-database/table-growth-query-cost/)。其他中文資料常寫作表膨脹或資料表肥大。

## 概念位置

| 動作               | 拿回的空間                                                                 | 鎖                                                                                                                                   |
| ------------------ | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `VACUUM`           | 表內可重用，檔案大小通常不變                                               | 不擋讀寫                                                                                                                             |
| `VACUUM FULL`      | 檔案縮回實際資料大小；要有約一份表加索引大小的空閒磁碟                     | 整張表擋讀寫，直到結束                                                                                                               |
| `pg_repack` 等工具 | 同 `VACUUM FULL`，線上重寫；同樣要空閒磁碟，表要有主鍵或非 NULL 的唯一索引 | 開始與結束各短暫取一次排他鎖，期間擋 DDL                                                                                             |
| 刪除整個分割區     | 整個分割區的空間，不留舊版本                                               | 對父表取排他鎖：持有很短，但要排在進行中的查詢後面、並擋住排在它後面的查詢；PostgreSQL 14 起可先 `DETACH PARTITION ... CONCURRENTLY` |

依時間分割的表用刪除分割區取代逐筆刪除，就是為了不產生要清理的舊版本，見 [Table Partitioning](/backend/knowledge-cards/table-partitioning/)。MySQL（InnoDB）把更新的舊版本放在 undo log，主表不會因為更新這樣膨脹，對應的成本是長交易讓 undo log 變大；刪除之後空出的空間同樣留在表的檔案裡，要 `OPTIMIZE TABLE` 才還給作業系統。

**HOT 更新**（heap-only tuple）是 PostgreSQL 減少膨脹的機制：更新沒有改到任何有索引的欄位、而且原來那一頁還有空位時，新版本寫在同一頁，索引不必新增一筆。大量寫入之後頁面通常是滿的，這時每個新版本都放到別的頁、每一個索引都要再寫一筆，索引跟著膨脹；預期會更新的表可以調低 `fillfactor`，讓每頁預留空位。`pg_stat_user_tables` 的 `n_tup_hot_upd` 與 `n_tup_upd` 相比，看得出有多少更新走了 HOT。

## 可觀察訊號與例子

- **大量更新之後表變大**：一次 `UPDATE` 改了大部分的列，表增加的大小約等於新版本的總大小，新版本與原列一樣寬時接近原來的兩倍。實測在一份沒有索引的表上，把 200 萬列裡 198 萬列約 120 字元的網址改成 NULL，表從 386 MB 變成 536 MB（新版本比原列窄，所以不到兩倍），`VACUUM` 之後仍是 536 MB，`VACUUM FULL` 之後是 156 MB。表上有索引時，沒走 HOT 的更新讓索引一起變大。
- **autovacuum 越跑越久**：`log_autovacuum_min_duration` 在 PostgreSQL 15 起預設 `10min`，只記超過十分鐘的清理（更早的版本預設不記），調低之後看得到同一張表每一輪的耗時跟著表的大小增加；`pg_stat_user_tables` 的 `n_dead_tup` 長時間居高不下，代表清理追不上更新。
- **清理被擋住**：有交易開著很久沒結束時，它開始之後才變成舊版本的列都不能清，因為那個交易可能還要讀它們；長交易的其他代價見 [1.13 應用層查詢反模式與 Query 預算](/backend/01-database/query-anti-patterns/)〈Long-Running Transaction〉。

## 設計責任

大批改寫既有資料（回填、遷移）之前先估膨脹：分批更新、批與批之間讓 `VACUUM` 跑，空間可以在表內重用；要縮回檔案大小，事先排定 `VACUUM FULL` 的停機時間或改用線上重寫工具。不刪除、只會一直變大的表，把 autovacuum 的耗時列為擴充的觸發指標之一。
