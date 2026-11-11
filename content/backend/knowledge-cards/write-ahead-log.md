---
title: "Write-Ahead Log"
date: 2026-05-22
description: "說明資料庫如何先寫入 log 再合併回主資料，以提供持久性與崩潰復原"
weight: 324
---

Write-Ahead Log（WAL）的核心概念是把每筆寫入先 append 到一個循序 log，再由背景程序合併回主要資料檔。這個順序讓資料庫在 crash 後能用 log 重放回到一致狀態，也讓 reader 與 writer 的衝突降低。WAL 是 [Single Writer Model](/backend/knowledge-cards/single-writer-model/) 的持久化基礎、是 [Replication Slot](/backend/knowledge-cards/replication-slot/) 與 [Change Data Capture](/backend/knowledge-cards/change-data-capture/) 的事件來源，累積的 log 由 [Checkpoint](/backend/knowledge-cards/checkpoint/) 收斂。

## 跟其他概念的關係

WAL 位在資料庫的 durability 與 recovery 機制核心。SQLite 的 WAL mode、PostgreSQL 的 WAL、MySQL InnoDB 的 redo log 都是同一個 write-ahead 原則的實作。它和記錄業務歷史的 [Event Log](/backend/knowledge-cards/event-log/) 是不同層：WAL 是引擎內部的 recovery 結構，[Event Log](/backend/knowledge-cards/event-log/) 是應用層可重播的事件流。

## 可觀察訊號與例子

需要理解 WAL 的訊號是寫入延遲、磁碟用量或 crash recovery 時間出現異常。WAL 檔持續長大通常代表 checkpoint 落後，或有長交易、inactive replication slot 卡住 log 回收；crash 後啟動變慢通常代表要重放的 WAL 區段過大。電商在尖峰寫入時若 WAL 成長速度超過 checkpoint，磁碟會先到上限。

## 判斷條件與後果

WAL 的保留長度同時被 crash recovery、replication 與 CDC 三條路徑依賴，太短與太長各有代價。保留太短時，落後的 replica 或 [Replication Slot](/backend/knowledge-cards/replication-slot/) 需要的 log 已被回收，replica 要整份重建、CDC 漏掉事件；保留太長、或 inactive slot 卡住回收時，WAL 持續佔用磁碟，尖峰寫入下磁碟先到上限，資料庫無法再寫入。checkpoint 頻率決定 crash 後要重放多少 log：間隔越長，crash recovery 越久。所以 observability 看 WAL 生成速率、checkpoint lag 與最舊仍被保留的 log 位置，三項分別對應磁碟成長的速度、recovery 要重放的量，以及回收被誰卡住。
