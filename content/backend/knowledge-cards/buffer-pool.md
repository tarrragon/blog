---
title: "Buffer Pool"
date: 2026-05-22
description: "說明資料庫如何用記憶體快取磁碟頁，以降低 I/O 並影響查詢效能"
weight: 348
---

Buffer Pool 的核心概念是資料庫在記憶體中快取磁碟上的資料頁，讓重複存取的資料不必每次讀磁碟。它是資料庫最主要的記憶體消耗者，命中率直接決定查詢要走記憶體還是 I/O。它是全域共用的快取，和每條連線各自配置的 [Per-Connection Memory](/backend/knowledge-cards/per-connection-memory/) 是兩種不同的記憶體。

## 跟其他概念的關係

Buffer Pool 位在資料庫的儲存與運算之間。MySQL 的 InnoDB buffer pool、PostgreSQL 的 shared buffers 都是同一個概念 — 磁碟頁的記憶體快取。它的更新搭配 [Write-Ahead Log](/backend/knowledge-cards/write-ahead-log/)：變更先發生在 buffer pool 的頁面上、寫入 WAL，再由 checkpoint 落回磁碟。容量不足時要決定哪些頁被換出，接回 [Eviction](/backend/knowledge-cards/eviction/)。

## 可觀察訊號與例子

觀察 buffer pool 的關鍵指標是命中率：命中率高代表多數讀取走記憶體，命中率掉代表查詢開始打磁碟、延遲上升。常見場景是資料量成長超過 buffer pool 大小，熱資料放不下、頁面頻繁換進換出，查詢延遲整體升高。這時要評估加大 buffer pool 或縮小工作集。

## 判斷條件與後果

Buffer pool 和 per-connection 記憶體、作業系統共用同一台機器的記憶體。熱資料工作集大於 buffer pool 時，頁面頻繁換進換出，查詢從記憶體退回磁碟 I/O，延遲整體升高；buffer pool 調大到擠壓連線與作業系統的記憶體時，連線數一上升，機器記憶體就不足，代價從查詢變慢換成資料庫程序被終止或作業系統開始 swap。三個指標各自指出一種狀態：命中率下降代表工作集放不下，換頁速率上升代表頁面正在換進換出，dirty page 比例偏高代表還沒落回磁碟的變更在累積，checkpoint 的寫入量會跟著增加。
