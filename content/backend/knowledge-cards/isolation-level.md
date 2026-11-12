---
title: "Isolation Level"
date: 2026-04-23
description: "說明資料庫交易隔離等級如何影響並發讀寫結果"
weight: 17
tags: ["backend", "database", "transaction", "concurrency", "knowledge-card"]
---

Isolation level 的核心概念是「交易彼此看見資料變更的規則」。隔離等級越高，越能降低並發異常；同時也可能增加鎖競爭、等待與重試成本。多數資料庫用 [MVCC（多版本並行控制）](/backend/knowledge-cards/mvcc/) 實作它：隔離等級決定讀取用的快照在什麼時候取。

## 跟其他概念的關係

隔離等級處理的是同一份資料被多個交易同時讀寫時的行為。常見問題包括 dirty read、non-repeatable read、phantom read、[Lost Update（遺失更新）](/backend/knowledge-cards/lost-update/) 與 [Write Skew（寫入偏斜）](/backend/knowledge-cards/write-skew/)；後兩者都出自[先讀後寫](/backend/knowledge-cards/check-then-act/)的交易，各隔離等級是否擋得住它們，寫在各自的卡上。不同資料庫的預設隔離與實作細節不同：PostgreSQL 預設 `READ COMMITTED`（每一句取一次快照），`REPEATABLE READ` 是 [Snapshot Isolation（快照隔離）](/backend/knowledge-cards/snapshot-isolation/)（整個交易用同一份快照），`SERIALIZABLE` 再加上讀寫相依的衝突偵測；MySQL InnoDB 預設 `REPEATABLE READ`，語意跟 PostgreSQL 的同名等級不同。

## 可觀察訊號與例子

系統需要討論隔離等級的訊號是高併發更新同一類資料。兩個使用者同時搶最後一件庫存、兩個 worker 同時認領同一筆工作、兩個後台操作同時修改權限，都需要明確的一致性策略。SQLite 沒有可選的隔離等級：寫入交易一個接一個執行，WAL 模式下的讀取交易用一份快照；交易用預設的 `BEGIN` 開始、先讀再寫而快照已經過期時，升級成寫入那一刻直接回 `SQLITE_BUSY_SNAPSHOT`，這是快照隔離在單一寫入者引擎上的表現形式。

## 判斷條件與後果

同一份資料被多個交易同時讀寫時，可以接受哪些並發結果（兩個使用者同時搶最後一件庫存，是否容許超賣）決定了該用哪一種工具：transaction、lock、unique constraint、optimistic concurrency 或 retry。沒有先定義可接受的結果就選隔離等級時，可能選得太低而留下遺失更新或寫入偏斜，也可能選得太高，付出鎖競爭、等待與重試的成本，換到的保證卻不是業務需要的那一種。隔離等級只規定交易彼此看見哪些變更，而不同資料庫的預設隔離與實作細節不同，只靠它表達的業務規則換一個資料庫就可能改變行為；寫成狀態機與唯一約束的正式規則落實在資料上，換了資料庫或隔離等級也照樣成立。
