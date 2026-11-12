---
title: "MVCC（多版本並行控制）"
date: 2026-11-12
description: "讀到「PostgreSQL 的讀不擋寫」「快照看不到別人還沒提交的資料」「dead tuple 與 vacuum」，或想知道兩個並行的交易各自看到資料的哪一個版本時"
weight: 504
tags: ["backend", "database", "transaction", "concurrency", "knowledge-card"]
---

MVCC（multi-version concurrency control，多版本並行控制）讓資料庫為每一列保留多個版本：更新不覆蓋原來那一列，而是寫一個新版本，舊版本留到沒有交易還需要它為止。每個讀取依一份**快照**（某一刻已經提交的資料）挑出它看得到的版本，所以讀取不必等寫入、寫入也不必等讀取。PostgreSQL、MySQL InnoDB、Oracle 都用這種方式；隔離語意由 [Isolation Level](/backend/knowledge-cards/isolation-level/) 決定快照在什麼時候取。

## 跟其他概念的關係

快照在什麼時候取，決定了交易看得到哪些別人的寫入：PostgreSQL 預設的 `READ COMMITTED` 在每一句開始時取，同一個交易的兩句可能讀到不同的資料；`REPEATABLE READ` 在交易的第一句取，整個交易讀同一份。MVCC 只解決讀與寫之間的等待，兩個交易要寫同一列時仍然靠 [Row Lock（列鎖）](/backend/knowledge-cards/row-lock/) 排隊；讀到舊快照再依它寫入，正是 [Check-then-act（先讀後寫）](/backend/knowledge-cards/check-then-act/) 在並行下出錯的原因。舊版本要定期回收，回收跟不上時就是 [Table Bloat](/backend/knowledge-cards/table-bloat/)。站上另有一張事件溯源的 snapshot 卡（ddd 模組），那個 snapshot 指聚合狀態的存檔點，跟這裡的讀取快照是不同所指。

## 可觀察訊號與例子

讀取在大量寫入時仍然不等待、長時間的報表查詢不擋住線上寫入，是 MVCC 的效果。代價的訊號是表與索引的實際大小遠大於資料量、`idle in transaction` 的長交易讓 vacuum 回收不了舊版本。在 PostgreSQL 上，一個交易的觸發器查不到另一個交易還沒提交的列，因為那一列的版本不在它的快照裡；SQL 分類 [SQL.20 引擎的部署形態與 SQL 構造](/backend/01-database/sql/deployment-shape-and-sql-constructs/) 的班表實測，兩筆重疊的班都通過觸發器檢查，原因就在這裡。機制的細節（xmin、xmax、可見性規則）在 [PostgreSQL MVCC + Lock Model](/backend/01-database/vendors/postgresql/mvcc-lock-model/)。

## 判斷條件與後果

讀多寫多、而且讀取不能被寫入擋住時，MVCC 換到的是讀寫互不等待，付出的是舊版本佔用的空間與回收它的背景工作；長交易存在時，回收被卡住，空間與查詢時間一起成長。交易的正確性依賴「讀到的資料到寫入時還成立」時，MVCC 的快照不保證這件事：快照只決定讀到哪個版本，讀完之後別人提交的寫入不會讓這次讀取失效，所以這類交易要另外靠列鎖、約束或 `SERIALIZABLE` 的衝突偵測。SQLite 的 WAL 模式也讓讀取者看到一份一致的版本、不擋寫入，但同一時間只有一個寫入者，寫入之間的衝突由寫入鎖排隊處理，見 [Single Writer Model](/backend/knowledge-cards/single-writer-model/)。
