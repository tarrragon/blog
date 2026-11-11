---
title: "Embedded Database"
date: 2026-05-22
description: "說明嵌入式資料庫如何隨 application process 運作，並把檔案生命週期責任交回應用"
weight: 330
---

Embedded Database 的核心概念是資料庫以 library 形式嵌入 application process，與應用共用同一個 process。它讓部署簡單、讀寫沒有網路往返，代價是 backup、locking、durability 與 corruption recovery 的責任從 DBA 回到 application process 與檔案系統。SQLite 是典型例子，它和 [Single Writer Model](/backend/knowledge-cards/single-writer-model/)、[Local-First](/backend/knowledge-cards/local-first/) 一起定義這類系統的邊界。

## 跟其他概念的關係

Embedded Database 位在 [Database](/backend/knowledge-cards/database/) 這個傘狀概念下、與 server-side database 相對的一端。server-side database 有獨立 process、連線協定與營運團隊；embedded database 的 production boundary 在裝置與檔案生命週期 — 資料庫的可用性等同那個檔案與那個 [Single Writer Model](/backend/knowledge-cards/single-writer-model/) process 的可用性。

## 可觀察訊號與例子

適合 embedded database 的訊號是單一 process 內的本地狀態、測試 fixture、桌面或行動 app 的本地儲存，或邊緣節點上讀多寫少的資料。需要重新評估的訊號是多個 process 或多台機器要同時寫同一份資料 — 那已超出 embedded database 加 single writer 的設計範圍。

## 判斷條件與後果

Embedded database 沒有 DBA 與獨立的資料庫 process，檔案的 owner、backup、崩潰復原與並發寫入的邊界沒有指定時，這幾項責任沒有任何一方承擔。直接複製一個正在寫入的資料庫檔時，複本可能停在寫入中途，還原後讀不出完整的資料，原因是檔案複製不知道資料庫的交易邊界；backup 因此要在一致的時點取。檔案已經 corruption 時直接在原檔上修，修壞了就沒有原檔可以重試，所以先保全原檔再修。多個 process 或多台機器要寫同一份資料時，已經超出 embedded database 加 single writer 的設計範圍，資料的同步是另一個設計主題，由 [Local-First](/backend/knowledge-cards/local-first/) 與 [Conflict Resolution](/backend/knowledge-cards/conflict-resolution/) 處理。
