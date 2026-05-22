---
title: "Embedded Database"
date: 2026-05-22
description: "說明嵌入式資料庫如何隨 application process 運作，並把檔案生命週期責任交回應用"
weight: 329
---

Embedded Database 的核心概念是資料庫以 library 形式嵌入 application process，與應用共用同一個 process。它讓部署簡單、讀寫沒有網路往返，代價是 backup、locking、durability 與 corruption recovery 的責任從 DBA 回到 application process 與檔案系統。SQLite 是典型例子，它和 [Single Writer Model](/backend/knowledge-cards/single-writer-model/)、[Local-First](/backend/knowledge-cards/local-first/) 一起定義這類系統的邊界。

## 概念位置

Embedded Database 位在 [Database](/backend/knowledge-cards/database/) 這個傘狀概念下、與 server-side database 相對的一端。server-side database 有獨立 process、連線協定與營運團隊；embedded database 的 production boundary 在裝置與檔案生命週期 — 資料庫的可用性等同那個檔案與那個 [Single Writer Model](/backend/knowledge-cards/single-writer-model/) process 的可用性。

## 可觀察訊號與例子

適合 embedded database 的訊號是單一 process 內的本地狀態、測試 fixture、桌面或行動 app 的本地儲存，或邊緣節點上讀多寫少的資料。需要重新評估的訊號是多個 process 或多台機器要同時寫同一份資料 — 那已超出 embedded database 加 single writer 的設計範圍。

## 設計責任

設計時要明確指認檔案的 owner、backup 方式、崩潰後的復原流程與並發寫入的邊界。backup 要在一致的時點取，避免複製到寫入中途的檔案；corruption 要先保全原檔再修復。要跨裝置或跨節點共享資料時，要把同步當成獨立問題，接回 [Local-First](/backend/knowledge-cards/local-first/) 與 [Conflict Resolution](/backend/knowledge-cards/conflict-resolution/)。
