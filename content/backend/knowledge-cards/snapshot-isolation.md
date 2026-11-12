---
title: "Snapshot Isolation（快照隔離）"
date: 2026-11-12
description: "讀到 PostgreSQL 的 REPEATABLE READ、Oracle 的 SERIALIZABLE、SSI，或交易回 could not serialize access due to concurrent update、SQLite 回 SQLITE_BUSY_SNAPSHOT，想知道一個交易整段讀到的是哪一刻的資料、擋得住哪些並發異常時"
weight: 506
tags: ["backend", "database", "transaction", "concurrency", "knowledge-card"]
---

快照隔離是一種[隔離等級](/backend/knowledge-cards/isolation-level/)：交易的所有讀取都來自同一份快照（交易開始讀取那一刻已經提交的資料），整段交易看不到別人在這之後提交的寫入；兩個並行的交易改到同一列時，先提交的成功，後提交的失敗。它通常建在 [MVCC（多版本並行控制）](/backend/knowledge-cards/mvcc/) 上：每一列保留多個版本，快照決定讀哪一個。PostgreSQL 的 `REPEATABLE READ` 就是快照隔離，Oracle 名為 `SERIALIZABLE` 的等級，行為也是快照隔離。

## 跟其他概念的關係

快照隔離擋得住 [Lost Update（遺失更新）](/backend/knowledge-cards/lost-update/)：兩個交易都讀到舊值、都要改同一列時，後到的那一個在寫入或提交時失敗（PostgreSQL 回 `could not serialize access due to concurrent update`，SQLSTATE `40001`），不會默默蓋掉。它擋不住 [Write Skew（寫入偏斜）](/backend/knowledge-cards/write-skew/)：兩個交易寫的是不同的列，沒有任何一列被兩邊同時改，快照隔離的衝突檢查看不到這一類，兩邊都會提交。Serializable Snapshot Isolation（SSI，PostgreSQL 的 `SERIALIZABLE`）在快照隔離上再追蹤交易之間的讀寫相依，偵測到寫入偏斜這種形狀時讓其中一個以 [Serialization Failure](/backend/knowledge-cards/serialization-failure/) 失敗。

快照隔離指交易讀取資料時用的一致時間點；備份的 snapshot 指某一刻整個磁碟或資料庫的複本，事件溯源的 snapshot 指聚合狀態的存檔點，三者是不同所指。

## 可觀察訊號與例子

PostgreSQL 預設的 `READ COMMITTED` 每一句取一次快照；改成 `REPEATABLE READ` 之後，同一個交易裡先後執行的兩次 `SELECT` 讀到相同的資料，長時間的報表交易在整段期間看到一致的數字。代價的訊號是 `40001` 的錯誤開始出現：兩個請求同時讀出同一筆餘額再寫回時，後寫入的那一個失敗，應用程式要重試整個交易。SQLite 的 WAL 模式也給讀取交易一份快照：交易用預設的 `BEGIN` 開始、先讀再寫時，若讀完之後別的連線已經提交了寫入，這個交易的快照過期，升級成寫入時直接回 `SQLITE_BUSY_SNAPSHOT`，不等 busy timeout，成因與處理在 [SQLite WAL Concurrency and Locking](/backend/01-database/vendors/sqlite/wal-concurrency-locking/) 的〈先讀後寫的交易〉。

## 判斷條件與後果

交易需要整段讀到一致的資料（多張表的對帳、報表、匯出）時，快照隔離提供這個保證，代價是長交易讓 MVCC 的舊版本留得更久、回收延後。交易要保護的是「兩筆寫入不能同時改同一列」時，快照隔離足夠，衝突以 `40001` 回報，應用程式要準備重試。要保護的是跨好幾列的條件（班表不重疊、值班至少一人、合計不超過上限）時，快照隔離不夠，兩個交易各自看到的快照都滿足條件，寫入後合起來違反；這時要用 SSI、把條件寫成約束，或讓寫入一個接一個執行。同樣寫成 `REPEATABLE READ`，各家的語意不同：MySQL InnoDB 的一般讀取用快照，`UPDATE` 與 `SELECT … FOR UPDATE` 卻讀最新版本，先讀後寫在應用程式裡算好值再寫回時仍可能遺失更新，所以換資料庫時要依各家文件重新確認這個等級擋得住哪些異常。
