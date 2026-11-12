---
title: "Lost Update（遺失更新）"
date: 2026-11-12
description: "兩個請求同時更新同一筆資料，其中一次的改動不見了而沒有任何錯誤，或要判斷一段先讀後寫的程式在並行下會不會蓋掉別人的寫入時"
weight: 501
tags: ["backend", "database", "transaction", "concurrency", "knowledge-card"]
---

遺失更新是兩個交易依同一份舊狀態各自算出新值、寫進同一筆資料，後寫的那一個把先寫的蓋掉，先寫的那一次改動因此消失的異常。它是 [Check-then-act（先讀後寫）](/backend/knowledge-cards/check-then-act/) 在並行下最常見的後果：餘額 15 的帳戶被兩個交易各扣 10，兩邊都讀到 15、各自寫入 5，最後餘額是 5，其中一次扣減不見了，而兩次寫入單獨看都合法，資料庫不回任何錯誤。

## 跟其他概念的關係

遺失更新與 [Write Skew（寫入偏斜）](/backend/knowledge-cards/write-skew/) 都出自先讀後寫，差別在寫入的對象：遺失更新指兩個交易寫同一筆資料、後寫的覆蓋先寫的；寫入偏斜指兩個交易寫不同的資料、每一筆單獨合法而合起來違反條件。會不會發生取決於 [Isolation Level](/backend/knowledge-cards/isolation-level/)：PostgreSQL 預設的 `READ COMMITTED` 不擋寫入算好的值的那種遺失更新，`REPEATABLE READ` 以上讓後到的交易回 [Serialization Failure](/backend/knowledge-cards/serialization-failure/)。[Row Lock（列鎖）](/backend/knowledge-cards/row-lock/) 是另一條路：讀的時候就鎖住那一列，後到的交易等前一個提交之後才讀得到。

## 可觀察訊號與例子

訊號是加總對不上而沒有錯誤紀錄：庫存或點數比預期多、計數器比實際事件少、同一筆工作被兩個 worker 都認領（第二個的寫入蓋掉第一個的）。這類錯誤只在兩個請求的讀與寫交錯時出現，依序送請求的測試永遠通過；兩條連線各自送完就提交的測試也多半跑成一前一後，要讓第一條寫完先不提交、第二條在這時讀，才重現得出來。SQL 分類 [SQL.20 引擎的部署形態與 SQL 構造](/backend/01-database/sql/deployment-shape-and-sql-constructs/) 有扣點數與工作佇列在 SQLite 與 PostgreSQL 上的實測。

## 判斷條件與後果

新值由應用程式讀出舊值、在程式裡算好再整個寫回（`SET balance = <算好的值>`）時，資料庫不知道這個值依賴哪一次讀取，隔離等級是 `READ COMMITTED` 時遺失更新就會發生。讀與寫能合成同一句帶條件的更新（`SET balance = balance - 10 WHERE id = ? AND balance >= 10`）時，資料庫在列鎖之後拿最新版本重新檢查條件，後到的交易更新 0 列而不是蓋掉，代價是應用程式要處理「更新 0 列」並決定重送或回報。判斷邏輯合不進單句時，讀的那一句加 `FOR UPDATE` 讓後到者等待、讀到新值再判斷，或提高隔離等級讓後到者失敗後重試；`FOR UPDATE` 把衝突變成等待，提高隔離等級把衝突變成重試，衝突頻繁時重試的成本較高。SQLite 上讀與寫在同一個以 `BEGIN IMMEDIATE` 開始的交易裡時，寫入鎖讓兩個交易一個接一個執行，遺失更新不會發生；讀在交易之外時照樣發生。
