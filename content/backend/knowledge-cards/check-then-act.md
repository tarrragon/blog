---
title: "Check-then-act（先讀後寫）"
date: 2026-11-12
description: "一段程式先查資料、依查到的結果決定要不要寫或寫什麼（領工作、扣庫存、檢查重複、檢查重疊），想知道它在多個請求同時執行時會不會出錯、要靠什麼保護時"
weight: 503
tags: ["backend", "database", "transaction", "concurrency", "knowledge-card"]
---

先讀後寫是一種交易的形狀：先讀資料、判斷條件，再依判斷的結果寫入。認領工作（查一筆還沒人領的工作再標成自己的）、扣點數（查餘額夠不夠再扣）、檢查重複打卡、檢查班表重疊都是這個形狀。它的正確性有一個隱含的前提：讀與寫之間沒有別的交易提交新的寫入。兩個交易交錯執行時這個前提不成立，後果是 [Lost Update（遺失更新）](/backend/knowledge-cards/lost-update/) 或 [Write Skew（寫入偏斜）](/backend/knowledge-cards/write-skew/)。「先讀後寫」不是業界固定的中文術語，英文文獻寫作 check-then-act 或 read-modify-write，本站以它指這個形狀。

## 跟其他概念的關係

先讀後寫是程式的形狀，遺失更新與寫入偏斜是它在並行下的兩種失效：寫同一筆資料時是遺失更新，寫不同的列而合起來違反條件時是寫入偏斜。保護它的機制分屬不同層：[Single Writer Model](/backend/knowledge-cards/single-writer-model/) 讓寫入一個接一個執行，前提自然成立；[Row Lock（列鎖）](/backend/knowledge-cards/row-lock/) 鎖住讀到的列；約束把條件交給資料庫在寫入時檢查；[Isolation Level](/backend/knowledge-cards/isolation-level/) 的 `SERIALIZABLE` 偵測衝突後讓其中一個交易以 [Serialization Failure](/backend/knowledge-cards/serialization-failure/) 失敗。它在並行下出錯時，英文文獻稱為 check-then-act race。

## 可觀察訊號與例子

同一段程式在 SQLite 與 PostgreSQL 上結果不同是常見的訊號。SQLite 只有一個寫入者：讀與寫在同一個以 `BEGIN IMMEDIATE` 開始（或第一句就寫入）的交易裡時，後到的交易等前一個提交才開始讀，結果正確；交易用預設的 `BEGIN` 開始、先 `SELECT` 再寫入時，後到者立刻回 `database is locked`，資料不會錯；讀在交易之外時（Python `sqlite3` 的預設行為），SQLite 上也會寫出重複。同一段程式搬到 PostgreSQL 預設的 `READ COMMITTED`，兩個交易可以同時進行，前兩種都變成靜靜地寫錯。兩家的實測在 SQL 分類 [SQL.20 引擎的部署形態與 SQL 構造](/backend/01-database/sql/deployment-shape-and-sql-constructs/)；SQLite 這一側的交易開始方式在 [SQLite WAL Concurrency and Locking](/backend/01-database/vendors/sqlite/wal-concurrency-locking/)。

## 判斷條件與後果

寫入者被排成一個接一個時（單一寫入者的資料庫、只有一條寫入連線、或所有寫入經過應用程式裡單一的寫入者），先讀後寫照寫就正確，代價是寫入量的上限由那個序列化點決定。寫入者並行時，正確性要寫進程式或資料庫：讀與寫能合成同一句帶條件的寫入時，條件由資料庫在寫入那一刻檢查；條件能寫成約束時，交給唯一鍵或排除約束；要先拿到某一列再做好幾步時，鎖住那一列；條件跨好幾列、寫不成約束時，用 `SERIALIZABLE` 加上整個交易的重試。四種做法把衝突分別變成「更新 0 列」「約束錯誤」「等待」「重試」，應用程式要處理的結果不同。
